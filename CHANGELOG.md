# CHANGELOG

Toutes les modifications notables entre la version d'origine (Remi Cozot, 2019)
et la reprise dans le cadre de la SAE 6A - Maintenance logicielle (BUT3 INFO
APP, 2025/2026).

## [2025-04] - Reprise SAE 6A

### Ajoute
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

### Modifie
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

### Nettoye
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
