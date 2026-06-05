# -*- coding: utf-8 -*-
"""
Color Studio - Rémi Cozot 2019
----------------------------------
new version of
Color Studio - Rémi Cozot 2019
"""

# import(s)
# ----------------------------------------------------------------------------------

import logging
import os
import time
import webbrowser

import skimage

from PyQt6.QtWidgets import (
    QLabel, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QScrollArea, QFrame, QFileDialog, QMessageBox,
    QStatusBar, QApplication,
)
from PyQt6.QtCore import Qt, QFile, QTextStream, QSettings, QSize, QPoint
from PyQt6.QtGui import QIcon, QAction, QKeySequence

from colorstudio import model as colorStudioModel
from colorstudio import widget as colorStudioWidget
from colorstudio import controller as colorStudioController

logger = logging.getLogger(__name__)

APP_NAME = "ColorStudio"
APP_ORG = "ColorStudio"
APP_VERSION = "1.0.0"
GITHUB_URL = "https://github.com/ittaq62/colorStudioApp"
MAX_RECENT_FILES = 5

# ----------------------------------------------------------------------------------
class CSUIBuilder:
    # class attributes
    uiLoadIMG  = None
    uiSaveIMG  = None
    uiAEonIMG  = None
    uiAEoffIMG = None
    uiDEIMG    = None
    uiIEIMG    = None
    uiCCIMG    = None

    template1920x1080 = {
        'scale': 0.5,
        'uiRenderWidget_pos': (480, 30),
        'uiRenderWidget_size': (int(1920 / 2), int(1080 / 2)),
        # color3D widget
        'uiColor3DWidget_pos': (1440, 30),
        'uiColor3DWidget_size': (480, 480),
        # menu/control widget
        'uiControlWidget_pos': (0, 30),
        'uiControlWidget_size': (480, 0),
    }

    template3000x200 = {
        'scale': 1,
        'uiRenderWidget_pos': (int(480 * 1.25), 60),
        'uiRenderWidget_size': (int(1920), int(1080)),
        # color3D widget
        'uiColor3DWidget_pos': (3000 - 480, 60),
        'uiColor3DWidget_size': (480, 480),
        # menu/control widget
        'uiControlWidget_pos': (0, 60),
        'uiControlWidget_size': (480, 0),
    }

    template = template1920x1080

    @staticmethod
    def setTemplate(widthScreen, heightScreen):
        if widthScreen == 3000:
            CSUIBuilder.template = CSUIBuilder.template3000x200

    def __init__(self):
        pass

    @staticmethod
    def uiLoadIcon(pathUIimg=None):
        # par defaut on cherche les icons dans le dossier du package
        # (fonctionne quel que soit le cwd, et marche aussi en mode bundle PyInstaller)
        if pathUIimg is None:
            import os
            pathUIimg = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 'icons', ''
            )
        # window with buttons
        CSUIBuilder.uiLoadIMG  = QIcon(pathUIimg + 'load.svg')
        CSUIBuilder.uiSaveIMG  = QIcon(pathUIimg + 'save.svg')
        CSUIBuilder.uiAEonIMG  = QIcon(pathUIimg + 'ae_on.svg')
        CSUIBuilder.uiAEoffIMG = QIcon(pathUIimg + 'ae_off.svg')
        CSUIBuilder.uiDEIMG    = QIcon(pathUIimg + 'minus.svg')
        CSUIBuilder.uiIEIMG    = QIcon(pathUIimg + 'plus.svg')
        CSUIBuilder.uiCCIMG    = QIcon(pathUIimg + 'palette.svg')

