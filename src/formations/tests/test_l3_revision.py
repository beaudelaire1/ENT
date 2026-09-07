"""Le plan de révision doit rester accroché au programme et au catalogue.

Un plan pédagogique isolé se périme sans bruit : on ajoute une compétence au programme,
on renomme une ressource, et le plan continue de désigner des choses qui n'existent plus.
Ces tests refusent ce silence — ils ne jugent pas la pédagogie, ils tiennent les liens.
"""

from django.test import SimpleTestCase

from formations.curated_resources import RESOURCES
from formations.l3_revision import CHAPTERS, SECTIONS, render_chapter
from formations.management.commands.load_licence_guyane import PROGRAMME

BRANCH_UNITS = {"Topologie": "Topologie", "Géométrie": "Géométrie"}


def programme_for(unit_title):
    for units in PROGRAMME.values():
        for unit, *_rest, competencies in units:
            if unit == unit_title:
                return list(competencies)
    raise AssertionError(f"module absent du programme : {unit_title}")


class RevisionPlanTests(SimpleTestCase):
    def test_the_plan_covers_both_revised_branches(self):
        self.assertEqual({chapter["branch"] for chapter in CHAPTERS}, set(BRANCH_UNITS))

    def test_a_chapter_key_is_unique(self):
        keys = [chapter["key"] for chapter in CHAPTERS]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_chapter_lays_out_the_ten_sections(self):
        """Huit sections rédigées ; objectifs et ressources sont insérés au rendu.

        Le seuil ne mesure pas la qualité : il attrape la section laissée vide ou réduite
        à un mot. Une ligne de prérequis tient légitimement en une phrase courte.
        """
        self.assertEqual(len(SECTIONS), 10)
        for chapter in CHAPTERS:
            with self.subTest(chapter=chapter["key"]):
                self.assertEqual(len(chapter["sections"]), 8)
                for position, section in enumerate(chapter["sections"], 1):
                    with self.subTest(section=position):
                        self.assertGreater(len(section), 40)

    def test_a_chapter_only_points_at_competencies_the_programme_declares(self):
        for branch, unit in BRANCH_UNITS.items():
            competencies = programme_for(unit)
            for chapter in (c for c in CHAPTERS if c["branch"] == branch):
                with self.subTest(chapter=chapter["key"]):
                    for rank in chapter["legacy"]:
                        self.assertGreaterEqual(rank, 1)
                        self.assertLessEqual(rank, len(competencies))

    def test_the_chapters_of_a_branch_cover_its_programme_without_gap_or_overlap(self):
        """Une compétence oubliée du plan est une compétence qu'on ne révisera pas.

        Et une compétence rattachée à deux chapitres est une leçon faite deux fois, ou
        pire, deux fois à moitié.
        """
        for branch, unit in BRANCH_UNITS.items():
            competencies = programme_for(unit)
            ranks = [rank for c in CHAPTERS if c["branch"] == branch for rank in c["legacy"]]
            with self.subTest(branch=branch):
                self.assertEqual(len(ranks), len(set(ranks)), "une compétence est traitée deux fois")
                self.assertEqual(set(ranks), set(range(1, len(competencies) + 1)))

    def test_every_chapter_opens_at_least_two_real_resources(self):
        for chapter in CHAPTERS:
            with self.subTest(chapter=chapter["key"]):
                self.assertGreaterEqual(len(chapter["resources"]), 2)
                self.assertEqual(len(chapter["resources"]), len(set(chapter["resources"])))
                for key in chapter["resources"]:
                    self.assertIn(key, RESOURCES)

    def test_the_algebraic_angles_chapter_carries_the_notions_it_was_missing(self):
        """C'est le chapitre pour lequel cette révision a été demandée.

        Les angles orientés n'existaient au programme qu'en filigrane — « angle » cité au
        passage du produit scalaire. Le chapitre doit nommer les deux modules, la relation
        de Chasles, l'angle inscrit et la cocyclicité, et atteindre un document qui les
        démontre.
        """
        chapter = next(c for c in CHAPTERS if c["key"] == "G06")
        body = " ".join(chapter["sections"]).casefold()
        for notion in ("modulo 2π", "modulo π", "chasles", "angle inscrit", "cocyclicité"):
            with self.subTest(notion=notion):
                self.assertIn(notion.casefold(), body)
        self.assertIn("geometry_angles_inscribed_lecon", chapter["resources"])

        competencies = programme_for("Géométrie")
        worked = " ".join(competencies[rank - 1] for rank in chapter["legacy"]).casefold()
        self.assertIn("cocyclicité", worked)
        self.assertIn("angle inscrit", worked)

    def test_rendering_a_chapter_numbers_the_ten_sections_and_links_the_resources(self):
        chapter = next(c for c in CHAPTERS if c["key"] == "G06")
        resources = [RESOURCES[key] for key in chapter["resources"]]
        entries = [{"title": r.title, "url": r.url, "reading": r.description} for r in resources]

        text, html = render_chapter(chapter, ["Savoir démontrer Chasles"], entries)

        for position, name in enumerate(SECTIONS, 1):
            with self.subTest(section=name):
                self.assertIn(f"{position}. {name}", text)
                self.assertIn(f"<h3>{position}. {name}</h3>", html)
        self.assertIn("Savoir démontrer Chasles", text)
        for resource in resources:
            self.assertIn(resource.url, html)

    def test_rendering_escapes_what_it_inserts(self):
        chapter = dict(CHAPTERS[0])
        entries = [{"title": "Cours <script>", "url": "https://example.test/?a=1&b=2", "reading": "Lire"}]

        _text, html = render_chapter(chapter, ["A & B"], entries)

        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&amp;", html)
