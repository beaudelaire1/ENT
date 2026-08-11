"""Nettoyage du stockage quand un objet porteur de fichier disparaît.

Django ne supprime pas le fichier avec la ligne : sans cela, chaque suppression
laisserait un objet orphelin dans le volume média ou le bucket S3, facturé et compté
dans les quotas sans qu'aucun écran ne le montre.
"""

from __future__ import annotations

from django.db.models.signals import post_delete


def _drop_files(field_names):
    def handler(sender, instance, **kwargs):
        for name in field_names:
            file = getattr(instance, name, None)
            if file:
                # save=False : la ligne n'existe plus, il n'y a rien à réécrire.
                file.delete(save=False)

    return handler


def discard_files_on_delete(model, *field_names):
    """Branche la purge du stockage sur la suppression d'un modèle."""
    post_delete.connect(
        _drop_files(field_names),
        sender=model,
        dispatch_uid=f"discard_files_{model._meta.label_lower}",
        weak=False,
    )
