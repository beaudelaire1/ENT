# Tempo Studio

Chronomètre de scène moderne pour orateurs, développé en Python avec
**PySide6 et Qt Quick/QML**.

![Aperçu de Tempo Studio](tempo-studio-preview.png)

## Lancer l’application

Sous Windows, double-cliquez sur :

```text
lancer_tempo_studio.bat
```

Au premier lancement, PySide6 est installé automatiquement si nécessaire.

Lancement manuel :

```powershell
python -m pip install -r requirements.txt
python orateur_timer.py
```

## Ce qui est inclus

- quatre visualisations : Anneau, Sablier, Digital et Zen ;
- sablier conservant visuellement le volume de sable entre les chambres ;
- grains et filet de sable animés uniquement quand le chronomètre avance ;
- ambiances Concentration, Calme, Énergie et Nocturne ;
- tapis sonore stéréo optionnel, généré localement et sans fichier tiers ;
- trois niveaux de concentration ;
- mode Zen avec respiration guidée et temps volontairement discret au niveau 3 ;
- seuil d’alerte réglable de 10 à 180 secondes ;
- mode scène plein écran sans panneau de configuration ;
- préférences persistantes ;
- chronométrage basé sur une horloge monotone, résistant aux ralentissements
  graphiques et aux changements de l’horloge système.

## Raccourcis

- `Espace` : démarrer ou mettre en pause ;
- `R` : réinitialiser ;
- `F11` : entrer ou sortir du mode scène ;
- `Échap` : quitter le mode scène.

Les raccourcis de lecture sont automatiquement désactivés pendant la saisie
d’un texte.

## Créer un exécutable Windows

Double-cliquez sur `construire_executable.bat`. Le résultat sera placé dans
le dossier `dist\Tempo Studio`.

Les choix techniques sont détaillés dans [ARCHITECTURE.md](ARCHITECTURE.md).
