"""Écran de formulaire partagé : créer et modifier suivent le même chemin.

Chaque module avait son gabarit et sa propre façon de rendre un formulaire. Résultat :
« Annuler » existait ici et pas là, le retour après enregistrement variait, et la moitié
des objets n'avaient tout simplement pas d'écran de modification — il fallait supprimer
puis recréer, en perdant les relations au passage.
"""

from __future__ import annotations

from django.contrib import messages
from django.shortcuts import redirect, render

from .navigation import safe_next


def parent_url(breadcrumbs: list[dict], default: str) -> str:
    """Le dernier maillon cliquable du fil : la page dont on vient, donc où l'on retourne."""
    for entry in reversed(breadcrumbs):
        if entry.get("url"):
            return entry["url"]
    return default


def form_page(
    request,
    *,
    form,
    title: str,
    breadcrumbs: list[dict],
    fallback,
    default_back: str,
    eyebrow: str = "",
    subtitle: str = "",
    delete_url: str | None = None,
    delete_label: str | None = None,
    multipart: bool = False,
    template: str = "core/_form_page.html",
    extra: dict | None = None,
    after_save=None,
):
    """Affiche le formulaire, l'enregistre, et ramène là d'où l'on vient.

    ``fallback`` reçoit l'objet enregistré et rend l'adresse par défaut : pour un nouvel
    objet, sa propre page. Un ``next`` valide dans la requête a la priorité, ce qui
    conserve le filtre ou la période de la page d'origine.
    """
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        # ``after_save`` sert aux rattachements que le formulaire ne porte pas : créer une
        # compétence depuis une matière doit aussi créer le lien entre les deux.
        if after_save is not None:
            after_save(obj)
        messages.success(request, f"« {obj} » enregistré.")
        return redirect(safe_next(request, fallback(obj)))
    context = {
        "form": form,
        "title": title,
        "subtitle": subtitle,
        "eyebrow": eyebrow,
        "breadcrumbs": breadcrumbs,
        "back_to": safe_next(request, parent_url(breadcrumbs, default_back)),
        "delete_url": delete_url,
        "delete_label": delete_label,
        "multipart": multipart,
    }
    context.update(extra or {})
    return render(request, template, context)
