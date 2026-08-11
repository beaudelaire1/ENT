"""Charge la maquette de la Licence Mathématiques de l'Université de Guyane.

Source : https://www.univ-guyane.fr/choisir-sa-formation/dfr-sciences-et-technologies/licence-mathematiques/

Deux réserves, assumées ici plutôt que masquées :

1. La page publie des ECTS qui ne s'additionnent pas. Les UE du semestre 5 totalisent
   25 crédits et celles du semestre 6 en totalisent 29, là où un semestre en compte 30.
   Les crédits sont donc repris tels quels, sans être « corrigés » : ils informent, ils
   ne servent à aucun calcul.

2. Le travail personnel n'est indiqué nulle part. Il est estimé à partir des heures
   encadrées, seule donnée cohérente de la page, selon l'effort qu'un enseignement
   demande en dehors des cours :

       mathématiques fondamentales   1,5 h par heure encadrée
       matières appliquées           1,0 h
       projet autonome               2,0 h
       langue et oraux               0,5 h

   Ces coefficients décrivent un étudiant moyen : quelqu'un qui suit les cours, refait
   les exercices et prépare ses examens sans prendre de retard. Ils sont un point de
   départ à ajuster dans la grille de suivi, pas une prescription.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from formations.models import Competency, LearningPath, LearningUnit, MetricDefinition, MetricValue, Period

FONDAMENTAL, APPLIQUE, PROJET, LANGUE = "fondamental", "appliqué", "projet", "langue"

EFFORT = {FONDAMENTAL: Decimal("1.5"), APPLIQUE: Decimal("1.0"), PROJET: Decimal("2.0"), LANGUE: Decimal("0.5")}

# (intitulé, UE d'appartenance, heures encadrées, ECTS publiés, nature, chapitres)
PROGRAMME = {
    "Semestre 5": [
        (
            "Topologie",
            "UEO Mathématiques 5",
            50,
            5,
            FONDAMENTAL,
            ["Espaces métriques et topologiques", "Continuité et homéomorphismes", "Compacité et connexité"],
        ),
        (
            "Mesure et intégration",
            "UEO Mathématiques 5",
            50,
            5,
            FONDAMENTAL,
            ["Théorie de la mesure (Lebesgue)", "Intégrale de Lebesgue", "Théorèmes de convergence"],
        ),
        (
            "Géométrie",
            "UEO Mathématiques 5",
            50,
            5,
            FONDAMENTAL,
            ["Géométrie différentielle", "Courbes et surfaces", "Courbure et géométrie riemannienne"],
        ),
        (
            "Oraux de mathématiques",
            "UEO Mathématiques 5",
            18,
            2,
            LANGUE,
            ["Exposé et argumentation", "Questions de cours"],
        ),
        (
            "Calcul scientifique 5",
            "UEO Math info 5",
            36,
            3,
            APPLIQUE,
            ["Méthodes numériques de résolution", "Programmation scientifique"],
        ),
        (
            "Algorithmique et programmation 5",
            "UEO Math info 5",
            24,
            3,
            APPLIQUE,
            ["Algorithmes fondamentaux", "Structures de données"],
        ),
        (
            "Systèmes dynamiques",
            "UEO Math info 5",
            24,
            3,
            APPLIQUE,
            ["Équations différentielles", "Stabilité et bifurcations"],
        ),
        ("Enseignement libre", "UEC Enseignements complémentaires", 24, 2, LANGUE, ["Travail personnel encadré"]),
        ("Anglais", "UEC Enseignements complémentaires", 24, 2, LANGUE, ["Compréhension écrite", "Expression orale"]),
    ],
    "Semestre 6": [
        (
            "Calcul différentiel",
            "UEO Mathématiques 6",
            50,
            5,
            FONDAMENTAL,
            [
                "Dérivées partielles et différentielles",
                "Théorèmes des fonctions implicites",
                "Optimisation différentielle",
            ],
        ),
        (
            "Mesure et probabilités",
            "UEO Mathématiques 6",
            50,
            5,
            FONDAMENTAL,
            ["Espaces probabilisés", "Variables aléatoires", "Théorèmes limites"],
        ),
        (
            "Analyse complexe",
            "UEO Mathématiques 6",
            50,
            5,
            FONDAMENTAL,
            ["Fonctions holomorphes", "Théorème de Cauchy", "Résidus et applications"],
        ),
        (
            "Oraux de mathématiques",
            "UEO Mathématiques 6",
            18,
            2,
            LANGUE,
            ["Exposé et argumentation", "Questions de cours"],
        ),
        (
            "Analyse numérique",
            "UEO Analyse numérique et statistiques",
            50,
            4,
            APPLIQUE,
            ["Interpolation et approximation", "Résolution de systèmes", "Intégration numérique"],
        ),
        (
            "Statistiques appliquées",
            "UEO Analyse numérique et statistiques",
            56,
            5,
            APPLIQUE,
            ["Estimation", "Tests d’hypothèses", "Régression"],
        ),
        (
            "Projet numérique",
            "UEO Études et recherche – Projet Numériques",
            24,
            4,
            PROJET,
            ["Conduite de projet", "Restitution écrite et orale"],
        ),
        (
            "Préprofessionnalisation",
            "UEP Préprofessionnalisation",
            44,
            4,
            LANGUE,
            ["Enseignement libre ou didactique-pédagogie"],
        ),
    ],
}

COLONNES = [
    ("ects", "ECTS", ""),
    ("encadre", "Heures encadrées", "h"),
    ("perso", "Travail personnel estimé", "h"),
]


class Command(BaseCommand):
    help = "Charge la maquette officielle de la L3 Mathématiques (Université de Guyane)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Compte propriétaire de la formation.")
        parser.add_argument("--title", default="L3 Mathématiques 2025-2026", help="Formation à alimenter.")

    @transaction.atomic
    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model

        try:
            owner = get_user_model().objects.get(username=options["username"])
        except get_user_model().DoesNotExist as exc:
            raise CommandError(f"Compte inconnu : {options['username']}") from exc

        path, _ = LearningPath.objects.get_or_create(
            owner=owner,
            title=options["title"],
            defaults={"training_type": "Licence Mathématiques · Université de Guyane", "level_label": "L3"},
        )
        metrics = {
            key: MetricDefinition.objects.update_or_create(
                path=path, key=key, defaults={"label": label, "unit_label": unit_label, "order": order}
            )[0]
            for order, (key, label, unit_label) in enumerate(COLONNES, start=1)
        }

        total_perso = Decimal(0)
        for period_order, (period_title, matieres) in enumerate(PROGRAMME.items(), start=5):
            period, _ = Period.objects.update_or_create(path=path, title=period_title, defaults={"order": period_order})
            for unit_order, (titre, ue, encadre, ects, nature, chapitres) in enumerate(matieres, start=1):
                perso = (Decimal(encadre) * EFFORT[nature]).quantize(Decimal("1"))
                total_perso += perso
                unit, _ = LearningUnit.objects.update_or_create(
                    period=period,
                    title=titre,
                    defaults={"order": unit_order, "description": f"{ue} · {nature}"},
                )
                for key, value in (("ects", ects), ("encadre", encadre), ("perso", perso)):
                    MetricValue.objects.update_or_create(
                        definition=metrics[key], unit=unit, defaults={"value": Decimal(value)}
                    )
                # Le travail personnel se répartit également entre les chapitres : c'est
                # une estimation de départ, que la grille de suivi permet d'ajuster.
                part = (perso / len(chapitres)).quantize(Decimal("0.01"))
                for chapter_order, chapitre in enumerate(chapitres, start=1):
                    competency, _ = Competency.objects.update_or_create(
                        unit=unit, title=chapitre, defaults={"order": chapter_order}
                    )
                    record, created = competency.progress_records.get_or_create(
                        owner=owner, defaults={"planned_hours": part}
                    )
                    if not created and not record.planned_hours:
                        record.planned_hours = part
                        record.save(update_fields=["planned_hours", "updated_at"])

        encadre_total = sum(m[2] for matieres in PROGRAMME.values() for m in matieres)
        self.stdout.write(
            self.style.SUCCESS(
                f"{path.title} : {LearningUnit.objects.filter(period__path=path).count()} matières, "
                f"{Competency.objects.filter(unit__period__path=path).count()} chapitres, "
                f"{encadre_total} h encadrées, {total_perso} h de travail personnel estimé."
            )
        )
        self.stdout.write(
            "Rappel : les ECTS publiés par l'université ne totalisent pas 30 par semestre ; "
            "ils sont repris tels quels et n'entrent dans aucun calcul."
        )
