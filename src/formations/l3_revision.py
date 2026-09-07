"""Le plan détaillé des chapitres de topologie et de géométrie de la L3.

Le programme (``load_licence_guyane.PROGRAMME``) dit ce qu'il faut savoir faire ; le
catalogue (``curated_resources``) dit où l'apprendre. Il manquait entre les deux l'ordre
dans lequel on traverse une notion : prérequis, définitions, théorèmes, démonstrations,
exemples, méthodes, exercices gradués, checklist. C'est ce que porte ce module.

Chaque chapitre désigne ses compétences par leur rang dans le programme, et ses ressources
par leur clé dans le catalogue. Les deux sont vérifiés par ``tests/test_l3_revision`` :
un chapitre ne peut pas renvoyer à une compétence ou à une ressource qui n'existe pas, et
les chapitres d'une branche couvrent son programme sans trou ni doublon.
"""

from html import escape

SECTIONS = (
    "Prérequis",
    "Objectifs et compétences précises",
    "Notions et définitions",
    "Théorèmes et propositions importants",
    "Démonstrations à connaître",
    "Exemples et contre-exemples",
    "Méthodes et savoir-faire",
    "Exercices types classés par difficulté",
    "Ressources recommandées",
    "Checklist de maîtrise",
)

# `legacy` : les rangs (base 1) des compétences du programme que le chapitre travaille.
# Un rang, pas une clé primaire : le programme est une liste ordonnée dans le code, pas
# une table. `resources` : les clés du catalogue à ouvrir pour ce chapitre.
CHAPTERS = []


def chapter(key, branch, title, legacy, additions, *sections, resources=(), optional=False):
    assert len(sections) == 8  # objectifs et ressources insérés au rendu
    CHAPTERS.append(
        dict(
            key=key,
            branch=branch,
            title=title,
            legacy=legacy,
            additions=additions,
            sections=list(sections),
            resources=tuple(resources),
            optional=optional,
        )
    )


chapter(
    "T01",
    "Topologie",
    "Langage topologique et espaces métriques",
    [1, 2, 4, 5, 6, 7, 8],
    ["Nier avec les bons quantificateurs les définitions d’adhérence et de convergence"],
    "Ensembles, unions et intersections ; implication et contraposée ; normes usuelles sur R². Réactiver la différence entre ∀ε ∃N et ∃N ∀ε.",
    "Une topologie contient ∅ et X, est stable par unions arbitraires et intersections finies. Un fermé est le complémentaire d’un ouvert. Un voisinage de x contient un ouvert contenant x. Int(A) est le plus grand ouvert inclus dans A ; adh(A) le plus petit fermé contenant A ; frontière(A)=adh(A)\\Int(A). Une base engendre les ouverts par unions ; une sous-base par unions d’intersections finies. Densité : adh(A)=X ; séparabilité : existence d’une partie dénombrable dense.",
    "Les boules ouvertes d’une distance forment une base. x appartient à adh(A) si tout voisinage de x rencontre A. Int(X\\A)=X\\adh(A). Une intersection infinie d’ouverts peut ne pas être ouverte.",
    "Montrer qu’une boule est ouverte par l’inégalité triangulaire. Démontrer la caractérisation de l’adhérence par les voisinages, puis la formule de complémentarité.",
    "Dans R, Q a un intérieur vide et une adhérence égale à R. Dans un espace discret, tout singleton est ouvert. L’intersection des intervalles ]−1/n,1/n[ est {0}. Une boule fermée n’est pas toujours l’adhérence de la boule ouverte de même rayon : distance discrète, rayon 1.",
    "Toujours préciser l’espace ambiant. Pour montrer x intérieur, construire un rayon ; pour réfuter l’adhérence, trouver un voisinage disjoint. Tester séparément les trois axiomes d’une distance.",
    "N1 : calculer intérieur, adhérence et frontière de Q∩[0,1] dans R (réponse : ∅, [0,1], [0,1]). N2 : donner ces ensembles dans Q pour la même partie. N3 : prouver le critère de base par raffinement des intersections, puis construire la topologie engendrée par une sous-base.",
    "Je sais distinguer ouvert et voisinage ; je donne un exemple ni ouvert ni fermé ; je calcule les trois opérateurs en précisant l’espace ; je justifie chaque quantificateur.",
    resources=(
        "topology_course_toulouse",
        "topology_course_bordeaux",
        "topology_exercises_lille",
    ),
)

