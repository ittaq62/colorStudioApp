# ColorStudio 1.0

Outil de compositing par sources lumineuses : melange d'images pre-rendues
(une image par position de lumiere), application d'une couleur + exposition
par lumiere, puis somme. Mode HDR, post-process (auto-exposure, saturation),
interface PyQt6 moderne avec dark theme.

Projet original : Remi Cozot, 2019.
Reprise dans le cadre de la **SAE 6A - Maintenance logicielle** (BUT3 INFO APP, 2025/2026).

## Sommaire

- [Installation](#installation)
- [Lancement](#lancement)
- [Fonctionnalites](#fonctionnalites)
- [Construire un .exe standalone](#construire-un-exe-standalone)
- [Structure du projet](#structure-du-projet)
- [Tests](#tests)
- [Documentation](#documentation)

## Installation

### Methode rapide (avec pip)

```bash
py -3.13 -m pip install -e .
```

L'app devient utilisable comme **commande** :
```bash
colorstudio              # ou
python -m colorstudio
```

### Methode classique (sans installation)

```bash
py -3.13 -m pip install -r requirements.txt
py -3.13 main.py
```

### Prerequis

- Python 3.12 ou superieur (testes : 3.12, 3.13)
- OS : Windows / Linux / macOS (PyQt6 cross-platform)

## Lancement

```bash
colorstudio                      # lance avec la derniere scene utilisee
colorstudio xml-hdr-demo.json    # lance avec un fichier specifique
```

Au premier lancement une boite de dialogue demande un fichier de scene
(JSON ou XML). Aux lancements suivants, **le dernier fichier ouvert est
re-charge automatiquement** (memorise via QSettings).

Pour changer de scene en cours d'execution : menu **Fichier > Ouvrir** (Ctrl+O)
ou **Fichier > Recemment ouverts**.

## Fonctionnalites

### Interface

- **Fenetre unique** (`QMainWindow`) avec dark theme moderne
- **Menu bar** : Fichier / Affichage / Aide
- **Status bar** en bas : fichier charge, mode (LDR/HDR), nb lumieres, temps de rendu
- **Sidebar scrollable** avec cards de controle (Project, HDR, Auto Exposure, Saturation, Lights)
- **Zone image** responsive + nuage 3D RGB en bas (moderngl)
- **Splash screen** au demarrage
- **Recents files** dans le menu Fichier (5 derniers)

### Raccourcis clavier

| Raccourci | Action                              |
|-----------|-------------------------------------|
| Ctrl+O    | Ouvrir une scene                    |
| Ctrl+S    | Sauvegarder le rendu en image       |
| Ctrl+Shift+S | Exporter la scene en JSON        |
| Ctrl+H    | Basculer le mode HDR                |
| Ctrl+Q    | Quitter                             |
| F1        | Documentation                       |

### Mode HDR

Le mode HDR garde les valeurs RGB > 1.0 dans le rendu (au lieu de les
clipper a 1) et applique un tone mapping de Reinhard (`x / (1+x)`) a
l'affichage. Utile pour les scenes avec des lumieres tres exposees.

Trois facons de l'activer :
1. dans le fichier de scene : `"hdr": true` (JSON) ou `hdr="true"` (XML racine)
2. case a cocher **HDR mode** dans la sidebar
3. menu **Affichage > Basculer HDR** (Ctrl+H)

Exemple : voir `xml-hdr-demo.json`.

### Format de scenes

Deux formats supportes (detectes par extension) :
- **JSON** : moderne, lisible. Voir `docs/xml-format.md`.
- **XML** : historique, conserve pour compat 2019.

## Construire un .exe standalone

```bash
py -3.13 -m pip install -r requirements-dev.txt
py -3.13 build_exe.py
```

Le binaire est produit dans `dist/colorstudio/colorstudio.exe` (~11 Mo).
Le bundle complet (avec dependances) fait ~270 Mo.

Mode "un seul fichier" (.exe portable) :
```bash
py -3.13 build_exe.py --onefile
```

## Structure du projet

```
colorstudio/              package principal
    __init__.py
    __main__.py           point d'entree pour `python -m colorstudio`
    app.py                fonction main() + init Qt + splash + load scene
    model.py              Light, Scene, PostProcess (Saturation, AE_Ymean, PPClip)
    widget.py             widgets PyQt6 (CardWidget, CSDisplayWidget, ...)
    ui_builder.py         CSMainWindow (menu, status, settings) + CSUIAllBuilder
    controller.py         controleurs (light, AE, saturation)
    utils.py              chargement images, toneMap, colorWheel, ...
    icons/                icones SVG + app.ico (multi-resolution)
    styles.qss            dark theme

tests/                    tests unitaires (24 tests)
    test_model.py
    test_utils.py

docs/                     documentation utilisateur + technique
    user-guide.md
    architecture.md
    xml-format.md

images/                   sets d'images pre-rendues (light01_*.jpg)
*.json / *.xml            scenes pre-configurees
splashScreen.jpg          splash screen au demarrage

pyproject.toml            packaging Python (PEP 621)
requirements.txt          dependances runtime
requirements-dev.txt      dependances de developpement (PyInstaller, pytest)
colorstudio.spec          spec PyInstaller pour bundle .exe
build_exe.py              wrapper de build .exe
generate_icons.py         regenere les icones SVG + app.ico

main.py                   entry point pour developpement
CHANGELOG.md              historique des versions
JOURNAL.md                journal de bord SAE 6A
```

## Tests

```bash
py -3.13 -m unittest discover -s tests -v
```

24 tests unitaires couvrent : modele (Light, Scene, Saturation, AE_Ymean,
PPClip, fromXML, fromJSON, render empty scene), utils (loadImage LDR+HDR,
toneMap).

## Documentation

- `docs/user-guide.md` : guide utilisateur (UI, raccourcis, ajout de scenes)
- `docs/architecture.md` : architecture MVC + flux de donnees
- `docs/xml-format.md` : format XML et JSON des scenes (avec correspondance)
- `CHANGELOG.md` : historique des versions
- `JOURNAL.md` : journal de bord de la reprise SAE 6A

## Auteurs

- **Blaszyk Constant**
- **Douilly Quentin**
- **Deldalle Corentin**

Repo : https://github.com/ittaq62/colorStudioApp
