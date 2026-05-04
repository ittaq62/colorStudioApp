# Journal de bord - ColorStudio

**SAE 6A - Maintenance logicielle**
**BUT3 INFO APP - 2025/2026**

Auteurs : Blaszyk Constant, Douilly Quentin, Deldalle Corentin

Repo : https://github.com/ittaq62/colorStudioApp

---

Ce journal est un journal de bord tenu au fil de la reprise du projet
ColorStudio (Remi Cozot, 2019). Il est volontairement informel : on note
ce qu'on a fait, ce qui nous a bloque, les arbitrages qu'on a pris.

## Decouverte du projet

On recupere le depot original. A l'ouverture c'est un peu dense :
- tout est a la racine, pas de package
- les noms de fichiers sont du type `colorStudioModel.py`, `colorStudioWidget.py`
- Python 3.8 + PyQt5 + easygui + moderngl
- pas de tests, pas de `requirements.txt`, pas de README
- quelques fichiers XML d'exemple a la racine
- un dossier `images/` avec les sets de rendu

On lance `python colorStudioApp.py` pour voir, evidemment ca crashe.
Premiers errors : `ModuleNotFoundError: PyQt5`. Normal, on est sur
Python 3.13 et personne n'a PyQt5 d'installe. On note : **il faut migrer**.

On lit le sujet de la SAE et le PDF `colorstudio_sae.pdf`. Les 3 phases
sont claires :
- 6.1 Migration technique
- 6.2 Qualite (tests, perfs, erreurs algo, docs)
- 6.3 Evolution (HDR, Blender)

On decide de suivre cet ordre.

## Mise en place du workflow git

Avant d'ecrire du code, on se met d'accord sur le workflow git parce que
on a deja vu des binomes se marcher dessus sur des SAE precedentes.

On part sur un **git-flow simplifie** :
- `main` : branche stable, uniquement les releases
- `develop` : branche d'integration, ou tout le monde merge ses features
- branches de feature : `fix/xxx`, `feat/xxx`, `clean/xxx`, `refactor/xxx`,
  `test/xxx`, `perf/xxx`, `docs/xxx`

