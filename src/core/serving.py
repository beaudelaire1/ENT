"""Remise d'un fichier privé, sans immobiliser un worker pendant toute la lecture.

Gunicorn tourne avec trois processus de deux fils : six requêtes simultanées. Un fichier
servi par Django occupe l'une de ces places du début à la fin du transfert — et une piste
audio d'un gigaoctet écoutée en entier l'occupe pendant toute l'écoute. Trois auditeurs
suffisaient à mobiliser la moitié du serveur, six à l'arrêter.

Trois remises, de la meilleure à la dernière :

1. **S3** — une redirection signée : le fichier ne passe jamais par l'application. Les
   en-têtes que la vue a choisis voyagent alors dans l'adresse signée elle-même, faute
   de quoi le navigateur ne verrait que ceux de l'objet déposé ;
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


def signed_url(file, *, as_attachment: bool, content_type: str | None) -> str:
    """L'adresse signée de l'objet, portant les en-têtes que la vue a choisis.

    Le type MIME d'un objet du bucket est celui posé au moment du dépôt, et lui seul. Un
    fichier arrivé par la console du fournisseur, par ``rclone`` ou par la restauration
    d'une sauvegarde porte le plus souvent ``application/octet-stream`` — ou rien. Le
    navigateur, que la redirection envoie droit sur le stockage, ne voit jamais le type
    que la vue a pourtant calculé : il reçoit celui de l'objet, et refuse de décoder une
    piste intacte. En développement, où Django sert lui-même le fichier et pose l'en-tête,
    la même piste se lit sans rien signaler — d'où une panne qui ne se voit qu'en production.

    ``response-content-type`` et ``response-content-disposition`` sont signés avec
    l'adresse : le stockage les substitue à la remise, sans que l'objet soit réécrit. Ce
    sont les deux arguments de cette fonction, qui étaient jusqu'ici silencieusement perdus
    dès que le stockage était un bucket.
    """
    parameters = {}
    if content_type:
        parameters["ResponseContentType"] = content_type
    if as_attachment:
        filename = file.name.rsplit("/", 1)[-1]
        parameters["ResponseContentDisposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
    # Sans en-tête à imposer, l'adresse ordinaire suffit : c'est celle que le stockage
    # signe pour tout le reste, et la faire passer par un autre chemin n'apporterait rien.
    return file.storage.url(file.name, parameters=parameters) if parameters else file.url


def serve_private_file(file, *, as_attachment: bool = False, content_type: str | None = None) -> HttpResponse:
    """Rend le fichier au client par le chemin le moins coûteux disponible."""
    if hasattr(file.storage, "bucket"):
        return redirect(signed_url(file, as_attachment=as_attachment, content_type=content_type))

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
