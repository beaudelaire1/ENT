# Architecture de Tempo Studio

## Principe

L’application sépare strictement le temps, l’état et le rendu :

```text
orateur_timer.py
  TimerController ─────── propriétés/signaux ───────► QML
  FocusSoundscape                                      │
                                                       ▼
qml/Main.qml ──► Sidebar / TimerStage / ControlBar / visualisations
```

## Moteur Python

`TimerController` est l’unique source de vérité. Il expose à QML des
propriétés en lecture seule et des opérations explicites : démarrer, suspendre,
réinitialiser, ajuster ou reconfigurer.

Le temps restant est calculé depuis `time.monotonic()`. L’application ne
soustrait donc pas naïvement 33 millisecondes à chaque image : même si le rendu
ralentit, le chronomètre reste juste.

Les préférences sont enregistrées avec `QSettings`.

## Interface QML

Qt Quick/QML est la couche déclarative native de Qt pour les interfaces
animées. Un document XML générique n’aurait apporté ni moteur d’animation, ni
liaisons réactives, ni rendu GPU. Le seul XML utilisé est le SVG du logo, format
approprié pour une ressource vectorielle.

Les visualisations sont isolées :

- `RingTimer.qml` : progression circulaire ;
- `HourglassTimer.qml` : géométrie du verre, conservation et écoulement du sable ;
- `DigitalTimer.qml` : lecture scénique à fort contraste ;
- `ZenTimer.qml` : respiration lente et réduction de la charge cognitive.

`TimerStage.qml` gère l’ambiance, les alertes et la scène, sans connaître la
logique interne du chronomètre.

## Sablier

La quantité de sable haute est `progress`. La quantité basse est exactement
`1 - progress`. La surface haute descend vers le goulot tandis que le tas bas
monte et s’élargit. Le filet et les particules ne sont dessinés que si le
chronomètre est actif.

## Son

`FocusSoundscape` synthétise une texture stéréo douce dans le cache local.
La génération s’exécute dans un fil secondaire afin de ne jamais bloquer
l’interface. Le son est désactivé par défaut et reste entièrement optionnel.

## Contrôles réalisés

- compilation Python avec `py_compile` ;
- analyse de tous les fichiers QML avec `qmllint` ;
- chargement réel de `Main.qml` avec `QQmlApplicationEngine` ;
- test des états du moteur, des quatre modes et des quatre ambiances ;
- rendu réel du sablier en cours d’écoulement et capture de contrôle.