Regle : **jamais de commit direct sur main**. Tout passe par une branche
de feature, on la merge dans `develop` avec `--no-ff` (pour garder l'historique),
puis quand on est satisfait on merge `develop` dans `main` avec un commit
"release".

On cree le `.gitignore` qui manquait (pycache, venv, IDE, OS files) parce
qu'on avait deja 2-3 `__pycache__` commites par erreur sur d'anciens projets.

## Phase 6.1 - Migration technique

### Python 3.8 -> 3.13

Pas de difficulte particuliere, le code de base est en Python "classique",
pas de trucs chelous qui auraient casse. On met a jour le README et on
note que la cible c'est Python 3.13 (la plus recente dispo sur nos postes).

### PyQt5 -> PyQt6

La, ca a ete plus rigolo. On a eu plusieurs categories de changements :
- les imports : `from PyQt5.QtWidgets import ...` -> `from PyQt6.QtWidgets import ...`
  (facile, un sed).
- les enums : dans PyQt6, tous les enums sont scopes. Par exemple
  `Qt.Horizontal` devient `Qt.Orientation.Horizontal`, `QImage.Format_RGB888`
  devient `QImage.Format.Format_RGB888`. On s'en est rendu compte au
  runtime avec `AttributeError`. C'est le truc le plus penible parce qu'on
  ne peut pas juste chercher "PyQt5" et remplacer.
- `app.exec_()` -> `app.exec()` (la methode a ete renommee, probleme
  historique de "exec" qui etait un mot cle en Python 2).
- `QGLWidget` n'existe plus du tout dans Qt6. Il faut utiliser
  `QOpenGLWidget` a la place. C'etait la partie la plus relou a corriger
  parce que le widget 3D (nuage de points RGB) etait construit autour de
  `QGLWidget` et utilisait `moderngl` en plus. On a bricole pour faire
  cohabiter les deux.

### easygui -> QFileDialog

`easygui` n'est plus maintenu et casse sur Python 3.13. On l'a remplace
par `QFileDialog.getOpenFileName(...)` qui est natif PyQt6, donc une
dependance en moins. Bonus : on a du ajouter un import `QFileDialog` qui
n'etait pas la.

### imageio deprecated warning

Au premier run propre de l'app on avait un `DeprecationWarning` qui
polluait la console : `imageio.imread is deprecated, use imageio.v2.imread`.
Fix rapide : `import imageio.v2 as imageio` et hop, plus de warning.

### Bug de la progress bar

Sous Windows la console est en `cp1252` par defaut. Le caractere unicode
utilise pour la barre de progression (`█` U+2588) n'est pas dans cp1252
et faisait crasher le `print` avec un `UnicodeEncodeError`. On l'a remplace
par un caractere ASCII (`#`). C'est moche mais ca marche partout.

### Refactorisation en package

A ce stade l'app marchait en PyQt6 mais les fichiers etaient toujours en
`colorStudioXxx.py` a la racine, ce qui etait moche et rendait les imports
bizarres. On a cree un vrai package :

```
colorstudio/
    __init__.py
    model.py        (ex colorStudioModel.py)
    widget.py       (ex colorStudioWidget.py)
    controller.py   (ex colorStudioController.py)
    ui_builder.py   (ex colorStudioUIBuilder.py)
    utils.py        (ex colorStudioUtils.py)
main.py             (ex colorStudioApp.py)
```

Ca a casse tous les imports croises, on les a mis a jour, et on a teste
que l'appli demarrait toujours. Check.

## Phase 6.2 - Qualite

### Tests unitaires

Le projet avait zero test. On a mis en place `unittest` (lib standard,
pas de dependance supplementaire) dans un dossier `tests/`. On a commence
par les classes qui avaient de la logique pure sans PyQt :
- `PPClip` : facile, on verifie que les valeurs hors range sont bien clippees
- `Light` : test du nom par defaut, du marquage `_needUpdate`, du rendu
  couleur + exposure
- `Saturation` : au minimum on teste que sat=0 est une no-op
- `Scene` : ajout de light, recherche par nom, chargement XML

Plus tard (phase audit) on a ajoute 3 tests pour `AE_Ymean` parce que
on a trouve un bug de division par zero sur les images noires.

Pour le chargement XML on a utilise `tempfile.mkstemp` pour ecrire un
XML bidon avec `max=0` (donc pas d'images a charger) et verifier que la
scene se construit bien et que l'attribut `hdr` est lu correctement.

Au final on a 20 tests qui passent. C'est pas enorme mais c'est deja
mieux que zero et ca couvre les parties critiques du modele.

### Perf : render vectorise

En lisant `Light.render()` on voit que le code d'origine fait :

```python
imgR = img[:,:,0] * self._npColorRGB[0] * pow(2, self._exposure)
imgG = img[:,:,1] * self._npColorRGB[1] * pow(2, self._exposure)
imgB = img[:,:,2] * self._npColorRGB[2] * pow(2, self._exposure)
imgOut = np.dstack([imgR, imgG, imgB])
```

C'est 3 multiplications par canal + un `dstack`, donc 4 allocations
numpy pour une operation qui devrait etre une seule multiplication
broadcastee. On a refactore en :

```python
factor = self._npColorRGB * math.pow(2, self._exposure)
imgOut = img * factor
```

Numpy broadcaste tout seul `(3,)` sur `(h, w, 3)` et fait l'operation
vectorisee. Idem dans `Scene.render()` on a enleve un `np.zeros()` +
`imgOut += light.render()` boucle, en initialisant avec `.copy()` du
premier light. On a gagne quelques ms par frame, visible sur les scenes
a plusieurs lumieres.

### Nettoyage des imports morts

En parcourant les fichiers on voit plein d'imports qui ne servent a
rien : `imageio`, `moderngl`, `numpy`, `skimage` importes dans des
fichiers qui ne les utilisent pas. On suppose que c'est l'IDE qui les
a ajoutes automatiquement ou des restes de refactos passees. On les
commente plutot que les supprimer completement (au cas ou), sauf quand
c'est evident.

Branche dediee `clean/dead-imports`, fichiers touches : `controller.py`,
`ui_builder.py`, `widget.py`, `utils.py`.

### Nettoyage des prints debug

Pareil, le code etait parseme de `print("DEBUG:", ...)` dans les
callbacks qui polluaient la console a chaque mouvement de slider. On
les a tous retires. Branche `clean/debug-prints`.

Plus tard on en a retrouve 2 qu'on avait rates dans `Saturation.postProcess`,
fixes dans la branche `fix/algo-audit`.

### Audit algorithmique (bugs mathematiques)

C'etait la partie la plus penible de la phase qualite. On a relu le
code du modele ligne par ligne en se demandant "est-ce que ca peut
planter dans un cas limite ?". On a trouve :

1. **`AE_Ymean.postProcess` divise par zero sur image noire**

   ```python
   ymeanb = image2Ymean(img)
   imgOut = img * (self._Ytarget / ymeanb) * math.pow(2, self._exposureON)
   ```

   Si l'image est totalement noire, `ymeanb = 0`, et la division explose
   en `inf`. Numpy le fait en silence avec juste un `RuntimeWarning`,
   mais le resultat est `NaN` partout et le rendu devient tout noir (ou
   tout blanc selon les postprocess qui suivent).

   On a mis un garde-fou `if ymeanb < 1e-6: ymeanb = 1e-6`. C'est pas
   elegant mais ca marche et c'est la solution standard dans la
   litterature (epsilon dans les denominateurs). On a ajoute 3 tests
   unitaires dans `TestAEYmean` pour verifier :
   - image noire ne crashe pas et reste noire
   - image grise a 0.25 avec Ytarget=0.5 -> doit monter a 0.5
   - mode off utilise bien `_exposureOFF`

2. **2 prints de debug restants dans `Saturation`**

   On a trouve 2 `print` qu'on avait rates dans la phase clean/debug-prints,
   dans les branches gamma positive et gamma negative. Retires.

3. **`Scene.fromXML` ignore les blocs `<POSTPROCESS>`**

   Le parser XML boucle bien sur les balises `<POSTPROCESS>` mais quand
   il trouve un `<CHROMA type="AWB">` ou `<CHROMA type="saturation">`
   il fait juste `pass`. C'est un stub du code d'origine. En pratique
   les post-process sont ajoutes par code dans `ui_builder.CSUIAllBuilder`
   ("hacking waiting to Post process in XML" dit le commentaire d'origine).

   On a identifie le bug mais on a decide de **ne pas le corriger**
   parce que ca aurait demande de rewrite une partie du ui_builder
   aussi et on voulait pas casser la scene par defaut a J-3 de la
   deadline. On l'a documente comme "known stub" dans le CHANGELOG.

### Documentation

On a etoffe la documentation :
- un `README.md` minimal avec install / lancement / structure / tests
- un dossier `docs/` avec :
  - `xml-format.md` : le format XML des scenes, toutes les balises,
    l'attribut `hdr="true"` qu'on a ajoute
  - `architecture.md` : schema MVC, qui fait quoi, flux de donnees du render
  - `user-guide.md` : guide utilisateur, comment ajouter une lumiere,
    comment creer une scene
- un `CHANGELOG.md` qui liste tout ce qui a change vs 2019

## Phase 6.3 - Evolution : mode HDR

Parmi les evolutions demandees, on a choisi de faire le **mode HDR**.
L'idee c'est de pouvoir charger et rendre des images avec des valeurs
RGB > 1.0 (typiquement des `.hdr` ou `.exr` de rendu physique).

### Etape 1 : charger les images HDR

Dans `loadImage` d'origine on avait :

```python
imgDouble = img.astype(np.float64) / 255.0
```

Ca divise toujours par 255 meme si l'image est deja en float. Pour les
HDR qui sont deja en `float32` / `float64`, il faut ne PAS diviser.
On a ajoute un check sur `img.dtype` :

```python
if img.dtype == np.uint8:
    imgDouble = img.astype(np.float64) / 255.0
elif img.dtype == np.uint16:
    imgDouble = img.astype(np.float64) / 65535.0
else:
    imgDouble = img.astype(np.float64)  # deja en float, HDR
```

Tests unitaires ajoutes dans `tests/test_utils.py` pour verifier les
3 branches (uint8, uint16, HDR float).

### Etape 2 : attribut XML `hdr="true"`

Dans `Scene.fromXML` on lit maintenant l'attribut `hdr` sur la balise
racine `<LIGHTSETTUP>`. Si present et egal a "true" (case insensitive),
on passe `self._hdr = True`.

Dans `Scene.render`, quand `_hdr` est a True, on ne fait **pas** le
`np.clip(imgOut, 0.0, 1.0)` final, donc les valeurs hautes sont
conservees. On a aussi ajoute un test unitaire pour verifier que
l'attribut est bien lu.

### Etape 3 : tone mapping a l'affichage

Probleme : si on garde des valeurs > 1.0, quand on les envoie au widget
d'affichage (qui est un `QImage` 8-bit) tout ce qui est > 1 est clippe
brutalement a 255 et l'image est cramee. C'est le probleme classique
qu'on a vu en cours d'infographie.

Solution : appliquer un tone mapping avant la conversion en 8-bit. On
a choisi **Reinhard** parce que c'est le plus simple : `x / (1 + x)`.
Ca ramene `[0, +inf[` dans `[0, 1[` de maniere non-lineaire (les basses
lumieres sont preservees, les hautes sont compressees).

Le tonemap est fait dans `utils.toneMap`, appele par `CSDisplayWidget._update`
uniquement si l'image a des valeurs > 1.0 (pour eviter de l'appliquer
aux images LDR normales et pour pas toucher aux tests existants qui
comparent des valeurs exactes).

### Etape 4 : case a cocher dans l'UI

On a ajoute un `CSQHDRControlLayout` dans `widget.py` qui contient juste
un `QCheckBox("HDR mode")`. Il est connecte a `_scene._hdr` et re-render
la scene a chaque toggle. Comme ca on peut basculer LDR/HDR en live sans
recharger le XML.

### Etape 5 : scene de demo HDR

Enfin on a cree `xml-hdr-demo.xml`, une scene volontairement sur-exposee
(+2.5 EV) qui demontre l'interet du mode HDR. Sans HDR l'image est
cramee partout, avec HDR + tone mapping on voit les details des hautes
lumieres. On a mis a jour le README pour expliquer comment l'utiliser.

## Retour d'experience et difficultes

### Le coup des deux dossiers imbriques

A un moment on s'est retrouve avec un dossier `colorStudioApp/` imbrique
dans `colorStudioApp/` (le checkout parent + un sous-checkout dans un
autre dossier). Ca venait d'un ancien refactor qui avait laisse des
`__pycache__` et un fichier de config local. On l'a ajoute au `.gitignore`.

### Divergence main/develop

Un des membres du groupe (qui n'etait pas au courant du workflow git-flow
qu'on avait decide) a pousse 3 commits directement sur `main` pour fixer
un probleme de demarrage de l'app. Ca a cree une divergence avec `develop`
et on a du re-synchroniser en mergeant `origin/main` dans `develop` avec
un commit "sync develop avec les fixes de main". Apres une discussion
on a retabli la regle "jamais de commit direct sur main".

Lecon : documenter le workflow git au debut du projet, pas juste l'annoncer
a l'oral.

### Limites identifiees (non corrigees)

On a conscience que le projet n'est pas "finish" au sens industriel :
- `Scene.fromXML` ne lit pas les post-process depuis le XML (stub)
- le widget 3D `MyWidgetGL` utilise `moderngl` de maniere un peu fragile
  (dependance optionnelle qu'on a pas osee toucher)
- pas de tests pour la partie UI (PyQt6 est dur a mocker en unittest)
- la gestion des erreurs de chargement d'image est minimale (un fichier
  manquant fait crasher l'app au demarrage)
- le dossier `images/museum2x2/light02_*` n'est pas dans le repo parce
  que trop volumineux -> certaines scenes ne marchent pas out-of-the-box

On a prefere stabiliser et documenter ce qui marche plutot que d'ouvrir
de nouveaux chantiers.

## Phase 6.3 bis - Format JSON

On a decide d'ajouter le support du format JSON en parallele du XML.
Le XML c'est verbeux et un peu penible a ecrire a la main, un JSON c'est
plus lisible et plus facile a generer depuis un script.

Le principe :
- `Scene.fromJSON(filename)` fait exactement la meme chose que `fromXML`
  mais en lisant un dict JSON au lieu de parser du DOM XML
- `Scene.toJSON(filename)` / `Light.toDict()` pour sauvegarder
- dans `main.py` on detecte l'extension et on appelle le bon loader

On a converti les 5 scenes XML existantes en JSON (a la main + verif
que le rendu etait identique). Le `QFileDialog` accepte maintenant les
deux formats. Le defaut passe a `xml-postProcess-test.json`.

Un truc pas top : les JSON contiennent un champ `"postprocesses"` mais
le loader ne le lit pas (meme stub que le XML). C'est pas bloquant
parce que les post-process sont de toute facon ajoutes en dur par le
`ui_builder`, mais c'est une incohérence qu'on documente ici.

## Phase 6.3 ter - Refonte de l'interface

Le dernier gros morceau : on est parti d'une UI "4 fenetres separees
posees sur le bureau" (style 2019 / multi-window) et on est passe a une
**fenetre unique** avec un layout moderne.

Nouveau layout :
- une `QMainWindow` avec un titre et un dark theme QSS
- a gauche : sidebar scrollable avec des "cards" (sections) pour
  chaque groupe de controles (Load/Save, HDR, Auto Exposure, Saturation,
  une card par lumiere)
- a droite en haut : l'image rendue (responsive au resize)
- a droite en bas : le nuage 3D + la roue chromatique cote a cote
- les deux zones droite/gauche sont separees par un splitter

Pour le dark theme on a fait un fichier `.qss` (QSS = CSS pour Qt) qui
est charge au demarrage. Ca donne un look professionnel et c'est facile
a modifier sans toucher au code Python.

Pour les icones on est passe de PNG (raster, mal adaptes au scaling) a
des SVG inline (vectoriels, nets a toutes les tailles). Un petit script
`generate_icons.py` les genere dans `colorstudio/icons/`.

La roue chromatique a necessite un refactor du handling souris pour gerer
le resize (avant la taille etait fixe a 480x480, maintenant elle s'adapte
au widget). On calcule un ratio de scaling pour convertir les coordonnees
souris en coordonnees "logiques" de la roue.

## Bilan chiffre

- ~60 commits sur develop, repartis sur ~25 branches de feature
- 23 tests unitaires (tous verts)
- 3 bugs algorithmiques identifies, 2 corriges, 1 documente
- 5 fichiers de documentation (README + docs/ + CHANGELOG + JOURNAL)
- 3 evolutions fonctionnelles : mode HDR, format JSON, refonte UI
- 0 dependance ajoutee, 1 dependance retiree (easygui)

## Ce qu'on ferait differemment

- Mettre en place les tests **avant** de commencer a toucher au code.
  On a passe du temps a craindre de casser quelque chose parce qu'on
  n'avait rien pour verifier.
- Decouper plus tot en package. La refacto "colorStudio*.py -> package
  colorstudio/" a ete plus longue qu'on pensait parce qu'on l'a faite
  apres la migration PyQt6.
- Ecrire le journal au fil de l'eau et pas a la fin. On a du se baser
  sur l'historique git pour reconstituer ce qu'on a fait, et pour certains
  choix on ne se rappelait plus exactement pourquoi on avait tranche
  dans un sens ou dans l'autre.