chapter(
    "T02",
    "Topologie",
    "Topologie induite, produits et comparaison",
    [3, 9, 10],
    ["Démontrer que la convergence dans un produit fini équivaut à la convergence de chaque coordonnée"],
    "T01 ; images directes et réciproques ; produit cartésien.",
    "Les ouverts de A⊂X sont les A∩U avec U ouvert de X. Les pavés ouverts forment une base du produit fini. Deux distances sont topologiquement équivalentes si elles engendrent les mêmes ouverts ; une comparaison bilipschitzienne est une condition plus forte.",
    "Une application vers un produit fini est continue si et seulement si ses composantes le sont. La métrique maximum induit la topologie produit d’un nombre fini d’espaces métriques.",
    "Démontrer la propriété universelle du produit par les projections et les pavés ; démontrer le critère de convergence coordonnée par coordonnée.",
    "[0,1[ est ouvert dans [0,1] mais pas dans R. Sur R, d(x,y)=|x−y| et min(1,d(x,y)) donnent les mêmes ouverts, sans être comparables par deux constantes positives globales.",
    "Exprimer les ouverts relatifs comme des traces. Pour comparer deux topologies, tester la continuité des deux applications identités. Travailler avec les boules de rayon inférieur à 1 pour la métrique tronquée.",
    "N1 : écrire ]−1,1[∩[0,2]. N2 : montrer la continuité de x↦(x,x²). N3 : démontrer l’équivalence topologique de d et min(1,d), puis expliquer pourquoi la bornitude n’est pas une propriété topologique.",
    "Je distingue ouvert relatif et ouvert ambiant ; je démontre le critère produit ; je ne confonds pas équivalence topologique et comparaison bilipschitzienne.",
    resources=(
        "topology_course_toulouse",
        "topology_course_bordeaux",
        "topology_exercises_lille",
    ),
)

chapter(
    "T03",
    "Topologie",
    "Suites, limites et séparation",
    [11, 12, 13],
    ["Distinguer les axiomes T1 et Hausdorff à l’aide d’exemples explicites"],
    "T01–T02 ; extraction de suites réelles ; négation de la convergence.",
    "Une suite converge vers x si elle est finalement dans tout voisinage de x. Une valeur d’adhérence séquentielle est une limite de sous-suite. T1 signifie que les singletons sont fermés ; Hausdorff signifie que deux points distincts possèdent des voisinages disjoints.",
    "Dans un espace Hausdorff, une suite a au plus une limite. Dans un espace métrique, x∈adh(A) équivaut à l’existence d’une suite de A convergeant vers x. L’implication réciproque ne se généralise pas sans hypothèse de dénombrabilité locale.",
    "Unicité : choisir deux voisinages disjoints et utiliser deux rangs, puis leur maximum. Caractérisation métrique de l’adhérence : choisir a_n dans A∩B(x,1/n).",
    "Dans l’espace indiscret à deux points, toute suite converge vers les deux points. Une topologie cofinie sur un ensemble infini est T1 sans être Hausdorff. La suite (−1)^n a deux valeurs d’adhérence et ne converge pas.",
    "Séparer existence et unicité de limite. Pour réfuter une limite, construire ε>0 et des indices arbitrairement grands hors de la boule. Ne pas importer un critère séquentiel métrique dans un espace quelconque.",
    "N1 : déterminer les valeurs d’adhérence de (−1)^n+1/n. N2 : prouver qu’un fermé métrique contient les limites de ses suites. N3 : vérifier les propriétés T1 et non-Hausdorff de la topologie cofinie.",
    "Je sais énoncer les hypothèses d’unicité ; je construis une suite approchante ; je distingue limite et valeur d’adhérence ; je cite un espace non séparé.",
    resources=(
        "topology_course_toulouse",
        "topology_exercises_lille",
    ),
)

chapter(
    "T04",
    "Topologie",
    "Continuité et homéomorphismes",
    [14, 15, 16, 17, 18],
    [],
    "T01–T03 ; fonctions usuelles ; calcul d’images réciproques.",
    "Continuité topologique : l’image réciproque de tout ouvert est ouverte. Continuité métrique en x : ∀ε>0 ∃δ>0 ∀y, d(x,y)<δ implique d(f(x),f(y))<ε. Continuité uniforme : δ ne dépend pas de x. Une application L-lipschitzienne vérifie d(f(x),f(y))≤L d(x,y). Un homéomorphisme est une bijection continue d’inverse continue.",
    "La continuité équivaut au critère par fermés. Si le domaine est métrique, elle équivaut à la préservation des limites de suites. Lipschitz implique uniformément continue, qui implique continue. La composition conserve ces propriétés.",
    "Démontrer l’équivalence ouverts/fermés. Prouver le critère séquentiel par contraposée, en choisissant x_n à distance <1/n. Construire explicitement l’inverse d’un homéomorphisme.",
    "x² est continue mais non uniformément continue sur R : comparer n et n+1/n. La racine carrée est uniformément continue sur [0,1], mais non lipschitzienne. Une bijection continue peut avoir un inverse discontinu.",
    "Choisir entre ε–δ, suites et images réciproques selon la question. Pour réfuter la continuité uniforme, utiliser deux suites dont la distance tend vers 0, mais pas celle des images.",
    "N1 : montrer que la distance à une partie non vide est 1-lipschitzienne. N2 : démontrer le contre-exemple x². N3 : établir que t↦tan(π(t−1/2)) est un homéomorphisme de ]0,1[ sur R.",
    "Je place les quantificateurs correctement ; je sais quand utiliser le critère séquentiel ; je vérifie la continuité de l’inverse ; je sépare les trois degrés de continuité.",
    resources=(
        "topology_course_toulouse",
        "topology_course_bordeaux",
        "topology_exercises_lille",
    ),
)

