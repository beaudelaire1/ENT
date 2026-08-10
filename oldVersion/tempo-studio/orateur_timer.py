"""Tempo Studio — moteur Python et point d’entrée Qt Quick.

La logique métier reste ici. Toute l’interface et les animations sont dans
`qml/`, ce qui évite de mélanger le chronométrage avec le rendu visuel.
"""

from __future__ import annotations

import math
import struct
import sys
import threading
import time
import wave
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QObject,
    QSettings,
    QStandardPaths,
    QTimer,
    QUrl,
    Signal,
    Slot,
    Qt,
)
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtQml import QQmlApplicationEngine


APP_DIR = Path(__file__).resolve().parent
QML_FILE = APP_DIR / "qml" / "Main.qml"
ICON_FILE = APP_DIR / "assets" / "tempo_mark.svg"


def format_time(seconds: float) -> str:
    total = max(0, math.ceil(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return (
        f"{hours:02d}:{minutes:02d}:{secs:02d}"
        if hours
        else f"{minutes:02d}:{secs:02d}"
    )


def parse_duration(value: str) -> int | None:
    """Accepte 5, 05:00 ou 01:05:00, dans la limite de 24 heures."""
    value = value.strip()
    try:
        if ":" not in value:
            seconds = round(float(value.replace(",", ".")) * 60)
        else:
            parts = [int(part) for part in value.split(":")]
            if len(parts) == 2:
                seconds = parts[0] * 60 + parts[1]
            elif len(parts) == 3:
                seconds = parts[0] * 3600 + parts[1] * 60 + parts[2]
            else:
                return None
        if not 1 <= seconds <= 24 * 3600:
            return None
        return seconds
    except (TypeError, ValueError):
        return None


class FocusSoundscape(QObject):
    """Génère localement un tapis sonore doux, puis le joue en boucle.

    Aucun fichier audio tiers ni accès réseau : les textures sont synthétisées
    dans le cache de l’application avec une enveloppe sans clic.
    """

    sourceReady = Signal(str, str)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.effect = QSoundEffect(self)
        self.effect.setLoopCount(QSoundEffect.Infinite.value)
        self.effect.setVolume(0.055)
        self._pending_play = False
        self._requested_ambience: str | None = None
        self.effect.statusChanged.connect(self._on_status_changed)
        self.sourceReady.connect(self._load_generated_source)

    @Slot()
    def _on_status_changed(self) -> None:
        if self._pending_play and self.effect.status() == QSoundEffect.Status.Ready:
            self._pending_play = False
            self.effect.play()

    def play(self, ambience: str) -> None:
        self._requested_ambience = ambience
        threading.Thread(
            target=self._prepare_source,
            args=(ambience,),
            daemon=True,
            name="tempo-soundscape",
        ).start()

    def stop(self) -> None:
        self._requested_ambience = None
        self._pending_play = False
        self.effect.stop()

    def _prepare_source(self, ambience: str) -> None:
        path = self._ensure_wave(ambience)
        if path is not None:
            self.sourceReady.emit(ambience, str(path))

    @Slot(str, str)
    def _load_generated_source(self, ambience: str, path: str) -> None:
        if self._requested_ambience != ambience:
            return
        self.effect.stop()
        self._pending_play = True
        self.effect.setSource(QUrl.fromLocalFile(path))
        if self.effect.status() == QSoundEffect.Status.Ready:
            self._pending_play = False
            self.effect.play()

    @staticmethod
    def _ensure_wave(ambience: str) -> Path | None:
        cache_root = QStandardPaths.writableLocation(
            QStandardPaths.StandardLocation.CacheLocation
        )
        if not cache_root:
            return None
        folder = Path(cache_root) / "soundscapes"
        folder.mkdir(parents=True, exist_ok=True)
        safe_name = ambience.lower().replace("é", "e").replace(" ", "_")
        output = folder / f"{safe_name}_v2.wav"
        if output.exists():
            return output

        profiles = {
            "Concentration": ((72.0, 108.0, 144.0), 0.055, 0.075),
            "Calme": ((87.3, 130.8, 174.6), 0.040, 0.055),
            "Énergie": ((92.0, 184.0, 276.0), 0.065, 0.090),
            "Nocturne": ((55.0, 82.4, 110.0), 0.045, 0.060),
        }
        frequencies, left_detune, right_detune = profiles.get(
            ambience, profiles["Concentration"]
        )
        sample_rate = 22_050
        duration = 10.0
        frame_count = int(sample_rate * duration)

        try:
            with wave.open(str(output), "wb") as wav:
                wav.setnchannels(2)
                wav.setsampwidth(2)
                wav.setframerate(sample_rate)
                chunk = bytearray()
                for index in range(frame_count):
                    t = index / sample_rate
                    # Départ et fin à zéro pour une boucle propre.
                    edge = min(1.0, t / 0.8, (duration - t) / 0.8)
                    envelope = math.sin(max(0.0, edge) * math.pi / 2) ** 2
                    breath = 0.68 + 0.18 * math.sin(2 * math.pi * t / 7.5)
                    left = 0.0
                    right = 0.0
                    weights = (1.0, 0.46, 0.24)
                    for frequency, weight in zip(frequencies, weights):
                        left += weight * math.sin(
                            2 * math.pi * (frequency - left_detune) * t
                        )
                        right += weight * math.sin(
                            2 * math.pi * (frequency + right_detune) * t + 0.18
                        )
                    amplitude = 2_500 * envelope * breath
                    chunk.extend(
                        struct.pack(
                            "<hh",
                            int(max(-32767, min(32767, left * amplitude))),
                            int(max(-32767, min(32767, right * amplitude))),
                        )
                    )
                    if len(chunk) >= 16_384:
                        wav.writeframesraw(chunk)
                        chunk.clear()
                if chunk:
                    wav.writeframesraw(chunk)
            return output
        except OSError:
            return None


class TimerController(QObject):
    stateChanged = Signal()
    configurationChanged = Signal()
    cue = Signal(str)

    MODES = {"Anneau", "Sablier", "Digital", "Zen"}
    AMBIENCES = {"Concentration", "Calme", "Énergie", "Nocturne"}

    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("TempoStudio", "SpeakerTimerQml")

        self._total = 300.0
        self._remaining = 300.0
        self._running = False
        self._finished = False
        self._end_monotonic = 0.0
        self._session_title = str(
            self.settings.value("sessionTitle", "Présentation principale")
        )
        self._mode = str(self.settings.value("mode", "Anneau"))
        if self._mode not in self.MODES:
            self._mode = "Anneau"
        self._ambience = str(
            self.settings.value("ambience", "Concentration")
        )
        if self._ambience not in self.AMBIENCES:
            self._ambience = "Concentration"
        self._warning_seconds = int(self.settings.value("warningSeconds", 60))
        self._sound_enabled = (
            str(self.settings.value("soundEnabled", "false")).lower() == "true"
        )
        self._focus_level = int(self.settings.value("focusLevel", 2))
        self._warning_cue_sent = False

        self.soundscape = FocusSoundscape(self)
        if self._sound_enabled:
            QTimer.singleShot(400, lambda: self.soundscape.play(self._ambience))

        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    @Property(float, notify=stateChanged)
    def totalSeconds(self) -> float:
        return self._total

    @Property(float, notify=stateChanged)
    def remainingSeconds(self) -> float:
        return self._remaining

    @Property(float, notify=stateChanged)
    def progress(self) -> float:
        return max(0.0, min(1.0, self._remaining / max(1.0, self._total)))

    @Property(str, notify=stateChanged)
    def formattedTime(self) -> str:
        return format_time(self._remaining)

    @Property(bool, notify=stateChanged)
    def running(self) -> bool:
        return self._running

    @Property(bool, notify=stateChanged)
    def finished(self) -> bool:
        return self._finished

    @Property(bool, notify=stateChanged)
    def warning(self) -> bool:
        return not self._finished and self._remaining <= self._warning_seconds

    @Property(str, notify=configurationChanged)
    def sessionTitle(self) -> str:
        return self._session_title

    @Property(str, notify=configurationChanged)
    def mode(self) -> str:
        return self._mode

    @Property(str, notify=configurationChanged)
    def ambience(self) -> str:
        return self._ambience

    @Property(int, notify=configurationChanged)
    def warningSeconds(self) -> int:
        return self._warning_seconds

    @Property(bool, notify=configurationChanged)
    def soundEnabled(self) -> bool:
        return self._sound_enabled

    @Property(int, notify=configurationChanged)
    def focusLevel(self) -> int:
        return self._focus_level

    @Slot(str, result=bool)
    def setDuration(self, value: str) -> bool:
        seconds = parse_duration(value)
        if seconds is None:
            return False
        self._running = False
        self._finished = False
        self._total = float(seconds)
        self._remaining = float(seconds)
        self._warning_cue_sent = False
        self.stateChanged.emit()
        return True

    @Slot(int)
    def setPreset(self, minutes: int) -> None:
        self.setDuration(f"{minutes}:00")

    @Slot()
    def startPause(self) -> None:
        if self._finished:
            self.reset()
        if self._running:
            self._remaining = max(0.0, self._end_monotonic - time.monotonic())
            self._running = False
        else:
            self._end_monotonic = time.monotonic() + self._remaining
            self._running = True
        self.stateChanged.emit()

    @Slot()
    def reset(self) -> None:
        self._running = False
        self._finished = False
        self._remaining = self._total
        self._warning_cue_sent = False
        self.stateChanged.emit()

    @Slot(int)
    def adjust(self, seconds: int) -> None:
        self._remaining = max(0.0, min(24 * 3600, self._remaining + seconds))
        self._total = max(1.0, self._total, self._remaining)
        self._finished = False
        self._warning_cue_sent = False
        if self._running:
            self._end_monotonic = time.monotonic() + self._remaining
        self.stateChanged.emit()

    @Slot(str)
    def setSessionTitle(self, value: str) -> None:
        cleaned = value.strip()[:80] or "Session sans titre"
        if cleaned == self._session_title:
            return
        self._session_title = cleaned
        self.settings.setValue("sessionTitle", cleaned)
        self.configurationChanged.emit()

    @Slot(str)
    def setMode(self, value: str) -> None:
        if value not in self.MODES or value == self._mode:
            return
        self._mode = value
        self.settings.setValue("mode", value)
        self.configurationChanged.emit()

    @Slot(str)
    def setAmbience(self, value: str) -> None:
        if value not in self.AMBIENCES or value == self._ambience:
            return
        self._ambience = value
        self.settings.setValue("ambience", value)
        if self._sound_enabled:
            self.soundscape.play(value)
        self.configurationChanged.emit()

    @Slot(int)
    def setWarningSeconds(self, value: int) -> None:
        value = max(10, min(180, value))
        if value == self._warning_seconds:
            return
        self._warning_seconds = value
        self.settings.setValue("warningSeconds", value)
        self.configurationChanged.emit()
        self.stateChanged.emit()

    @Slot(int)
    def setFocusLevel(self, value: int) -> None:
        value = max(1, min(3, value))
        if value == self._focus_level:
            return
        self._focus_level = value
        self.settings.setValue("focusLevel", value)
        self.configurationChanged.emit()

    @Slot()
    def toggleSound(self) -> None:
        self._sound_enabled = not self._sound_enabled
        self.settings.setValue("soundEnabled", self._sound_enabled)
        if self._sound_enabled:
            self.soundscape.play(self._ambience)
        else:
            self.soundscape.stop()
        self.configurationChanged.emit()

    @Slot()
    def _tick(self) -> None:
        if not self._running:
            return
        previous = self._remaining
        self._remaining = max(0.0, self._end_monotonic - time.monotonic())

        if (
            previous > self._warning_seconds >= self._remaining
            and not self._warning_cue_sent
        ):
            self._warning_cue_sent = True
            self.cue.emit("warning")

        if self._remaining <= 0:
            self._remaining = 0.0
            self._running = False
            self._finished = True
            self.cue.emit("finished")

        self.stateChanged.emit()


def main() -> int:
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Tempo Studio")
    app.setApplicationDisplayName("Tempo Studio")
    app.setOrganizationName("TempoStudio")
    if ICON_FILE.exists():
        app.setWindowIcon(QIcon(str(ICON_FILE)))

    controller = TimerController()
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("timerController", controller)
    engine.load(QUrl.fromLocalFile(str(QML_FILE)))
    if not engine.rootObjects():
        return 1
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