# ----------------------------------------------------------------------------------
class CSMainWindow(QMainWindow):
    """
    Fenetre principale de l'application.

    Gere :
    - le titre + icone + dark theme QSS
    - le menu bar (File / View / Help)
    - le status bar (fichier, mode, lights, temps de rendu)
    - la persistance de la geometrie via QSettings
    - la persistance des fichiers recents
    """

    def __init__(self, title="ColorStudio"):
        super().__init__()
        self._uiBuilder = None  # set par CSUIAllBuilder pour pouvoir le rebuilder
        self._scene = None
        self._settings = QSettings(APP_ORG, APP_NAME)

        self.setWindowTitle(title)

        # icone de la fenetre (barre des taches Windows + alt+tab)
        ico_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons', 'app.ico')
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))
        else:
            repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            splash = os.path.join(repo_root, 'splashScreen.jpg')
            if os.path.exists(splash):
                self.setWindowIcon(QIcon(splash))

        # taille par defaut (sera ecrasee par QSettings si une geometrie est memorisee)
        s_width, s_height = colorStudioWidget.getScreenSize()
        w = min(1400, int(s_width * 0.9))
        h = min(800, int(s_height * 0.9))
        self.resize(w, h)

        self.apply_style()

        # menu bar + status bar
        self._build_menu_bar()
        self._build_status_bar()

        # restaure la geometrie memorisee (si elle existe)
        geom = self._settings.value("window/geometry")
        if geom is not None:
            self.restoreGeometry(geom)
        state = self._settings.value("window/state")
        if state is not None:
            self.restoreState(state)

    # ------------------------------------------------------------------ style
    def apply_style(self):
        qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'styles.qss')
        style_file = QFile(qss_path)
        if style_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(style_file)
            self.setStyleSheet(stream.readAll())

    # -------------------------------------------------------------- menu bar
    def _build_menu_bar(self):
        """construit la menu bar File / View / Help avec leurs actions"""
        menubar = self.menuBar()

        # --- File ---
        file_menu = menubar.addMenu("&Fichier")

        act_open = QAction("&Ouvrir une scene...", self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._action_open)
        file_menu.addAction(act_open)

        # sous-menu Recents
        self._recent_menu = file_menu.addMenu("Recemment ouverts")
        self._rebuild_recent_menu()

        file_menu.addSeparator()

        act_save = QAction("&Sauvegarder le rendu...", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._action_save_render)
        file_menu.addAction(act_save)

        act_save_scene = QAction("&Exporter la scene (JSON)...", self)
        act_save_scene.setShortcut(QKeySequence("Ctrl+Shift+S"))
        act_save_scene.triggered.connect(self._action_export_scene)
        file_menu.addAction(act_save_scene)

        file_menu.addSeparator()

        act_quit = QAction("&Quitter", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # --- View ---
        view_menu = menubar.addMenu("&Affichage")

        self._act_toggle_hdr = QAction("Basculer le mode &HDR", self)
        self._act_toggle_hdr.setShortcut(QKeySequence("Ctrl+H"))
        self._act_toggle_hdr.setCheckable(True)
        self._act_toggle_hdr.triggered.connect(self._action_toggle_hdr)
        view_menu.addAction(self._act_toggle_hdr)

        # --- Help ---
        help_menu = menubar.addMenu("&Aide")

        act_docs = QAction("Documentation", self)
        act_docs.setShortcut(QKeySequence.StandardKey.HelpContents)
        act_docs.triggered.connect(self._action_open_docs)
        help_menu.addAction(act_docs)

        act_github = QAction("Voir sur GitHub", self)
        act_github.triggered.connect(lambda: webbrowser.open(GITHUB_URL))
        help_menu.addAction(act_github)

        help_menu.addSeparator()

        act_about = QAction("&A propos de ColorStudio...", self)
        act_about.triggered.connect(self._action_about)
        help_menu.addAction(act_about)

    def _rebuild_recent_menu(self):
        """rafraichit le sous-menu des fichiers recents depuis QSettings"""
        self._recent_menu.clear()
        recent = self._settings.value("recent/files", []) or []
        if not isinstance(recent, list):
            recent = [recent]
        recent = [r for r in recent if r and os.path.exists(r)]

        if not recent:
            no_recent = QAction("(aucun fichier recent)", self)
            no_recent.setEnabled(False)
            self._recent_menu.addAction(no_recent)
            return

        for path in recent:
            act = QAction(os.path.basename(path), self)
            act.setToolTip(path)
            # bind explicite avec default arg pour eviter la late-binding
            act.triggered.connect(lambda checked=False, p=path: self._open_scene(p))
            self._recent_menu.addAction(act)

        self._recent_menu.addSeparator()
        act_clear = QAction("Effacer la liste", self)
        act_clear.triggered.connect(self._action_clear_recent)
        self._recent_menu.addAction(act_clear)

    # ------------------------------------------------------------ status bar
    def _build_status_bar(self):
        """construit le status bar avec 4 labels permanents"""
        sb = QStatusBar(self)
        self.setStatusBar(sb)

        self._sb_file = QLabel("aucun fichier")
        self._sb_mode = QLabel("LDR")
        self._sb_lights = QLabel("0 lumieres")
        self._sb_render = QLabel("- ms")

        for w in (self._sb_file, self._sb_mode, self._sb_lights, self._sb_render):
            w.setMinimumWidth(80)
            sb.addPermanentWidget(w)

    def update_status_bar(self, filename=None, hdr=False, n_lights=0, render_ms=None):
        """met a jour les infos affichees en bas. appelable a tout moment."""
        if filename:
            self._sb_file.setText(os.path.basename(filename))
            self._sb_file.setToolTip(filename)
        self._sb_mode.setText("HDR" if hdr else "LDR")
        self._sb_lights.setText(f"{n_lights} lumiere{'s' if n_lights != 1 else ''}")
        if render_ms is not None:
            self._sb_render.setText(f"{render_ms:.1f} ms")

    # ----------------------------------------------------------- file actions
    def _action_open(self):
        """ouvre une scene depuis le disque (callback du menu Fichier > Ouvrir)"""
        start_dir = ""
        last = self._settings.value("recent/lastFile", type=str)
        if last and os.path.exists(last):
            start_dir = os.path.dirname(last)

        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Ouvrir une scene",
            start_dir,
            "Scene files (*.json *.xml);;JSON files (*.json);;XML files (*.xml)",
        )
        if filename:
            self._open_scene(filename)

    def _open_scene(self, filename):
        """charge une scene et reconstruit l'UI. Gere les erreurs proprement."""
        scale = CSUIBuilder.template['scale']
        try:
            scene = colorStudioModel.Scene()
            if filename.lower().endswith('.json'):
                scene.fromJSON(filename, scale)
            else:
                scene.fromXML(filename, scale)
            scene._sourceFile = filename
        except Exception as exc:
            logger.exception("echec du chargement de %s", filename)
            QMessageBox.critical(
                self,
                "Erreur de chargement",
                f"Impossible de charger la scene :\n\n{filename}\n\nDetail : {exc}"
            )
            return

        # memorise le fichier
        self._settings.setValue("recent/lastFile", filename)
        self._add_to_recent(filename)
        self._rebuild_recent_menu()

        # rebuild de l'UI avec la nouvelle scene
        # on garde le mainWindow vivant, on recree juste son contenu via UIBuilder
        if self._uiBuilder is not None:
            self._uiBuilder._rebuild_with_scene(scene)

    def _action_save_render(self):
        """sauvegarde l'image rendue courante en .png/.jpg"""
        if self._scene is None:
            return
        suggested = "render.png"
        if hasattr(self._scene, '_renderFile') and self._scene._renderFile:
            suggested = self._scene._renderFile

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Sauvegarder le rendu",
            suggested,
            "Images (*.png *.jpg *.jpeg *.bmp)",
        )
        if not filename:
            return

        try:
            import imageio.v2 as imageio
            import numpy as np
            img = self._scene.render()
            if img.max() > 1.0:
                from colorstudio.utils import toneMap
                img = toneMap(img)
            img_uint8 = (np.clip(img, 0.0, 1.0) * 255).astype(np.uint8)
            imageio.imwrite(filename, img_uint8)
            self.statusBar().showMessage(f"Rendu sauvegarde : {filename}", 5000)
            logger.info("rendu sauvegarde dans %s", filename)
        except Exception as exc:
            logger.exception("echec de la sauvegarde du rendu")
            QMessageBox.critical(
                self, "Erreur",
                f"Impossible de sauvegarder le rendu :\n\n{exc}"
            )

    def _action_export_scene(self):
        """exporte la scene courante au format JSON"""
        if self._scene is None:
            return
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter la scene en JSON",
            "scene.json",
            "JSON files (*.json)",
        )
        if not filename:
            return
        try:
            self._scene.toJSON(filename)
            self.statusBar().showMessage(f"Scene exportee : {filename}", 5000)
            logger.info("scene exportee dans %s", filename)
        except Exception as exc:
            logger.exception("echec de l'export de la scene")
            QMessageBox.critical(
                self, "Erreur",
                f"Impossible d'exporter la scene :\n\n{exc}"
            )

    # ----------------------------------------------------------- view actions
    def _action_toggle_hdr(self, checked):
        """bascule le mode HDR depuis le menu"""
        if self._scene is None:
            return
        self._scene._hdr = bool(checked)
        if self._uiBuilder is not None:
            img = self._scene.render()
            for w in self._uiBuilder._displayWidgets():
                w._update(img)
        self.update_status_bar(hdr=self._scene._hdr,
                               n_lights=len(self._scene._lights))

    # ----------------------------------------------------------- help actions
    def _action_about(self):
        """affiche le dialogue A propos"""
        QMessageBox.about(
            self,
            f"A propos de {APP_NAME}",
            f"<h2>{APP_NAME} {APP_VERSION}</h2>"
            "<p>Outil de compositing par sources lumineuses.</p>"
            "<p><b>Auteurs :</b><br>"
            "Blaszyk Constant<br>"
            "Douilly Quentin<br>"
            "Deldalle Corentin</p>"
            "<p><b>Projet original :</b> Remi Cozot, 2019</p>"
            "<p><b>Reprise :</b> SAE 6A Maintenance Logicielle, "
            "BUT3 INFO APP, 2025/2026</p>"
            f"<p><a href='{GITHUB_URL}'>GitHub</a></p>"
        )

    def _action_open_docs(self):
        """ouvre le dossier docs/ dans l'explorateur de fichiers"""
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        docs_dir = os.path.join(repo_root, 'docs')
        if os.path.isdir(docs_dir):
            webbrowser.open(f'file:///{docs_dir.replace(os.sep, "/")}')
        else:
            QMessageBox.information(
                self, "Documentation",
                f"Documentation en ligne :\n{GITHUB_URL}"
            )

    # --------------------------------------------------------- recent files
    def _add_to_recent(self, filename):
        recent = self._settings.value("recent/files", []) or []
        if not isinstance(recent, list):
            recent = [recent]
        recent = [filename] + [f for f in recent if f != filename]
        recent = recent[:MAX_RECENT_FILES]
        self._settings.setValue("recent/files", recent)

    def _action_clear_recent(self):
        self._settings.setValue("recent/files", [])
        self._rebuild_recent_menu()

    # --------------------------------------------------- persistance Qt close
    def closeEvent(self, event):
        """sauvegarde la geometrie de la fenetre avant fermeture"""
        self._settings.setValue("window/geometry", self.saveGeometry())
        self._settings.setValue("window/state", self.saveState())
        super().closeEvent(event)

