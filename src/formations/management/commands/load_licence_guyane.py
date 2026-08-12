"""Charge la maquette de la Licence Mathématiques de l'Université de Guyane.

Source : https://www.univ-guyane.fr/choisir-sa-formation/dfr-sciences-et-technologies/licence-mathematiques/

Trois réserves, assumées ici plutôt que masquées :

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

3. LE DÉCOUPAGE EN COMPÉTENCES N'EST PAS PUBLIÉ PAR L'UNIVERSITÉ. La page ne donne que
   des intitulés de matières. Les compétences ci-dessous sont une proposition
   pédagogique : le programme usuel d'une L3 de mathématiques en France, découpé en
   savoir-faire d'une granularité utilisable pour se suivre. Un cours de topologie de
   50 heures ne se résume pas à trois lignes — c'est une douzaine de notions qu'on
   maîtrise ou non séparément, et c'est cette granularité qui permet de repérer laquelle
   bloque. Chaque intitulé reste modifiable, supprimable, et complétable par l'étudiant
   selon le cours réellement suivi.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from formations.models import (
    Competency,
    LearningGroup,
    LearningPath,
    LearningUnit,
    MetricDefinition,
    MetricValue,
    Period,
    ProgressRecord,
    UnitCompetency,
)
from formations.resource_services import sync_path_curated_resources

FONDAMENTAL, APPLIQUE, PROJET, LANGUE = "fondamental", "appliqué", "projet", "langue"

EFFORT = {FONDAMENTAL: Decimal("1.5"), APPLIQUE: Decimal("1.0"), PROJET: Decimal("2.0"), LANGUE: Decimal("0.5")}

# Compétences transversales des oraux : le module revient aux deux semestres à l'identique.
ORAUX = [
    "Choisir et délimiter un sujet d’exposé",
    "Construire un plan progressif",
    "Rédiger une démonstration au tableau, lisiblement",
    "Énoncer précisément une définition et un théorème",
    "Choisir un exemple et un contre-exemple éclairants",
    "Répondre à une question de cours sans préparation",
    "Gérer son temps et l’espace du tableau",
    "Reconnaître et corriger une erreur en direct",
]

# L'ancien bloc de « Géométrie » décrivait par erreur un cours de géométrie
# différentielle (courbes, surfaces, courbures). Ces intitulés ne font pas partie du
# programme affine et euclidien visé. La liste est conservée uniquement pour nettoyer
# prudemment les formations déjà chargées ; elle ne sert jamais à fabriquer de nouvelles
# compétences.
LEGACY_DIFFERENTIAL_GEOMETRY_COMPETENCIES = [
    "Paramétrer une courbe et étudier sa régularité",
    "Calculer la longueur d’un arc",
    "Reparamétrer une courbe par l’abscisse curviligne",
    "Construire le repère de Frenet d’une courbe plane",
    "Calculer la courbure d’une courbe plane et interpréter son signe",
    "Déterminer cercle osculateur et développée",
    "Construire le repère de Frenet d’une courbe gauche",
    "Calculer courbure et torsion d’une courbe de l’espace",
    "Utiliser le théorème fondamental des courbes",
    "Étudier une courbe fermée, son indice et l’inégalité isopérimétrique",
    "Paramétrer une surface régulière et déterminer son plan tangent",
    "Changer de paramétrage et vérifier la régularité",
    "Calculer la première forme fondamentale",
    "Calculer longueurs, angles et aires sur une surface",
    "Déterminer l’application de Gauss et orienter une surface",
    "Calculer la seconde forme fondamentale",
    "Déterminer courbures et directions principales",
    "Calculer courbure de Gauss et courbure moyenne",
    "Classer un point : elliptique, hyperbolique, parabolique, planaire",
    "Énoncer et exploiter le theorema egregium de Gauss",
    "Reconnaître une isométrie locale et une application conforme",
    "Étudier les surfaces réglées et les surfaces de révolution",
    "Écrire les équations des géodésiques",
    "Déterminer les géodésiques du plan et de la sphère",
    "Utiliser la dérivée covariante et le transport parallèle",
    "Appliquer le théorème de Gauss-Bonnet local",
    "Situer ces notions dans le cadre des variétés riemanniennes",
]

# Granularité issue des gestes distincts du programme L3, et non du nombre de lignes de
# l'ancien bloc. Les quatre parties suivent le syllabus « Géométrie affine et
# euclidienne » de Lille : affine, euclidien, coniques/quadriques et géométrie plane.
GEOMETRY_COMPETENCIES = [
    # Espaces et calcul affine
    "Modéliser un espace affine et utiliser la relation de Chasles",
    "Reconnaître un sous-espace affine et déterminer sa direction et sa dimension",
    "Étudier l’intersection et le parallélisme de sous-espaces affines",
    "Déterminer l’enveloppe affine d’une famille de points et son équation",
    "Caractériser l’indépendance affine et reconnaître un repère affine",
    "Calculer les coordonnées d’un point et effectuer un changement de repère affine",
    "Écrire des équations paramétriques et cartésiennes de droites, plans et hyperplans",
    "Définir une application affine et déterminer son application linéaire associée",
    "Écrire la représentation matricielle d’une application affine",
    "Composer et inverser des applications affines",
    "Déterminer l’ensemble des points fixes d’une application affine",
    "Construire une translation et une homothétie affines",
    "Construire une projection affine parallèlement à une direction",
    "Construire une symétrie affine et identifier ses sous-espaces caractéristiques",
    "Exploiter les invariants affines : alignement, parallélisme, rapports, aires et volumes",
    # Barycentres et convexité
    "Déterminer l’existence d’un barycentre et le calculer",
    "Utiliser l’associativité des barycentres et les barycentres partiels",
    "Calculer des coordonnées barycentriques dans un simplexe",
    "Caractériser une application affine par la conservation des barycentres",
    "Reconnaître une combinaison convexe et déterminer une enveloppe convexe",
    # Structure euclidienne et projections orthogonales
    "Manipuler produit scalaire, norme, distance et angle dans un espace euclidien",
    "Déterminer l’orthogonal d’un sous-espace et une décomposition orthogonale",
    "Construire une base orthonormée par le procédé de Gram-Schmidt",
    "Calculer la projection orthogonale sur un sous-espace vectoriel",
    "Calculer la projection orthogonale sur un sous-espace affine et la distance à ce sous-espace",
    "Calculer la distance entre deux sous-espaces affines",
    "Décrire médiatrices, sphères et lieux d’équidistance par le produit scalaire",
    "Calculer orientations, déterminants, aires et volumes dans un repère orthonormé",
    # Isométries et similitudes
    "Caractériser une isométrie linéaire et reconnaître une matrice orthogonale",
    "Décomposer une transformation orthogonale en réflexions et rotations",
    "Démontrer qu’une isométrie d’un espace affine euclidien est affine",
    "Décomposer canoniquement une isométrie affine en translation et isométrie à point fixe",
    "Classifier les isométries affines du plan",
    "Classifier les isométries affines de l’espace de dimension trois",
    "Déterminer le groupe des isométries laissant stable une figure",
    "Classifier les similitudes directes et indirectes du plan à l’aide des complexes",
    "Résoudre un problème de géométrie plane par les nombres complexes",
    "Établir des relations métriques et trigonométriques dans le triangle et le cercle",
    # Coniques et quadriques
    "Caractériser une conique par foyer, directrice et excentricité",
    "Réduire l’équation d’une conique et la classifier dans un repère adapté",
    "Interpréter les coniques comme sections planes d’un cône de révolution",
    "Réduire et classifier une quadrique par transformations affines et euclidiennes",
    "Déterminer centre, axes et éléments de symétrie d’une quadrique",
    "Reconnaître ellipsoïdes, hyperboloïdes, paraboloïdes, cylindres et cônes",
]

# (intitulé, UE d'appartenance, heures encadrées, ECTS publiés, nature, compétences)
#
# Le découpage suit le programme usuel d'une L3 de mathématiques : chaque ligne est un
# savoir-faire qu'on maîtrise ou non séparément. C'est cette granularité qui permet de
# répondre à « qu'est-ce qui bloque ? » autrement que par le nom du cours.
PROGRAMME = {
    "Semestre 5": [
        (
            "Topologie",
            "UEO Mathématiques 5",
            50,
            5,
            FONDAMENTAL,
            [
                "Reconnaître une distance et construire des exemples (discrète, sup, produit)",
                "Manipuler boules ouvertes, boules fermées et voisinages",
                "Comparer deux distances et reconnaître leur équivalence topologique",
                "Déterminer les ouverts et les fermés d’un espace métrique",
                "Calculer intérieur, adhérence et frontière d’une partie",
                "Caractériser une partie dense et un espace séparable",
                "Vérifier les axiomes d’une topologie sur un ensemble",
                "Construire une topologie par une base ou une prébase d’ouverts",
                "Munir une partie de la topologie induite",
                "Construire la topologie produit d’un nombre fini d’espaces",
                "Reconnaître un espace séparé et en tirer l’unicité des limites",
                "Étudier la convergence d’une suite et ses valeurs d’adhérence",
                "Caractériser l’adhérence par les suites en espace métrique",
                "Démontrer la continuité en un point, puis globalement",
                "Caractériser la continuité par les images réciproques d’ouverts",
                "Caractériser la continuité par les suites",
                "Distinguer continuité, continuité uniforme et lipschitzianité",
                "Reconnaître un homéomorphisme et exhiber un invariant topologique",
                "Démontrer qu’une suite est de Cauchy",
                "Établir la complétude d’un espace, ou son défaut",
                "Compléter un espace métrique et exploiter la densité",
                "Appliquer le théorème du point fixe de Banach",
                "Appliquer le théorème de Baire",
                "Établir la compacité par la propriété de Borel-Lebesgue",
                "Établir la compacité séquentielle (Bolzano-Weierstrass)",
                "Caractériser les compacts de R^n (Heine-Borel)",
                "Exploiter la compacité : image continue, extrema atteints",
                "Appliquer le théorème de Heine sur la continuité uniforme",
                "Démontrer la connexité d’une partie",
                "Distinguer connexité et connexité par arcs, déterminer les composantes",
                "Comparer des normes et conclure en dimension finie",
                "Étudier la continuité d’une application linéaire et calculer sa norme",
                "Reconnaître la convergence uniforme et la complétude de C(K)",
                "Appliquer un théorème d’approximation ou de compacité fonctionnelle",
            ],
        ),
        (
            "Mesure et intégration",
            "UEO Mathématiques 5",
            50,
            5,
            FONDAMENTAL,
            [
                "Reconnaître une tribu et déterminer la tribu engendrée",
                "Manipuler la tribu borélienne de R et de R^n",
                "Construire une tribu produit",
                "Reconnaître une mesure positive et ses propriétés élémentaires",
                "Utiliser croissance, sous-additivité et continuité monotone d’une mesure",
                "Construire et utiliser la mesure de Lebesgue sur R et R^n",
                "Manipuler les ensembles négligeables et les propriétés « presque partout »",
                "Reconnaître mesure de comptage, mesure de Dirac et mesure à densité",
                "Démontrer la mesurabilité d’une fonction",
                "Utiliser la stabilité de la mesurabilité par sup, inf et limites",
                "Approcher une fonction mesurable par des fonctions étagées",
                "Intégrer une fonction étagée positive",
                "Définir l’intégrale d’une fonction mesurable positive",
                "Appliquer le théorème de convergence monotone",
                "Appliquer le lemme de Fatou",
                "Définir l’intégrabilité d’une fonction de signe quelconque",
                "Appliquer le théorème de convergence dominée",
                "Dériver ou intégrer sous le signe intégral",
                "Comparer intégrale de Riemann et intégrale de Lebesgue",
                "Intégrer par rapport à une mesure image ou à une mesure à densité",
                "Construire la mesure produit et appliquer le théorème de Tonelli",
                "Appliquer le théorème de Fubini",
                "Effectuer un changement de variables dans une intégrale multiple",
                "Reconnaître les espaces L^p et leurs semi-normes",
                "Appliquer les inégalités de Hölder et de Minkowski",
                "Démontrer la complétude des espaces L^p",
                "Utiliser la densité des fonctions continues à support compact",
                "Distinguer convergence en norme, en mesure et presque partout",
                "Calculer une intégrale par interversion série-intégrale",
            ],
        ),
        (
            "Géométrie",
            "UEO Mathématiques 5",
            50,
            5,
            FONDAMENTAL,
            GEOMETRY_COMPETENCIES,
        ),
        ("Oraux de mathématiques", "UEO Mathématiques 5", 18, 2, LANGUE, ORAUX),
        (
            "Calcul scientifique 5",
            "UEO Math info 5",
            36,
            3,
            APPLIQUE,
            [
                "Comprendre la représentation en virgule flottante et l’epsilon machine",
                "Distinguer erreur absolue, relative, de troncature et d’arrondi",
                "Reconnaître une annulation catastrophique et la contourner",
                "Résoudre f(x)=0 par dichotomie et majorer le nombre d’itérations",
                "Résoudre f(x)=0 par itération de point fixe et étudier la convergence",
                "Appliquer la méthode de Newton, puis la méthode de la sécante",
                "Déterminer l’ordre de convergence d’une méthode itérative",
                "Résoudre un système linéaire par élimination de Gauss avec pivot",
                "Utiliser la décomposition LU et les résolutions triangulaires",
                "Utiliser la décomposition de Cholesky sur une matrice définie positive",
                "Mettre en œuvre les méthodes de Jacobi et de Gauss-Seidel",
                "Étudier la convergence d’une méthode itérative par le rayon spectral",
                "Calculer un conditionnement et en déduire la sensibilité du résultat",
                "Programmer un calcul vectorisé en Python et NumPy",
                "Représenter et valider graphiquement un résultat numérique",
                "Comparer deux méthodes par coût, précision et robustesse",
            ],
        ),
        (
            "Algorithmique et programmation 5",
            "UEO Math info 5",
            24,
            3,
            APPLIQUE,
            [
                "Évaluer une complexité en temps dans le pire cas",
                "Évaluer une complexité en espace",
                "Utiliser les notations O, Θ et Ω",
                "Implémenter les tris quadratiques et en montrer les limites",
                "Implémenter tri fusion et tri rapide",
                "Établir la borne inférieure des tris par comparaison",
                "Implémenter et justifier la recherche dichotomique",
                "Utiliser piles et files à bon escient",
                "Implémenter listes chaînées et tableaux dynamiques",
                "Utiliser un arbre binaire de recherche",
                "Utiliser une table de hachage et gérer les collisions",
                "Écrire un algorithme récursif et prouver sa terminaison",
                "Appliquer diviser-pour-régner et le théorème maître",
                "Parcourir un graphe en largeur et en profondeur",
                "Appliquer un algorithme de plus court chemin",
                "Tester, tracer et mettre au point un programme",
            ],
        ),
        (
            "Systèmes dynamiques",
            "UEO Math info 5",
            24,
            3,
            APPLIQUE,
            [
                "Résoudre une équation différentielle linéaire scalaire",
                "Résoudre un système linéaire par exponentielle de matrice",
                "Classer les systèmes linéaires plans selon le spectre",
                "Appliquer le théorème de Cauchy-Lipschitz local",
                "Discuter existence globale et explosion en temps fini",
                "Utiliser le lemme de Grönwall",
                "Tracer et lire un portrait de phase",
                "Déterminer les points d’équilibre d’un système",
                "Linéariser autour d’un équilibre et conclure sur sa nature",
                "Étudier la stabilité par une fonction de Lyapunov",
                "Identifier orbites périodiques et cycles limites",
                "Appliquer le théorème de Poincaré-Bendixson",
                "Étudier une suite récurrente et ses points fixes",
                "Reconnaître une bifurcation nœud-col, transcritique ou de Hopf",
            ],
        ),
        (
            "Enseignement libre",
            "UEC Enseignements complémentaires",
            24,
            2,
            LANGUE,
            [
                "Choisir et délimiter un sujet",
                "Établir une bibliographie de départ",
                "Tenir un rythme de travail personnel régulier",
                "Prendre des notes réutilisables",
                "Restituer ce qui a été appris",
            ],
        ),
        (
            "Anglais",
            "UEC Enseignements complémentaires",
            24,
            2,
            LANGUE,
            [
                "Lire un énoncé mathématique en anglais",
                "Lire un article ou un chapitre de manuel",
                "Maîtriser le vocabulaire mathématique anglais",
                "Comprendre un exposé oral en anglais",
                "Présenter un travail à l’oral en anglais",
                "Rédiger un résumé écrit",
                "Participer à une discussion technique",
                "Rédiger un courriel professionnel",
            ],
        ),
    ],
    "Semestre 6": [
        (
            "Calcul différentiel",
            "UEO Mathématiques 6",
            50,
            5,
            FONDAMENTAL,
            [
                "Reconnaître une application linéaire continue et calculer sa norme",
                "Définir la différentiabilité en un point",
                "Calculer une différentielle et l’identifier à une matrice jacobienne",
                "Calculer dérivées partielles et dérivées directionnelles",
                "Distinguer différentiabilité, dérivées partielles et continuité",
                "Appliquer la règle de composition des différentielles",
                "Reconnaître une application de classe C¹",
                "Reconnaître une application de classe C^k et appliquer le lemme de Schwarz",
                "Appliquer l’inégalité des accroissements finis",
                "Écrire la formule de Taylor-Young à plusieurs variables",
                "Écrire une formule de Taylor avec reste intégral",
                "Calculer un gradient et l’interpréter géométriquement",
                "Calculer une matrice hessienne",
                "Appliquer le théorème d’inversion locale",
                "Passer de l’inversion locale à l’inversion globale",
                "Appliquer le théorème des fonctions implicites",
                "Reconnaître un difféomorphisme",
                "Déterminer les points critiques d’une fonction",
                "Classer un point critique par la hessienne",
                "Rechercher les extrema d’une fonction sur un compact",
                "Traiter un problème d’extrema liés par multiplicateurs de Lagrange",
                "Reconnaître et paramétrer une sous-variété de R^n",
                "Déterminer l’espace tangent à une sous-variété",
                "Manipuler une forme différentielle de degré 1",
                "Distinguer forme fermée et forme exacte",
                "Résoudre une équation aux dérivées partielles par changement de variables",
            ],
        ),
        (
            "Mesure et probabilités",
            "UEO Mathématiques 6",
            50,
            5,
            FONDAMENTAL,
            [
                "Construire un espace probabilisé",
                "Utiliser les propriétés élémentaires d’une probabilité",
                "Appliquer la formule des probabilités totales et celle de Bayes",
                "Caractériser l’indépendance d’événements",
                "Définir une variable aléatoire et déterminer sa loi",
                "Manipuler une fonction de répartition",
                "Reconnaître une loi discrète et calculer avec elle",
                "Reconnaître une loi à densité et calculer avec elle",
                "Identifier les lois discrètes usuelles et leur domaine d’emploi",
                "Identifier les lois continues usuelles",
                "Calculer une espérance et exploiter sa linéarité",
                "Calculer variance, écart-type et moments",
                "Appliquer le théorème de transfert",
                "Appliquer les inégalités de Markov et de Bienaymé-Tchebychev",
                "Appliquer les inégalités de Cauchy-Schwarz et de Jensen",
                "Manipuler un vecteur aléatoire et sa loi conjointe",
                "Déterminer lois marginales et lois conditionnelles",
                "Caractériser l’indépendance de variables aléatoires",
                "Calculer covariance et coefficient de corrélation",
                "Déterminer la loi d’une somme par convolution",
                "Utiliser fonction génératrice et fonction caractéristique",
                "Reconnaître un vecteur gaussien et utiliser ses propriétés",
                "Distinguer convergence en loi, en probabilité, presque sûre et L^p",
                "Appliquer la loi faible des grands nombres",
                "Appliquer la loi forte des grands nombres",
                "Appliquer le théorème central limite",
                "Appliquer le lemme de Borel-Cantelli",
                "Calculer une espérance conditionnelle",
            ],
        ),
        (
            "Analyse complexe",
            "UEO Mathématiques 6",
            50,
            5,
            FONDAMENTAL,
            [
                "Manipuler module, argument et géométrie du plan complexe",
                "Reconnaître une fonction d’une variable complexe et ses parties réelle et imaginaire",
                "Définir la C-dérivabilité et l’holomorphie",
                "Vérifier les équations de Cauchy-Riemann",
                "Relier holomorphie et fonctions harmoniques",
                "Déterminer le rayon de convergence d’une série entière",
                "Dériver et intégrer une série entière terme à terme",
                "Manipuler exponentielle et fonctions trigonométriques complexes",
                "Construire une détermination du logarithme et des puissances",
                "Calculer une intégrale curviligne le long d’un chemin",
                "Appliquer le théorème de Cauchy sur un ouvert convexe",
                "Construire une primitive d’une fonction holomorphe",
                "Appliquer la version homotopique du théorème de Cauchy",
                "Appliquer la formule intégrale de Cauchy",
                "Établir l’analyticité d’une fonction holomorphe",
                "Appliquer les inégalités de Cauchy",
                "Appliquer le théorème de Liouville et en déduire le théorème fondamental de l’algèbre",
                "Appliquer le principe du maximum",
                "Appliquer le principe des zéros isolés et prolonger analytiquement",
                "Classer une singularité isolée",
                "Développer une fonction en série de Laurent",
                "Calculer un résidu",
                "Appliquer le théorème des résidus",
                "Calculer une intégrale réelle par la méthode des résidus",
                "Compter les zéros par le théorème de Rouché",
                "Reconnaître une transformation conforme et manipuler les homographies",
            ],
        ),
        ("Oraux de mathématiques", "UEO Mathématiques 6", 18, 2, LANGUE, ORAUX),
        (
            "Analyse numérique",
            "UEO Analyse numérique et statistiques",
            50,
            4,
            APPLIQUE,
            [
                "Construire le polynôme d’interpolation de Lagrange",
                "Utiliser la forme de Newton et les différences divisées",
                "Majorer l’erreur d’interpolation",
                "Reconnaître le phénomène de Runge et le rôle des nœuds de Tchebychev",
                "Interpoler par la méthode de Hermite",
                "Construire une spline cubique",
                "Approcher une fonction au sens des moindres carrés",
                "Utiliser une base de polynômes orthogonaux",
                "Appliquer les formules du rectangle, du trapèze et de Simpson",
                "Majorer une erreur de quadrature et composer une formule",
                "Appliquer une quadrature de Gauss",
                "Traiter une intégrale singulière ou sur un intervalle non borné",
                "Intégrer une équation différentielle par Euler explicite et implicite",
                "Mettre en œuvre une méthode de Runge-Kutta d’ordre 4",
                "Étudier consistance, stabilité et convergence d’un schéma",
                "Reconnaître un problème raide et justifier un schéma implicite",
                "Utiliser la décomposition QR et le procédé de Gram-Schmidt",
                "Utiliser la décomposition de Cholesky",
                "Approcher une valeur propre par la méthode de la puissance",
                "Approcher le spectre par la méthode QR",
                "Estimer une erreur a posteriori et un ordre de convergence observé",
                "Choisir une méthode selon le coût et la précision visée",
            ],
        ),
        (
            "Statistiques appliquées",
            "UEO Analyse numérique et statistiques",
            56,
            5,
            APPLIQUE,
            [
                "Décrire une distribution par ses indicateurs",
                "Représenter des données par histogramme, boîte et nuage de points",
                "Reconnaître un échantillon aléatoire simple",
                "Déterminer la loi de la moyenne et de la variance empiriques",
                "Utiliser les lois du khi-deux, de Student et de Fisher",
                "Construire un estimateur ponctuel",
                "Évaluer le biais d’un estimateur",
                "Comparer des estimateurs par le risque quadratique",
                "Établir la convergence d’un estimateur",
                "Appliquer la méthode des moments",
                "Appliquer la méthode du maximum de vraisemblance",
                "Utiliser l’information de Fisher et la borne de Cramér-Rao",
                "Construire un intervalle de confiance pour une moyenne",
                "Construire un intervalle de confiance pour une proportion et pour une variance",
                "Poser un test d’hypothèses et identifier ses deux risques",
                "Déterminer une région critique et calculer une puissance",
                "Mener un test de Student sur une ou deux moyennes",
                "Mener un test du khi-deux d’ajustement et d’indépendance",
                "Mener un test de Fisher de comparaison de variances",
                "Choisir un test non paramétrique adapté",
                "Interpréter une p-valeur sans la surinterpréter",
                "Ajuster une régression linéaire simple et tester ses coefficients",
                "Ajuster une régression multiple et diagnostiquer les résidus",
                "Mener une analyse de la variance à un facteur",
                "Conduire une étude complète sur logiciel et rédiger ses conclusions",
            ],
        ),
        (
            "Projet numérique",
            "UEO Études et recherche – Projet Numériques",
            24,
            4,
            PROJET,
            [
                "Définir un sujet et des objectifs atteignables",
                "Rechercher et lire la documentation nécessaire",
                "Choisir méthodes et outils, et justifier ce choix",
                "Découper le travail et tenir un calendrier",
                "Implémenter par étapes vérifiables",
                "Valider les résultats et discuter leurs limites",
                "Rédiger un rapport structuré et reproductible",
                "Soutenir le projet à l’oral et répondre aux questions",
            ],
        ),
        (
            "Préprofessionnalisation",
            "UEP Préprofessionnalisation",
            44,
            4,
            LANGUE,
            [
                "Situer les métiers de l’enseignement, de la recherche et de l’entreprise",
                "Connaître les voies d’accès aux concours de l’enseignement",
                "Utiliser les notions de base de la didactique des mathématiques",
                "Analyser un programme scolaire et ses attendus",
                "Construire la progression d’une séquence",
                "Concevoir une séance et formuler ses objectifs",
                "Choisir et concevoir une évaluation",
                "Analyser une erreur d’élève et y répondre",
                "Prendre en compte l’hétérogénéité d’un groupe",
                "Animer une séance et gérer un groupe",
                "Utiliser un outil numérique en classe",
                "Observer une pratique et en rendre compte",
                "Construire un CV et une lettre de motivation",
                "Préparer un entretien",
                "Formuler son projet professionnel à moyen terme",
            ],
        ),
    ],
}

COLONNES = [
    ("ects", "ECTS", ""),
    ("encadre", "Heures encadrées", "h"),
    ("perso", "Travail personnel estimé", "h"),
]


# Une durée se lit avant de s'additionner : « 2 h 30 » se retient, « 2 h 21 » ne veut rien
# dire, et « 2,25 h » se lit de travers : on y voit 2 h 25 là où il s'agit de 2 h 15. Le
# temps par compétence tombe donc sur l'heure ou la demi-heure, arrondi au-dessus. Le
# total dépasse l'estimation du module — c'est assumé, et annoncé dans la sortie.
HALF_HOUR = Decimal("0.5")


def readable_share(hours: Decimal, count: int) -> Decimal:
    """Part par compétence, arrondie à la demi-heure supérieure."""
    exact = hours / count
    return (exact / HALF_HOUR).to_integral_value(rounding="ROUND_CEILING") * HALF_HOUR


def expected_titles() -> dict[str, set[str]]:
    """Les intitulés attendus par matière, tels que cette maquette les déclare."""
    titles: dict[str, set[str]] = {}
    for matieres in PROGRAMME.values():
        for titre, _ue, _encadre, _ects, _nature, competences in matieres:
            titles.setdefault(titre, set()).update(competences)
    return titles


def declared_titles() -> set[str]:
    """Tous les intitulés de la maquette, sans distinction de matière.

    Une compétence peut être déclarée par plusieurs matières — les oraux reviennent aux
    deux semestres. Elle n'appartient donc plus à une seule, et sa légitimité s'apprécie
    au niveau de la maquette entière.
    """
    return {title for titles in expected_titles().values() for title in titles}


def prune_obsolete(path, owner) -> int:
    """Supprime les compétences d'un ancien découpage sur lesquelles rien n'a été fait.

    Une compétence porte du travail dès qu'elle a un niveau, un temps réel, un
    commentaire, une ressource ou une session : elle est alors conservée, même absente de
    la maquette, car c'est l'étudiant qui l'a fait vivre. Le reste n'est qu'un intitulé
    laissé par un chargement précédent.
    """
    declared = declared_titles()
    removable = []
    queryset = Competency.objects.filter(path=path).prefetch_related("resources", "progress_records")
    for competency in queryset:
        if competency.title in declared:
            continue
        if competency.resources.exists() or competency.focus_sessions.exists():
            continue
        if any(r.mastery_level or r.actual_hours or r.notes.strip() for r in competency.progress_records.all()):
            continue
        removable.append(competency.pk)
    if not removable:
        return 0
    Competency.objects.filter(pk__in=removable).delete()
    return len(removable)


def retire_legacy_geometry(path, owner) -> tuple[int, int]:
    """Retire le bloc différentiel erroné sans effacer un travail réel de l'étudiant.

    Les recommandations créées par MyENT ne comptent pas comme du travail personnel :
    elles sont détachées avant la décision. Une note, une ressource personnelle, un temps
    réalisé, un niveau ou une séance protège en revanche l'ancienne compétence.
    """
    removed = preserved = 0
    competencies = Competency.objects.filter(
        path=path,
        title__in=LEGACY_DIFFERENTIAL_GEOMETRY_COMPETENCIES,
    ).prefetch_related("resources", "progress_records")
    for competency in competencies:
        managed_ids = list(
            competency.resources.filter(owner=owner, legacy_source="curated").values_list("pk", flat=True)
        )
        if managed_ids:
            competency.resources.remove(*managed_ids)
        has_recorded_work = any(
            record.mastery_level or record.actual_hours or record.notes.strip()
            for record in competency.progress_records.all()
        )
        has_recorded_work = (
            has_recorded_work or competency.resources.exists() or competency.focus_sessions.filter(owner=owner).exists()
        )
        if has_recorded_work:
            preserved += 1
        else:
            competency.delete()
            removed += 1
    return removed, preserved


class Command(BaseCommand):
    help = "Charge la maquette officielle de la L3 Mathématiques (Université de Guyane)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True, help="Compte propriétaire de la formation.")
        parser.add_argument("--title", default="L3 Mathématiques 2025-2026", help="Formation à alimenter.")
        parser.add_argument(
            "--reset-hours",
            action="store_true",
            help=(
                "Réécrit le travail personnel estimé de chaque compétence depuis la maquette. "
                "Sans cette option, une estimation déjà présente est conservée — on ne sait pas "
                "distinguer celle qu'un chargement précédent a posée de celle que vous avez saisie. "
                "Le temps réel et le niveau de maîtrise ne sont jamais touchés."
            ),
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help=(
                "Retire les compétences absentes de cette maquette, à condition que rien n'y ait "
                "été travaillé : niveau non abordé, aucun temps réel, aucun commentaire, aucune "
                "ressource et aucune session. Sans cette option, un ancien découpage cohabite "
                "avec le nouveau."
            ),
        )

    @staticmethod
    def ensure_group(period, title, order):
        """L'UE déclarée par la maquette, créée à la demande.

        Les intitulés d'UE vivaient dans la description de la matière, faute de modèle pour
        les porter. Ils deviennent des regroupements, ce qui les rend visibles dans la
        grille et modifiables.
        """
        group, _ = LearningGroup.objects.get_or_create(
            period=period, title=title, defaults={"kind": "UE", "order": order}
        )
        return group

    @staticmethod
    def sync_competencies(path, plan: dict, *, owner, reset: bool) -> int:
        """Cree les competences du parcours et les rattache a leurs matieres.

        Une competence appartient a la formation, pas a une matiere : un intitule declare
        par deux modules — les oraux reviennent aux deux semestres — donne une seule
        competence liee aux deux, et non deux suivis paralleles du meme savoir-faire. Sa
        periode reste vide dans ce cas : elle traverse la formation.

        Le traitement est groupe parce que la maquette compte plus de trois cents
        competences ; une requete par ligne en faisait un millier.
        """
        existing = {competency.title: competency for competency in Competency.objects.filter(path=path)}
        missing, reordered = [], []
        for order, (title, entry) in enumerate(plan.items(), start=1):
            period = entry["period"]
            competency = existing.get(title)
            if competency is None:
                missing.append(Competency(path=path, period=period, title=title, order=order))
            elif competency.order != order or competency.period_id != (period.pk if period else None):
                competency.order = order
                competency.period = period
                reordered.append(competency)
        if missing:
            Competency.objects.bulk_create(missing)
        if reordered:
            Competency.objects.bulk_update(reordered, ["order", "period"])

        competencies = {competency.title: competency for competency in Competency.objects.filter(path=path)}

        # Liens de matiere : une competence peut en avoir plusieurs.
        wanted = {
            (unit.pk, competencies[title].pk): order for title, entry in plan.items() for order, unit in entry["units"]
        }
        present = {
            (link.unit_id, link.competency_id) for link in UnitCompetency.objects.filter(unit__period__path=path)
        }
        new_links = [
            UnitCompetency(unit_id=unit_id, competency_id=competency_id, order=order, is_primary=True)
            for (unit_id, competency_id), order in wanted.items()
            if (unit_id, competency_id) not in present
        ]
        if new_links:
            UnitCompetency.objects.bulk_create(new_links)

        records = {
            record.competency_id: record for record in ProgressRecord.objects.filter(owner=owner, competency__path=path)
        }
        fresh, rewritten = [], []
        for title, entry in plan.items():
            competency = competencies[title]
            record = records.get(competency.pk)
            if record is None:
                fresh.append(ProgressRecord(owner=owner, competency=competency, planned_hours=entry["hours"]))
            elif reset or not record.planned_hours:
                record.planned_hours = entry["hours"]
                rewritten.append(record)
        if fresh:
            ProgressRecord.objects.bulk_create(fresh)
        if rewritten:
            ProgressRecord.objects.bulk_update(rewritten, ["planned_hours", "updated_at"])
        return len(missing)

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
        # Le plan rassemble, par intitule de competence, les matieres qui la declarent, le
        # temps cumule et la periode — vide des qu'elle en traverse plusieurs.
        plan: dict[str, dict] = {}
        for period_order, (period_title, matieres) in enumerate(PROGRAMME.items(), start=5):
            period, _ = Period.objects.update_or_create(path=path, title=period_title, defaults={"order": period_order})
            for unit_order, (titre, ue, encadre, ects, nature, competences) in enumerate(matieres, start=1):
                perso = (Decimal(encadre) * EFFORT[nature]).quantize(Decimal("1"))
                total_perso += perso
                unit, _ = LearningUnit.objects.update_or_create(
                    period=period,
                    title=titre,
                    defaults={
                        "order": unit_order,
                        "group": self.ensure_group(period, ue, unit_order),
                        "description": nature,
                    },
                )
                for key, value in (("ects", ects), ("encadre", encadre), ("perso", perso)):
                    MetricValue.objects.update_or_create(
                        definition=metrics[key], unit=unit, defaults={"value": Decimal(value)}
                    )
                # Le travail personnel se repartit egalement entre les competences, au quart
                # d'heure superieur : c'est une estimation de depart que la grille de suivi
                # permet d'ajuster, et une duree qu'on doit pouvoir lire d'un coup d'oeil.
                part = readable_share(perso, len(competences))
                for order, title in enumerate(competences, start=1):
                    entry = plan.setdefault(title, {"units": [], "hours": Decimal(0), "period": period})
                    entry["units"].append((order, unit))
                    entry["hours"] += part
                    if entry["period"] is not None and entry["period"].pk != period.pk:
                        # Declaree dans deux periodes : elle devient transversale.
                        entry["period"] = None

        distributed = sum((entry["hours"] for entry in plan.values()), Decimal(0))
        added = self.sync_competencies(path, plan, owner=owner, reset=options["reset_hours"])

        retired, preserved_legacy = retire_legacy_geometry(path, owner)
        resource_sync = sync_path_curated_resources(
            owner=owner,
            path=path,
            competency_titles=declared_titles(),
        )

        pruned = retired + (prune_obsolete(path, owner) if options["prune"] else 0)

        encadre_total = sum(m[2] for matieres in PROGRAMME.values() for m in matieres)
        total = Competency.objects.filter(path=path).count()
        units = LearningUnit.objects.filter(period__path=path).count()
        self.stdout.write(
            self.style.SUCCESS(
                f"{path.title} : {units} matières, {total} compétences "
                f"({added} ajoutées, {pruned} retirées), "
                f"{encadre_total} h encadrées, {total_perso} h de travail personnel estimé."
            )
        )
        self.stdout.write(
            f"Réparti par demi-heures : {distributed.normalize():f} h au total, soit "
            f"{(distributed - total_perso).normalize():+f} h par rapport à l'estimation. "
            "Une durée lisible vaut mieux qu'une division exacte."
        )
        self.stdout.write(
            f"Bibliothèque : {resource_sync.created} ressource(s) créée(s), "
            f"{resource_sync.updated} actualisée(s) et {resource_sync.attached} rattachement(s) ajouté(s)."
        )
        if preserved_legacy:
            self.stdout.write(
                self.style.WARNING(
                    f"{preserved_legacy} ancienne(s) compétence(s) de géométrie différentielle "
                    "contiennent un travail personnel et ont donc été conservées."
                )
            )
        if not options["prune"]:
            self.stdout.write(
                "Un découpage antérieur reste en place s'il en existait un. "
                "Relancer avec --prune retire ce qui n'appartient plus à la maquette et sur "
                "quoi rien n'a été travaillé."
            )
        self.stdout.write(
            "Rappel : les ECTS publiés par l'université ne totalisent pas 30 par semestre ; "
            "ils sont repris tels quels et n'entrent dans aucun calcul."
        )
        self.stdout.write(
            "Rappel : le découpage en compétences est une proposition pédagogique, non publiée "
            "par l'université. Ajustez-le au cours réellement suivi."
        )
