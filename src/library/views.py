from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from .forms import FolderForm, LibraryItemForm, TagForm
from .models import Folder, LibraryItem


@login_required
def item_list(request):
    items = LibraryItem.objects.filter(owner=request.user).select_related("folder")
    folder_id = request.GET.get("folder")
    kind = request.GET.get("kind")
    query = request.GET.get("q", "").strip()
    if folder_id:
        items = items.filter(folder_id=folder_id)
    if kind in LibraryItem.Kind.values:
        items = items.filter(kind=kind)
    if query:
        items = items.search(query)
    return render(
        request,
        "library/list.html",
        {"items": items, "folders": Folder.objects.filter(owner=request.user), "kind": kind, "query": query},
    )


@login_required
def item_detail(request, pk):
    item = get_object_or_404(LibraryItem.objects.prefetch_related("tags"), owner=request.user, pk=pk)
    return render(request, "library/detail.html", {"item": item})


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
        return redirect("library:detail", pk=item.pk)
    return render(request, "library/form.html", {"form": form, "item": item})


@login_required
def folder_new(request):
    form = FolderForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Dossier créé.")
        return redirect("library:list")
    return render(request, "library/simple_form.html", {"form": form, "title": "Nouveau dossier"})


@login_required
def tag_new(request):
    form = TagForm(request.POST or None, user=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Étiquette créée.")
        return redirect("library:list")
    return render(request, "library/simple_form.html", {"form": form, "title": "Nouvelle étiquette"})


@login_required
def download(request, pk):
    item = get_object_or_404(LibraryItem, owner=request.user, pk=pk, kind=LibraryItem.Kind.FILE)
    if not item.file:
        raise Http404
    storage = item.file.storage
    if hasattr(storage, "bucket"):
        return redirect(item.file.url)
    return FileResponse(item.file.open("rb"), as_attachment=True, filename=item.file.name.rsplit("/", 1)[-1])
