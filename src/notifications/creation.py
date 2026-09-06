"""Ce qui vient d'apparaître dans l'espace de quelqu'un.

Ces notifications ne préviennent pas d'une urgence : elles tiennent le journal de ce qui
entre dans l'ENT. C'est ce que l'utilisateur a demandé — « lorsqu'une tâche est créée » —
et c'est aussi ce qui rend la cloche utile quand plusieurs chemins créent des objets :
un import de maquette, une série de tâches répétées, une reprise depuis l'administration.

Aucune n'est urgente : rien de tout cela ne part par email.
"""

from __future__ import annotations

from .services import notify

# Étiquette du modèle → comment l'annoncer. Le libellé est au singulier, tel qu'il
# apparaîtra dans la cloche, et l'URL mène là où l'objet se consulte.
ANNOUNCED: dict[str, tuple[str, str, str]] = {
    "planner.Task": ("task.created", "Nouvelle tâche", "/tasks/"),
    "formations.LearningPath": ("formation.created", "Nouveau parcours", "/formations/"),
    "formations.LearningUnit": ("formation.created", "Nouvelle matière", "/formations/"),
    "formations.Competency": ("formation.created", "Nouvelle compétence", "/formations/"),
    "library.LibraryItem": ("library.added", "Document ajouté", "/bibliotheque/"),
}


def announce(sender, instance, created=False, **kwargs):
    if not created:
        return
    declaration = ANNOUNCED.get(instance._meta.label)
    if declaration is None:
        return
    owner = _owner_of(instance)
    if owner is None:
        return
    event_key, lead, url = declaration
    notify(
        owner,
        event_key,
        dedupe_key=f"{event_key}:{instance._meta.label}:{instance.pk}",
        title=f"{lead} · {instance}",
        url=url,
    )


# Chemins de remontée vers le propriétaire, du plus court au plus long. Une compétence
# et une matière n'ont pas de propriétaire à elles : elles appartiennent au parcours qui
# les porte, directement ou par leur période. Remonter jusqu'à lui évite de dupliquer un
# champ dont le modèle s'est justement passé.
OWNERSHIP = ("owner", "path.owner", "period.path.owner")


def _owner_of(instance):
    for chain in OWNERSHIP:
        current = instance
        for step in chain.split("."):
            current = getattr(current, step, None)
            if current is None:
                break
        if current is not None:
            return current
    return None
