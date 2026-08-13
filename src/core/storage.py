"""Stockage des fichiers statiques en production.

Le stockage à manifeste renomme chaque fichier avec l'empreinte de son contenu et refuse,
par défaut, de rendre une adresse pour un nom absent du manifeste. Cette rigueur est utile
— elle attrape les ressources oubliées à la construction de l'image — mais elle suppose
que tous les gabarits ne demandent que des fichiers réels.

Jazzmin ne respecte pas cette hypothèse. Son `admin/base.html` écrit :

    data-theme-base="{% static 'vendor/bootswatch' %}"

soit un *répertoire*, que son script client complète ensuite pour changer de thème. Aucun
manifeste ne contient de répertoire : la recherche lève `ValueError` et toute
l'administration rend une erreur 500. Le défaut est chez Jazzmin, mais il est dans un
gabarit tiers de plusieurs centaines de lignes qu'il faudrait recopier entièrement — et
maintenir — pour corriger une seule ligne.

`manifest_strict = False` fait retomber les noms inconnus sur l'adresse non empreintée au
lieu de lever. La contrepartie est réelle et assumée : une ressource réellement absente ne
casse plus la page côté serveur, elle devient un 404 sur cette seule ressource dans le
navigateur. C'est le comportement raisonnable ici, où l'alternative est une administration
inutilisable.
"""

from __future__ import annotations

from whitenoise.storage import CompressedManifestStaticFilesStorage


class ForgivingManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """Empreinte et compresse comme son parent, mais ne lève pas sur un nom inconnu."""

    manifest_strict = False
