# -*- coding: utf-8 -*-
"""
Exporteurs de scenes ColorStudio vers d'autres outils.

Export Blender :
  ColorStudio NE FAIT PAS de rendu 3D - il composite des images pre-rendues.
  L'export Blender doit donc refleter ca honnetement :
  - artefact principal : l'image composee finale (PNG)
  - dans Blender : un plan textured avec cette image (ce que l'utilisateur voit)
  - chaque lumiere = un Empty (marqueur) en cercle avec custom properties
    (couleur, EV, image source, index) -> on ne pretend PAS que ce sont
    de vraies lights 3D, parce qu'elles ne le sont pas dans CS
  - la camera regarde directement le plan
"""

import glob
import math
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime


def export_to_blender(scene, output_path, source_scene_file=None, image_path=None):
    """
    genere un script Python Blender qui recree la scene ColorStudio dans Blender.

    Strategie d'export : ColorStudio composite des images, pas de 3D.
      - le script importe l'image composee (image_path) comme un plan textured
        au centre de la scene
      - chaque Light devient un Empty en cercle autour du plan, avec les
        proprietes ColorStudio en custom properties (cs_color, cs_exposure_ev,
        cs_image_source, cs_image_idx)
      - optionnellement, chaque Empty est accompagne d'un POINT light Blender
        avec la meme couleur (pour avoir aussi un light 3D si on veut, mais
        clairement separe de l'Empty marqueur)

    Parameters
    ----------
    scene : model.Scene
    output_path : str
        chemin du script .py a generer
    source_scene_file : str ou None
        chemin du fichier .json/.xml source (pour les commentaires)
    image_path : str ou None
        chemin de l'image composee a integrer dans Blender. Si None, le script
        ne creera pas de plan textured (juste les Empties).
    """
    lights = scene._lights
    if not lights:
        raise ValueError("La scene ne contient aucune lumiere a exporter")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # construit les data des lights : ce sont des marqueurs, PAS des lights 3D
    lights_data = []
    n = max(1, len(lights))
    for i, light in enumerate(lights):
        r, g, b = float(light._npColorRGB[0]), float(light._npColorRGB[1]), float(light._npColorRGB[2])
        # position en cercle de rayon 4m autour du plan
        angle = 2.0 * math.pi * i / n
        pos_x = 4.0 * math.cos(angle)
        pos_y = 4.0 * math.sin(angle)
        pos_z = 1.5

        lights_data.append({
            "name": light._name,
            "color": (r, g, b),
            "exposure_ev": float(light._exposure),
            "position": (pos_x, pos_y, pos_z),
            "image_path": _images_info(light),
            "image_idx": light._imageIdx,
        })

    # genere le script
    script = _build_blender_script(
        lights_data=lights_data,
        scene_file=source_scene_file,
        composited_image_path=image_path,
        hdr=scene._hdr,
        timestamp=timestamp,
    )

    # ecriture
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script)

    return output_path


def _images_info(light):
    """retourne le pattern du set d'images source d'une light (pour les commentaires)"""
    arr = light._ImagesArray
    if arr is None:
        return "(pas d'images)"
    base = arr._pathImage + arr._baseImageName if arr._pathImage else arr._baseImageName
    return f"{base}<{arr._nbImage:0{arr._nbDigit}d}>{arr._extImageName}"


