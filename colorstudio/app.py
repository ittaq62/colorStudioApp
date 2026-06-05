# -*- coding: utf-8 -*-
"""
ColorStudio - point d'entree principal.

Cree l'application Qt, charge la scene initiale et instancie la fenetre
principale. Cette fonction est appelee :
- par `main.py` a la racine du repo (developpement)
- par la commande `colorstudio` une fois le projet installe via pip
- par l'executable PyInstaller bundle
"""

import logging
import os
import sys

from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen

logger = logging.getLogger(__name__)


# nom de l'app + organisation utilises par QSettings (registre Windows / ini Linux)
APP_NAME = "ColorStudio"
APP_ORG = "ColorStudio"
APP_VERSION = "1.0.0"


def _get_asset_path(relative_path):
    """
    retourne un chemin absolu vers un asset (icones, qss, images, ...)
    fonctionne en mode developpement (lance depuis le repo) et en mode bundle
    PyInstaller (les assets sont dans sys._MEIPASS).
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller : assets bundles dans le dossier temporaire
        base = sys._MEIPASS
    else:
        # developpement : repo racine = parent du package colorstudio/
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative_path)


def _setup_logging():
    """initialise le module logging avec un format propre"""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)-7s %(name)s: %(message)s',
        datefmt='%H:%M:%S',
        stream=sys.stderr,
    )


def _load_scene(filename, scale=0.5):
    """
    charge une scene depuis un fichier (detection JSON/XML par extension).
    retourne une instance de Scene chargee, ou leve une exception en cas d'erreur.
    """
    # import local pour eviter le cout du chargement skimage/numpy a l'import du module
    from colorstudio import model as colorStudioModel

    scene = colorStudioModel.Scene()
    if filename.lower().endswith('.json'):
        scene.fromJSON(filename, scale)
    else:
        scene.fromXML(filename, scale)
    return scene


def main(argv=None):
    """
    point d'entree de l'application.

    parametres
    ----------
    argv : list[str] ou None
        arguments en ligne de commande (utilise sys.argv si None).

    retour
    ------
    int : code de sortie de l'app Qt
    """
    if argv is None:
        argv = sys.argv

    _setup_logging()
    logger.info("ColorStudio %s - demarrage", APP_VERSION)

    # imports tardifs : ces modules sont assez gros (skimage, moderngl, PyQt6)
    # on attend d'avoir initialise le logging pour avoir des messages d'erreur lisibles
    from colorstudio import widget as colorStudioWidget
    from colorstudio import ui_builder as colorStudioUIBuilder

    # init Qt
    app = QApplication.instance() or QApplication(argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_ORG)

    # icone de l'application
    icon_path = _get_asset_path('colorstudio/icons/app.ico')
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    # splash screen pendant le chargement de la scene
    splash_path = _get_asset_path('splashScreen.jpg')
    splash = None
    if os.path.exists(splash_path):
        splash_pix = QPixmap(splash_path).scaledToWidth(480)
        splash = QSplashScreen(splash_pix)
        splash.show()
        splash.showMessage(
            "Chargement...",
            color=app.palette().windowText().color(),
        )
        app.processEvents()

    # configure le template d'UI selon la resolution
    screenX, screenY = colorStudioWidget.getScreenSize()
    logger.info("resolution ecran : %dx%d", screenX, screenY)
    colorStudioUIBuilder.CSUIBuilder.setTemplate(screenX, screenY)

    # selection du fichier de scene (resolution silencieuse, sans interrompre l'utilisateur) :
    # 1. argument CLI (ex: `colorstudio xml-hdr-demo.json`)
    # 2. dernier fichier ouvert memorise par QSettings
    # 3. scene par defaut livree avec l'app (xml-postProcess-test.json)
    #
    # L'utilisateur peut toujours ouvrir un autre fichier via le menu Fichier > Ouvrir.
    # On ne lui balance plus de QFileDialog au demarrage : c'etait un comportement
    # heritage du code 2019, pas adapte a une vraie app desktop.
    settings = QSettings(APP_ORG, APP_NAME)
    inputFilename = None

    if len(argv) > 1 and os.path.exists(argv[1]):
        inputFilename = argv[1]
        logger.info("fichier passe en argument : %s", inputFilename)

    if inputFilename is None:
        # essaie d'utiliser le dernier fichier ouvert (lancements suivants)
        last_file = settings.value("recent/lastFile", type=str)
        if last_file and os.path.exists(last_file):
            inputFilename = last_file
            logger.info("dernier fichier reouvert : %s", inputFilename)

    if not inputFilename:
        # premier lancement : scene par defaut livree dans le bundle
        default_file = _get_asset_path('xml-postProcess-test.json')
        if os.path.exists(default_file):
            inputFilename = default_file
            logger.info("premier lancement, scene par defaut : %s", inputFilename)
        else:
            QMessageBox.critical(
                None,
                "ColorStudio",
                "Aucun fichier de scene selectionne et la scene par defaut "
                "est introuvable. L'application va se fermer."
            )
            return 1

    # chargement de la scene avec gestion d'erreur
    scale = colorStudioUIBuilder.CSUIBuilder.template['scale']
    try:
        if splash:
            splash.showMessage(
                f"Chargement de {os.path.basename(inputFilename)}...",
                color=app.palette().windowText().color(),
            )
            app.processEvents()
        lightsScene = _load_scene(inputFilename, scale=scale)
        lightsScene._sourceFile = inputFilename  # stocke pour le status bar / save
    except Exception as exc:
        logger.exception("echec du chargement de la scene")
        if splash:
            splash.close()
        QMessageBox.critical(
            None,
            "Erreur de chargement",
            f"Impossible de charger la scene :\n\n{inputFilename}\n\n"
            f"Detail : {exc}"
        )
        return 1

    # memorise le fichier comme dernier ouvert + ajoute aux recents
    settings.setValue("recent/lastFile", inputFilename)
    _add_to_recent(settings, inputFilename)

    # build de l'UI
    ui = colorStudioUIBuilder.CSUIAllBuilder(lightsScene)

    if splash:
        splash.finish(ui.mainWindow)

    # boucle d'evenements
    return app.exec()


def _add_to_recent(settings, filename, max_recent=5):
    """ajoute un fichier a la liste des recents (deduplique, capee a max_recent)"""
    recent = settings.value("recent/files", []) or []
    if not isinstance(recent, list):
        recent = [recent]
    # remonte le fichier en tete et supprime les doublons
    recent = [filename] + [f for f in recent if f != filename]
    recent = recent[:max_recent]
    settings.setValue("recent/files", recent)


if __name__ == "__main__":
    sys.exit(main())
