"""Le temps travaillé propose un niveau de maîtrise ; il ne le décide pas.

La règle demandée : au quart du travail personnel estimé, la compétence est « découverte » ;
à la moitié elle est « en cours » ; aux trois quarts « acquise » ; au bout « maîtrisée ».

Le plan initial posait que le temps ne détermine jamais le niveau, et ce module ne revient
pas dessus — il l'amende. Ce que le temps produit est une *proposition*, marquée comme
telle par ``ProgressRecord.Origin.SUGGESTED`` (« Suggéré, à confirmer »), champ prévu dès
l'origine pour cet usage et jamais écrit jusqu'ici. Cinq garde-fous séparent la proposition
de la décision :

1. sans estimation, aucune proposition — il n'y a pas de dénominateur, et une compétence
   qu'on n'a pas estimée ne progresse pas toute seule ;
2. le palier ne fait que monter — corriger une estimation à la hausse, ce qui arrive dès
   qu'on découvre qu'un chapitre est plus long que prévu, ne doit pas rétrograder une
   compétence déjà travaillée ;
3. le niveau posé par le temps est marqué « suggéré », et se distingue à l'écran d'un
   niveau déclaré ;
4. ce qui a été déclaré à la main n'est jamais défait : le palier cesse alors de s'écrire
   et devient une proposition affichée. Sans cela, une correction serait annulée à la
   session Sablier suivante, et « l'utilisateur peut toujours modifier » serait faux ;
5. une proposition n'horodate pas ``assessed_at`` : ce champ signifie « dernière
   autoévaluation », et personne ne s'est autoévalué parce que du temps a passé.
"""

from __future__ import annotations

from decimal import Decimal

# Un palier par quart du temps estimé. L'ordre des seuils correspond aux niveaux 1 à 4 de
# ``ProgressRecord.Mastery`` : découvert, en cours, acquis, maîtrisé.
QUARTERS = (Decimal("0.25"), Decimal("0.50"), Decimal("0.75"), Decimal("1"))

# Ce que chaque niveau veut dire, en termes de ce qu'on sait faire.
#
# Cinq niveaux nommés sans critère observable, c'est une échelle qui dérive : la frontière
# entre « acquis » et « maîtrisé » se déplace avec la fatigue et l'humeur, et les totaux de
# la grille cessent d'être comparables d'un mois à l'autre. Les descripteurs sont formulés
# à la première personne et en termes d'action — « je sais refaire », « je sais expliquer »
# — parce qu'une autoévaluation se cale sur ce qu'on a fait, pas sur ce qu'on ressent.
#
# Ils comptent doublement depuis que le temps propose des paliers : c'est à partir de cette
# échelle que la proposition est jugée, acceptée ou corrigée.
MASTERY_DESCRIPTIONS = {
    0: "Je n’ai pas encore ouvert le sujet.",
    1: "J’ai vu de quoi il s’agit. Je ne saurais pas le refaire seul.",
    2: "Je sais le refaire en m’aidant du cours ou d’un exemple.",
    3: "Je sais le refaire seul sur un exercice que je n’ai jamais vu.",
    4: "Je sais l’expliquer à quelqu’un et le transposer à un autre problème.",
}

# Poids d'une compétence dans la progression d'ensemble. Une compétence principale dans au
# moins une matière est au programme de cette matière ; une compétence seulement rappelée
# ailleurs est un renfort. Les compter à égalité laissait une compétence secondaire peser
# autant qu'une compétence centrale dans le pourcentage du tableau de bord.
PRIMARY_WEIGHT = 2
SECONDARY_WEIGHT = 1


def level_for_ratio(ratio: Decimal) -> int:
    """Le niveau qu'implique une fraction du temps estimé, de 0 à 4."""
    return sum(1 for threshold in QUARTERS if ratio >= threshold)


def time_ratio(record) -> Decimal | None:
    """La part du temps estimé qui est écoulée, ou ``None`` faute d'estimation.

    Le numérateur est ``actual_hours`` : le total que la grille affiche déjà, saisie
    manuelle et sessions Sablier confondues. Compter l'un sans l'autre ferait dépendre le
    palier de la manière dont le temps a été enregistré, ce qui n'a aucun sens pour
    l'étudiant.
    """
    planned = record.planned_hours or Decimal(0)
    if planned <= 0:
        return None
    return (record.actual_hours or Decimal(0)) / planned


