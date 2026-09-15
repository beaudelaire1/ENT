from datetime import datetime, timedelta
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.exporting import export_account
from formations.models import Competency, LearningPath, LearningUnit, Period
from library.models import LibraryItem
from planner.continuity import planning_slot, task_resources
from planner.models import CalendarEvent, Task

PARIS = ZoneInfo("Europe/Paris")


def note(owner, title):
    return LibraryItem.objects.create(owner=owner, kind=LibraryItem.Kind.NOTE, title=title, note_text=title)


class TaskResourcesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.client.force_login(self.user)
        path = LearningPath.objects.create(owner=self.user, title="Licence")
        period = Period.objects.create(path=path, title="S5")
        self.unit = LearningUnit.objects.create(period=period, title="Topologie")
        self.competency = Competency.objects.create(path=path, period=period, title="Compacité")

    def test_own_and_inherited_resources_are_merged_without_duplicates(self):
        shared, course, sheet = note(self.user, "Fiche"), note(self.user, "Cours"), note(self.user, "Exercices")
        task = Task.objects.create(owner=self.user, title="Réviser", unit=self.unit, competency=self.competency)
        task.resources.add(shared)
        self.competency.resources.add(shared, sheet)
        self.unit.resources.add(course)
        entries = {entry["item"].title: entry["sources"] for entry in task_resources(task)}
        self.assertEqual(list(entries), ["Fiche", "Exercices", "Cours"])
        self.assertEqual(entries["Fiche"], ["Tâche", "Compétence · Compacité"])
        self.assertEqual(entries["Cours"], ["Matière · Topologie"])

    def test_the_task_form_offers_only_the_account_resources(self):
        mine, foreign = note(self.user, "À moi"), note(get_user_model().objects.create_user("bob"), "Privée")
        task = Task.objects.create(owner=self.user, title="Réviser")
        url = reverse("planner:task_edit", args=[task.pk])
        data = {"title": "Réviser", "status": "todo", "priority": 2, "repeat": "none", "email_reminder": "on"}
        response = self.client.post(url, {**data, "resources": [foreign.pk]})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(task.resources.exists())
        self.client.post(url, {**data, "resources": [mine.pk]})
        self.assertEqual(list(task.resources.all()), [mine])

    def test_the_task_list_opens_resources_and_focus_with_the_competency(self):
        task = Task.objects.create(owner=self.user, title="Réviser", competency=self.competency)
        self.competency.resources.add(note(self.user, "Fiche"))
        Task.objects.create(owner=self.user, title="Ranger")
        page = self.client.get(reverse("planner:tasks"))
        self.assertContains(page, "Ressources (1)")
        self.assertContains(page, f"competency={self.competency.pk}", count=1)
        self.assertContains(page, "Se concentrer", count=2)
        self.assertContains(page, f"{reverse('planner:event_new')}?task={task.pk}")


class PlanningFromTaskTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice")
        self.client.force_login(self.user)

    def test_the_slot_starts_at_the_next_full_hour(self):
        now = datetime(2026, 9, 15, 14, 20, tzinfo=PARIS)
        with timezone.override(PARIS):
            starts_at, ends_at = planning_slot(Task(title="X"), now=now)
            self.assertEqual((starts_at.hour, starts_at.minute, ends_at.hour), (15, 0, 16))
            due_tonight = Task(title="X", due_at=datetime(2026, 9, 15, 18, 30, tzinfo=PARIS))
            starts_at, ends_at = planning_slot(due_tonight, now=now)
            self.assertEqual((starts_at.hour, starts_at.minute, ends_at.hour, ends_at.minute), (17, 30, 18, 30))
            due_soon = Task(title="X", due_at=datetime(2026, 9, 15, 14, 50, tzinfo=PARIS))
            self.assertEqual(planning_slot(due_soon, now=now)[0].hour, 15)

    def test_planning_prefills_the_slot_and_keeps_the_task_link(self):
        task = Task.objects.create(owner=self.user, title="Réviser la compacité")
        # La page s'affiche dans le fuseau du compte, celui de Cayenne par défaut.
        now = datetime(2026, 9, 15, 14, 20, tzinfo=ZoneInfo("America/Cayenne"))
        with mock.patch("planner.continuity.timezone.now", return_value=now):
            page = self.client.get(reverse("planner:event_new"), {"task": task.pk})
        self.assertContains(page, 'value="2026-09-15T15:00"')
        self.assertContains(page, 'value="2026-09-15T16:00"')
        url = f"{reverse('planner:event_new')}?task={task.pk}"
        self.client.post(
            url,
            {"title": task.title, "starts_at": "2026-09-15T15:00", "ends_at": "2026-09-15T16:00", "repeat": "none"},
        )
        event = CalendarEvent.objects.get(owner=self.user)
        self.assertEqual(event.task, task)
        agenda = self.client.get(reverse("planner:agenda"), {"month": "2026-09"})
        self.assertContains(agenda, f'Tâche : <a href="{reverse("planner:task_edit", args=[task.pk])}">')

    def test_a_foreign_task_is_never_linked(self):
        foreign = Task.objects.create(owner=get_user_model().objects.create_user("bob"), title="Privée")
        self.client.post(
            f"{reverse('planner:event_new')}?task={foreign.pk}",
            {"title": "Créneau", "starts_at": "2026-09-15T15:00", "ends_at": "2026-09-15T16:00", "repeat": "none"},
        )
        self.assertIsNone(CalendarEvent.objects.get(owner=self.user).task)

    def test_the_export_keeps_task_resources_and_event_links(self):
        task = Task.objects.create(owner=self.user, title="Réviser")
        item = note(self.user, "Fiche")
        task.resources.add(item)
        start = timezone.now() + timedelta(days=1)
        CalendarEvent.objects.create(owner=self.user, title="Créneau", starts_at=start, ends_at=start, task=task)
        planner = export_account(self.user)["planner"]
        self.assertEqual(planner["task_resources"], [{"task_id": task.pk, "libraryitem_id": item.pk}])
        self.assertEqual(planner["events"][0]["task_id"], task.pk)
