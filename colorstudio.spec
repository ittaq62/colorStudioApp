# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec pour ColorStudio.

Construit un .exe Windows standalone qui embarque :
- le package colorstudio (model, widget, ui_builder, controller, utils, app)
- les assets : icones SVG, app.ico, styles.qss, splashScreen.jpg
- les scenes par defaut (.json, .xml) a la racine
- le dossier images/ pour la scene par defaut

Build :
    py -3.13 -m PyInstaller colorstudio.spec --clean

Le binaire produit est dans dist/colorstudio/colorstudio.exe (ou
dist/colorstudio.exe en mode --onefile).
"""

from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata

# resolution du repo root via le cwd (PyInstaller cd dans le repo avant de lire la spec)
project_root = Path(SPECPATH)

# ------- collecte des assets -------
datas = [
    # icones du package
    (str(project_root / 'colorstudio' / 'icons'), 'colorstudio/icons'),
    # stylesheet QSS du dark theme
    (str(project_root / 'colorstudio' / 'styles.qss'), 'colorstudio'),
    # splash screen
    (str(project_root / 'splashScreen.jpg'), '.'),
    # scenes par defaut (l'utilisateur peut les ouvrir depuis le menu File)
    (str(project_root / 'xml-postProcess-test.json'), '.'),
    (str(project_root / 'xml-hdr-demo.json'), '.'),
    (str(project_root / 'xml-postProcess-test.xml'), '.'),
    (str(project_root / 'xml-hdr-demo.xml'), '.'),
    # dossier images pour la scene par defaut
    (str(project_root / 'images'), 'images'),
]

# ------- metadata des packages qui en ont besoin a runtime -------
# imageio lit sa propre version via importlib.metadata.version("imageio") au demarrage,
# PackageNotFoundError sinon. Idem prudemment pour scikit-image / numpy.
for pkg in ('imageio', 'scikit-image', 'numpy', 'Pillow'):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        # le package n'est peut-etre pas installe sous ce nom canonique, on ignore
        pass

# ------- hidden imports -------
# PyInstaller ne detecte pas toujours moderngl + ses backends. On les force.
hiddenimports = [
    'moderngl',
    'moderngl.opengl',
    'skimage.color',
    'skimage.transform',
    'imageio.v2',
    'imageio.plugins.pillow',
    'imageio.plugins.freeimage',
    'PyQt6.QtOpenGLWidgets',
    'PyQt6.QtOpenGL',
]


a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # exclure les modules tests / dev pour reduire la taille
        'pytest', 'unittest', 'tests',
        'tkinter', 'PyQt5', 'PySide2', 'PySide6',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='colorstudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI app -> pas de console derriere
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'colorstudio' / 'icons' / 'app.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='colorstudio',
)