chapter(
    "T05",
    "Topologie",
    "Compacité et applications",
    [24, 25, 26, 27, 28],
    ["Distinguer bornitude, précompacité et compacité dans un espace métrique"],
    "T03–T04 ; Bolzano-Weierstrass dans R ; bornes supérieure et inférieure.",
    "Convention : compact = Hausdorff et tout recouvrement ouvert possède un sous-recouvrement fini. En métrique, précompact = pour tout ε>0, existence d’un recouvrement par un nombre fini de boules de rayon ε. Compacité séquentielle : toute suite admet une sous-suite convergeant dans l’espace.",
    "En métrique, compacité ⇔ compacité séquentielle ⇔ complet et précompact (complétude étudiée en T07). Dans R^n, compact ⇔ fermé et borné. Une image continue d’un compact dans un espace Hausdorff est compacte. Une fonction réelle continue sur un compact non vide atteint ses extrema ; une application continue d’un compact métrique vers un espace métrique est uniformément continue.",
    "Démontrer l’image continue compacte par transport des recouvrements ; en déduire les extrema. Démontrer Heine par contradiction et extraction de sous-suites.",
    "]0,1[ est borné mais non compact. Un ensemble infini muni de la distance discrète est fermé et borné, mais non précompact. Une boule fermée en dimension infinie n’est pas automatiquement compacte.",
    "Vérifier d’abord le cadre : R^n, espace métrique ou topologique. Produire un recouvrement sans sous-recouvrement fini ou une suite sans sous-suite convergente pour nier la compacité.",
    "N1 : tester [0,1]∪{2} et Q∩[0,1] dans R. N2 : prouver l’existence d’un point minimisant d(x,A) quand A est compact non vide. N3 : démontrer qu’une bijection continue d’un compact vers un Hausdorff est un homéomorphisme.",
    "Je n’utilise Heine-Borel que dans son cadre ; je sais transporter un recouvrement ; je vérifie non-vacuité avant les extrema ; je distingue fermé-borné et compact.",
    resources=(
        "topology_course_toulouse",
        "topology_exercises_lille",
        "topology_exercises_advanced_lille",
    ),
)

chapter(
    "T06",
    "Topologie",
    "Connexité et connexité par arcs",
    [29, 30],
    [],
    "T01–T04 ; intervalles de R ; théorème des valeurs intermédiaires.",
    "Un espace est connexe s’il n’est pas réunion de deux ouverts non vides disjoints. Il est connexe par arcs si deux points se relient par une application continue de [0,1]. La composante connexe d’un point est le connexe maximal qui le contient.",
    "Les connexes de R sont les intervalles. Une image continue d’un connexe est connexe. Connexe par arcs implique connexe. L’adhérence d’un connexe est connexe. Une réunion de connexes ayant un point commun est connexe.",
    "Démontrer le transport de la connexité par image continue ; retrouver le théorème des valeurs intermédiaires ; montrer qu’un convexe est connexe par arcs via le segment paramétré.",
    "R\\{0} a deux composantes connexes ; R²\\{0} est connexe par arcs. L’adhérence du graphe de sin(1/x), x>0, fournit un connexe non connexe par arcs (preuve détaillée en approfondissement).",
    "Pour montrer la connexité, rechercher une image continue ou une réunion avec point commun. Pour la nier, exhiber une séparation relative. Un dessin suggère un chemin, mais ne démontre pas sa continuité.",
    "N1 : composantes de ]−2,−1[∪[0,1]. N2 : construire un chemin entre deux points de R²\\{0}. N3 : utiliser la connexité après retrait d’un point pour montrer que R et R² ne sont pas homéomorphes.",
    "Je construis un chemin explicite ; je donne une séparation ; je sais que connexe n’implique pas connexe par arcs ; je relie cette notion au TVI.",
    resources=(
        "topology_course_bordeaux",
        "topology_exercises_lille",
    ),
)

