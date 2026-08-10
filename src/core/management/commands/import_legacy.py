from __future__ import annotations

import json
import re
import sqlite3
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from formations.models import (
    Competency,
    LearningPath,
    LearningUnit,
    MetricDefinition,
    MetricValue,
    Period,
    ProgressRecord,
)
from library.models import Folder, LibraryItem, Tag


class TrainingTableParser(HTMLParser):
    """Extract the recoverable rows without executing prototype JavaScript."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.table = None
        self.row = None
        self.cell = None
        self.option = None
        self.rows = []

    @staticmethod
    def attrs(values):
        return {key: value if value is not None else "" for key, value in values}

    def handle_starttag(self, tag, attrs):
        attrs = self.attrs(attrs)
        if tag == "table" and attrs.get("id") in {"tableS5", "tableS6"}:
            self.table = attrs["id"][-2:]
        elif tag == "tr" and self.table:
            self.row = {"period": self.table, "class": attrs.get("class", ""), "cells": []}
        elif tag == "td" and self.row is not None:
            self.cell = {"class": attrs.get("class", ""), "text": [], "inputs": [], "select": None}
        elif tag == "input" and self.cell is not None:
            self.cell["inputs"].append(attrs)
        elif tag == "option" and self.cell is not None:
            self.option = {"value": attrs.get("value", "0"), "selected": "selected" in attrs, "text": []}

    def handle_data(self, data):
        if self.option is not None:
            self.option["text"].append(data)
        if self.cell is not None:
            self.cell["text"].append(data)

    def handle_endtag(self, tag):
        if tag == "option" and self.option is not None and self.cell is not None:
            if self.cell["select"] is None or self.option["selected"]:
                self.cell["select"] = self.option["value"]
            self.option = None
        elif tag == "td" and self.cell is not None and self.row is not None:
            self.cell["text"] = " ".join("".join(self.cell["text"]).split())
            self.row["cells"].append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            if self.row["cells"]:
                self.rows.append(self.row)
            self.row = None
        elif tag == "table" and self.table:
            self.table = None


def clean_label(value: str) -> str:
    value = value.replace("•", " ").strip()
    return re.sub(r"^[^0-9A-Za-zÀ-ÿ]+", "", value).strip()


def decimal_or_zero(value) -> Decimal:
    try:
        return Decimal(str(value or "0").replace(",", "."))
    except InvalidOperation:
        return Decimal("0")


def number_input(cell, default="0"):
    for item in cell.get("inputs", []):
        if item.get("type") == "number":
            return item.get("value", default)
    return default


class Command(BaseCommand):
    help = "Importe sans destruction la base SQLite et les prototypes archivés."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Compte propriétaire des données importées.")
        parser.add_argument("--archive", type=Path, help="Dossier oldVersion (détecté par défaut).")
        parser.add_argument("--report", type=Path, default=Path("migration-report.json"))

    def handle(self, *args, **options):
        user_model = get_user_model()
        try:
            owner = user_model.objects.get(username=options["username"])
        except user_model.DoesNotExist as exc:
            raise CommandError("Le compte cible n’existe pas. Créez-le avant l’import.") from exc

        archive = options["archive"] or Path(__file__).resolve().parents[4] / "oldVersion"
        archive = archive.resolve()
        if not archive.is_dir():
            raise CommandError(f"Archive introuvable : {archive}")

        report = {
            "archive": str(archive),
            "target_username": owner.username,
            "sqlite": {},
            "l3_prototype": {},
            "documents": {},
            "warnings": [],
        }
        with transaction.atomic():
            self.import_sqlite(owner, archive, report)
            self.import_l3(owner, archive, report)
            self.import_documents(owner, archive, report)

        report_path = options["report"].resolve()
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        self.stdout.write(self.style.SUCCESS(f"Import terminé. Rapport : {report_path}"))

    def import_sqlite(self, owner, archive, report):
        database = archive / "django-initial" / "ENT" / "db.sqlite3"
        if not database.exists():
            report["warnings"].append(f"Base SQLite absente : {database}")
            return
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            categories = list(connection.execute("SELECT id, name, description FROM core_category ORDER BY id"))
            providers = list(connection.execute("SELECT id, name, website FROM core_resourceprovider ORDER BY id"))
            old_users = [
                dict(row)
                for row in connection.execute(
                    "SELECT username, email, is_active, is_staff, is_superuser FROM auth_user ORDER BY id"
                )
            ]
            folders = {}
            for row in categories:
                folders[row["id"]], _ = Folder.objects.get_or_create(owner=owner, parent=None, name=row["name"])
            provider_tags = {}
            for row in providers:
                provider_tags[row["id"]], _ = Tag.objects.get_or_create(
                    owner=owner, name=f"Fournisseur · {row['name']}"
                )
            courses = list(
                connection.execute(
                    """
                    SELECT c.*, cat.name category_name, p.name provider_name
                    FROM curriculum_course c
                    JOIN core_category cat ON cat.id = c.category_id
                    LEFT JOIN core_resourceprovider p ON p.id = c.provider_id
                    ORDER BY c.id
                    """
                )
            )
            course_items = {}
            for row in courses:
                item, _ = LibraryItem.objects.get_or_create(
                    owner=owner,
                    legacy_source="legacy-sqlite-course",
                    legacy_id=str(row["id"]),
                    defaults={"kind": LibraryItem.Kind.LINK, "title": row["title"], "url": row["link"]},
                )
                item.kind = LibraryItem.Kind.LINK
                item.title = row["title"]
                item.description = row["description"]
                item.url = row["link"]
                item.folder = folders[row["category_id"]]
                item.source_category = row["category_name"]
                item.provider_name = row["provider_name"] or ""
                item.save()
                if row["provider_id"]:
                    item.tags.add(provider_tags[row["provider_id"]])
                course_items[row["id"]] = item

            resources = list(connection.execute("SELECT * FROM curriculum_resource ORDER BY id"))
            for row in resources:
                parent = course_items[row["course_id"]]
                item, _ = LibraryItem.objects.get_or_create(
                    owner=owner,
                    legacy_source="legacy-sqlite-resource",
                    legacy_id=str(row["id"]),
                    defaults={"kind": LibraryItem.Kind.LINK, "title": row["title"], "url": row["link"]},
                )
                item.kind = LibraryItem.Kind.LINK
                item.title = row["title"]
                item.description = row["description"]
                item.url = row["link"]
                item.folder = parent.folder
                item.source_category = parent.source_category
                item.provider_name = parent.provider_name
                item.save()
                item.tags.set(parent.tags.all())

            modules = list(
                connection.execute(
                    """SELECT m.*, c.title course_title FROM curriculum_module m
                    JOIN curriculum_course c ON c.id = m.course_id ORDER BY c.id, m."order", m.id"""
                )
            )
            if modules:
                path, _ = LearningPath.objects.get_or_create(
                    owner=owner,
                    title="Structure pédagogique historique",
                    defaults={"description": "Modules récupérés de la première base MyENT."},
                )
                period, _ = Period.objects.get_or_create(path=path, title="Import SQLite", defaults={"order": 1})
                for row in modules:
                    unit, _ = LearningUnit.objects.get_or_create(period=period, title=row["course_title"])
                    unit.resources.add(course_items[row["course_id"]])
                    Competency.objects.update_or_create(
                        unit=unit,
                        title=row["title"],
                        defaults={"description": row["description"], "order": row["order"]},
                    )
            report["sqlite"] = {
                "database": str(database),
                "categories": len(categories),
                "providers": len(providers),
                "courses": len(courses),
                "child_resources": len(resources),
                "modules": len(modules),
                "legacy_accounts_to_verify": old_users,
            }
            report["warnings"].append(
                "Les mots de passe et comptes historiques ne sont jamais fusionnés automatiquement ; vérifiez la liste des comptes."
            )
        finally:
            connection.close()

    def import_l3(self, owner, archive, report):
        source = archive / "prototypes" / "suivi1.html"
        if not source.exists():
            report["warnings"].append(f"Prototype L3 absent : {source}")
            return
        parser = TrainingTableParser()
        parser.feed(source.read_text(encoding="utf-8"))
        path, _ = LearningPath.objects.get_or_create(
            owner=owner,
            title="L3 Mathématiques 2025-2026",
            defaults={"training_type": "Formation universitaire", "level_label": "L3"},
        )
        metrics = {}
        for order, (key, label, unit_label) in enumerate(
            [
                ("coefficient", "Coefficient", ""),
                ("ects", "ECTS", ""),
                ("cm", "CM", "h"),
                ("td", "TD", "h"),
                ("tp", "TP", "h"),
            ]
        ):
            metrics[key], _ = MetricDefinition.objects.update_or_create(
                path=path, key=key, defaults={"label": label, "unit_label": unit_label, "order": order}
            )
        periods = {
            "S5": Period.objects.get_or_create(path=path, title="Semestre 5", defaults={"order": 5})[0],
            "S6": Period.objects.get_or_create(path=path, title="Semestre 6", defaults={"order": 6})[0],
        }
        current_units = {}
        unit_count = competency_count = 0
        # L'ordre du document porte du sens : il est conservé plutôt que de laisser le
        # tri alphabétique décider de l'affichage.
        unit_order = dict.fromkeys(periods, 0)
        competency_order = {}
        for row in parser.rows:
            cells = row["cells"]
            if not cells:
                continue
            if "matiere-row" in row["class"]:
                title = clean_label(cells[0]["text"])
                if not title:
                    continue
                unit_order[row["period"]] += 1
                unit, _ = LearningUnit.objects.update_or_create(
                    period=periods[row["period"]], title=title, defaults={"order": unit_order[row["period"]]}
                )
                competency_order[unit.pk] = 0
                current_units[row["period"]] = unit
                unit_count += 1
                for index, key in enumerate(("coefficient", "ects", "cm", "td", "tp"), start=1):
                    if len(cells) > index:
                        MetricValue.objects.update_or_create(
                            definition=metrics[key],
                            unit=unit,
                            defaults={"value": decimal_or_zero(cells[index]["text"])},
                        )
                continue
            unit = current_units.get(row["period"])
            if unit is None or "competence" not in cells[0]["class"]:
                continue
            title = clean_label(cells[0]["text"])
            competency_order[unit.pk] = competency_order.get(unit.pk, 0) + 1
            competency, _ = Competency.objects.update_or_create(
                unit=unit, title=title, defaults={"order": competency_order[unit.pk]}
            )
            actual = next((number_input(cell) for cell in cells if number_input(cell, "") != ""), "0")
            mastery = next((cell["select"] for cell in cells if cell["select"] is not None), "0")
            ProgressRecord.objects.update_or_create(
                owner=owner,
                competency=competency,
                defaults={"actual_hours": decimal_or_zero(actual), "mastery_level": int(mastery or 0)},
            )
            competency_count += 1
        report["l3_prototype"] = {
            "source": str(source),
            "subjects": unit_count,
            "competencies": competency_count,
            "period_rows": {period: sum(1 for row in parser.rows if row["period"] == period) for period in periods},
        }
        report["warnings"].append(
            "Le prototype L3 est partiel : le Semestre 6 s’arrête après les lignes présentes dans le HTML archivé."
        )

    def import_documents(self, owner, archive, report):
        document = archive / "documents" / "topo25.pdf"
        if not document.exists():
            report["documents"] = {"topo25.pdf": "absent"}
            report["warnings"].append("topo25.pdf est absent de l’archive et n’a pas été importé.")
            return
        item, created = LibraryItem.objects.get_or_create(
            owner=owner,
            legacy_source="legacy-document",
            legacy_id="topo25.pdf",
            defaults={"kind": LibraryItem.Kind.FILE, "title": "Topologie 2025", "mime_type": "application/pdf"},
        )
        if created or not item.file:
            with document.open("rb") as handle:
                item.file.save("topo25.pdf", File(handle), save=False)
            item.file_size = document.stat().st_size
            item.save()
        unit = LearningUnit.objects.filter(period__path__owner=owner, title__icontains="topologie").first()
        if unit:
            unit.resources.add(item)
        report["documents"] = {"topo25.pdf": "imported", "attached_to": unit.title if unit else None}
