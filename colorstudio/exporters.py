# -*- coding: utf-8 -*-
"""
Exporteurs de scenes ColorStudio vers d'autres outils.

Pour l'instant : export Blender via un script Python autonome.
Le script genere peut etre execute avec : `blender --python scene_blender.py`
ou colle dans l'editeur Python de Blender.
"""

import math
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime


def export_to_blender(scene, output_path, source_scene_file=None):
    """
    genere un script Python Blender qui recree le setup d'eclairage de la scene
    ColorStudio dans une scene Blender vide.

    Pour chaque Light de la scene, on cree une POINT light Blender avec :
    - sa couleur RGB (canal `light.color`)
    - une intensite calculee depuis l'exposition EV (canal `light.energy`)
    - une position en placeholder (cercle autour de l'origine) car ColorStudio
      ne connait pas les positions 3D reelles (juste un index dans la trajectoire)
    - un commentaire qui mappe la light Blender vers ses images source

    Parameters
    ----------
    scene : model.Scene
        la scene ColorStudio a exporter
    output_path : str
        chemin du script .py a generer
    source_scene_file : str ou None
        chemin du fichier .json/.xml source, pour info dans le header
    """
    lights = scene._lights
    if not lights:
        raise ValueError("La scene ne contient aucune lumiere a exporter")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # construit les data des lights (couleur normalisee + energie en watts)
    lights_data = []
    n = max(1, len(lights))
    for i, light in enumerate(lights):
        r, g, b = float(light._npColorRGB[0]), float(light._npColorRGB[1]), float(light._npColorRGB[2])
        # energie : 1000 W (= equivalent point light typique) * 2^EV
        energy = 1000.0 * (2.0 ** float(light._exposure))
        # position en cercle de rayon 5m autour de l'origine, hauteur 3m
        angle = 2.0 * math.pi * i / n
        pos_x = 5.0 * math.cos(angle)
        pos_y = 5.0 * math.sin(angle)
        pos_z = 3.0

        lights_data.append({
            "name": light._name,
            "color": (r, g, b),
            "energy": energy,
            "exposure_ev": float(light._exposure),
            "position": (pos_x, pos_y, pos_z),
            "image_path": _images_info(light),
            "image_idx": light._imageIdx,
        })

    # genere le script
    script = _build_blender_script(
        lights_data=lights_data,
        scene_file=source_scene_file,
        hdr=scene._hdr,
        timestamp=timestamp,
    )

    # ecriture
    os.makedirs(os.path.dirname(os.path.abspath(output_path)) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(script)

    return output_path


def _images_info(light):
    """retourne le chemin du set d'images source d'une light (pour les commentaires)"""
    arr = light._ImagesArray
    if arr is None:
        return "(pas d'images)"
    base = arr._pathImage + arr._baseImageName if arr._pathImage else arr._baseImageName
    return f"{base}<{arr._nbImage:0{arr._nbDigit}d}>{arr._extImageName}"


def _build_blender_script(lights_data, scene_file, hdr, timestamp):
    """assemble le code Python Blender complet"""
    header = f'''# -*- coding: utf-8 -*-
"""
Script Blender genere par ColorStudio le {timestamp}.

Pour l'utiliser :
  - Soit en CLI :  blender --python {os.path.basename("scene_blender.py")}
  - Soit dans Blender : ouvrir l'editeur Scripting, charger ce fichier, Run Script

Ce script :
  1. clear la scene courante (a faire avec precaution sur un .blend existant !)
  2. ajoute {len(lights_data)} POINT lights, une pour chaque Light de ColorStudio
  3. positionne les lights en cercle autour de l'origine (placeholder)
  4. configure la camera + un cube simple comme sujet de demo

Source ColorStudio :
  fichier : {scene_file or "(non specifie)"}
  mode    : {"HDR" if hdr else "LDR"}
  lights  : {len(lights_data)}

NOTE sur les positions :
  ColorStudio compose des images pre-rendues indexees par position le long
  d'une trajectoire. Les positions 3D reelles des lumieres ne sont pas
  connues. Les positions ci-dessous sont des placeholders (cercle 5m de rayon).
  Adapter manuellement dans Blender pour matcher votre scene.
"""

import bpy
import math


def clear_scene():
    """vide la scene courante (objets, lights, cameras)"""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)


def add_demo_sujet():
    """ajoute un cube + un sol pour avoir un sujet visible"""
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
    bpy.context.object.name = "DemoCube"

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    bpy.context.object.name = "DemoFloor"


def add_camera():
    """ajoute une camera qui regarde le cube depuis (8, -8, 5)"""
    bpy.ops.object.camera_add(location=(8, -8, 5))
    cam = bpy.context.object
    cam.rotation_euler = (math.radians(63), 0, math.radians(45))
    bpy.context.scene.camera = cam


def add_light(name, color, energy, exposure_ev, position, image_path, image_idx):
    """cree une POINT light Blender avec la config ColorStudio"""
    bpy.ops.object.light_add(type='POINT', location=position)
    obj = bpy.context.object
    obj.name = name
    light_data = obj.data
    light_data.color = color
    light_data.energy = energy
    # on stocke l'info ColorStudio dans les custom properties pour reference
    obj["cs_exposure_ev"] = exposure_ev
    obj["cs_source_images"] = image_path
    obj["cs_active_image_idx"] = image_idx
    print(f"  + Light '{{name}}' : color={{color}} energy={{energy:.0f}}W pos={{position}}")


# =============================================================================
# Setup de la scene
# =============================================================================
print("[ColorStudio -> Blender] init de la scene...")
clear_scene()
add_demo_sujet()
add_camera()

# =============================================================================
# Ajout des lumieres
# =============================================================================
print("[ColorStudio -> Blender] ajout de {len(lights_data)} lumieres...")
'''

    body_lines = []
    for ld in lights_data:
        c = ld["color"]
        p = ld["position"]
        body_lines.append(
            f'add_light(\n'
            f'    name="{ld["name"]}",\n'
            f'    color=({c[0]:.4f}, {c[1]:.4f}, {c[2]:.4f}),\n'
            f'    energy={ld["energy"]:.2f},  # = 1000 W * 2^{ld["exposure_ev"]:.2f} EV\n'
            f'    exposure_ev={ld["exposure_ev"]:.2f},\n'
            f'    position=({p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f}),  # placeholder, a adapter\n'
            f'    image_path={repr(ld["image_path"])},\n'
            f'    image_idx={ld["image_idx"]},\n'
            f')'
        )

    footer = '''

# =============================================================================
print("[ColorStudio -> Blender] termine. Cliquer F12 pour render.")
'''

    return header + "\n".join(body_lines) + footer


# -----------------------------------------------------------------------------
# Export direct au format .blend (necessite Blender installe + sur le PATH)
# -----------------------------------------------------------------------------

def find_blender_executable():
    """
    cherche l'executable Blender sur le systeme.
    retourne le chemin trouve ou None.
    """
    # 1. dans le PATH
    p = shutil.which("blender")
    if p:
        return p

    # 2. emplacements connus sur Windows
    if sys.platform.startswith("win"):
        candidates = [
            r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.1\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.0\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

    # 3. emplacements connus sur macOS
    if sys.platform == "darwin":
        candidates = [
            "/Applications/Blender.app/Contents/MacOS/Blender",
        ]
        for c in candidates:
            if os.path.isfile(c):
                return c

    return None


def export_to_blend(scene, blend_output_path, source_scene_file=None, blender_exe=None, timeout=120):
    """
    genere directement un fichier .blend en invoquant Blender en mode headless.

    Workflow :
    1. genere le script Python ColorStudio -> Blender dans un fichier temporaire
    2. invoque : blender --background --python script.py --save out.blend
    3. retourne le chemin du .blend

    Parameters
    ----------
    scene : model.Scene
    blend_output_path : str
        chemin du .blend a produire
    source_scene_file : str ou None
        chemin du fichier source ColorStudio (pour les commentaires)
    blender_exe : str ou None
        chemin de l'executable Blender. Si None, auto-detection via find_blender_executable.
    timeout : int
        timeout en secondes pour l'invocation Blender (defaut 120s).

    Returns
    -------
    str : chemin absolu du .blend produit

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

    # 1. genere le script .py dans un fichier temporaire
    fd, tmp_script = tempfile.mkstemp(suffix=".py", prefix="colorstudio_export_")
    os.close(fd)
    try:
        export_to_blender(scene, tmp_script, source_scene_file=source_scene_file)

        # 2. invoque Blender en headless avec --save
        blend_output_path = os.path.abspath(blend_output_path)
        os.makedirs(os.path.dirname(blend_output_path) or ".", exist_ok=True)

        # script qu'on injecte en plus : sauvegarde du .blend a la fin
        # NB : --save de Blender ne fonctionne pas avec --python, on doit le faire
        # dans le script Python via bpy.ops.wm.save_as_mainfile
        save_snippet = f'\n\nimport bpy as _bpy\n_bpy.ops.wm.save_as_mainfile(filepath={blend_output_path!r})\n'
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
            stderr_tail = (result.stderr or "").splitlines()[-10:]
            raise RuntimeError(
                f"Blender a echoue (exit={result.returncode}).\n"
                f"stderr (10 dernieres lignes) :\n" + "\n".join(stderr_tail)
            )

        if not os.path.isfile(blend_output_path):
            raise RuntimeError(
                "Blender a tourne sans erreur mais le .blend attendu n'a pas ete cree.\n"
                f"Attendu : {blend_output_path}"
            )

        return blend_output_path
    finally:
        # nettoyage du script temporaire
        if os.path.exists(tmp_script):
            try:
                os.unlink(tmp_script)
            except OSError:
                pass
