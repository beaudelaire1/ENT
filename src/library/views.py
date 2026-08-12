from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from core.deletion import confirm_delete
from core.editing import form_page
from core.navigation import crumb, safe_next

from .forms import FolderForm, LibraryItemForm, TagForm
from .models import Folder, LibraryItem, Tag


def library_crumbs() -> list[dict]:
    return [crumb("Bibliothèque", reverse("library:list"))]


def item_crumbs(item) -> list[dict]:
    """Le dossier apparaît dans le fil : une ressource se situe d'abord par son rangement."""
    trail = library_crumbs()
    if item.folder_id:
        trail.append(crumb(item.folder.name, f"{reverse('library:list')}?folder={item.folder_id}"))
    return trail + [crumb(item.title, reverse("library:detail", args=[item.pk]))]


@login_required
def item_list(request):
    items = LibraryItem.objects.filter(owner=request.user).select_related("folder")
    folder_id = request.GET.get("folder")
    tag_id = request.GET.get("tag")
    kind = request.GET.get("kind")
    query = request.GET.get("q", "").strip()
    if folder_id:
        items = items.filter(folder_id=folder_id)
    if tag_id:
        items = items.filter(tags__id=tag_id)
    if kind in LibraryItem.Kind.values:
        items = items.filter(kind=kind)
    if query:
        items = items.search(query)
    return render(
        request,
        "library/list.html",
        {
            "items": items,
            "folders": Folder.objects.filter(owner=request.user),
            "tags": Tag.objects.filter(owner=request.user),
            "kind": kind,
            "query": query,
            "breadcrumbs": [crumb("Bibliothèque")],
        },
    )


@login_required
def item_detail(request, pk):
    item = get_object_or_404(
        LibraryItem.objects.select_related("folder").prefetch_related("tags", "learning_units", "competencies"),
        owner=request.user,
        pk=pk,
    )
    return render(request, "library/detail.html", {"item": item, "breadcrumbs": item_crumbs(item)})


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
def download(request, pk):
    item = get_object_or_404(LibraryItem, owner=request.user, pk=pk, kind=LibraryItem.Kind.FILE)
    if not item.file:
        raise Http404
    storage = item.file.storage
    if hasattr(storage, "bucket"):
        return redirect(item.file.url)
    return FileResponse(item.file.open("rb"), as_attachment=True, filename=item.file.name.rsplit("/", 1)[-1])
