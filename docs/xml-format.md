# Format des scenes ColorStudio (XML et JSON)

Une scene ColorStudio est decrite dans un fichier **XML** ou **JSON**
charge au demarrage de l'application via la boite de dialogue (ou en
fallback avec `xml-postProcess-test.json`).

L'application detecte automatiquement le format selon l'extension du
fichier (`.xml` → `Scene.fromXML`, `.json` → `Scene.fromJSON`).

Un fichier de scene decrit :
- un ensemble de lumieres (chacune = un dossier d'images pre-rendues + couleur + exposition)
- un mode de rendu (LDR par defaut, HDR optionnel)
- eventuellement un nom de fichier de rendu

## Structure generale

```xml
<?xml version="1.0"?>
<LIGHTSETTUP hdr="true">
  <LIGHTS>
    <LIGHT name="Light0">
      ...
    </LIGHT>
    <LIGHT name="Light1">
      ...
    </LIGHT>
  </LIGHTS>
  <RENDERFILE>render-hdr-demo.jpg</RENDERFILE>
</LIGHTSETTUP>
```

## Racine `<LIGHTSETTUP>`

Balise racine du document. Contient toute la scene.

### Attribut `hdr` (optionnel)

Ajoute depuis la version 2025 du projet. Valeurs possibles :
- `hdr="true"` : active le mode HDR. Les valeurs RGB du rendu ne sont plus
  clippees a [0,1] et l'affichage applique un tone mapping de Reinhard.
- `hdr="false"` ou attribut absent : mode LDR classique (comportement d'origine).

Exemple : `<LIGHTSETTUP hdr="true">`

Si l'attribut est absent, le mode LDR est utilise par defaut. Le mode peut
aussi etre bascule depuis l'interface via la case a cocher "HDR mode" du
panneau de controle.

## Bloc `<LIGHTS>`

Contient une liste de balises `<LIGHT>`. L'ordre n'a pas d'importance pour
le rendu (les lumieres sont simplement sommees) mais il est conserve dans
l'ordre d'affichage dans le panneau de controle.

## Balise `<LIGHT>`

Decrit une lumiere. Une lumiere correspond a un set d'images pre-rendues
(toutes les positions possibles de cette lumiere dans la scene 3D), auquel
on applique une couleur et une exposition.

### Attribut `name` (obligatoire)

Nom affiche dans l'interface, ex: `name="light01"`. Doit etre unique dans
la scene (sinon `Scene.getLightByName` retournera la premiere trouvee).

### Sous-balise `<INPUTFILE>` (obligatoire)

Chemin et parametres du set d'images. Le texte de la balise contient le
prefixe du nom de fichier (sans le numero ni l'extension).

Attributs :
- `ext` : extension des images, ex: `.jpg`, `.png`, `.hdr`
- `min` : numero de la premiere image du set
- `max` : numero de la derniere image (= nombre d'images dans le set)
- `digit` : nombre de chiffres du numero (zero-padding), ex: `4` pour `0001`

Exemple :
```xml
<INPUTFILE ext=".jpg" min="0" max="100" digit="4">./images/set02/arnold_pass</INPUTFILE>
```
-> charge les fichiers `./images/set02/arnold_pass0000.jpg`,
`./images/set02/arnold_pass0001.jpg`, ..., `./images/set02/arnold_pass0099.jpg`.

### Sous-balise `<IDXPOS>` (obligatoire)

Index de l'image active dans le set au demarrage (position de la lumiere
dans la scene 3D). Valeur entiere entre 0 et `max - 1`.

Exemple : `<IDXPOS>36</IDXPOS>`

### Sous-balise `<EXP>` (obligatoire)

Exposition de la lumiere, en EV (valeur flottante). Un EV positif multiplie
la luminosite par 2^EV, un EV negatif par 2^(-EV).

Exemple : `<EXP>2.5</EXP>` -> multiplie par `2^2.5 ~= 5.66`.

En mode LDR, les valeurs seront ensuite clippees a [0,1]. En mode HDR
elles sont conservees telles quelles.

### Sous-balise `<COLOR>` (obligatoire)

Filtre colore applique a la lumiere. Trois sous-balises `<R>`, `<G>`, `<B>`
avec les valeurs des trois canaux.

Attributs :
- `format="float"` : valeurs dans [0,1]

Exemple :
```xml
<COLOR format="float">
  <R>1.0</R><G>0.5</G><B>0.0</B>
</COLOR>
```
-> lumiere orange (rouge + demi-vert).

## Bloc `<POSTPROCESS>` (optionnel, stub)

Balise reservee pour declarer des post-traitements (saturation, balance des
blancs, ...). Le parser la reconnait et boucle sur ses enfants `<CHROMA>`
mais les implementations sont vides pour l'instant. Les post-process sont
en pratique ajoutes par code (voir `ui_builder.CSUIAllBuilder` qui cree un
`AE_Ymean` et un `Saturation` en dur).

## Bloc `<RENDERFILE>` (optionnel)

Nom du fichier dans lequel sauvegarder le rendu quand on clique sur le
bouton "Save". Si absent, un nom par defaut base sur la date est utilise.

Exemple : `<RENDERFILE>render-final.jpg</RENDERFILE>`

## Exemple complet (mode HDR)

Voir `xml-hdr-demo.xml` a la racine du repo :

```xml
<?xml version="1.0"?>
<LIGHTSETTUP hdr="true">
  <LIGHTS>
    <LIGHT name="Light0">
      <INPUTFILE ext=".jpg" min="0" max="100" digit="4">./images/museum2x2/light01_</INPUTFILE>
      <IDXPOS>25</IDXPOS>
      <EXP>2.5</EXP>
      <COLOR format="float"><R>1.0</R><G>1.0</G><B>1.0</B></COLOR>
    </LIGHT>
  </LIGHTS>
  <RENDERFILE>render-hdr-demo.jpg</RENDERFILE>
</LIGHTSETTUP>
```

Cet exemple pousse volontairement l'exposition a +2.5 EV pour demontrer
l'interet du mode HDR : sans `hdr="true"` l'image serait totalement cramee
(clippee a 1.0), avec HDR les hautes lumieres sont preservees et le tone
mapping permet quand meme de voir l'image.

---

# Format JSON (alternative)

Depuis avril 2025, les scenes peuvent aussi etre decrites en JSON. Le
format est plus compact et plus facile a editer a la main.

## Structure

```json
{
    "hdr": true,
    "lights": [
        {
            "name": "Light0",
            "inputFile": {
                "path": "./images/museum2x2/light01_",
                "ext": ".jpg",
                "min": 0,
                "max": 100,
                "digit": 4
            },
            "idxPos": 25,
            "exposure": 2.5,
            "color": [1.0, 1.0, 1.0]
        }
    ],
    "postprocesses": [],
    "renderFile": "render-hdr-demo.jpg"
}
```

## Correspondance XML → JSON

| XML                          | JSON                              |
|------------------------------|-----------------------------------|
| `<LIGHTSETTUP hdr="true">`   | `"hdr": true`                     |
| `<LIGHT name="X">`           | `"name": "X"`                     |
| `<INPUTFILE ext min max digit>path</INPUTFILE>` | `"inputFile": {"path", "ext", "min", "max", "digit"}` |
| `<IDXPOS>N</IDXPOS>`         | `"idxPos": N`                     |
| `<EXP>X</EXP>`               | `"exposure": X`                   |
| `<COLOR><R>r</R><G>g</G><B>b</B></COLOR>` | `"color": [r, g, b]`  |
| `<RENDERFILE>nom</RENDERFILE>` | `"renderFile": "nom"`           |

## Champ `postprocesses` (stub)

Le JSON peut contenir un champ `"postprocesses"` listant des noms de
post-traitements, mais **ce champ n'est pas lu par `fromJSON`** pour
l'instant (meme situation que le `<POSTPROCESS>` en XML). Les
post-traitements sont ajoutes par code dans le `ui_builder`.

## Fichiers JSON livres dans le repo

- `xml-postProcess-test.json` (defaut au demarrage)
- `xml-hdr-demo.json`
- `xml-2019-6-6-15-28-37.json`
- `xml-2019-6-7-22-38-31.json`
- `xml-2019-6-7-22-47-1.json`
