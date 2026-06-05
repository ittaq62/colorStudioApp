# CHANGELOG

Toutes les modifications notables entre la version d'origine (Remi Cozot, 2019)
et la reprise dans le cadre de la SAE 6A - Maintenance logicielle (BUT3 INFO
APP, 2025/2026).

## [1.0.0] - 2025-06 - "Vraie application"

### Ajoute
- **Packaging Python (PEP 621)** : `pyproject.toml` complet avec metadata,
  dependencies, classifiers, entry_points. L'app est maintenant installable
  via `pip install -e .` et exposable comme commande `colorstudio` ou
  `python -m colorstudio`.
- **Module `colorstudio.app`** : point d'entree unique `main()`, separation
  propre de la logique de demarrage (init Qt, splash, load scene, build UI).
- **`colorstudio/__main__.py`** pour permettre `python -m colorstudio`.
- **Menu bar complete** dans la fenetre principale :
  - Fichier : Ouvrir (Ctrl+O), Recemment ouverts (sous-menu), Sauvegarder
    le rendu (Ctrl+S), Exporter la scene JSON (Ctrl+Shift+S), Quitter
  - Affichage : Basculer HDR (Ctrl+H)
  - Aide : Documentation (F1), Voir sur GitHub, A propos
- **Status bar** en bas avec 4 indicateurs permanents :
  fichier charge, mode (LDR/HDR), nombre de lumieres, temps de rendu en ms.
- **About dialog** (Aide > A propos) avec version, auteurs, credits Cozot
  2019, lien GitHub, license.
- **Splash screen** au demarrage utilisant `splashScreen.jpg`, avec message
  de chargement.
- **Icone de l'application** `colorstudio/icons/app.ico` multi-resolution
  (16/32/48/64/128/256) genere depuis `splashScreen.jpg` via Pillow.
  Window icon + taskbar Windows + icone du .exe.
- **QSettings persistance** : geometrie/etat de la fenetre, dernier
  fichier ouvert (re-charge automatique au demarrage suivant), liste des
  5 fichiers recemment ouverts.
- **Error handling propre** : `QMessageBox.critical` au lieu de stack
  trace quand un fichier de scene est introuvable ou corrompu.
- **Logging propre** : module `logging` standard avec format horodate, plus
  de `print` non desires en mode app.
- **Rechargement de scene a chaud** : Fichier > Ouvrir reconstruit l'UI
  sur la nouvelle scene sans relancer l'app.
- **PyInstaller bundle** : `colorstudio.spec` + `build_exe.py` pour
  generer un `.exe` Windows standalone. Le bundle inclut tous les assets
  (icones, QSS, splash, scenes par defaut, images). Lancement par
  double-clic, sans Python installe sur la machine cible.
- `requirements-dev.txt` pour les deps de developpement (PyInstaller,
  pytest).
- Dependance `Pillow>=10.0` ajoutee pour la generation .ico.

### Modifie
- `generate_icons.py` genere maintenant aussi `app.ico` multi-resolution
  depuis `splashScreen.jpg` (en plus des SVG existants).
- `CSUIBuilder.uiLoadIcon` utilise un chemin relatif au package pour les
  SVG (au lieu de `./colorstudio/icons/` qui depend du cwd).
- `CSMainWindow.apply_style` charge `styles.qss` depuis le package
  (idem, plus de dependance au cwd).
- `CSUIAllBuilder` separe en plusieurs methodes (`_buildCentralContent`,
  `_initialRender`, `_rebuild_with_scene`) pour permettre le rechargement
  de scene a chaud.
- `main.py` racine devient un thin wrapper sur `colorstudio.app:main`.

## [0.3.0] - 2025-05 - Palette de couleur native

### Ajoute (phase 3 : palette de couleur native)
- Remplacement de la roue chromatique custom (`CSDisplayColorWheel`) par un
  `QColorDialog` natif Qt (palette + hex + RGB/HSV/CMYK + pipette ecran)
- Carre de preview 20x20px a cote de chaque slider de lumiere, affichant
  la couleur courante et mis a jour en temps reel
- Methode `CSQLightControlLayout.updatePreview(rgb)` pour rafraichir le preview

### Retire (phase 3)
- Widget `CSDisplayColorWheel` (~100 lignes) — remplace par `QColorDialog`
- Controller `CSColorWheelController` (~20 lignes) — plus necessaire,
  `CSLightController` gere directement le changement de couleur (event type 2)
- Entrees mortes `uiColorWheelWidget_pos` / `uiColorWheelWidget_size` dans
  les templates de `ui_builder.py`

### Ajoute (phase 2 : JSON + refonte UI)
- Support du format **JSON** comme alternative au XML pour decrire les scenes
- Methodes `Scene.fromJSON()`, `Scene.toJSON()`, `Light.toDict()`, `Scene.toDict()`
- Detection automatique du format dans `main.py` (`.json` ou `.xml`)
- 5 fichiers JSON pre-convertis a partir des scenes XML existantes
- **Refonte complete de l'interface** : passage de 4 fenetres separees a une fenetre unique (`QMainWindow`) avec :
  - Sidebar scrollable a gauche avec des "cards" par section
  - Splitter horizontal (sidebar | zone image + analytics)
  - Splitter vertical droit (image en haut | 3D + color wheel en bas)
  - Dark theme (fichier `styles.qss`, 173 lignes)
  - Icones SVG vectorielles (remplacent les anciens PNG)
