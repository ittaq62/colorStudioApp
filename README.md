# ColorStudio 1.4.1

Outil de compositing par sources lumineuses : melange d'images pre-rendues
(une image par position de lumiere), application d'une couleur + exposition
par lumiere, puis somme. Mode HDR, post-process (auto-exposure, saturation),
interface PyQt6 moderne avec dark theme, export Blender.

Projet original : Remi Cozot, 2019.
Reprise dans le cadre de la **SAE 6A - Maintenance logicielle** (BUT3 INFO APP, 2025/2026).

---

## Demarrage rapide

### Vous voulez juste lancer l'app (3 commandes)

```bash
git clone https://github.com/ittaq62/colorStudioApp
cd colorStudioApp
py -3.13 -m pip install -r requirements.txt
py -3.13 main.py
```

L'app demarre sur la scene par defaut (`xml-postProcess-test.json`). Tout est
fourni dans le repo : code source, 101 images pre-rendues, 5 scenes d'exemple,
icones, theme. **Aucun fichier supplementaire a telecharger.**

### Vous voulez fabriquer le `.exe` Windows (1 commande de plus)

```bash
py -3.13 -m pip install -r requirements-dev.txt
py -3.13 build_exe.py
```

Le `.exe` est genere dans `dist/colorstudio/colorstudio.exe` (~11 Mo).
Double-cliquer pour lancer. Le bundle complet (dossier `dist/colorstudio/`)
fait ~270 Mo et est copiable n'importe ou : c'est une app **standalone**, la
machine cible n'a pas besoin de Python installe.

### Vous etes sur Linux

```bash
sudo apt install python3 python3-pip libxcb-cursor0 libegl1
python3 -m pip install -r requirements-dev.txt
chmod +x build_linux.sh
./build_linux.sh
```

Le script build le binaire puis l'installe dans `~/.local/` avec un
raccourci `.desktop` integre au menu d'applications du DE.

---

## Sommaire