chapter(
    "T07",
    "Topologie",
    "Complétude et point fixe de Banach",
    [19, 20, 22],
    [],
    "T03–T04 ; suites réelles de Cauchy ; séries géométriques.",
    "Suite de Cauchy : ∀ε>0 ∃N ∀p,q≥N, d(x_p,x_q)<ε. Un espace est complet si toute suite de Cauchy y converge. Une contraction f:X→X possède une constante q<1 telle que d(f(x),f(y))≤q d(x,y).",
    "Une partie fermée d’un espace complet est complète ; une partie complète d’un espace métrique est fermée. Un compact métrique est complet. Sur un espace complet non vide, une contraction de X dans X admet un unique point fixe a ; l’itération x_(n+1)=f(x_n) vérifie d(x_n,a)≤q^n d(x_1,x_0)/(1−q).",
    "Démontrer le critère de sous-espace fermé. Pour Banach : majorer les accroissements, sommer une série géométrique, utiliser la complétude, passer à la limite, puis prouver l’unicité.",
    "Q n’est pas complet pour la distance usuelle. ]0,1[ est homéomorphe à R sans être complet pour cette distance : la complétude n’est pas un invariant topologique. f(x)=x/2 sur ]0,1[ est contractante sans point fixe dans son domaine.",
    "Avant Banach, contrôler domaine stable, non-vacuité, complétude et constante strictement inférieure à 1. Transformer la majoration d’erreur en nombre d’itérations suffisant.",
    "N1 : montrer qu’une suite convergente est de Cauchy. N2 : appliquer Banach à f(x)=cos(x)/2 sur [0,1]. N3 : construire un exemple de contraction dans un espace incomplet et identifier exactement l’hypothèse manquante.",
    "Je distingue Cauchy et convergente ; je vérifie la stabilité du domaine ; je reconstruis la preuve de Banach ; je calcule un majorant d’erreur.",
    resources=(
        "topology_course_toulouse",
        "topology_exercises_advanced_lille",
    ),
)

chapter(
    "T08",
    "Topologie",
    "Espaces normés et convergence uniforme",
    [31, 32, 33],
    [],
    "T04–T07 ; algèbre linéaire et normes ; suprema.",
    "Une norme induit d(x,y)=||x−y||. La norme opérateur est sup_{||x||≤1}||Tx|| pour une application linéaire continue. Sur C(K,R), K compact non vide, ||f||∞=sup_K|f|. La convergence uniforme signifie que cette norme de la différence tend vers 0.",
    "En dimension finie, toutes les normes sont équivalentes et toute application linéaire est continue. En général, linéaire continue ⇔ majorée par C||x||. Une limite uniforme de fonctions continues est continue. C(K,R) est complet pour la norme uniforme.",
    "Prouver la continuité linéaire à partir d’une majoration ; démontrer la continuité de la limite uniforme par une décomposition en trois termes ; établir la complétude de C(K,R).",
    "x↦x^n converge simplement mais non uniformément sur [0,1]. Les normes intégrale et uniforme sur C([0,1]) ne sont pas équivalentes : utiliser des pics triangulaires.",
    "Calculer ou majorer un supremum pour la convergence uniforme. Ne jamais appliquer l’équivalence des normes sans vérifier la dimension finie. Pour une preuve par limite, annoncer le type de convergence utilisé.",
    "N1 : norme opérateur d’une matrice diagonale en norme euclidienne. N2 : convergence uniforme de x^n sur [0,a], 0<a<1. N3 : construire les pics triangulaires de hauteur 1 et de support décroissant ; comparer leurs normes.",
    "Je justifie la finitude de la norme ; je distingue convergence simple et uniforme ; je sais où intervient la dimension finie ; je refais la preuve en trois termes.",
    resources=(
        "topology_course_toulouse",
        "topology_exercises_advanced_lille",
    ),
)

chapter(
    "T09",
    "Topologie",
    "Constructions et prolongements après le socle",
    [21, 23, 34],
    ["Construire une topologie initiale, finale ou quotient et vérifier sa propriété universelle"],
    "T01–T08 acquis. Complément proposé, à confronter au syllabus détaillé de Guyane ; ne conditionne pas le travail CAPES prioritaire.",
    "Initiale : topologie la moins fine rendant continues des applications sortantes données. Finale : la plus fine rendant continues des applications entrantes. Quotient par une surjection p : U est ouvert si p⁻¹(U) est ouvert. Complétion : espace complet contenant une copie isométrique dense de X.",
    "Une application issue d’un quotient est continue si et seulement si sa composée avec p l’est. Théorème de Baire : dans un espace métrique complet, une intersection dénombrable d’ouverts denses est dense. Arzelà-Ascoli, version C(K,R), K compact métrique : une famille équicontinue et ponctuellement bornée est relativement compacte pour la norme uniforme.",
    "Propriété universelle du quotient par images réciproques. Baire par boules fermées emboîtées de rayons tendant vers 0. Pour Ascoli, connaître d’abord le rôle de chaque hypothèse ; preuve complète seulement après le socle.",
    "Identifier les extrémités de [0,1] donne un cercle. Q se complète en R. Les topologies induite et produit sont des cas de topologies initiales.",
    "Partir de la surjection explicite ; vérifier l’indépendance du représentant. Distinguer topologie quotient et métrique quotient, qui n’existe pas automatiquement sous la forme naïve d’une distance.",
    "N1 : reconnaître la topologie induite comme initiale. N2 : montrer que t↦exp(2πit) descend au quotient de [0,1]. N3 : vérifier séparément équicontinuité et bornitude ponctuelle sur une famille avant d’appliquer Ascoli.",
    "Je distingue moins fine et plus fine ; je sais faire descendre une application ; j’énonce Baire avec complétude ; je ne remplace pas un théorème nommé par « un théorème d’approximation ».",
    optional=True,
    resources=(
        "topology_course_toulouse",
        "topology_exercises_advanced_lille",
    ),
)

