from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Génère le carillon de fin de session, sans ressource tierce."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path, default=settings.BASE_DIR / "static" / "sablier" / "audio")

    def handle(self, *args, **options):
        output = options["output"]
        output.mkdir(parents=True, exist_ok=True)
        self._write_chime(output / "finished.wav")
        self.stdout.write(self.style.SUCCESS("Généré : finished.wav"))

    @staticmethod
    def _write_chime(path):
        sample_rate, duration = 22050, 1.6
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            frames = bytearray()
            for index in range(int(sample_rate * duration)):
                t = index / sample_rate
                envelope = math.exp(-2.7 * t)
                sample = envelope * (math.sin(2 * math.pi * 660 * t) + 0.55 * math.sin(2 * math.pi * 990 * t))
                frames.extend(struct.pack("<h", int(7000 * sample)))
            wav.writeframes(frames)
