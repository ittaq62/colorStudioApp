# -*- coding: utf-8 -*-
"""
Script de build de l'executable Windows .exe via PyInstaller.

Usage :
    py -3.13 build_exe.py            # build complet (clean + spec)
    py -3.13 build_exe.py --onefile  # build en un seul .exe (plus lent au demarrage)

Prerequis :
    py -3.13 -m pip install pyinstaller Pillow

Le .exe est genere dans dist/colorstudio/colorstudio.exe (mode dossier, plus rapide
a demarrer) ou dist/colorstudio.exe (mode --onefile, plus pratique a distribuer).
"""

import argparse
import os
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description="Build ColorStudio.exe via PyInstaller")
    parser.add_argument('--onefile', action='store_true',
                        help="Genere un seul .exe (au lieu d'un dossier dist/colorstudio/)")
    parser.add_argument('--no-clean', action='store_true',
                        help="N'efface pas dist/ et build/ avant le build")
    parser.add_argument('--no-icons', action='store_true',
                        help="N'execute pas generate_icons.py avant le build")
    args = parser.parse_args()

    repo_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(repo_root)

    # 1) regenerer les icones (au cas ou splashScreen.jpg ait change)
    if not args.no_icons:
        print(">>> regeneration des icones SVG + app.ico...")
        subprocess.check_call([sys.executable, 'generate_icons.py'])

    # 2) clean
    if not args.no_clean:
        for d in ('build', 'dist'):
            if os.path.exists(d):
                print(f">>> suppression de {d}/")
                shutil.rmtree(d)

    # 3) PyInstaller
    cmd = [sys.executable, '-m', 'PyInstaller']
    if args.onefile:
        # mode onefile : pas de spec, on passe les args directement
        cmd += [
            '--onefile',
            '--windowed',
            '--name', 'colorstudio',
            '--icon', os.path.join('colorstudio', 'icons', 'app.ico'),
            '--add-data', f'colorstudio/icons{os.pathsep}colorstudio/icons',
            '--add-data', f'colorstudio/styles.qss{os.pathsep}colorstudio',
            '--add-data', f'splashScreen.jpg{os.pathsep}.',
            '--add-data', f'xml-postProcess-test.json{os.pathsep}.',
            '--add-data', f'xml-hdr-demo.json{os.pathsep}.',
            '--add-data', f'images{os.pathsep}images',
            '--hidden-import', 'moderngl',
            '--hidden-import', 'skimage.color',
            '--hidden-import', 'skimage.transform',
            '--hidden-import', 'PyQt6.QtOpenGLWidgets',
            '--clean',
            'main.py',
        ]
    else:
        cmd += ['colorstudio.spec']
        if not args.no_clean:
            cmd.append('--clean')

    print(">>>", ' '.join(cmd))
    subprocess.check_call(cmd)

    # 4) report
    if args.onefile:
        out = os.path.join('dist', 'colorstudio.exe')
    else:
        out = os.path.join('dist', 'colorstudio', 'colorstudio.exe')

    if os.path.exists(out):
        size_mb = os.path.getsize(out) / (1024 * 1024)
        print(f"\n>>> Build OK : {out} ({size_mb:.1f} Mo)")
    else:
        print("\n>>> Build termine mais le binaire attendu est introuvable.")
        print(f"    attendu : {out}")
        sys.exit(1)


if __name__ == "__main__":
    main()