chapter(
    "G01",
    "Géométrie",
    "Espaces affines, repères et intersections",
    [1, 2, 3, 4, 5, 6, 7],
    [],
    "Espaces vectoriels réels de dimension finie ; bases, rang et systèmes linéaires ; relation de Chasles.",
    "Un espace affine possède un espace vectoriel de translations : pour A et v, il existe un unique B tel que AB=v. Un sous-espace affine non vide est A+F ; F est sa direction. Un repère est une origine et une base de directions. A0,…,Ak sont affinement indépendants si les vecteurs A0Ai sont libres.",
    "(A+F)∩(B+G) est non vide si et seulement si AB∈F+G ; lorsqu’elle est non vide, sa direction est F∩G. L’enveloppe affine de A0,…,Ak est A0+Vect(A0A1,…,A0Ak).",
    "Démontrer l’indépendance de la direction par rapport au point choisi ; démontrer le critère d’intersection ; établir l’unicité des coordonnées dans un repère affine.",
    "Le lieu x+y=1 est affine sans être vectoriel. Dans R³, des droites peuvent être disjointes sans être parallèles. La réunion des deux axes de R² n’est pas un sous-espace affine.",
    "Choisir un point particulier, résoudre le système homogène pour la direction, puis calculer le rang. Fixer la convention de parallélisme : directions égales pour deux sous-espaces de même dimension.",
    "N1 : direction et dimension de x+y+z=1. N2 : intersection de ce plan avec x−y=0. N3 : comparer deux droites de R³ en résolvant A+tu=B+sv ; distinguer sécantes, parallèles et gauches.",
    "Je distingue points et vecteurs ; je trouve une origine admissible ; je calcule direction et dimension ; je justifie les cas d’intersection sans me fier au dessin.",
    resources=(
        "geometry_affine_course_lyon",
        "geometry_affine_td_coordinates_lyon",
        "geometry_affine_summary_lyon",
    ),
)

chapter(
    "G02",
    "Géométrie",
    "Barycentres et convexité",
    [16, 17, 18, 19, 20],
    [],
    "G01 ; calcul vectoriel ; résolution de systèmes ; sommes pondérées.",
    "Pour des poids λ_i de somme s≠0, le barycentre G est l’unique point vérifiant Σλ_i GA_i=0 ; OG=Σλ_i OA_i/s. Les coordonnées barycentriques normalisées ont somme 1. Une combinaison convexe a des poids positifs ou nuls et de somme 1.",
    "Existence et unicité si la somme des poids est non nulle. Associativité par regroupements dont les sommes intermédiaires sont non nulles. Une application est affine si et seulement si elle conserve tous les barycentres définis. Dans un simplexe, l’enveloppe convexe correspond aux coordonnées barycentriques positives ou nulles.",
    "Démontrer l’indépendance du point O avec Chasles. Prouver l’associativité puis la caractérisation des applications affines par barycentres.",
    "Le milieu a pour poids (1,1). Avec A≠B et poids (1,−1), aucun barycentre n’est défini. Un poids négatif peut placer le point hors du segment. Les trois médianes d’un triangle se rencontrent en l’isobarycentre.",
    "Normaliser les poids avant calcul. Choisir des barycentres partiels pour exploiter un alignement ; vérifier chaque somme intermédiaire avant regroupement.",
    "N1 : barycentre de A=(0,0), B=(3,0), C=(0,3), poids (1,1,1) : (1,1). N2 : démontrer la concurrence des médianes. N3 : caractériser l’intérieur d’un triangle non aplati par la stricte positivité des trois coordonnées barycentcentriques normalisées.",
    "Je vérifie la somme des poids ; je justifie un regroupement ; je distingue affine et convexe ; je prouve la concurrence des médianes.",
    resources=(
        "geometry_affine_course_lyon",
        "geometry_affine_td_barycentres_lyon",
        "geometry_affine_video_caldero",
    ),
)

