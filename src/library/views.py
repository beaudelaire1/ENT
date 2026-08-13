from __future__ import annotations

from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from core.deletion import confirm_delete
from core.editing import form_page
from core.navigation import crumb, safe_next
from core.serving import serve_private_file
from formations.models import Competency, LearningUnit

from .forms import FolderForm, LibraryItemForm, TagForm
from .models import Folder, LibraryItem, Tag


def library_crumbs() -> list[dict]:
    return [crumb("Bibliothèque", reverse("library:list"))]


def item_crumbs(item) -> list[dict]:
    """Le dossier apparaît dans le fil : une ressource se situe d'abord par son rangement."""
    trail = library_crumbs()
    if item.folder_id:
        for folder in [*item.folder.ancestors(), item.folder]:
            trail.append(crumb(folder.name, f"{reverse('library:list')}?folder={folder.pk}"))
    return trail + [crumb(item.title, reverse("library:detail", args=[item.pk]))]


def _folder_tree(folders):
    """Aplatit l'arbre dans l'ordre visuel tout en conservant sa profondeur."""
    children = {}
    for folder in folders:
        children.setdefault(folder.parent_id, []).append(folder)
    result = []

    def visit(parent_id, depth):
        for folder in children.get(parent_id, []):
            folder.tree_depth = min(depth, 5)
            result.append(folder)
            visit(folder.pk, depth + 1)

    visit(None, 0)
    return result


@login_required
def item_list(request):
    items = LibraryItem.objects.filter(owner=request.user).select_related("folder").prefetch_related("tags")
    folder_id = request.GET.get("folder")
    tag_id = request.GET.get("tag")
    kind = request.GET.get("kind")
    purpose = request.GET.get("purpose")
    unit_id = request.GET.get("unit")
    competency_id = request.GET.get("competency")
    sort = request.GET.get("sort", "updated")
    query = request.GET.get("q", "").strip()
    folders = list(Folder.objects.filter(owner=request.user).select_related("parent"))
    selected_folder = next((folder for folder in folders if str(folder.pk) == folder_id), None)
    selected_tag = Tag.objects.filter(owner=request.user, pk=tag_id).first() if tag_id else None
    selected_unit = (
        LearningUnit.objects.filter(period__path__owner=request.user, pk=unit_id).select_related("period").first()
        if unit_id
        else None
    )
    selected_competency = (
        Competency.objects.filter(path__owner=request.user, pk=competency_id).first() if competency_id else None
    )
    if selected_folder:
        items = items.filter(folder_id__in=[selected_folder.pk, *selected_folder.descendant_ids()])
    if selected_tag:
        items = items.filter(tags=selected_tag)
    if kind in LibraryItem.Kind.values:
        items = items.filter(kind=kind)
    if purpose in LibraryItem.Purpose.values:
        items = items.filter(purpose=purpose)
    if selected_unit:
        items = items.filter(learning_units=selected_unit)
    if selected_competency:
        items = items.filter(competencies=selected_competency)
    if query:
        items = items.search(query)
    orderings = {
        "updated": ("-updated_at", "title"),
        "created": ("-created_at", "title"),
        "title": ("title",),
        "title_desc": ("-title",),
    }
    sort = sort if sort in orderings else "updated"
    items = items.distinct().order_by(*orderings[sort])
    total = items.count()
    page_obj = Paginator(items, 24).get_page(request.GET.get("page"))
    preserved = [(key, value) for key, value in request.GET.items() if key != "page" and value]
    page_query = urlencode(preserved)
    active_filters = any([query, selected_folder, selected_tag, kind, purpose, selected_unit, selected_competency])
    breadcrumbs = [crumb("Bibliothèque", reverse("library:list"))]
    if selected_folder:
        breadcrumbs.extend(
            crumb(folder.name, f"{reverse('library:list')}?folder={folder.pk}")
            for folder in selected_folder.ancestors()
        )
        breadcrumbs.append(crumb(selected_folder.name))
    return render(
        request,
        "library/list.html",
        {
            "items": page_obj,
            "page_obj": page_obj,
            "total": total,
            "folders": _folder_tree(folders),
            "tags": Tag.objects.filter(owner=request.user),
            "kind": kind,
            "purpose": purpose,
            "query": query,
            "selected_folder": selected_folder,
            "selected_tag": selected_tag,
            "selected_unit": selected_unit,
            "selected_competency": selected_competency,
            "kinds": LibraryItem.Kind.choices,
            "purposes": LibraryItem.Purpose.choices,
            "units": LearningUnit.objects.filter(period__path__owner=request.user).select_related(
                "period", "period__path"
            ),
            "competencies": Competency.objects.filter(path__owner=request.user).select_related("path"),
            "sort": sort,
            "page_query": page_query,
            "active_filters": active_filters,
            "breadcrumbs": breadcrumbs,
        },
    )