- [Prerequis](#prerequis)
- [Installation detaillee](#installation-detaillee)
- [Lancement](#lancement)
- [Fonctionnalites](#fonctionnalites)
- [Construire un binaire standalone](#construire-un-binaire-standalone)
- [Structure du projet](#structure-du-projet)
- [Que contient le repo / qu'est-ce qui est genere](#que-contient-le-repo--quest-ce-qui-est-genere)
- [Tests](#tests)
- [Documentation](#documentation)
- [Auteurs](#auteurs)

## Prerequis

- **Python 3.12 ou superieur** (testes : 3.12, 3.13)
- **OS** : Windows / Linux / macOS (PyQt6 est cross-platform)
- Pour le mode `.exe` standalone : PyInstaller (inclus dans `requirements-dev.txt`)
- Pour l'export Blender en .blend : Blender installe (optionnel, l'app le detecte automatiquement)

## Installation detaillee

### Methode 1 - installation editable via pip (recommandee)

```bash
py -3.13 -m pip install -e .
```

L'app devient utilisable comme **commande shell** :
```bash
colorstudio                       # lance l'app
colorstudio xml-hdr-demo.json     # lance avec une scene specifique
python -m colorstudio             # equivalent
```

### Methode 2 - sans installation (dev / debug)

```bash
py -3.13 -m pip install -r requirements.txt
py -3.13 main.py
```

### Methode 3 - `.exe` standalone (utilisateurs finaux Windows)

Voir [Construire un binaire standalone](#construire-un-binaire-standalone) plus bas.
Le binaire produit ne necessite **aucune installation Python** sur la machine cible.

## Lancement

```bash
colorstudio                      # lance avec la derniere scene utilisee
colorstudio xml-hdr-demo.json    # lance avec un fichier specifique
```

Au **premier lancement**, l'app charge automatiquement la scene par defaut
`xml-postProcess-test.json` qui est livree dans le repo (utilise les images
`light01_*` deja presentes).

Aux **lancements suivants**, le dernier fichier ouvert est re-charge
automatiquement (memorise via QSettings dans le registre Windows / les
preferences Linux).

Pour changer de scene en cours d'execution : menu **Fichier > Ouvrir** (Ctrl+O)
ou **Fichier > Recemment ouverts**.

## Fonctionnalites

### Interface

- **Fenetre unique** (`QMainWindow`) avec dark theme moderne
- **Menu bar** : Fichier / Affichage / Aide
- **Status bar** en bas : fichier charge, mode (LDR/HDR), nb lumieres, temps de rendu
- **Sidebar scrollable** avec cards de controle (Projet, HDR, Auto Exposure, Saturation, Lumieres)
- **Zone image** responsive + nuage 3D RGB en bas (moderngl, zoomable a la molette)
- **Splash screen** au demarrage
- **Recents files** dans le menu Fichier (5 derniers)
- **Tooltips** sur tous les controles + double-clic = reset des sliders

### Raccourcis clavier

| Raccourci | Action                              |
|-----------|-------------------------------------|
| Ctrl+O    | Ouvrir une scene                    |
| Ctrl+S    | Sauvegarder le rendu en image       |
| Ctrl+Shift+S | Exporter la scene en JSON        |
| Ctrl+B    | Exporter la scene vers Blender (.py ou .blend) |
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

### Export Blender

Menu **Fichier > Exporter vers Blender** (Ctrl+B) genere :
- soit un script `.py` (sans Blender installe)
- soit directement un `.blend` (si Blender est detecte sur le systeme)

Le `.blend` contient l'image composee ColorStudio comme texture + des Empties
marqueurs avec metadata (couleur, EV, image source) pour chaque lumiere.

L'app cherche Blender dans : variable `COLORSTUDIO_BLENDER`, PATH, Program Files,
LocalAppData, Steam, registre Windows. Si introuvable, un dialogue propose de
pointer manuellement vers `blender.exe` (chemin memorise pour la prochaine fois).

## Construire un binaire standalone

### Windows (`.exe`)

```bash
py -3.13 -m pip install -r requirements-dev.txt
py -3.13 build_exe.py
```

Le binaire est produit dans `dist/colorstudio/colorstudio.exe` (~11 Mo).
Le bundle complet (avec dependances) fait ~270 Mo.

Mode "un seul fichier" (`.exe` portable, demarre plus lentement) :
```bash
py -3.13 build_exe.py --onefile
```

### Linux

```bash
# prerequis (Debian/Ubuntu) :
sudo apt install python3 python3-pip python3-venv libxcb-cursor0 libegl1
python3 -m pip install -r requirements-dev.txt

# build du binaire + integration desktop (icone + raccourci menu)
chmod +x build_linux.sh
./build_linux.sh
```

Le binaire est dans `dist/colorstudio/colorstudio`. Le script copie aussi tout
dans `~/.local/share/colorstudio/` et cree :
- un symlink `~/.local/bin/colorstudio` (lancable depuis le shell)
- un raccourci `~/.local/share/applications/colorstudio.desktop` (menu DE)
- une icone `~/.local/share/icons/hicolor/256x256/apps/colorstudio.png`

Pour build sans installer :
```bash
./build_linux.sh --no-install
```

Pour une installation systeme (root), copier `dist/colorstudio/` dans `/opt/colorstudio/`
puis adapter le fichier `packaging/colorstudio.desktop` (champ `Exec=`).

### macOS

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m PyInstaller colorstudio.spec --clean
```

Le binaire est dans `dist/colorstudio/colorstudio`.

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
    utils.py              chargement images, toneMap, rgb2hsv_fast, ...
    exporters.py          export Blender (.py + .blend)
    icons/                icones SVG + app.ico (Windows) + app.png (Linux)
    styles.qss            dark theme

tests/                    tests unitaires (26 tests)
    test_model.py
    test_utils.py

docs/                     documentation utilisateur + technique
    user-guide.md
    architecture.md
    xml-format.md

images/                   101 images pre-rendues (light01_0000.jpg a light01_0100.jpg)
*.json / *.xml            5 scenes pre-configurees (defaut : xml-postProcess-test.json)
splashScreen.jpg          splash screen au demarrage + source de l'icone .ico/.png

pyproject.toml            packaging Python (PEP 621)
requirements.txt          dependances runtime
requirements-dev.txt      dependances de developpement (PyInstaller, pytest)
colorstudio.spec          spec PyInstaller pour bundle .exe / binaire Linux
build_exe.py              wrapper de build Windows
build_linux.sh            wrapper de build + integration desktop Linux
generate_icons.py         regenere les icones SVG + app.ico + app.png
packaging/                fichier .desktop pour integration au menu Linux

main.py                   entry point pour developpement
CHANGELOG.md              historique des versions
JOURNAL.md                journal de bord SAE 6A
README.md                 ce fichier
```

## Que contient le repo / qu'est-ce qui est genere

**Tout ce qui est necessaire pour faire tourner et builder l'app est dans le repo.**
Le `.gitignore` n'exclut que des fichiers generes automatiquement, jamais des sources
ou des assets.

### Tracke (dans le repo apres `git clone`)

- Code source du package `colorstudio/` (10 fichiers .py)
- Icones (`.ico`, `.png`, 7 `.svg`) et theme `styles.qss`
- `splashScreen.jpg`
- 101 images source `images/museum2x2/light01_*.jpg`
- 5 scenes pre-configurees (JSON et XML)
- Tests unitaires (`tests/`)
- Documentation (`docs/`, `README.md`, `CHANGELOG.md`, `JOURNAL.md`, `Documentation.md`)
- Tous les fichiers de build : `pyproject.toml`, `colorstudio.spec`, `requirements*.txt`,
  `build_exe.py`, `build_linux.sh`, `generate_icons.py`, `packaging/colorstudio.desktop`

### Ignore (genere par les builds, recreable a tout moment)

- `__pycache__/` : bytecode Python (regenere a chaque execution)
- `build/` : dossier intermediaire PyInstaller (recree a chaque build)
- `dist/` : sortie du build (le `.exe` lui-meme, ~272 Mo). On le regenere
  avec `py -3.13 build_exe.py` -- ne pas le commit pour ne pas alourdir le repo
- `.venv/`, `venv/` : environnements virtuels (chacun en cree un local)
- `.vscode/`, `.idea/` : configurations IDE personnelles
- `*.pyc` : fichiers Python compiles

**Donc apres un clone propre, les seules etapes pour utiliser l'app sont :**
1. Installer les dependances (`pip install -r requirements.txt`)
2. Lancer (`python main.py`) ou builder le `.exe` (`python build_exe.py`)

Aucune ressource externe a telecharger.

## Tests

```bash
py -3.13 -m unittest discover -s tests -v
```

**26 tests unitaires** couvrent :
- Modele : `Light`, `Scene` (`addLight`, `getLightByName`, `render` empty),
  `Saturation` (no-op si zero), `AE_Ymean` (image noire, grise, mode off),
  `PPClip`, `fromXML` (HDR detection), `fromJSON` (LDR/HDR/couleur)
- Utils : `loadImage` (LDR uint8 + HDR float), `toneMap` (zero, 1.0, grandes valeurs, valeurs negatives)
- Exporters : `export_to_blender` (Python valide + scene vide)

## Documentation

- `docs/user-guide.md` : guide utilisateur (UI, raccourcis, ajout de scenes)
- `docs/architecture.md` : architecture MVC + flux de donnees
- `docs/xml-format.md` : format XML et JSON des scenes (avec correspondance)
- `CHANGELOG.md` : historique des versions (v1.0.0 a v1.4.1)
- `JOURNAL.md` : journal de bord de la reprise SAE 6A

## Auteurs

- **Blaszyk Constant**
- **Douilly Quentin**
- **Deldalle Corentin**

Repo : https://github.com/ittaq62/colorStudioApp
Releases : https://github.com/ittaq62/colorStudioApp/releases (toutes versions taggees)