chapter(
    "G03",
    "Géométrie",
    "Applications affines et invariants",
    [8, 9, 10, 11, 12, 13, 14, 15],
    [],
    "G01–G02 ; applications linéaires, noyaux, images ; supplémentaires.",
    "Une application affine f vérifie f(B)−f(A)=L(AB) pour une application linéaire L. Dans des repères, f(x)=Mx+b. Une projection affine se définit par un sous-espace affine cible et une direction supplémentaire ; une symétrie affine utilise la même décomposition, avec signe opposé sur la direction projetée.",
    "f est bijective si et seulement si L l’est. La partie linéaire d’une composée est le produit des parties linéaires. Les points fixes résolvent (I−M)x=b. Une bijection affine conserve alignement, parallélisme et rapports sur une droite ; en dimension n, les volumes sont multipliés par |det M|, et ne sont donc pas invariants en général.",
    "Démontrer l’unicité de L, la formule de composition et la conservation des barycentres. Déduire p²=p et s²=Id d’une décomposition directe.",
    "L’homothétie de rapport 2 multiplie les aires par 4 dans le plan. Une projection oblique est affine mais ne conserve ni distances ni angles. Une translation non nulle n’a aucun point fixe.",
    "Séparer la partie linéaire et le déplacement d’origine. Pour classifier, examiner M, puis les solutions de (I−M)x=b. Ne pas confondre projection affine et projection orthogonale.",
    "N1 : composer x↦2x+a et x↦x+b. N2 : construire la projection sur y=0 parallèlement à (1,1). N3 : démontrer que toute application affine est déterminée par les images d’un repère affine.",
    "Je calcule la partie linéaire ; je résous les points fixes ; je construis une projection ; je sais que les volumes changent selon le déterminant.",
    resources=(
        "geometry_affine_course_lyon",
        "geometry_affine_td_applications_lyon",
        "geometry_affine_transformations_lyon",
    ),
)

chapter(
    "G04",
    "Géométrie",
    "Configurations et théorèmes affines",
    [],
    [
        "Démontrer et appliquer Thalès avec des rapports algébriques",
        "Établir les critères de Ceva et de Ménélaüs dans un triangle non aplati",
    ],
    "G01–G03 ; rapports signés sur une droite ; déterminants 2×2.",
    "La mesure algébrique AB dépend d’une direction choisie ; le rapport de deux mesures sur une même droite ne dépend pas de ce choix. Fixer un triangle ABC non aplati et D∈(BC), E∈(CA), F∈(AB), distincts des sommets.",
    "Thalès relie parallélisme et égalité de rapports dans une configuration de deux droites sécantes. Avec les rapports cycliques BD/DC, CE/EA, AF/FB, Ménélaüs donne −1 pour l’alignement de D,E,F ; Ceva donne +1 pour des céviennes concourantes ou toutes parallèles. Le cas parallèle doit être exclu si l’on exige un point de concours fini.",
    "Démontrer Thalès avec deux vecteurs indépendants. Déduire Ménélaüs d’un déterminant nul en coordonnées barycentriques. Pour Ceva, rechercher les coordonnées d’un point commun, puis traiter explicitement le cas parallèle.",
    "Les médianes vérifient Ceva avec trois rapports égaux à 1. Une configuration sur les prolongements des côtés impose de conserver les signes. Des rapports non orientés masquent le signe de Ménélaüs.",
    "Faire un schéma légendé, annoncer la convention de signes, vérifier les dénominateurs non nuls ; traiter à part les cas dégénérés. Relier preuve vectorielle et preuve barycentrique.",
    "N1 : retrouver le théorème des milieux par Thalès. N2 : prouver l’alignement avec des rapports de produit −1. N3 : dans A=(0,0), B=(1,0), C=(0,1), prendre D=(1/2,1/2), E=(0,−1), F=(−1,0) et expliquer le cas parallèle de Ceva.",
    "Je définis les rapports signés ; je contrôle les hypothèses de non-dégénérescence ; je sais traiter concurrence et parallélisme ; je reconstruis au moins une preuve.",
    resources=(
        "geometry_affine_course_lyon",
        "geometry_exam_2015_final_lyon",
        "geometry_affine_video_exo7",
    ),
)

