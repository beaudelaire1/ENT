"""Le minuteur est un seul script : une fonction manquante l'arrête en entier.

`sablier.js` s'exécute dans une fermeture unique. Un appel vers un nom qui n'existe
pas ne se voit ni à la lecture, ni au `node --check` — la syntaxe reste valable. À
l'exécution, la première image lève `ReferenceError`, la boucle meurt, et *tout*
s'arrête avec elle : le décompte, le changement de visualisation, la mise à jour du
décor. L'écran garde alors le dernier état rendu par le serveur, ce qui ressemble à
un problème de visuel alors que c'est le script qui est mort.

C'est arrivé : une fusion a emporté `flash`, `finish`, `logSession` et
`ambienceLabel`, quatre fonctions voisines, et plus aucun bouton ne répondait.
"""

from __future__ import annotations

import re

from django.conf import settings
from django.test import SimpleTestCase

# Ce que le navigateur fournit. La liste est volontairement explicite : un nom
# inconnu doit faire échouer le test, pas passer pour un objet global.
BROWSER_GLOBALS = frozenset(
    """
    Array Audio Boolean CustomEvent Date Error Event FormData Headers Image Intl JSON Map Math
    Number Object Promise Proxy Reflect Request Response Set String Symbol TextEncoder TypeError
    URL URLSearchParams Uint8Array Float32Array WeakMap WeakSet
    alert atob btoa cancelAnimationFrame clearInterval clearTimeout confirm console crypto
    decodeURIComponent devicePixelRatio document encodeURIComponent fetch getComputedStyle
    history isFinite isNaN localStorage location matchMedia navigator parseFloat parseInt
    performance queueMicrotask requestAnimationFrame sessionStorage setInterval setTimeout
    structuredClone window
    """.split()
)

# Mots-clés suivis d'une parenthèse : `if (`, `for (`, `catch (`… Ce ne sont pas des appels.
KEYWORDS = frozenset(
    "if else for while do switch case return typeof new delete void in of instanceof "
    "function class try catch finally throw await async yield super this with".split()
)


def strip_literals(source: str) -> str:
    """Retire commentaires et littéraux, mais garde le code interpolé.

    Un commentaire français contient « invalide (maximum 24 h) », qu'une recherche
    naïve prendrait pour un appel à une fonction `invalide` : il faut donc écarter
    les commentaires et les chaînes.

    Les gabarits, eux, ne sont pas que du texte. `${ambienceLabel()}` est un appel
    réel — vider le gabarit en entier rendait invisible précisément l'appel qui a
    cassé le minuteur, et ce contrôle l'aurait laissé passer.
    """
    out = []
    i, n = 0, len(source)
    while i < n:
        char = source[i]
        pair = source[i : i + 2]
        if pair == "//":
            i = source.find("\n", i)
            if i < 0:
                break
        elif pair == "/*":
            end = source.find("*/", i + 2)
            i = n if end < 0 else end + 2
        elif char in "\"'":
            i += 1
            while i < n and source[i] != char:
                i += 2 if source[i] == "\\" else 1
            i += 1
            out.append('""')
        elif char == "`":
            i += 1
            while i < n and source[i] != "`":
                if source[i] == "\\":
                    i += 2
                elif source[i : i + 2] == "${":
                    depth, start = 1, i + 2
                    i = start
                    while i < n and depth:
                        depth += {"{": 1, "}": -1}.get(source[i], 0)
                        i += 1
                    out.append(" " + strip_literals(source[start : i - 1]) + " ")
                else:
                    i += 1
            i += 1
            out.append('""')
        else:
            out.append(char)
            i += 1
    return "".join(out)


class TimerScriptResolutionTests(SimpleTestCase):
    maxDiff = None

    def setUp(self):
        path = settings.BASE_DIR / "static" / "sablier" / "sablier.js"
        self.code = strip_literals(path.read_text(encoding="utf-8"))

    def declared_names(self) -> set[str]:
        """Les noms que la fermeture introduit, dans les formes que `sablier.js` emploie.

        Sont reconnus : `function nom`, `const`/`let`/`var` simples, variables de boucle,
        liaison de `catch`, paramètres de fonctions et de flèches, et déstructuration
        d'objet à un niveau. Ne le sont pas : `class`, `function*`, déstructuration
        imbriquée, `import`. Ce fichier est un script classique dans une fermeture unique
        et n'en contient aucun ; le jour où il en contiendrait, le contrôle d'en face
        signalerait le nom comme non résolu — un faux positif bruyant, jamais un silence.
        """
        names: set[str] = set()
        names.update(re.findall(r"function\s+([A-Za-z_$][\w$]*)", self.code))
        names.update(re.findall(r"(?:const|let|var)\s+([A-Za-z_$][\w$]*)", self.code))
        names.update(re.findall(r"for\s*\(\s*(?:const|let|var)\s+([A-Za-z_$][\w$]*)", self.code))
        names.update(re.findall(r"catch\s*\(\s*([A-Za-z_$][\w$]*)", self.code))
        names.update(re.findall(r"([A-Za-z_$][\w$]*)\s*=>", self.code))
        # Déstructurations et listes de paramètres.
        for group in re.findall(r"(?:const|let|var)\s*\{([^{}]*)\}\s*=", self.code):
            names.update(re.findall(r"([A-Za-z_$][\w$]*)\s*(?:[,:}]|$)", group))
        for group in re.findall(r"function\s*[\w$]*\s*\(([^()]*)\)", self.code):
            names.update(re.findall(r"([A-Za-z_$][\w$]*)", group))
        for group in re.findall(r"\(([^()]*)\)\s*=>", self.code):
            names.update(re.findall(r"([A-Za-z_$][\w$]*)", group))
        return names

    def called_names(self) -> set[str]:
        # Un appel : un nom suivi d'une parenthèse, qui n'est pas une propriété (`a.b(`).
        return {name for name in re.findall(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(", self.code) if name not in KEYWORDS}

    def test_every_call_resolves_to_something_the_script_can_reach(self):
        """Aucun appel ne doit viser un nom que la fermeture ne contient pas."""
        unresolved = sorted(self.called_names() - self.declared_names() - BROWSER_GLOBALS)
        self.assertEqual(unresolved, [], f"appels non résolus dans sablier.js : {unresolved}")

    def test_the_functions_a_session_depends_on_are_present(self):
        """Les quatre fonctions perdues en fusion, nommées pour qu'on les revoie partir."""
        for name in ("flash", "finish", "logSession", "ambienceLabel", "render", "startPause"):
            with self.subTest(name=name):
                self.assertIn(f"function {name}(", self.code)
