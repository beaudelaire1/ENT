"""De la compétence en difficulté à la ressource, et retour.

Le chemin existait dans un seul sens et passait par une liste de cases à cocher portant
toute la bibliothèque. Il est maintenant recherchable, symétrique, et distingue « retirer
l'association » de « supprimer la ressource ».
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from formations.models import Competency, LearningPath, LearningUnit, Period
from library.models import LibraryItem, Tag


class ResourcePickerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.period = Period.objects.create(path=self.path, title="Semestre 5", order=5)
        self.unit = LearningUnit.objects.create(period=self.period, title="Topologie", order=1)
        self.competency = Competency.objects.create(unit=self.unit, title="Établir la compacité", order=1)
        self.annale = self.resource("Annale 2023", purpose=LibraryItem.Purpose.PAST_PAPER, provider="Université")
        self.cours = self.resource("Polycopié de topologie", purpose=LibraryItem.Purpose.COURSE)

    def resource(self, title, *, purpose=LibraryItem.Purpose.OTHER, provider="", description=""):
        return LibraryItem.objects.create(
            owner=self.user,
            kind=LibraryItem.Kind.NOTE,
            purpose=purpose,
            title=title,
            note_text="x",
            provider_name=provider,
            description=description,
        )

    def url(self):
        return reverse("formations:competency_resources", args=[self.competency.pk])

    # ----------------------------------------------------------------- association

    def test_several_resources_are_associated_at_once(self):
        response = self.client.post(self.url(), {"resources": [self.annale.pk, self.cours.pk]})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(set(self.competency.resources.values_list("pk", flat=True)), {self.annale.pk, self.cours.pk})

    def test_removing_an_association_keeps_the_resource(self):
        self.competency.resources.add(self.annale)

        self.client.post(self.url(), {"remove": self.annale.pk})

        self.assertFalse(self.competency.resources.exists())
        self.assertTrue(LibraryItem.objects.filter(pk=self.annale.pk).exists())

    def test_the_message_says_the_resource_stays_in_the_library(self):
        self.competency.resources.add(self.annale)
        response = self.client.post(self.url(), {"remove": self.annale.pk}, follow=True)
        self.assertContains(response, "reste dans la bibliothèque")

    def test_an_empty_submission_is_refused_without_touching_anything(self):
        self.competency.resources.add(self.annale)
        response = self.client.post(self.url(), {}, follow=True)
        self.assertContains(response, "Aucune ressource sélectionnée")
        self.assertEqual(self.competency.resources.count(), 1)

    def test_another_users_resource_cannot_be_associated(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign = LibraryItem.objects.create(owner=bob, kind=LibraryItem.Kind.NOTE, title="Privé", note_text="x")

        self.client.post(self.url(), {"resources": [foreign.pk]})

        self.assertFalse(self.competency.resources.exists())

    # -------------------------------------------------------------------- recherche

    def test_the_search_matches_the_title(self):
        response = self.client.get(self.url(), {"q": "annale"})
        self.assertContains(response, "Annale 2023")
        self.assertNotContains(response, "Polycopié de topologie")

    def test_the_search_matches_a_tag(self):
        tag = Tag.objects.create(owner=self.user, name="révisions")
        self.cours.tags.add(tag)

        response = self.client.get(self.url(), {"q": "révisions"})

        self.assertContains(response, "Polycopié de topologie")
        self.assertNotContains(response, "Annale 2023")

    def test_the_search_matches_the_source(self):
        response = self.client.get(self.url(), {"q": "Université"})
        self.assertContains(response, "Annale 2023")

    def test_results_can_be_filtered_by_purpose(self):
        response = self.client.get(self.url(), {"purpose": LibraryItem.Purpose.PAST_PAPER})
        self.assertContains(response, "Annale 2023")
        self.assertNotContains(response, "Polycopié de topologie")

    def test_results_can_be_filtered_by_technical_kind(self):
        link = self.resource("Vidéo de cours")
        LibraryItem.objects.filter(pk=link.pk).update(kind=LibraryItem.Kind.LINK, url="https://exemple.test")

        response = self.client.get(self.url(), {"kind": LibraryItem.Kind.LINK})

        self.assertContains(response, "Vidéo de cours")
        self.assertNotContains(response, "Annale 2023")

    def test_an_already_associated_resource_leaves_the_results(self):
        self.competency.resources.add(self.annale)
        response = self.client.get(self.url())
        candidates = [item.pk for item in response.context["candidates"]]
        self.assertNotIn(self.annale.pk, candidates)
        self.assertIn(self.annale, list(response.context["attached"]))

    def test_the_search_survives_an_association(self):
        """Le filtre en cours est conservé : associer ne renvoie pas à une liste vierge."""
        response = self.client.post(f"{self.url()}?q=annale", {"resources": [self.annale.pk]})
        self.assertEqual(response["Location"], f"{self.url()}?q=annale")

    def test_creating_a_resource_returns_to_the_picker(self):
        response = self.client.get(self.url())
        self.assertIn(reverse("library:new"), response.context["create_url"])
        self.assertIn("next=", response.context["create_url"])

    # --------------------------------------------------------------------- matières

    def test_a_unit_has_its_own_picker(self):
        response = self.client.post(
            reverse("formations:unit_resources", args=[self.unit.pk]), {"resources": [self.cours.pk]}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(self.unit.resources.all()), [self.cours])

    def test_another_users_competency_picker_is_out_of_reach(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign_path = LearningPath.objects.create(owner=bob, title="Privé")
        foreign_period = Period.objects.create(path=foreign_path, title="Bloc")
        foreign_unit = LearningUnit.objects.create(period=foreign_period, title="Unité")
        foreign = Competency.objects.create(unit=foreign_unit, title="Compétence")
        url = reverse("formations:competency_resources", args=[foreign.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    # ------------------------------------------------------- affichage par nature

    def test_the_competency_page_groups_resources_by_purpose(self):
        self.competency.resources.add(self.annale, self.cours)

        response = self.client.get(reverse("formations:competency", args=[self.competency.pk]))
        groups = {
            group["purpose"]: [item.title for item in group["items"]] for group in response.context["resource_groups"]
        }

        self.assertEqual(groups[LibraryItem.Purpose.COURSE], ["Polycopié de topologie"])
        self.assertEqual(groups[LibraryItem.Purpose.PAST_PAPER], ["Annale 2023"])
        self.assertContains(response, "Annale")

    def test_the_groups_follow_the_declared_order_not_the_alphabet(self):
        self.competency.resources.add(self.annale, self.cours)
        response = self.client.get(reverse("formations:competency", args=[self.competency.pk]))
        order = [group["purpose"] for group in response.context["resource_groups"]]
        self.assertEqual(order, [LibraryItem.Purpose.COURSE, LibraryItem.Purpose.PAST_PAPER])


class LibrarySideLinkTests(TestCase):
    """La même association, vue depuis la ressource."""

    def setUp(self):
        self.user = get_user_model().objects.create_user("alice", password="secret")
        self.client.force_login(self.user)
        self.path = LearningPath.objects.create(owner=self.user, title="L3 Mathématiques")
        self.period = Period.objects.create(path=self.path, title="Semestre 5", order=5)
        self.unit = LearningUnit.objects.create(period=self.period, title="Topologie", order=1)
        self.competency = Competency.objects.create(unit=self.unit, title="Établir la compacité", order=1)
        self.item = LibraryItem.objects.create(
            owner=self.user,
            kind=LibraryItem.Kind.NOTE,
            purpose=LibraryItem.Purpose.PAST_PAPER,
            title="Annale 2023",
            note_text="x",
        )

    def url(self):
        return reverse("library:links", args=[self.item.pk])

    def test_a_resource_can_be_attached_to_a_competency(self):
        self.client.post(self.url(), {"target": "competency", "chosen": [self.competency.pk]})
        self.assertEqual(list(self.competency.resources.all()), [self.item])

    def test_a_resource_can_be_attached_to_a_unit(self):
        self.client.post(self.url(), {"target": "unit", "chosen": [self.unit.pk]})
        self.assertEqual(list(self.unit.resources.all()), [self.item])

    def test_an_association_can_be_removed_from_the_resource_side(self):
        self.competency.resources.add(self.item)
        self.client.post(self.url(), {"target": "competency", "remove": self.competency.pk})
        self.assertFalse(self.competency.resources.exists())
        self.assertTrue(LibraryItem.objects.filter(pk=self.item.pk).exists())

    def test_the_detail_page_shows_the_inverse_relations(self):
        self.competency.resources.add(self.item)
        self.unit.resources.add(self.item)

        response = self.client.get(reverse("library:detail", args=[self.item.pk]))

        self.assertContains(response, "Établir la compacité")
        self.assertContains(response, "Topologie")
        self.assertContains(response, "Annale")
        self.assertContains(response, reverse("formations:competency", args=[self.competency.pk]))

    def test_the_detail_page_says_when_nothing_is_linked(self):
        response = self.client.get(reverse("library:detail", args=[self.item.pk]))
        self.assertContains(response, "n’est reliée à aucune compétence")

    def test_a_competency_of_another_user_cannot_be_targeted(self):
        bob = get_user_model().objects.create_user("bob", password="secret")
        foreign_path = LearningPath.objects.create(owner=bob, title="Privé")
        foreign_period = Period.objects.create(path=foreign_path, title="Bloc")
        foreign_unit = LearningUnit.objects.create(period=foreign_period, title="Unité")
        foreign = Competency.objects.create(unit=foreign_unit, title="Compétence")

        self.client.post(self.url(), {"target": "competency", "chosen": [foreign.pk]})

        self.assertFalse(foreign.resources.exists())

    def test_the_search_narrows_the_candidates(self):
        Competency.objects.create(unit=self.unit, title="Déterminer une adhérence", order=2)
        response = self.client.get(self.url(), {"q": "compacité"})
        titles = [c.title for c in response.context["competencies"]]
        self.assertEqual(titles, ["Établir la compacité"])