chapter(
    "G05",
    "Géométrie",
    "Structure euclidienne et orthogonalité",
    [21, 22, 23, 24, 25, 26, 27, 28],
    [],
    "Algèbre linéaire, produit scalaire réel, G01–G03 ; Pythagore.",
    "Un produit scalaire réel est bilinéaire, symétrique et défini positif. ||u||²=⟨u,u⟩ ; u⊥v si ⟨u,v⟩=0. L’orthogonal F⊥ rassemble les vecteurs orthogonaux à F. Dans un repère orthonormé, déterminants et produit scalaire donnent aires, volumes et distances.",
    "Cauchy-Schwarz ; décomposition E=F⊕F⊥ en dimension finie. Le projeté orthogonal sur A+F est l’unique point de ce sous-espace qui minimise la distance. Pour un hyperplan ⟨n,x⟩=c, la distance de x vaut |⟨n,x⟩−c|/||n||.",
    "Démontrer Cauchy-Schwarz par positivité d’un trinôme. Démontrer la propriété de minimum par Pythagore. Justifier Gram-Schmidt sur une famille libre.",
    "La projection oblique de G03 ne minimise pas la distance en général. Les points équidistants de A et B, A≠B, forment l’hyperplan médiateur. L’orientation est un choix supplémentaire à la métrique.",
    "Orthonormaliser avant d’utiliser une formule euclidienne en coordonnées. Pour la distance entre deux sous-espaces, minimiser ||AB+v−u|| avec u∈F,v∈G. Traiter séparément le cas parallèle pour deux droites.",
    "N1 : distance de (1,2) à x+y=0 : 3/√2. N2 : trouver le projeté orthogonal sur ce même axe. N3 : établir la distance entre deux droites gauches de R³ à l’aide d’une normale commune.",
    "Je vérifie l’orthonormalité du repère ; je construis le projeté ; je distingue orthogonalité et parallélisme ; je justifie un minimum de distance.",
    resources=(
        "geometry_affine_course_lyon",
        "geometry_euclidean_td_lyon",
    ),
)

chapter(
    "G06",
    "Géométrie",
    "Angles algébriques et géométrie du cercle",
    [38, 39, 40, 41, 42, 43],
    [],
    "G05 ; cercle trigonométrique ; nombres complexes, module, argument ; congruences modulo π et 2π. Le plan est euclidien et orienté.",
    "Pour u,v non nuls, (u,v) est la classe θ modulo 2π de la rotation envoyant u/||u|| sur v/||v||. Pour des droites non orientées, changer un vecteur directeur en son opposé conduit à travailler modulo π. L’angle géométrique dans [0,π] ne retient pas le signe. cos θ=⟨u,v⟩/(||u||||v||), sin θ=det(u,v)/(||u||||v||).",
    "Chasles : (u,v)+(v,w)=(u,w) modulo 2π. Inversion : (v,u)=−(u,v). Une isométrie directe conserve les angles orientés ; une indirecte les oppose. En affixes, θ=arg(z_v/z_u). Pour A,B,M distincts sur un cercle de centre O, (OA,OB)=2(MA,MB) modulo 2π. Pour A,B,C,D distincts et A,B,C non alignés, cocyclicité ⇔ (CA,CB)=(DA,DB) modulo π.",
    "Démontrer Chasles par composition des rotations. Déduire le changement de signe par conjugaison complexe. Prouver l’angle inscrit puis le critère de cocyclicité, en distinguant bien les deux modules.",
    "Avec u=(1,0), v=(0,−1), l’angle orienté est −π/2 modulo 2π, tandis que l’angle géométrique est π/2. Une réflexion change le signe. Aucun angle n’est défini avec le vecteur nul. Deux angles égaux modulo π ne le sont pas forcément modulo 2π.",
    "Annoncer le module à chaque égalité ; utiliser atan2(det(u,v),⟨u,v⟩) pour une mesure principale. Ne pas employer arccos seul pour déterminer l’orientation. Avant cocyclicité, vérifier les points distincts et la non-colinéarité requise.",
    "N1 : calculer ((1,1),(−1,1)) : π/2 modulo 2π. N2 : calculer l’effet de z↦conj(z) sur cet angle. N3 : pour A=1, B=i, C=−1, D=−i, vérifier la cocyclicité par arg((b−c)/(a−c)) et arg((b−d)/(a−d)) modulo π.",
    "Je distingue angle géométrique, angle de vecteurs et angle de droites ; je conserve les signes ; je démontre Chasles ; je sais quand utiliser modulo π ou modulo 2π ; je peux prouver la cocyclicité.",
    resources=(
        "geometry_angles_inscribed_lecon",
        "geometry_affine_course_lyon",
        "geometry_exam_2016_final_lyon",
    ),
)

