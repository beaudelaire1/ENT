"""Créer une note à partir d'un simple texte, sans passer par l'éditeur riche."""

from __future__ import annotations

from django.utils.html import escape

from .models import LibraryItem


def create_plain_note(owner, text: str) -> LibraryItem:
    """Une note complète — texte, delta de l'éditeur et HTML — faite d'un seul paragraphe.

    Partagée par la note rapide de l'accueil et la capture de l'en-tête : deux entrées, une
    seule façon de fabriquer la note, que l'éditeur rouvre ensuite comme les autres.
    """
    text = text.strip()
    return LibraryItem.objects.create(
        owner=owner,
        kind=LibraryItem.Kind.NOTE,
        title=text[:70],
        note_text=text,
        note_delta={"ops": [{"insert": text + "\n"}]},
        note_html=f"<p>{escape(text)}</p>",
    )
