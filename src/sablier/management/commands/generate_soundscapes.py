from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

PROFILES = {
    "concentration": ((72.0, 108.0, 144.0), 0.055, 0.075),
    "calm": ((87.3, 130.8, 174.6), 0.040, 0.055),
    "energy": ((92.0, 184.0, 276.0), 0.065, 0.090),
    "night": ((55.0, 82.4, 110.0), 0.045, 0.060),
}


class Command(BaseCommand):
    help = "Génère les paysages sonores originaux de Sablier sans ressource tierce."

    def add_arguments(self, parser):
        parser.add_argument("--output", type=Path, default=settings.BASE_DIR / "static" / "sablier" / "audio")

    def handle(self, *args, **options):
        output = options["output"]
        output.mkdir(parents=True, exist_ok=True)
        for name, profile in PROFILES.items():
            self._write_soundscape(output / f"{name}.wav", profile)
            self.stdout.write(self.style.SUCCESS(f"Généré : {name}.wav"))
        self._write_chime(output / "finished.wav")
        self.stdout.write(self.style.SUCCESS("Généré : finished.wav"))

    @staticmethod
    def _write_soundscape(path, profile):
        frequencies, left_detune, right_detune = profile
        sample_rate, duration = 22050, 10.0
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(2)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            chunk = bytearray()
            for index in range(int(sample_rate * duration)):
                t = index / sample_rate
                edge = min(1.0, t / 0.8, (duration - t) / 0.8)
                envelope = math.sin(max(0.0, edge) * math.pi / 2) ** 2
                breath = 0.68 + 0.18 * math.sin(2 * math.pi * t / 7.5)
                left = right = 0.0
                for frequency, weight in zip(frequencies, (1.0, 0.46, 0.24)):
                    left += weight * math.sin(2 * math.pi * (frequency - left_detune) * t)
                    right += weight * math.sin(2 * math.pi * (frequency + right_detune) * t + 0.18)
                amplitude = 2500 * envelope * breath
                chunk.extend(struct.pack("<hh", int(left * amplitude), int(right * amplitude)))
                if len(chunk) >= 16384:
                    wav.writeframesraw(chunk)
                    chunk.clear()
            if chunk:
                wav.writeframesraw(chunk)

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
