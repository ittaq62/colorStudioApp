# Architecture du projet ColorStudio

## Vue d'ensemble

ColorStudio suit une architecture MVC (Model - View - Controller) assez
classique, repartie sur 4 fichiers du package `colorstudio/` :

```
colorstudio/
    model.py        (M) classes metier : Light, Scene, PostProcess
    widget.py       (V) widgets PyQt6 d'affichage / controle
    controller.py   (C) logique de reaction aux evenements UI
    ui_builder.py   (construction) assemble M + V + C a partir d'une Scene
    utils.py        (helpers) chargement d'images, tone mapping, etc.
```

Le point d'entree est `main.py` qui :
1. demande a l'utilisateur un fichier de scene (JSON ou XML)
2. instancie une `Scene` et la remplit via `Scene.fromJSON` ou `Scene.fromXML`
3. delegue a `CSUIAllBuilder` la construction de l'UI (`QMainWindow` unique)
4. lance la boucle d'evenements Qt

## Diagramme des responsabilites

```
 +----------------+            +---------------------+
 |   main.py      |----------->|   CSUIAllBuilder    |
 | (QFileDialog)  |            |  (ui_builder.py)    |
 +----------------+            +---------------------+
          |                         |        |        |
          v                         v        v        v
   +-----------+             +---------+  +---------+  +-----------+
   |   Scene   | <---------  |  Light  |  |  Post-  |  |  Widget   |
   | (model.py)|             | (model) |  | Process |  |(widget.py)|
   +-----------+             +---------+  +---------+  +-----------+
          ^                                                   |
          |           events                                  |
          |       (slider, boutons, ...)                      |
          +-------------- Controller <------------------------+
                          (controller.py)
```

## Flux de donnees lors d'un rendu

Chaque interaction utilisateur (slider d'exposition, ouverture de la
palette de couleur, changement d'index de lumiere...) declenche le meme
pattern :

```
  UI widget  ---event--->  Controller
                              |
                              | 1. modifie l'etat du Light / PostProcess
                              |    (via un setter : setColor, setExposure...)
                              v
                           Scene.render()
                              |
                              | 2. pour chaque Light :
                              |      Light.render() = img * color * 2^exposure
                              | 3. somme toutes les images
                              | 4. applique les post-process (AE, Saturation)
                              | 5. clip [0,1] si mode LDR
                              v
                           image RGB numpy
                              |
                              | 6. envoie l'image aux widgets d'affichage
                              v
                           Widget._update(img)  -> refresh ecran
```

## Detail des classes principales

### Model (`colorstudio/model.py`)

| Classe      | Role                                                    |
|-------------|---------------------------------------------------------|
| `Images`    | Set d'images pre-rendues (chargement, stockage)         |
| `Light`     | Une lumiere = set d'images + couleur + exposure + index |
| `Scene`     | Conteneur de `Light` + liste de `PostProcess`           |
| `PostProcess` | Classe de base (identite)                             |
| `Saturation`| Modifie la saturation en HSV (lineaire + gamma)         |
| `AE_Ymean`  | Auto-exposure : ramene la luminance moyenne a `Ytarget` |
| `PPClip`    | Clippe les valeurs dans un intervalle                   |

### View (`colorstudio/widget.py`)

Les widgets PyQt6 utilises :

| Widget                  | Role                                              |
|-------------------------|---------------------------------------------------|
| `CSDisplayWidget`       | Affichage de l'image rendue (QLabel + QPixmap)    |
| `CardWidget`            | Wrapper de "card" pour la sidebar (dark theme)    |
| `MyWidgetGL`            | Nuage de points 3D (moderngl + QOpenGLWidget)     |
| `CSQLightControlLayout` | Card de controle d'une lumiere (boutons + slider + preview couleur + palette `QColorDialog`) |
| `CSQAEControlLayout`    | Controle de l'auto-exposure                       |
| `CSQSaturationLayout`   | Controle de la saturation                         |
| `CSQLoadSaveLayout`     | Boutons Load / Save                               |
| `CSQHDRControlLayout`   | Case a cocher HDR mode                            |

### Controller (`colorstudio/controller.py`)

Un controleur par type de widget de controle. Ils implementent tous
`_event(widget, event)` ou `event` est un tuple `(type, value)`.

| Controleur                | Ecoute                                    | Mute                  |
|---------------------------|-------------------------------------------|-----------------------|
| `CSLightController`       | slider position, EV +/-, palette couleur  | `Light` (couleur/exp) |
| `CSAEController`          | toggle AE, slider exposure                | `AE_Ymean`            |
| `CSSaturationController`  | sliders saturation                        | `Saturation`          |

### Construction (`colorstudio/ui_builder.py`)

`CSUIAllBuilder` est le "ciment" entre M, V et C. Il prend une `Scene`
deja chargee, instancie une `QMainWindow` (`CSMainWindow`) avec :
- une sidebar scrollable contenant les "cards" de controle
- une zone image (rendu) + nuage 3D, separees par des splitters

Il instancie un controleur pour chaque layout et les connecte aux widgets
et aux objets du modele. Le choix de couleur des lumieres passe par un
`QColorDialog` natif declenche depuis chaque card lumiere (depuis avril
2025, en remplacement de l'ancienne roue chromatique custom).

Deux templates de resolution restent definis pour compat avec l'ancien
code (`template1920x1080` et `template3000x200`).

## Cycle de vie d'une session

1. `main.py` ouvre une `QFileDialog` -> chemin du fichier scene (JSON ou XML)
2. `Scene()` + `Scene.fromJSON(path)` ou `Scene.fromXML(path)` -> remplit `_lights` (et `_hdr` si present)
3. `CSUIAllBuilder(scene)` ouvre la `QMainWindow` et branche les controleurs
4. `QApplication.exec()` -> boucle d'evenements
5. A chaque event : controller -> setter modele -> `scene.render()` -> widgets

## Utilitaires (`colorstudio/utils.py`)

Fonctions pures utilisees par le modele et les widgets :

| Fonction            | Role                                              |
|---------------------|---------------------------------------------------|
| `loadImage`         | Charge une image (LDR uint8/uint16 ou HDR float)  |
| `toneMap`           | Tone mapping de Reinhard `x / (1+x)` pour HDR     |
| `image2Ymean`       | Luminance moyenne (conversion YUV)                |
| `imgRGB2chromaRG`   | Projection RGB -> chromaticite (rg)               |
| `img2chromaVertices`| Genere les vertices pour le nuage 3D              |
| `colorWheel`        | Genere l'image d'une roue chromatique (utilitaire, plus utilise dans l'UI depuis le passage a `QColorDialog`) |
| `printProgressBar`  | Barre de progression terminal                     |