def suggested_level(record) -> int | None:
    """Le niveau proposé par le temps, ou ``None`` s'il n'y a rien à proposer.

    ``None`` couvre les trois cas où la question ne se pose pas : pas d'estimation, palier
    déjà atteint ou dépassé par le niveau courant, et formation qui a coupé les paliers.
    Le contrôle de la formation vient en dernier parce qu'il peut coûter une requête ;
    les deux premiers l'évitent sur l'immense majorité des lignes.
    """
    ratio = time_ratio(record)
    if ratio is None:
        return None
    level = level_for_ratio(ratio)
    if level <= record.mastery_level:
        return None
    return level if path_allows_suggestions(record) else None


def path_allows_suggestions(record) -> bool:
    """La formation accepte-t-elle les paliers de temps ?

    Une compétence orpheline — cas des tests unitaires et des imports en cours — est
    traitée comme permissive : mieux vaut proposer que se taire sur une donnée incomplète.
    """
    competency = getattr(record, "competency", None)
    path = getattr(competency, "path", None)
    return True if path is None else path.time_suggests_level


def accepts_automatic_level(record) -> bool:
    """Le palier peut-il s'écrire tout seul sur cette ligne ?

    Oui tant que personne n'a déclaré de niveau à la main — ``assessed_at`` vide — ou tant
    que le niveau en place vient lui-même d'un palier. Non dès qu'une appréciation
    personnelle existe : c'est elle qui fait foi, et le palier passe en proposition.
    """
    return record.assessed_at is None or record.level_origin == record.Origin.SUGGESTED


def level_from_result(result) -> int | None:
    """Le niveau que suggère une note, ou ``None`` quand elle ne dit rien.

    La même échelle par quarts que pour le temps : une source différente, une règle
    identique, pour que « acquis » veuille dire la même chose d'où qu'il vienne. Une
    absence et une évaluation sans note ne suggèrent rien — il n'y a pas de résultat à
    interpréter, et en inventer un serait pire que se taire.

    La proposition ne descend jamais : une mauvaise note dit qu'il reste du travail, pas
    que ce qui était su a été oublié. C'est à l'étudiant de baisser son niveau s'il le
    juge, et l'écran le lui propose ailleurs.
    """
    ratio = result.ratio
    return None if ratio is None else level_for_ratio(ratio)


def weighted_progress(records, primary_ids) -> int:
    """La progression d'ensemble, en pourcentage, pondérée par l'importance des compétences.

    Deux différences avec un simple « acquises sur total ». Le niveau entre pour ce qu'il
    vaut plutôt qu'en tout ou rien — sans quoi passer de « en cours » à « acquis » ferait
    bondir le chiffre de vingt-cinq points d'un coup et le reste du temps ne montrerait
    aucun mouvement. Et une compétence principale pèse le double d'une compétence
    seulement rappelée.
    """
    total = 0
    obtained = 0
    for record in records:
        weight = PRIMARY_WEIGHT if record.competency_id in primary_ids else SECONDARY_WEIGHT
        total += weight * 4
        obtained += weight * record.mastery_level
    return round(obtained * 100 / total) if total else 0


def hours_gap(record) -> str:
    """Ce que l'écart entre le temps estimé et le temps passé mérite qu'on en dise.

    Estimer une charge de travail est une compétence qui s'acquiert par rétroaction : sans
    retour, elle ne progresse pas. La phrase constate, elle ne juge pas — dépasser une
    estimation n'est pas une faute, et rester en dessous n'est pas un mérite.
    """
    planned = record.planned_hours or Decimal(0)
    actual = record.actual_hours or Decimal(0)
    if planned <= 0 or actual <= 0:
        return ""
    ratio = actual / planned
    if ratio >= Decimal("1.25"):
        return f"Vous aviez estimé {_hours(planned)} h, vous en êtes à {_hours(actual)} h."
    if ratio <= Decimal("0.5"):
        return f"Il reste {_hours(planned - actual)} h sur les {_hours(planned)} h que vous aviez estimées."
    return ""


def _hours(value: Decimal) -> str:
    """Le nombre débarrassé de ses zéros inutiles, sans notation exponentielle.

    ``normalize()`` seul rendrait « 2.5E+1 » pour 25 ; le format ``f`` le déplie.
    """
    return format(value.normalize(), "f")


def pending_suggestion(record) -> int | None:
    """Le niveau proposé qu'il reste à accepter, pour l'affichage.

    Vaut ``None`` quand le palier s'est appliqué tout seul : il n'y a alors plus rien à
    proposer, seulement un niveau suggéré à confirmer.
    """
    if accepts_automatic_level(record):
        return None
    return suggested_level(record)