def _build_blender_script(lights_data, scene_file, composited_image_path, hdr, timestamp):
    """assemble le code Python Blender complet"""
    has_image = composited_image_path is not None and os.path.exists(composited_image_path)
    # chemin absolu pour Blender (Windows : \\ -> /, evite les soucis d'escape)
    img_path_for_script = ""
    if has_image:
        img_path_for_script = os.path.abspath(composited_image_path).replace("\\", "/")

    header = f'''# -*- coding: utf-8 -*-
"""
Scene Blender generee par ColorStudio le {timestamp}.

ColorStudio ne fait PAS de rendu 3D : il composite des images pre-rendues en
multipliant chacune par une couleur et une exposition (color * 2^EV) puis en
les sommant. Le resultat est UNE IMAGE FINALE, pas une scene 3D.

Ce script reflete fidelement cela :
  - il importe l'image COMPOSEE (le resultat de ColorStudio) comme texture
    sur un plan 16:9 au centre de la scene
  - chaque "lumiere" ColorStudio devient un Empty marqueur en cercle autour
    du plan, avec les proprietes ColorStudio en CUSTOM PROPERTIES
    (cs_color, cs_exposure_ev, cs_image_source, cs_image_idx)
  - les Empties ne sont PAS de vraies lights : on ne pretend pas que ColorStudio
    fait de la 3D. Ce sont juste des marqueurs visuels avec metadata.

Si vous voulez utiliser ces lights comme de vraies POINT lights Blender :
  - decommentez la section "add_real_point_light" plus bas
  - adaptez les positions en fonction de votre scene 3D reelle

Source ColorStudio :
  fichier : {scene_file or "(non specifie)"}
  mode    : {"HDR" if hdr else "LDR"}
  lights  : {len(lights_data)}
  image composee : {img_path_for_script or "(non incluse)"}

Pour utiliser :
  - en CLI : blender --background --python {os.path.basename("scene_blender.py")}
  - dans Blender : Scripting > charger le fichier > Run Script
ATTENTION : le script EFFACE la scene courante.
"""

import bpy
import math


def clear_scene():
    """vide la scene Blender courante (objets, lights, cameras)"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # vide aussi les images orphelines + materiaux
    for img in list(bpy.data.images):
        bpy.data.images.remove(img)
    for mat in list(bpy.data.materials):
        bpy.data.materials.remove(mat)


def add_image_plane(image_path, plane_size=4.0):
    """
    cree un plan 16:9 textured avec l'image composee ColorStudio au centre.
    L'image est emissive : pas besoin de lighting Blender pour la voir.
    """
    if not image_path:
        return None

    # ratio 16:9 (les rendus ColorStudio sont en general dans ce ratio)
    width = plane_size
    height = plane_size * 9.0 / 16.0

    # cree le mesh plane
    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(0, 0, 0))
    plane = bpy.context.object
    plane.name = "ColorStudio_Render"
    plane.scale = (width, height, 1.0)
    plane.rotation_euler = (math.pi / 2, 0, 0)  # debout face camera

    # cree un material avec une image emissive
    mat = bpy.data.materials.new(name="ColorStudio_RenderMat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    # output node
    out = nodes.new(type='ShaderNodeOutputMaterial')
    out.location = (400, 0)

    # emission node (pas besoin d'eclairer le plan, l'image se voit toute seule)
    emission = nodes.new(type='ShaderNodeEmission')
    emission.location = (200, 0)
    emission.inputs['Strength'].default_value = 1.0

    # image texture node
    img_node = nodes.new(type='ShaderNodeTexImage')
    img_node.location = (-100, 0)
    try:
        img_node.image = bpy.data.images.load(image_path)
    except Exception as e:
        print(f"  ! impossible de charger l'image {{image_path}} : {{e}}")

    links.new(img_node.outputs['Color'], emission.inputs['Color'])
    links.new(emission.outputs['Emission'], out.inputs['Surface'])

    plane.data.materials.append(mat)
    return plane


def add_camera(distance=5.0):
    """camera positionnee face au plan ColorStudio"""
    bpy.ops.object.camera_add(location=(0, -distance, 0.5))
    cam = bpy.context.object
    cam.name = "ColorStudio_Camera"
    cam.rotation_euler = (math.pi / 2, 0, 0)
    bpy.context.scene.camera = cam


def add_light_marker(name, color, exposure_ev, position, image_path, image_idx):
    """
    Ajoute un Empty (marqueur visuel) qui represente une lumiere ColorStudio.
    Les proprietes ColorStudio sont stockees en custom properties.

    On NE cree PAS de vraie POINT light parce que les "lights" ColorStudio
    n'ont pas de position 3D reelle - elles sont des multiplicateurs sur des
    images pre-rendues. Faire une vraie light induirait en erreur.
    """
    bpy.ops.object.empty_add(type='SPHERE', radius=0.2, location=position)
    obj = bpy.context.object
    obj.name = f"CS_{{name}}"
    # custom properties : on peut les lire/inspecter dans Blender (panneau Properties > Object)
    obj["cs_color_r"] = color[0]
    obj["cs_color_g"] = color[1]
    obj["cs_color_b"] = color[2]
    obj["cs_exposure_ev"] = exposure_ev
    obj["cs_image_source"] = image_path
    obj["cs_active_image_idx"] = image_idx
    # color de l'Empty dans le viewport (visualisation rapide de la couleur de light)
    obj.color = (color[0], color[1], color[2], 1.0)
    # NB : pour voir cette couleur dans le viewport, activer
    #   Viewport Shading > Object Color (Properties N panel)
    print(f"  + Marker '{{name}}' : color={{color}} EV={{exposure_ev}} pos={{position}}")


# Optionnel : si on veut une VRAIE point light Blender en plus du marqueur
# (utile pour avoir un eclairage 3D en partant de la couleur de la light CS),
# decommenter cette fonction et son appel dans la boucle plus bas.
def add_real_point_light(name, color, exposure_ev, position):
    """ajoute en plus une vraie POINT light Blender avec la couleur ColorStudio"""
    bpy.ops.object.light_add(type='POINT', location=position)
    obj = bpy.context.object
    obj.name = f"CS_{{name}}_Light"
    obj.data.color = color
    # energy reference : 100 W * 2^EV (arbitraire mais coherent avec l'echelle EV)
    obj.data.energy = 100.0 * (2.0 ** exposure_ev)


# =============================================================================
# Setup de la scene
# =============================================================================
print("[ColorStudio -> Blender] init...")
clear_scene()
'''

    if has_image:
        header += f'''
print("[ColorStudio -> Blender] import de l'image composee...")
add_image_plane({img_path_for_script!r})
'''

    header += '''add_camera()

# =============================================================================
# Ajout des marqueurs de lumieres (chacun avec ses metadata ColorStudio)
# =============================================================================
'''

    body_lines = []
    for ld in lights_data:
        c = ld["color"]
        p = ld["position"]
        body_lines.append(
            f'add_light_marker(\n'
            f'    name="{ld["name"]}",\n'
            f'    color=({c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f}),\n'
            f'    exposure_ev={ld["exposure_ev"]:.2f},\n'
            f'    position=({p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}),  # placeholder, a adapter\n'
            f'    image_path={ld["image_path"]!r},\n'
            f'    image_idx={ld["image_idx"]},\n'
            f')\n'
            f'# decommenter pour avoir aussi une vraie point light Blender :\n'
            f'# add_real_point_light("{ld["name"]}", ({c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f}), {ld["exposure_ev"]:.2f}, ({p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}))'
        )

    footer = '''


# =============================================================================
print("[ColorStudio -> Blender] termine.")
print("  Pour voir le rendu compose : Viewport Shading > Material Preview ou Rendered")
print("  Pour voir les metadata d'un marqueur : selectionner CS_LightX > Properties > Object > Custom Properties")
'''

    return header + "\n".join(body_lines) + footer