- Script `generate_icons.py` pour regenerer les icones SVG
- `markdown/rapport_8avril.md` : rapport de presentation du projet

### Ajoute (phase 1 : migration + HDR)
- Mode HDR : support des images HDR (`.hdr`, `.exr`) dans `loadImage`
- Attribut XML `hdr="true"` sur `<LIGHTSETTUP>` pour activer le mode HDR depuis la scene
- Case a cocher "HDR mode" dans le panneau de controle (bascule LDR / HDR a la volee)
- Tone mapping de Reinhard `x / (1+x)` applique a l'affichage quand l'image est HDR
- Scene de demonstration HDR : `xml-hdr-demo.xml`
- Tests unitaires pour `colorstudio.model` (classe `Light`, `Saturation`, `PPClip`, `Scene`, `Scene.fromXML`)
- Tests unitaires pour `AE_Ymean` (image noire, image grise, mode off)
- Tests unitaires pour `colorstudio.utils.loadImage` (LDR uint8, HDR float)
- Fichier `README.md` (install, lancement, structure, tests)
- Dossier `docs/` avec :
  - `xml-format.md` : documentation complete du format XML des scenes
  - `architecture.md` : schema d'architecture MVC + flux de donnees
  - `user-guide.md` : guide utilisateur (UI, panneau de controle, raccourcis)
- `CHANGELOG.md` (ce fichier)
- `JOURNAL.md` : journal de bord de la reprise

### Modifie (phase 2)
- `ui_builder.py` : `CSUIAllBuilder` reecrit pour produire une seule `QMainWindow` au lieu de 4 fenetres independantes
- `widget.py` : nouveau `CardWidget`, `CSDisplayWidget` avec scaling responsive, `CSDisplayColorWheel` avec gestion mouse adaptee au resize
- Icones chargees depuis `./colorstudio/icons/*.svg` au lieu de `./images/others/*.png`
- Filtre de la boite de dialogue : accepte `*.json` en plus de `*.xml`

### Modifie (phase 1)
- Migration Python 3.8 -> Python 3.13
- Migration PyQt5 -> PyQt6 (imports, `Qt.Orientation.Horizontal`, `QImage.Format.Format_RGB888`, `app.exec()`)
- `QGLWidget` (supprime dans Qt6) remplace par `QOpenGLWidget`
- `easygui` (non maintenu) remplace par `QFileDialog` natif PyQt6
- `imageio` : utilisation de `imageio.v2` pour eviter le `DeprecationWarning`
- Refactorisation : structure en package `colorstudio/` (model, widget, controller, ui_builder, utils)
- Nouveau point d'entree `main.py`
- `Light.render()` et `Scene.render()` vectorises (broadcast numpy, init sans `np.zeros`)

### Corrige
- **[BUG critique]** `AE_Ymean.postProcess` divisait par zero sur une image totalement noire (`Ymean = 0` -> `inf` / `NaN`) ; protection par un epsilon `1e-6`
- Import manquant de `numpy` dans `colorStudioWidget` (crash au chargement du widget)
- `progressBar` : caractere unicode non supporte en `cp1252` (Windows) -> remplace
- Scene XML par defaut : pointait vers `xml-2019-6-7-22-47-1.xml` qui reference le set `light02_*` absent du repo -> maintenant `xml-postProcess-test.xml`
- Import de `QFileDialog` absent apres la suppression de `easygui`

### Nettoye (phase 2)
- Import `QSizePolicy` inutilise retire de `ui_builder.py`
- Classe `CSDisplayControls` retiree de `widget.py` (remplacee par la sidebar)
- `bare except:` remplace par `except (KeyError, TypeError):` dans `widget.py`
- Chemin absolu `c:/Users/Constant/...` dans `generate_icons.py` remplace par chemin relatif

### Nettoye (phase 1)
- Suppression / commentaire des imports inutiles dans `controller.py`, `ui_builder.py`, `widget.py`, `utils.py` (`imageio`, `moderngl`, `numpy`, `skimage`, `sys`, `QtCore`, `QApplication`, `QWidget`, `QPushButton`, ...)
- Retrait de plusieurs `print` de debug qui polluaient la console a chaque mouvement de slider (`colorStudioUtils`, `Saturation.postProcess`)
- `.gitignore` : ajout des patterns Python (`__pycache__`, `*.pyc`, `build/`, `dist/`, `*.egg-info/`, `.pytest_cache/`, venv, IDE, OS)
- Suppression du dossier imbrique legacy `/colorStudioApp/` (ignore)

## [2019] - Version d'origine

Version initiale de Remi Cozot, en Python 3.8 / PyQt5.
Fonctionnalites :
- Chargement d'un set d'images pre-rendues (une par position de lumiere)
- Composition multi-lumieres (couleur + exposition par lumiere)
- Post-process : auto exposure (`AE_Ymean`), saturation (`Saturation`)
- UI PyQt5 : rendu, controles, roue chromatique, nuage de points 3D
- Sauvegarde / chargement de scenes au format XML
