# ColorStudio

Outil de mise en lumiere d'une scene 3D a partir d'un set d'images pre-rendues
(une image par position de lumiere). Chaque "lumiere" applique une couleur et une
exposition sur l'image correspondante puis on additionne tout.

Projet original : Remi Cozot, 2019.
Reprise dans le cadre de la SAE 6A - Maintenance logicielle (BUT3 INFO APP).

## Prerequis

- Python 3.13
- Les paquets listes dans `requirements.txt` :
  - PyQt6
  - numpy
  - scikit-image
  - imageio
  - moderngl

## Installation

```
py -3.13 -m pip install -r requirements.txt
```

## Lancement

```
py -3.13 main.py
```

Au demarrage une fenetre demande de selectionner un fichier de scene
(**JSON** ou XML). Par defaut `xml-postProcess-test.json` qui marche
avec les images presentes dans le repo. Le fichier de scene decrit
chaque lumiere : le set d'images source, la position dans le set,
l'exposition et la couleur RGB.

### Mode HDR

Deux manieres d'activer le mode HDR :
- dans le fichier de scene, mettre `"hdr": true` (JSON) ou `hdr="true"`
  sur la racine XML. Exemple : `xml-hdr-demo.json`.
- dans l'interface, cocher la case "HDR mode" dans la sidebar.

En mode HDR les valeurs RGB du rendu ne sont plus clippees a 1.0.
L'affichage applique un tone mapping de Reinhard (`x / (1+x)`) pour eviter
une image cramee.

## Structure du projet

```
colorstudio/        package principal
    __init__.py
    model.py        Light, Scene, PostProcess (Saturation, AE_Ymean, PPClip)
    widget.py       widgets PyQt6 (CardWidget, CSDisplayWidget, ColorWheel, ...)
    ui_builder.py   construction de l'UI a partir d'une Scene (QMainWindow unique)
    controller.py   logique de controle
    utils.py        chargement images, helpers (toneMap, colorWheel, ...)
    icons/          icones SVG de l'interface
    styles.qss      theme sombre (dark mode)
tests/              tests unitaires
    test_model.py
    test_utils.py
main.py             point d'entree
images/             sets d'images source
*.json / *.xml      scenes pre-configurees (les deux formats sont supportes)
docs/               documentation detaillee
```

## Tests

Tests unitaires avec `unittest` (lib standard, pas de dependance) :

```
py -3.13 -m unittest discover -s tests -v
```

## Documentation

Documentation detaillee dans `docs/` :
- `docs/xml-format.md` : format XML des scenes (balises, attribut `hdr`, exemples)
- `docs/architecture.md` : schema MVC + flux de donnees render
- `docs/user-guide.md` : guide utilisateur (UI, panneau de controle, comment ajouter une lumiere)

Voir aussi :
- `CHANGELOG.md` : liste des modifs par rapport a la version 2019
- `JOURNAL.md` : journal de bord de la reprise SAE 6A
- `Documentation.md` : notes de migration techniques (PyQt5 -> PyQt6, Python 3.13)
