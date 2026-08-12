"""Défauts de gabarit qu'aucun test de vue ne remarque.

Un ``{# … #}`` réparti sur plusieurs lignes n'est pas un commentaire pour Django : la
syntaxe est mono-ligne. Le texte s'affiche alors dans la page, au milieu du contenu, sans
qu'aucune assertion habituelle ne s'en aperçoive — un test vérifie qu'une phrase est
présente, jamais qu'un commentaire est absent.
"""

from __future__ import annotations

import re

from django.conf import settings
from django.test import SimpleTestCase

TEMPLATE_DIR = settings.BASE_DIR / "templates"


def multiline_comments(source: str) -> list[int]:
    """Numéros de ligne des ``{#`` qui ne se referment pas sur la même ligne."""
    offenders = []
    for match in re.finditer(r"\{#", source):
        rest = source[match.start() :]
        end = rest.find("#}")
        if end == -1 or "\n" in rest[:end]:
            offenders.append(source[: match.start()].count("\n") + 1)
    return offenders


class TemplateCommentTests(SimpleTestCase):
    def test_no_template_uses_a_multiline_hash_comment(self):
        offenders = []
        for template in sorted(TEMPLATE_DIR.rglob("*.html")):
            for line in multiline_comments(template.read_text(encoding="utf-8")):
                offenders.append(f"{template.relative_to(TEMPLATE_DIR)}:{line}")
        self.assertEqual(
            offenders,
            [],
            "Commentaire {# … #} sur plusieurs lignes : il sera affiché dans la page. "
            "Utiliser {% comment %} … {% endcomment %}.",
        )

    def test_the_detector_recognises_a_multiline_comment(self):
        self.assertEqual(multiline_comments("{# sur\nplusieurs lignes #}"), [1])
        self.assertEqual(multiline_comments("{# tenu sur une ligne #}"), [])
        self.assertEqual(multiline_comments("<p>{# ouvert et jamais fermé"), [1])