# -----------------------------------------------------------------------------
# Rendu de l'image composee (PNG) pour l'embarquer dans l'export Blender
# -----------------------------------------------------------------------------

def render_scene_to_image(scene, output_path):
    """
    rend la scene ColorStudio courante en une image PNG sauvegardee sur disque.
    Applique les memes post-process / clipping / tone mapping que l'app.
    """
    import imageio.v2 as imageio
    import numpy as np
    from colorstudio.utils import toneMap

    img = scene.render()
    # tone mapping si HDR (sinon l'image serait cramee a l'enregistrement uint8)
    if img.max() > 1.0:
        img = toneMap(img)
    img_uint8 = (np.clip(img, 0.0, 1.0) * 255).astype(np.uint8)

    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    imageio.imwrite(output_path, img_uint8)
    return output_path


# -----------------------------------------------------------------------------
# Export direct au format .blend (necessite Blender installe + sur le PATH)
# -----------------------------------------------------------------------------

def find_blender_executable():
    """
    cherche l'executable Blender sur le systeme.

    Strategie (ordre) :
    1. variable d'env COLORSTUDIO_BLENDER si definie
    2. PATH (commande `blender`)
    3. patterns glob sur les emplacements standards de chaque OS
       (couvre TOUTES les versions de Blender, pas une liste hardcodee)
    4. Registre Windows (cle BlenderFoundation)

    Retourne le chemin trouve ou None si introuvable.
    """
    # 1. variable d'environnement explicite (utile pour les CI / setups custom)
    env_path = os.environ.get("COLORSTUDIO_BLENDER")
    if env_path and os.path.isfile(env_path):
        return env_path

    # 2. PATH
    p = shutil.which("blender")
    if p:
        return p

    # 3. patterns glob par OS (matche n'importe quelle version)
    candidates = []
    if sys.platform.startswith("win"):
        local_app = os.environ.get("LOCALAPPDATA", "")
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        program_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

        patterns = [
            # install standard (system-wide)
            os.path.join(program_files, "Blender Foundation", "Blender *", "blender.exe"),
            os.path.join(program_files_x86, "Blender Foundation", "Blender *", "blender.exe"),
            # install user-only
            os.path.join(local_app, "Programs", "Blender Foundation", "Blender *", "blender.exe"),
            # Steam
            os.path.join(program_files_x86, "Steam", "steamapps", "common", "Blender", "blender.exe"),
            os.path.join(program_files, "Steam", "steamapps", "common", "Blender", "blender.exe"),
            # Microsoft Store / WindowsApps (rare, pas toujours executable)
            os.path.join(local_app, "Microsoft", "WindowsApps", "blender.exe"),
        ]
        for pat in patterns:
            candidates.extend(glob.glob(pat))

    elif sys.platform == "darwin":
        candidates.extend(glob.glob("/Applications/Blender.app/Contents/MacOS/Blender"))
        candidates.extend(glob.glob("/Applications/Blender */Blender.app/Contents/MacOS/Blender"))
        candidates.extend(glob.glob(
            os.path.expanduser("~/Applications/Blender.app/Contents/MacOS/Blender")
        ))

    else:
        for pat in [
            "/usr/bin/blender",
            "/usr/local/bin/blender",
            "/opt/blender/blender",
            "/opt/blender-*/blender",
            "/snap/blender/current/blender",
            os.path.expanduser("~/.local/bin/blender"),
            os.path.expanduser("~/Applications/Blender*/blender"),
        ]:
            candidates.extend(glob.glob(pat))

    # filtre : garde seulement les fichiers existants, trie pour avoir la
    # version la plus haute en premier ('Blender 5.0' > 'Blender 4.5' lexico)
    candidates = [c for c in candidates if os.path.isfile(c)]
    candidates.sort(reverse=True)
    if candidates:
        return candidates[0]

    # 4. Registre Windows (Blender s'enregistre comme application installee)
    if sys.platform.startswith("win"):
        try:
            import winreg
            for hive, sub in [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BlenderFoundation\Blender"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\BlenderFoundation\Blender"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Classes\blendfile\shell\open\command"),
            ]:
                try:
                    with winreg.OpenKey(hive, sub) as key:
                        val, _ = winreg.QueryValueEx(key, "")
                        if val.startswith('"'):
                            val = val.split('"')[1]
                        if os.path.isfile(val):
                            return val
                except OSError:
                    continue
        except ImportError:
            pass

    return None