@login_required
def item_detail(request, pk):
    item = get_object_or_404(
        LibraryItem.objects.select_related("folder").prefetch_related("tags"), owner=request.user, pk=pk
    )
    return render(
        request,
        "library/detail.html",
        {
            "item": item,
            # Les relations inverses : à quoi la ressource sert, et non seulement ce
            # qu'elle est.
            "competencies": item.competencies.select_related("path", "period").prefetch_related("unit_links__unit"),
            "units": item.learning_units.select_related("period__path"),
            "breadcrumbs": item_crumbs(item),
        },
    )


LINK_RESULT_LIMIT = 40


@login_required
def item_links(request, pk):
    """Associer une ressource à des compétences ou des matières, depuis la ressource.

    L'association n'existait que dans un sens. En trouvant une annale dans la
    bibliothèque, rien ne permettait de la rattacher au cours qu'elle prépare : il fallait
    retrouver la compétence, ouvrir son écran, y chercher la ressource.
    """
    item = get_object_or_404(LibraryItem, owner=request.user, pk=pk)
    if request.method == "POST":
        target = request.POST.get("target", "")
        removed = request.POST.get("remove")
        chosen = request.POST.getlist("chosen")
        model = Competency if target == "competency" else LearningUnit
        scope = {"path__owner": request.user} if target == "competency" else {"period__path__owner": request.user}
        if removed:
            holder = get_object_or_404(model, pk=removed, **scope)
            holder.resources.remove(item)
            messages.success(request, f"Association retirée. « {item.title} » reste dans la bibliothèque.")
        elif chosen:
            holders = list(model.objects.filter(pk__in=chosen, **scope))
            for holder in holders:
                holder.resources.add(item)
            messages.success(request, f"{len(holders)} association(s) ajoutée(s).")
        else:
            messages.error(request, "Aucune cible sélectionnée.")
        return redirect(request.get_full_path())

    query = request.GET.get("q", "").strip()
    competencies = Competency.objects.filter(path__owner=request.user).select_related("path", "period")
    units = LearningUnit.objects.filter(period__path__owner=request.user).select_related("period__path")
    if query:
        competencies = competencies.filter(Q(title__icontains=query) | Q(units__title__icontains=query)).distinct()
        units = units.filter(Q(title__icontains=query) | Q(period__title__icontains=query))
    free_competencies = competencies.exclude(resources=item).order_by("period__order", "order", "title")
    free_units = units.exclude(resources=item).order_by("period__order", "order", "title")
    return render(
        request,
        "library/links.html",
        {
            "item": item,
            "attached_competencies": item.competencies.select_related("path", "period"),
            "attached_units": item.learning_units.select_related("period__path"),
            "competencies": free_competencies[:LINK_RESULT_LIMIT],
            "units": free_units[:LINK_RESULT_LIMIT],
            "competency_overflow": max(0, free_competencies.count() - LINK_RESULT_LIMIT),
            "unit_overflow": max(0, free_units.count() - LINK_RESULT_LIMIT),
            "query": query,
            "breadcrumbs": item_crumbs(item) + [crumb("Associations")],
            "back_to": reverse("library:detail", args=[item.pk]),
        },
    )


