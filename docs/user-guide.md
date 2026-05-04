# Guide utilisateur ColorStudio

## Lancement

Apres avoir installe les dependances (`pip install -r requirements.txt`),
lancer l'application depuis la racine du projet :

```
py -3.13 main.py
```

Une boite de dialogue s'ouvre et demande de selectionner un fichier de
scene (JSON ou XML). Les scenes preconfigurees sont a la racine du repo :

- `xml-postProcess-test.json` (**defaut**) : scene legere qui utilise
  uniquement le set `light01_*` (le seul present dans le repo).
- `xml-hdr-demo.json` : scene HDR volontairement sur-exposee, demontre
  le mode HDR + tone mapping.
- `xml-2019-*.json` / `xml-2019-*.xml` : anciennes scenes d'exemple,
  referencent `light02_*` qui n'est pas dans le repo par defaut (cf. plus bas).

Si la boite de dialogue est annulee, l'application utilise le fichier
`xml-postProcess-test.json` par defaut.

## Interface (fenetre unique)

L'application s'ouvre dans une **fenetre unique** avec un theme sombre :

```
+---------------------+--------------------------------------------+
|     SIDEBAR         |         IMAGE RENDUE                       |
|  (scrollable)       |        (responsive au resize)              |
|                     |                                            |
|  [Project]          |                                            |
|  [HDR Mode]         +--------------------------------------------+
|  [Auto Exposure]    |    NUAGE 3D      |     ROUE CHROMATIQUE    |
|  [Saturation]       |   (moderngl)     |    (click = couleur)    |
|  [Light: xxx]       |                  |                         |
+---------------------+------------------+-------------------------+
```

- Le splitter entre la sidebar et la zone image est deplacable
- Le splitter vertical entre l'image et le panneau analytique aussi
- Le tout est responsive (s'adapte au resize de la fenetre)

## Panneau de controle (sidebar)

La sidebar regroupe tous les controles, organises en "cards" :

### Load / Save

- **Load** : charge un nouveau fichier de scene (JSON ou XML).
- **Save** : sauvegarde la scene courante. Le nom du fichier de rendu
  vient de `renderFile` (JSON) ou `<RENDERFILE>` (XML), sinon un nom
  par defaut base sur la date est genere.

### Une ligne par lumiere

Pour chaque lumiere presente dans la scene, une card de controle est
ajoutee :

- `[ - ]` : diminue l'exposition de la lumiere de 0.5 EV
- `[ +/- X.XX ]` : valeur d'exposition courante (label, pas editable directement)
- `[ + ]` : augmente l'exposition de la lumiere de 0.5 EV
- `[ CC ]` : selectionne cette lumiere comme active pour la roue chromatique
- `[ slider ]` : deplace l'index de l'image active dans le set (position
  de la lumiere dans la scene 3D pre-calculee)

### Automatic Exposure

Post-process d'auto-exposure (`AE_Ymean`). Ramene la luminance moyenne
de l'image a une valeur cible `Ytarget = 0.5`.

- `[ ON / OFF ]` : active / desactive l'auto-exposure
- `[ - ]` `[ + ]` : ajustement manuel de l'exposure au-dessus de l'AE

### Saturation

Post-process de saturation (`Saturation`). Deux sliders independants :

- **linear** : saturation lineaire dans [-100, 100]
- **gamma** : saturation gamma (vibrance) dans [-100, 100]

### HDR mode (nouveaute 2025)

Case a cocher `HDR mode`. Quand elle est cochee :
- les valeurs RGB du rendu ne sont plus clippees a [0,1]
- l'affichage applique un tone mapping de Reinhard `x / (1+x)`
- on peut voir les hautes lumieres sans ecraser le reste de l'image

Quand elle est decochee, on retombe en mode LDR classique (clip a 1.0).

L'etat peut aussi etre initialise depuis le XML avec l'attribut
`hdr="true"` sur la balise racine `<LIGHTSETTUP>` (voir `xml-format.md`).

## Roue chromatique

Pour changer la couleur d'une lumiere :
1. cliquer sur le bouton palette (CC) de la lumiere concernee dans la
   sidebar.
2. cliquer n'importe ou sur la roue (en bas a droite) pour appliquer
   cette couleur. Le rendu se met a jour instantanement.

## Ajouter une scene

1. Placer le set d'images pre-rendues dans `./images/mon_set/`, nommees par
   exemple `mon_set_0000.jpg`, `mon_set_0001.jpg`, ..., `mon_set_0099.jpg`
2. Creer un fichier JSON (plus simple) ou XML :

**JSON** (recommande) :
```json
{
    "hdr": false,
    "lights": [
        {
            "name": "key_light",
            "inputFile": {
                "path": "./images/mon_set/mon_set_",
                "ext": ".jpg",
                "min": 0,
                "max": 100,
                "digit": 4
            },
            "idxPos": 50,
            "exposure": 0.0,
            "color": [1.0, 1.0, 1.0]
        }
    ]
}
```

**XML** (format d'origine, voir `xml-format.md` pour le detail) :
```xml
<?xml version="1.0"?>
<LIGHTSETTUP>
  <LIGHTS>
    <LIGHT name="key_light">
      <INPUTFILE ext=".jpg" min="0" max="100" digit="4">./images/mon_set/mon_set_</INPUTFILE>
      <IDXPOS>50</IDXPOS>
      <EXP>0.0</EXP>
      <COLOR format="float"><R>1.0</R><G>1.0</G><B>1.0</B></COLOR>
    </LIGHT>
  </LIGHTS>
</LIGHTSETTUP>
```

3. Lancer `main.py`, selectionner le fichier dans la boite de dialogue.

## Ajouter une deuxieme lumiere

Dupliquer la balise `<LIGHT>` dans le XML. Les deux lumieres peuvent
partager le meme set d'images (elles seront chargees une seule fois) ou
en utiliser des differents. Exemple avec deux lumieres sur le meme set :

```xml
<LIGHTS>
  <LIGHT name="key">
    <INPUTFILE ext=".jpg" min="0" max="100" digit="4">./images/mon_set/mon_set_</INPUTFILE>
    <IDXPOS>30</IDXPOS>
    <EXP>0.0</EXP>
    <COLOR format="float"><R>1.0</R><G>0.9</G><B>0.8</B></COLOR>
  </LIGHT>
  <LIGHT name="fill">
    <INPUTFILE ext=".jpg" min="0" max="100" digit="4">./images/mon_set/mon_set_</INPUTFILE>
    <IDXPOS>70</IDXPOS>
    <EXP>-1.5</EXP>
    <COLOR format="float"><R>0.8</R><G>0.85</G><B>1.0</B></COLOR>
  </LIGHT>
</LIGHTS>
```

## Ou trouver les images light02 / museum2x2 ?

Seul le set `light01_*` est commit dans le repo (taille des binaires).
Pour utiliser les scenes `xml-2019-6-*.xml` il faut recuperer le set
`light02_*` a part et le placer dans `./images/museum2x2/`.

Pour la scene HDR `xml-hdr-demo.xml`, elle fonctionne avec le meme set
`light01_*` que `xml-postProcess-test.xml` (elle le reference dans le
chemin `./images/museum2x2/light01_`).

## Raccourcis utiles

Il n'y a pas de raccourcis clavier pour l'instant. Toutes les actions
passent par le panneau de controle a la souris.

## Quitter

Fermer la fenetre principale de rendu (Color Studio - render) termine
l'application Qt et ferme toutes les autres fenetres.