chapter(
    "G07",
    "Géométrie",
    "Isométries et similitudes du plan",
    [29, 30, 31, 32, 33, 35, 36, 37],
    [],
    "G03, G05–G06 ; matrices orthogonales ; conjugaison complexe.",
    "Une isométrie conserve les distances. Sa partie linéaire est orthogonale : MᵀM=I. Directe ou indirecte selon det M=+1 ou −1. Dans le plan complexe, une similitude directe s’écrit az+b, a≠0, une indirecte a conj(z)+b ; leur rapport vaut |a|.",
    "Une isométrie d’un espace affine euclidien de dimension finie dans lui-même est affine. Dans le plan : identité, translation, rotation, réflexion ou réflexion glissée. La composée de deux réflexions d’axes sécants est une rotation ; d’axes parallèles, une translation.",
    "Retirer l’image de l’origine puis retrouver le produit scalaire par polarisation pour prouver l’affinité. Classifier avec M, son déterminant et (I−M)x=b. Démontrer la formule de composition de deux réflexions par affixes.",
    "z↦iz+1 est une rotation de centre (1+i)/2. z↦conj(z)+1 est une réflexion glissée sans point fixe. Une similitude de rapport différent de 1 n’est pas une isométrie.",
    "Calculer rapport, caractère direct/indirect et points fixes avant de nommer la transformation. Pour un groupe de symétries d’une figure, vérifier que les transformations préservent effectivement toute la figure.",
    "N1 : classifier z↦−z+2. N2 : composer deux réflexions dont les axes font π/6. N3 : déterminer toutes les isométries d’un triangle équilatéral et leur loi de composition.",
    "Je vérifie MᵀM=I ; je ne déduis pas le type du seul déterminant ; je trouve centre ou axe ; je distingue réflexion et réflexion glissée.",
    resources=(
        "geometry_euclidean_isometries_td_lyon",
        "geometry_complex_video_exo7",
        "geometry_exam_2016_final_lyon",
    ),
)

chapter(
    "G08",
    "Géométrie",
    "Coniques et prolongements en dimension trois",
    [34, 44, 45, 46, 47, 48, 49],
    [],
    "G01–G07 acquis ; réduction des matrices symétriques réelles. Complément à confirmer avec le syllabus local ; priorité aux coniques planes avant les quadriques.",
    "Une conique est un lieu défini par une équation quadratique plane, éventuellement dégénérée. Le modèle foyer-directrice avec e>0 décrit les coniques non circulaires non dégénérées ; le cercle se traite séparément. Une quadrique est l’analogue dans R³.",
    "Une rotation diagonalise la partie quadratique symétrique ; une translation élimine les termes linéaires quand le centre existe. Le rang et la signature ne suffisent pas seuls : il faut aussi examiner le terme constant réduit et les directions du noyau.",
    "Démontrer la réduction d’une équation quadratique à centre par diagonalisation et complétion du carré. Pour les sections coniques d’un cône, savoir expliquer une configuration simple ; réserver la preuve générale à la confirmation du programme.",
    "x²+y²=−1 donne l’ensemble vide ; x²−y²=0 deux droites ; x²+y²=1 un cercle ; y=x² une parabole. En dimension trois, x²+y²−z²=1 et =−1 ne décrivent pas le même type d’hyperboloïde.",
    "Écrire la matrice symétrique, calculer valeurs propres et directions principales, chercher le centre puis traduire l’équation réduite en géométrie. Les transformations affines ne conservent pas toutes les données métriques de la conique.",
    "N1 : réduire x²+y²−2x+4y=0. N2 : classifier 2xy=1 par rotation de π/4. N3 : classifier x²+y²−z²=c selon c, puis repérer les symétries. Classification complète des isométries de R³ : prolongement après les exercices plans.",
    "Je traite les cas dégénérés ; je distingue réduction affine et euclidienne ; je ne confonds pas cercle et modèle à directrice finie ; je sais reporter un approfondissement non nécessaire au socle.",
    optional=True,
    resources=(
        "geometry_conics_td_lyon",
        "geometry_affine_video_exo7",
    ),
)


def render_chapter(ch, competencies, resources):
    values = list(ch["sections"])
    values.insert(1, "\n".join(competencies))
    values.insert(8, "\n".join(f"{r['title']} — {r['url']}\n{r['reading']}" for r in resources))
    text = (
        ch["title"]
        + "\n\n"
        + "\n\n".join(f"{i}. {name}\n{value}" for i, (name, value) in enumerate(zip(SECTIONS, values, strict=True), 1))
    )
    html = "<h2>" + escape(ch["title"]) + "</h2>"
    for i, (name, value) in enumerate(zip(SECTIONS, values, strict=True), 1):
        html += f"<h3>{i}. {escape(name)}</h3>"
        if i == 9:
            html += (
                "<ul>"
                + "".join(
                    f'<li><a href="{escape(r["url"], quote=True)}">{escape(r["title"])}</a> — {escape(r["reading"])}</li>'
                    for r in resources
                )
                + "</ul>"
            )
        else:
            html += "".join(f"<p>{escape(line)}</p>" for line in value.splitlines())
    return text, html
