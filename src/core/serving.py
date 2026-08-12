"""Remise d'un fichier privé, sans immobiliser un worker pendant toute la lecture.

Gunicorn tourne avec trois processus de deux fils : six requêtes simultanées. Un fichier
servi par Django occupe l'une de ces places du début à la fin du transfert — et une piste
audio d'un gigaoctet écoutée en entier l'occupe pendant toute l'écoute. Trois auditeurs
suffisaient à mobiliser la moitié du serveur, six à l'arrêter.

Trois remises, de la meilleure à la dernière :

1. **S3** — une redirection signée : le fichier ne passe jamais par l'application ;
2. **le proxy** — `X-Accel-Redirect` : Django vérifie le droit d'accès et rend une réponse
   vide, le proxy envoie le fichier. C'est lui qui sait faire cela sans bloquer ;
3. **Django** — le repli, correct mais coûteux, et le seul disponible en développement.

Le contrôle d'accès reste dans tous les cas ici : c'est la vue qui a vérifié le
propriétaire, et l'emplacement interne du proxy ne doit jamais être exposé publiquement.
"""

from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse, HttpResponse
from django.shortcuts import redirect


def internal_location() -> str:
    """Le préfixe interne du proxy, vide quand la délégation n'est pas configurée."""
    location = getattr(settings, "MEDIA_INTERNAL_LOCATION", "") or ""
    return location if location.endswith("/") else f"{location}/" if location else ""


def serve_private_file(file, *, as_attachment: bool = False, content_type: str | None = None) -> HttpResponse:
    """Rend le fichier au client par le chemin le moins coûteux disponible."""
    if hasattr(file.storage, "bucket"):
        return redirect(file.url)

    filename = file.name.rsplit("/", 1)[-1]
    location = internal_location()
    if location:
        response = HttpResponse(content_type=content_type or "application/octet-stream")
        # Le nom est encodé : un fichier nommé « résumé du cours.pdf » produirait sinon un
        # en-tête invalide, et le proxy refuserait la requête.
        response["X-Accel-Redirect"] = f"{location}{quote(file.name)}"
        response["X-Sendfile"] = file.path if hasattr(file, "path") else ""
        if as_attachment:
            response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
        # Le corps est vide : c'est le proxy qui remplit la réponse. Laisser Django
        # calculer une longueur nulle ferait croire au navigateur à un fichier vide.
        del response["Content-Length"]
        return response

    return FileResponse(file.open("rb"), as_attachment=as_attachment, filename=filename, content_type=content_type)