# ----------------------------------------------------------------------------------
class CSUIAllBuilder(CSUIBuilder):
    def __init__(self, lightsScene):
        # (0) load qIcon images
        CSUIBuilder.uiLoadIcon()

        # (1) Main Window Init
        self.mainWindow = CSMainWindow("ColorStudio")
        # branche le main window sur le UIBuilder pour les callbacks
        self.mainWindow._uiBuilder = self
        self.mainWindow._scene = lightsScene

        # construit le contenu central
        self._buildCentralContent(lightsScene)

        # met a jour le status bar avec les infos initiales
        self._initialRender(lightsScene)

    def _displayWidgets(self):
        """liste des widgets qui doivent etre rafraichis quand l'image change"""
        return [self._renderWidget, self._color3DWidget]

    def _initialRender(self, scene):
        """fait un rendu initial + met a jour le status bar"""
        t0 = time.perf_counter()
        img = scene.render()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._renderWidget._update(img)
        # met a jour le menu HDR + le status bar
        self.mainWindow._act_toggle_hdr.setChecked(scene._hdr)
        self.mainWindow.update_status_bar(
            filename=getattr(scene, '_sourceFile', None),
            hdr=scene._hdr,
            n_lights=len(scene._lights),
            render_ms=elapsed_ms,
        )

    def _rebuild_with_scene(self, newScene):
        """
        appele depuis le menu File > Open : recharge entierement le contenu
        central avec une nouvelle scene sans relancer l'app.
        """
        self.mainWindow._scene = newScene
        # vide le contenu central existant
        old_central = self.mainWindow.centralWidget()
        if old_central is not None:
            old_central.deleteLater()
        # rebuild
        self._buildCentralContent(newScene)
        self._initialRender(newScene)

    def _buildCentralContent(self, lightsScene):
        """construit tout le contenu central (sidebar + image + 3D)"""
        # Central widget and main layout
        central_widget = QWidget()
        self.mainWindow.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # (2) Splitter for Sidebar | Image area
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        # (3) Sidebar Construction
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(350)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        # Scroll Area for Controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        self.controls_layout = QVBoxLayout(scroll_content)
        self.controls_layout.setContentsMargins(15, 15, 15, 15)
        self.controls_layout.setSpacing(10)
        scroll.setWidget(scroll_content)

        sidebar_layout.addWidget(scroll)

        # (4) Widgets Creation
        # Image Display
        self._renderWidget = colorStudioWidget.CSDisplayWidget(None)
        self._renderWidget.setObjectName("imageArea")

        # 3D color cloud
        self._color3DWidget = colorStudioWidget.MyWidgetGL(
            skimage.transform.rescale(lightsScene.render(), 0.1, anti_aliasing=True, channel_axis=2), True)
        self._color3DWidget.setMinimumHeight(100)

        # (5) Populating Sidebar
        title_label = QLabel("COLOR STUDIO")
        title_label.setObjectName("title")
        self.controls_layout.addWidget(title_label)

        # Load / Save Card
        loadSaveLayout = colorStudioWidget.CSQLoadSaveLayout(CSUIBuilder.uiLoadIMG, CSUIBuilder.uiSaveIMG)
        self.controls_layout.addWidget(colorStudioWidget.CardWidget(loadSaveLayout, "Project"))

        # HDR Card
        hdr_layout = colorStudioWidget.CSQHDRControlLayout(lightsScene, [self._renderWidget, self._color3DWidget])
        self.controls_layout.addWidget(colorStudioWidget.CardWidget(hdr_layout, "HDR Mode"))

        # Auto Exposure Card
        ae = colorStudioModel.AE_Ymean(Ytarget=0.5, exposure=0.0)
        lightsScene.addPostProcess(ae)
        AE_layout = colorStudioWidget.CSQAEControlLayout(None)
        ae_controller = colorStudioController.CSAEController(lightsScene, ae, [self._renderWidget, self._color3DWidget])
        AE_layout._controller = ae_controller
        self.controls_layout.addWidget(colorStudioWidget.CardWidget(AE_layout, "Auto Exposure"))

        # Saturation Card
        sat = colorStudioModel.Saturation()
        lightsScene.addPostProcess(sat)
        sat_layout = colorStudioWidget.CSQSaturationLayout(None)
        sat_controller = colorStudioController.CSSaturationController(lightsScene, sat, [self._renderWidget, self._color3DWidget])
        sat_layout._controller = sat_controller
        self.controls_layout.addWidget(colorStudioWidget.CardWidget(sat_layout, "Color & Saturation"))

        # Lights Cards
        for light in lightsScene._lights:
            lightControl_layout = colorStudioWidget.CSQLightControlLayout(None, lightPosIdx=light._imageIdx)
            expoString = "{:+.2f}".format(light._exposure)
            lightControl_layout._exposureValueLabel.setText(expoString)
            lightControl_layout.updatePreview(light._npColorRGB)

            lightController = colorStudioController.CSLightController(lightsScene, light, [self._renderWidget, self._color3DWidget])
            lightControl_layout._controller = lightController

            self.controls_layout.addWidget(colorStudioWidget.CardWidget(lightControl_layout, f"Light: {light._name}"))

        self.controls_layout.addStretch()

        # (6) Assembly
        # Right side: Vertical Splitter [Top: Image | Bottom: Analytics]
        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(self._renderWidget)
        
        # Bottom Analytics Panel
        bottom_analytics = QWidget()
        bottom_analytics.setObjectName("bottomAnalytics")
        bottom_layout = QHBoxLayout(bottom_analytics)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(10)
        
        # Limit height of bottom panel
        bottom_analytics.setMaximumHeight(250)
        
        bottom_layout.addWidget(self._color3DWidget)
        
        right_splitter.addWidget(bottom_analytics)
        
        # Initial proportions
        right_splitter.setStretchFactor(0, 10)
        right_splitter.setStretchFactor(1, 1)
        right_splitter.setSizes([600, 200])

        # Main Splitter Assembly
        self.splitter.addWidget(sidebar)
        self.splitter.addWidget(right_splitter)
        self.splitter.setStretchFactor(1, 1)

        # Show the main window (idempotent : appeler show() plusieurs fois est ok)
        self.mainWindow.show()