def export_to_blend(scene, blend_output_path, source_scene_file=None, blender_exe=None, timeout=120):
    """
    genere directement un fichier .blend via Blender headless. Inclut :
    - le rendu de la scene composee en PNG a cote du .blend
    - un plan textured affichant ce PNG (= la sortie ColorStudio)
    - les Empties marqueurs de chaque lumiere avec metadata

    Parameters
    ----------
    scene : model.Scene
    blend_output_path : str
        chemin du .blend a produire. Une image .png du meme nom est sauvegardee
        a cote pour etre referencee depuis le .blend.
    source_scene_file : str ou None
        chemin du fichier source ColorStudio (pour les commentaires du script)
    blender_exe : str ou None
        chemin de l'executable Blender. Si None, auto-detection.
    timeout : int
        timeout en secondes pour l'invocation Blender (defaut 120s).

    Returns
    -------
    tuple (str, str) : (chemin du .blend produit, chemin du .png produit a cote)

    Raises
    ------
    FileNotFoundError : Blender introuvable
    RuntimeError      : echec de l'invocation Blender
    """
    if blender_exe is None:
        blender_exe = find_blender_executable()
    if blender_exe is None:
        raise FileNotFoundError(
            "Blender n'a pas ete trouve sur ce systeme. Installer Blender ou "
            "ajouter son executable au PATH, puis reessayer."
        )

    # 1. rend la scene en PNG a cote du .blend
    blend_output_path = os.path.abspath(blend_output_path)
    blend_dir = os.path.dirname(blend_output_path) or "."
    png_path = os.path.join(
        blend_dir,
        os.path.splitext(os.path.basename(blend_output_path))[0] + "_render.png"
    )
    try:
        render_scene_to_image(scene, png_path)
    except Exception as e:
        # pas bloquant : on continue sans image (script .blend sans plan textured)
        print(f"[warning] rendu PNG echoue, .blend sera sans image : {e}")
        png_path = None

    # 2. genere le script .py dans un fichier temporaire
    fd, tmp_script = tempfile.mkstemp(suffix=".py", prefix="colorstudio_export_")
    os.close(fd)
    try:
        export_to_blender(
            scene, tmp_script,
            source_scene_file=source_scene_file,
            image_path=png_path,
        )

        # 3. invoque Blender en headless avec save_as_mainfile a la fin
        os.makedirs(blend_dir, exist_ok=True)
        save_snippet = (
            f'\n\nimport bpy as _bpy\n'
            f'_bpy.ops.wm.save_as_mainfile(filepath={blend_output_path!r})\n'
        )
        with open(tmp_script, "a", encoding="utf-8") as f:
            f.write(save_snippet)

        cmd = [blender_exe, "--background", "--python", tmp_script]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        if result.returncode != 0:
            stderr_tail = (result.stderr or "").splitlines()[-15:]
            raise RuntimeError(
                f"Blender a echoue (exit={result.returncode}).\n"
                f"stderr (15 dernieres lignes) :\n" + "\n".join(stderr_tail)
            )

        if not os.path.isfile(blend_output_path):
            raise RuntimeError(
                "Blender a tourne sans erreur mais le .blend attendu n'a pas ete cree.\n"
                f"Attendu : {blend_output_path}"
            )

        return blend_output_path, png_path
    finally:
        if os.path.exists(tmp_script):
            try:
                os.unlink(tmp_script)
            except OSError:
                pass
