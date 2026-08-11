"""Affichage des tailles de fichier.

Les limites se règlent en mégaoctets, mais « 1024 Mo » ne se lit pas : au-delà du
gigaoctet, on écrit ce que l'utilisateur attend.
"""

from __future__ import annotations


def human_mb(megabytes: float) -> str:
    if megabytes >= 1024:
        gigabytes = megabytes / 1024
        return f"{gigabytes:.0f} Go" if gigabytes == int(gigabytes) else f"{gigabytes:.1f} Go"
    return f"{megabytes:.0f} Mo" if megabytes == int(megabytes) else f"{megabytes:.1f} Mo"
