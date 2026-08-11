"""Suppression confirmée, partagée par tous les modules.

Une seule vue générique plutôt qu'une par modèle : les écrans de confirmation se
ressemblent tous, et ce qui change d'un objet à l'autre — le titre, la page de retour —
tient dans trois arguments.

L'écran annonce ce qui disparaîtra en cascade. Supprimer une formation emporte ses
périodes, ses modules, ses compétences et leur progression ; il faut le voir avant de
confirmer, pas le découvrir après.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.admin.utils import NestedObjects
from django.db import router
from django.shortcuts import redirect, render


def cascade_summary(instance) -> list[tuple[str, int]]:
    """Compte, par type, les objets que la suppression emportera avec elle."""
    collector = NestedObjects(using=router.db_for_write(type(instance)))
    collector.collect([instance])
    summary = []
    for model, objects in collector.model_objs.items():
        count = len(objects)
        if model is type(instance):
            count -= 1  # l'objet lui-même n'est pas une conséquence
        if count > 0:
            meta = model._meta
            summary.append((str(meta.verbose_name_plural if count > 1 else meta.verbose_name), count))
    return sorted(summary, key=lambda row: (-row[1], row[0]))


def confirm_delete(request, instance, *, redirect_to: str, title: str, back_to: str | None = None):
    """Affiche la confirmation en GET, supprime en POST."""
    if request.method == "POST":
        label = str(instance)
        instance.delete()
        messages.success(request, f"« {label} » a été supprimé.")
        return redirect(redirect_to)
    return render(
        request,
        "core/confirm_delete.html",
        {
            "instance": instance,
            "title": title,
            "cascade": cascade_summary(instance),
            "back_to": back_to or redirect_to,
        },
    )
