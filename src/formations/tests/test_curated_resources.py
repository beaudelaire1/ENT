"""Couverture et import des parcours pédagogiques recommandés."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from formations.curated_resources import RESOURCES, UNIT_BUNDLES, recommendations_for
from formations.management.commands.load_licence_guyane import PROGRAMME
from formations.models import LearningPath, LearningUnit, Period
from formations.tests.factories import competency_in
from library.models import LibraryItem


class CuratedCatalogTests(TestCase):
    def test_every_declared_competency_has_a_real_learning_path(self):
        """Une recommandation doit proposer plusieurs gestes, pas un lien bouche-trou."""
        for period, units in PROGRAMME.items():
            for unit, _group, _hours, _ects, _kind, competencies in units:
                for title in competencies:
                    with self.subTest(period=period, unit=unit, competency=title):
                        resources = recommendations_for(title, [unit])
                        roles = {resource.role for resource in resources}
                        self.assertGreaterEqual(len(resources), 2)
                        self.assertIn("understand", roles)
                        self.assertTrue(roles.intersection({"practice", "watch", "deepen", "tool"}))

    def test_every_unit_bundle_combines_at_least_three_resources(self):
        declared_units = {unit[0] for semester in PROGRAMME.values() for unit in semester}
        self.assertEqual(set(UNIT_BUNDLES), declared_units)
        for unit, keys in UNIT_BUNDLES.items():
            with self.subTest(unit=unit):
                self.assertGreaterEqual(len(keys), 3)
                self.assertEqual(len(keys), len(set(keys)))

    def test_every_resource_is_identified_and_uses_https(self):
        for key, resource in RESOURCES.items():
            with self.subTest(resource=key):
                self.assertEqual(key, resource.key)
                self.assertTrue(resource.url.startswith("https://"))
                self.assertTrue(resource.provider)
                self.assertTrue(resource.description)
                self.assertIn(resource.language, {"fr", "en"})

    def test_a_precise_topic_receives_a_precise_complement(self):
        residues = recommendations_for("Appliquer le théorème des résidus", ["Analyse complexe"])
        interpolation = recommendations_for("Construire une spline cubique", ["Analyse numérique"])
        regression = recommendations_for(
            "Ajuster une régression multiple et diagnostiquer les résidus", ["Statistiques appliquées"]
        )

        self.assertIn("complex_residues_bibmath", [resource.key for resource in residues])
        self.assertIn("scipy_interpolation", [resource.key for resource in interpolation])
        self.assertIn("statistics_regression_lyon", [resource.key for resource in regression])

    def test_geometry_uses_affine_euclidean_and_topic_specific_resources(self):
        barycentre = recommendations_for(
            "Utiliser l’associativité des barycentres et les barycentres partiels",
            ["Géométrie"],
        )
        projection = recommendations_for(
            "Calculer la projection orthogonale sur un sous-espace affine",
            ["Géométrie"],
        )
        conic = recommendations_for(
            "Réduire l’équation d’une conique et la classifier",
            ["Géométrie"],
        )

        self.assertIn("geometry_affine_video_caldero", [resource.key for resource in barycentre])
        self.assertIn("geometry_euclidean_td_lyon", [resource.key for resource in projection])
        self.assertIn("geometry_conics_td_lyon", [resource.key for resource in conic])
        all_keys = {resource.key for resources in (barycentre, projection, conic) for resource in resources}
        self.assertFalse(
            all_keys.intersection(
                {
                    "geometry_course_exercises_saclay",
                    "geometry_interactive_unisciel",
                    "geometry_advanced_ens",
                }
            )
        )

    def test_recommendations_never_repeat_the_same_catalog_entry(self):
        resources = recommendations_for(
            "Mener un test de Fisher de comparaison de variances",
            ["Statistiques appliquées", "Statistiques appliquées"],
        )
        keys = [resource.key for resource in resources]
        self.assertEqual(len(keys), len(set(keys)))


class CuratedResourceImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.period = Period.objects.create(path=self.path, title="Semestre 5", order=5)
        self.unit = LearningUnit.objects.create(period=self.period, title="Topologie", order=1)
        self.competency = competency_in(self.unit, title="Établir la compacité", order=1)
        self.detail_url = reverse("formations:competency", args=[self.competency.pk])
        self.import_url = reverse("formations:competency_import_recommendations", args=[self.competency.pk])

    def test_the_competency_page_explains_and_displays_the_path(self):
        response = self.client.get(self.detail_url)

        self.assertContains(response, "Parcours recommandé")
        self.assertContains(response, "Cours de topologie")
        self.assertContains(response, "PDF de cours")
        self.assertContains(response, "Français")
        self.assertEqual(response.context["curated_count"], 3)

    def test_import_adds_every_recommendation_to_the_library_and_competency(self):
        response = self.client.post(self.import_url, follow=True)

        self.assertEqual(LibraryItem.objects.filter(owner=self.user).count(), 3)
        self.assertEqual(self.competency.resources.count(), 3)
        self.assertContains(response, "3 ressource(s) du parcours ajoutée(s)")
        item = LibraryItem.objects.get(legacy_id="topology_course_lille")
        self.assertEqual(item.kind, LibraryItem.Kind.LINK)
        self.assertEqual(item.purpose, LibraryItem.Purpose.COURSE)
        self.assertIn("Comprendre", item.source_category)

    def test_import_is_idempotent(self):
        self.client.post(self.import_url)
        self.client.post(self.import_url)

        self.assertEqual(LibraryItem.objects.filter(owner=self.user).count(), 3)
        self.assertEqual(self.competency.resources.count(), 3)

    def test_page_reports_when_every_resource_is_already_in_the_library(self):
        self.client.post(self.import_url)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.context["curated_missing_count"], 0)
        self.assertContains(response, "déjà disponible dans Ma bibliothèque")

    def test_an_existing_personal_link_is_reused_without_overwriting_it(self):
        recommendation = recommendations_for(self.competency.title, [self.unit.title])[0]
        existing = LibraryItem.objects.create(
            owner=self.user,
            kind=LibraryItem.Kind.LINK,
            purpose=LibraryItem.Purpose.OTHER,
            title="Mon intitulé",
            url=recommendation.url,
        )

        self.client.post(self.import_url)

        self.assertEqual(LibraryItem.objects.filter(owner=self.user).count(), 3)
        existing.refresh_from_db()
        self.assertEqual(existing.title, "Mon intitulé")
        self.assertIn(existing, self.competency.resources.all())

    def test_import_requires_post(self):
        self.assertEqual(self.client.get(self.import_url).status_code, 405)

    def test_another_users_competency_cannot_be_imported(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        path = LearningPath.objects.create(owner=bob, title="Privé")
        period = Period.objects.create(path=path, title="Semestre 5")
        unit = LearningUnit.objects.create(period=period, title="Topologie")
        foreign = competency_in(unit, title="Établir la compacité")

        response = self.client.post(reverse("formations:competency_import_recommendations", args=[foreign.pk]))

        self.assertEqual(response.status_code, 404)
        self.assertFalse(LibraryItem.objects.filter(owner=self.user).exists())