@login_required
def item_edit(request, pk=None):
    item = get_object_or_404(LibraryItem, owner=request.user, pk=pk) if pk else None
    initial_kind = (
        request.GET.get("kind") if request.GET.get("kind") in LibraryItem.Kind.values else LibraryItem.Kind.NOTE
    )
    form = LibraryItemForm(
        request.POST or None, request.FILES or None, instance=item, user=request.user, initial={"kind": initial_kind}
    )
    if request.method == "POST" and form.is_valid():
        item = form.save()
        messages.success(request, "Élément enregistré.")
        return redirect(safe_next(request, reverse("library:detail", args=[item.pk])))
    return render(
        request,
        "library/form.html",
        {
            "form": form,
            "item": item,
            "breadcrumbs": (item_crumbs(item) + [crumb("Modifier")] if item else library_crumbs() + [crumb("Ajouter")]),
            "back_to": safe_next(
                request, reverse("library:detail", args=[item.pk]) if item else reverse("library:list")
            ),
        },
    )


@login_required
def folder_edit(request, pk=None):
    folder = get_object_or_404(Folder, owner=request.user, pk=pk) if pk else None
    return form_page(
        request,
        form=FolderForm(request.POST or None, instance=folder, user=request.user),
        title="Modifier le dossier" if folder else "Nouveau dossier",
        eyebrow="BIBLIOTHÈQUE",
        breadcrumbs=library_crumbs() + [{"label": folder.name if folder else "Nouveau dossier", "url": None}],
        fallback=lambda obj: f"{reverse('library:list')}?folder={obj.pk}",
        default_back=reverse("library:list"),
        delete_url=reverse("library:folder_delete", args=[folder.pk]) if folder else None,
        delete_label="ce dossier",
    )


@login_required
def tag_edit(request, pk=None):
    tag = get_object_or_404(Tag, owner=request.user, pk=pk) if pk else None
    return form_page(
        request,
        form=TagForm(request.POST or None, instance=tag, user=request.user),
        title="Modifier l’étiquette" if tag else "Nouvelle étiquette",
        eyebrow="BIBLIOTHÈQUE",
        breadcrumbs=library_crumbs() + [{"label": tag.name if tag else "Nouvelle étiquette", "url": None}],
        fallback=lambda obj: f"{reverse('library:list')}?tag={obj.pk}",
        default_back=reverse("library:list"),
        delete_url=reverse("library:tag_delete", args=[tag.pk]) if tag else None,
        delete_label="cette étiquette",
    )


@login_required
def item_delete(request, pk):
    item = get_object_or_404(LibraryItem, owner=request.user, pk=pk)
    return confirm_delete(
        request,
        item,
        redirect_to=reverse("library:list"),
        title="Supprimer cet élément",
        back_to=reverse("library:detail", args=[item.pk]),
    )


@login_required
def folder_delete(request, pk):
    folder = get_object_or_404(Folder, owner=request.user, pk=pk)
    return confirm_delete(request, folder, redirect_to=reverse("library:list"), title="Supprimer ce dossier")


@login_required
def tag_delete(request, pk):
    tag = get_object_or_404(Tag, owner=request.user, pk=pk)
    return confirm_delete(request, tag, redirect_to=reverse("library:list"), title="Supprimer cette étiquette")


@login_required
@never_cache
def download(request, pk):
    """Même précaution que pour les pistes : la redirection signée expire, pas le cache."""
    item = get_object_or_404(LibraryItem, owner=request.user, pk=pk, kind=LibraryItem.Kind.FILE)
    if not item.file:
        raise Http404
    return serve_private_file(item.file, as_attachment=True)
