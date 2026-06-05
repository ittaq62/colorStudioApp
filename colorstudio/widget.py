# -*- coding: utf-8 -*-
"""
Color Studio - Rémi Cozot 2019
----------------------------------
new version of
Color Studio - Rémi Cozot 2019
"""
# ----------------------------------------------------------------------------------
# import(s)
# ----------------------------------------------------------------------------------

import sys
import moderngl
import numpy as np
# math et skimage etaient utilises par CSDisplayColorWheel (supprime, remplace par QColorDialog)

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QSlider, QCheckBox, QFrame, QColorDialog,
)
from PyQt6.QtGui import QPixmap, QImage, QSurfaceFormat, QColor
#from PyQt6.QtGui import QIcon  # plus utilise dans ce fichier
from PyQt6 import QtCore
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

#from colorstudio import model as colorStudioModel  # plus utilise dans ce fichier
from colorstudio import utils as colorStudioUtils
from colorstudio import ui_builder as colorStudioUIBuilder

# functions
# ----------------------------------------------------------------------------------
def getScreenSize():
    app = QApplication.instance() or QApplication(sys.argv)
    screen = app.primaryScreen()
    size = screen.size()
    return size.width(), size.height()

# ----------------------------------------------------------------------------------
class CardWidget(QWidget):
    """
    Wrapper d'un layout dans une "card" du dark theme.
    Affiche un titre en majuscules + un sous-titre descriptif optionnel.
    """
    def __init__(self, layout, title=None, subtitle=None):
        super().__init__()
        self.setObjectName("card")
        self.setProperty("class", "card")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 12, 15, 12)
        main_layout.setSpacing(8)

        if title:
            title_label = QLabel(title.upper())
            title_label.setObjectName("sectionHeader")
            main_layout.addWidget(title_label)

        if subtitle:
            # petit texte descriptif sous le titre (gris)
            subtitle_label = QLabel(subtitle)
            subtitle_label.setObjectName("sectionSubtitle")
            subtitle_label.setWordWrap(True)
            main_layout.addWidget(subtitle_label)

        # If the passed layout is already a layout object
        if isinstance(layout, (QHBoxLayout, QVBoxLayout)):
            content_widget = QWidget()
            content_widget.setLayout(layout)
            main_layout.addWidget(content_widget)
        else:
            main_layout.addWidget(layout)

# ----------------------------------------------------------------------------------
# classes
# ----------------------------------------------------------------------------------
class QModernGLWidget(QOpenGLWidget):
    def __init__(self):
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 3)
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setSamples(4)
        QSurfaceFormat.setDefaultFormat(fmt)
        self.timer = QtCore.QElapsedTimer()
        super().__init__()

    def initializeGL(self):
        pass

    def paintGL(self):
        self.ctx = moderngl.create_context()
        self.screen = self.ctx.detect_framebuffer()
        self.init()
        self.render()
        self.paintGL = self.render

    def init(self):
        pass

    def render(self):
        pass

# ----------------------------------------------------------------------------------
class HelloWorld2D:
    def __init__(self, ctx, reserve='1024MB'):
        self.ctx = ctx
        # le shader applique d'abord le zoom puis le pan : (vertex * zoom) - pan
        self.prog = self.ctx.program(
            vertex_shader='''
                #version 330
                uniform vec2 Pan;
                uniform float Zoom;
                in vec2 in_vert;
                in vec4 in_color;
                out vec4 v_color;
                void main() {
                    v_color = in_color;
                    gl_Position = vec4(in_vert * Zoom - Pan, 0.0, 1.0);
                }
            ''',
            fragment_shader='''
                #version 330
                in vec4 v_color;
                out vec4 f_color;
                void main() {
                    f_color = v_color;
                }
            ''',
        )
        # init Pan + Zoom a leurs valeurs neutres
        self.prog['Pan'].value = (0.0, 0.0)
        self.prog['Zoom'].value = 1.0

        self.vbo = ctx.buffer(reserve='1024MB', dynamic=True)
        self.vao = ctx.vertex_array(self.prog, [(self.vbo, '2f 4f', 'in_vert', 'in_color')])

    def pan(self, pos):
        self.prog['Pan'].value = pos

    def zoom(self, factor):
        """factor > 1 = zoom avant, factor < 1 = zoom arriere"""
        self.prog['Zoom'].value = float(factor)

    def clear(self, color=(0, 0, 0, 0)):
        self.ctx.clear(*color)

    def plot(self, points, type='points'):
        data = points.astype('f4').tobytes()
        self.vbo.orphan()
        self.vbo.write(data)
        if type == 'line':
            self.ctx.line_width = 1.0
            self.vao.render(moderngl.LINE_STRIP, vertices=len(data) // 24)
        if type == 'points':
            self.ctx.point_size = 3.0
            self.vao.render(moderngl.POINTS, vertices=len(data) // 24)

# ----------------------------------------------------------------------------------
class PanTool:
    def __init__(self):
        self.total_x = 0.0
        self.total_y = 0.0
        self.start_x = 0.0
        self.start_y = 0.0
        self.delta_x = 0.0
        self.delta_y = 0.0
        self.drag = False

    def start_drag(self, x, y):
        self.start_x = x
        self.start_y = y
        self.drag = True

    def dragging(self, x, y):
        if self.drag:
            self.delta_x = (x - self.start_x) * 2.0
            self.delta_y = (y - self.start_y) * 2.0

    def stop_drag(self, x, y):
        if self.drag:
            self.dragging(x, y)
            self.total_x -= self.delta_x
            self.total_y += self.delta_y
            self.delta_x = 0.0
            self.delta_y = 0.0
            self.drag = False

    @property
    def value(self):
        return (self.total_x - self.delta_x, self.total_y + self.delta_y)

# ----------------------------------------------------------------------------------
pan_tool = PanTool()

# ----------------------------------------------------------------------------------
class MyWidgetGL(QModernGLWidget):
    """
    Widget OpenGL qui affiche le nuage de points 3D des couleurs de l'image.
    Controles :
    - drag souris : pan (deplacer la vue)
    - molette     : zoom in/out (par 1.2x par tick)
    - double-clic : reset pan + zoom
    """
    def __init__(self, img, scene=None):
        super().__init__()
        self.VBOdata = colorStudioUtils.img2chromaVertices(img, False)
        self.setWindowTitle("3D Color")
        self._zoomLevel = 1.0
        self.setToolTip(
            "Nuage 3D des couleurs de l'image\n"
            "  - Drag souris : deplacer la vue\n"
            "  - Molette : zoom avant / arriere\n"
            "  - Double-clic : reset pan + zoom"
        )

    def init(self):
        self.ctx.viewport = (0, 0, 480, 480)
        self.scene = HelloWorld2D(self.ctx)
        # applique le zoom courant (au cas ou il a ete change avant l'init OpenGL)
        self.scene.zoom(self._zoomLevel)

    def render(self):
        self.screen.use()
        self.scene.clear()
        self.scene.plot(self.VBOdata)

    def mousePressEvent(self, evt):
        pan_tool.start_drag(evt.position().x() / 512, evt.position().y() / 512)
        self.scene.pan(pan_tool.value)
        self.update()

    def mouseMoveEvent(self, evt):
        pan_tool.dragging(evt.position().x() / 512, evt.position().y() / 512)
        self.scene.pan(pan_tool.value)
        self.update()

    def mouseReleaseEvent(self, evt):
        pan_tool.stop_drag(evt.position().x() / 512, evt.position().y() / 512)
        self.scene.pan(pan_tool.value)
        self.update()

    def mouseDoubleClickEvent(self, evt):
        """double-clic = reset pan + zoom"""
        pan_tool.total_x = 0.0
        pan_tool.total_y = 0.0
        pan_tool.delta_x = 0.0
        pan_tool.delta_y = 0.0
        pan_tool.drag = False
        self._zoomLevel = 1.0
        if hasattr(self, 'scene'):
            self.scene.pan((0.0, 0.0))
            self.scene.zoom(self._zoomLevel)
        self.update()

    def wheelEvent(self, evt):
        """molette = zoom (1 tick = facteur 1.2)"""
        # angleDelta().y() retourne typiquement +/- 120 par cran
        delta = evt.angleDelta().y()
        if delta == 0:
            return
        factor = 1.2 if delta > 0 else (1.0 / 1.2)
        new_zoom = self._zoomLevel * factor
        # clamping pour eviter de zoomer dans le vide ou de devenir invisible
        new_zoom = max(0.1, min(20.0, new_zoom))
        self._zoomLevel = new_zoom
        if hasattr(self, 'scene'):
            self.scene.zoom(self._zoomLevel)
        self.update()

    def _update(self, img):
        self.VBOdata = colorStudioUtils.img2chromaVertices(img, False)
        self.update()

# ----------------------------------------------------------------------------------
class CSQIMGButton(QPushButton):

    def __init__(self, qicon, size, name="noname"):
        # qicon     (QIcon)
        # size      ((x,y))
        # name      (String)
        super().__init__()
        self.setIcon(qicon)
        self.name = name
        x, y = size
        self.setIconSize(QtCore.QSize(x, y))
        self.clicked.connect(self.cbClicked)

    def cbClicked(self):
        pass

# ----------------------------------------------------------------------------------
class CSQIMGSwitchButton(QPushButton):

    def __init__(self, qiconOn, qiconOff, size, name="noname"):
        # qicon     (QIcon)
        # size      ((x,y))
        # name      (String)
        super().__init__()
        self.iconOn = qiconOn
        self.iconOff = qiconOff
        # default state : on (true)
        self.on = True
        self.setIcon(self.iconOn)
        self.name = name
        x, y = size
        self.setIconSize(QtCore.QSize(x, y))
        self.clicked.connect(self.cbClicked)

    def cbClicked(self):
        self.on = not self.on
        if self.on:
            self.setIcon(self.iconOn)
        else:
            self.setIcon(self.iconOff)

# ----------------------------------------------------------------------------------
class CSQLoadSaveLayout(QHBoxLayout):

    def __init__(self, qiconLoad, qiconSave):
        super().__init__()

        # create load and save button
        self.loadButton = CSQIMGButton(qiconLoad, (32, 32), name="load button")
        self.saveButton = CSQIMGButton(qiconSave, (32, 32), name="save button")
        self.loadButton.setToolTip("Ouvrir une scene (Ctrl+O)")
        self.saveButton.setToolTip("Sauvegarder le rendu (Ctrl+S)")

        # add button to layout
        self.addWidget(self.loadButton)
        self.addWidget(self.saveButton)
        self.addStretch(1)  # boutons a gauche, pas en plein milieu

        # NB : les callbacks sont branches plus tard par CSUIAllBuilder
        # via wireToMainWindow(mainWindow), parce qu'on a besoin de la
        # main window pour declencher _action_open / _action_save_render

# ----------------------------------------------------------------------------------
class CSQLightControlLayout(QVBoxLayout):
    """
    Card de controle d'une lumiere, organisee en 2 lignes :
      Ligne 1 : [EV-] [+X.XX EV] [EV+] | [palette] [color preview]
      Ligne 2 : "Position dans la trajectoire"  [================ slider ================]  42 / 99
    """

    def __init__(self, controller, uiDEIMG=None, uiIEIMG=None, uiCCIMG=None, stepE=0.2, maxE=5, lightPosIdx=50, maxPos=99):
        super().__init__()
        # controller
        self._controller = controller

        # manage default Qicon
        if uiDEIMG is None:
            uiDEIMG = colorStudioUIBuilder.CSUIBuilder.uiDEIMG
        if uiIEIMG is None:
            uiIEIMG = colorStudioUIBuilder.CSUIBuilder.uiIEIMG
        if uiCCIMG is None:
            uiCCIMG = colorStudioUIBuilder.CSUIBuilder.uiCCIMG

        # boutons EV-/EV+ et palette de couleur
        self._deButton = CSQIMGButton(uiDEIMG, (28, 28), name="decrease exposure button")
        self._ieButton = CSQIMGButton(uiIEIMG, (28, 28), name="increase exposure button")
        self._ccButton = CSQIMGButton(uiCCIMG, (28, 28), name="light color button")
        self._deButton.setToolTip(f"Diminuer l'exposition de {stepE:.1f} EV")
        self._ieButton.setToolTip(f"Augmenter l'exposition de {stepE:.1f} EV")
        self._ccButton.setToolTip("Choisir la couleur de la lumiere (palette)")

        # label de la valeur d'exposition (en EV)
        self._exposureValueLabel = QLabel("+0.00 EV")
        self._exposureValueLabel.setMinimumWidth(60)
        self._exposureValueLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._exposureValueLabel.setObjectName("exposureLabel")
        self._exposureValueLabel.setToolTip(
            "Exposition courante en EV (double-clic pour reset a 0)"
        )

        # preview de la couleur de la lumiere
        self._colorPreview = QFrame()
        self._colorPreview.setFixedSize(28, 28)
        self._colorPreview.setStyleSheet(
            "background-color: white; border: 1px solid #555; border-radius: 4px;"
        )
        self._colorPreview.setToolTip("Couleur courante de la lumiere (cliquer la palette pour changer)")

        # control of Exposure
        self._step = stepE
        self._max = maxE
        self._maxPos = maxPos
        self._exposure = 0.0

        # ----- Ligne 1 : controles d'exposition + couleur -----
        topRow = QHBoxLayout()
        topRow.addWidget(self._deButton)
        topRow.addWidget(self._exposureValueLabel)
        topRow.addWidget(self._ieButton)
        topRow.addSpacing(10)
        topRow.addWidget(self._ccButton)
        topRow.addWidget(self._colorPreview)
        topRow.addStretch(1)
        topRow.setSpacing(6)
        self.addLayout(topRow)

        # ----- Ligne 2 : slider de position avec label + valeur en clair -----
        posLabelLeft = QLabel("Position")
        posLabelLeft.setMinimumWidth(60)
        posLabelLeft.setToolTip(
            "Position de la lumiere le long de la trajectoire pre-rendue.\n"
            "Chaque valeur correspond a une image differente du set."
        )

        self._sliderPosition = QSlider(QtCore.Qt.Orientation.Horizontal)
        self._sliderPosition.setRange(0, maxPos)
        self._sliderPosition.setValue(lightPosIdx)
        self._sliderPosition.setObjectName("posSlider")
        self._sliderPosition.setMinimumHeight(20)
        self._sliderPosition.setToolTip(
            f"Deplacer la lumiere sur sa trajectoire pre-rendue (0 a {maxPos})"
        )

        # label de position : "42 / 99"
        self._posLabel = QLabel(f"{lightPosIdx} / {maxPos}")
        self._posLabel.setMinimumWidth(55)
        self._posLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._posLabel.setObjectName("posLabel")
        self._posLabel.setToolTip("Index courant / nombre total d'images dans la trajectoire")

        posRow = QHBoxLayout()
        posRow.addWidget(posLabelLeft)
        posRow.addWidget(self._sliderPosition, 1)
        posRow.addWidget(self._posLabel)
        posRow.setSpacing(8)
        self.addLayout(posRow)

        # callbacks click
        self._ieButton.clicked.connect(self.incExposure)
        self._deButton.clicked.connect(self.decExposure)
        self._ccButton.clicked.connect(self.setColor)
        self._sliderPosition.valueChanged.connect(self.sliderValueChanged)
        # double-clic sur le label d'exposition = reset a 0 EV
        self._exposureValueLabel.mouseDoubleClickEvent = lambda e: self._resetExposure()

    def _updateExposureLabel(self):
        """formatte +X.XX EV avec unite"""
        self._exposureValueLabel.setText("{:+.2f} EV".format(self._exposure))

    def incExposure(self):
        self._exposure = min(self._exposure + self._step, self._max)
        self._updateExposureLabel()
        self._controller._event(self, [1, self._exposure])

    def decExposure(self):
        self._exposure = max(self._exposure - self._step, -self._max)
        self._updateExposureLabel()
        self._controller._event(self, [-1, self._exposure])

    def _resetExposure(self):
        """double-clic sur le label : remet a 0 EV"""
        self._exposure = 0.0
        self._updateExposureLabel()
        self._controller._event(self, [1, self._exposure])

    def setColor(self):
        # ouvre le picker natif Qt avec la couleur actuelle pre-selectionnee
        current_rgb = self._controller._scene._npColorRGB

        color = QColorDialog.getColor(
            QColor.fromRgbF(current_rgb[0], current_rgb[1], current_rgb[2]),
            self.parentWidget() if self.parentWidget() else None,
            "Select Light Color"
        )

        if color.isValid():
            new_color = np.array([color.redF(), color.greenF(), color.blueF()])
            self.updatePreview(new_color)
            self._controller._event(self, [2, new_color])

    def updatePreview(self, rgb_array):
        r_int = int(rgb_array[0] * 255)
        g_int = int(rgb_array[1] * 255)
        b_int = int(rgb_array[2] * 255)
        self._colorPreview.setStyleSheet(f"background-color: rgb({r_int}, {g_int}, {b_int}); border: 1px solid #aaa; border-radius: 3px;")

    def sliderValueChanged(self, value):
        self._posLabel.setText(f"{value} / {self._maxPos}")
        self._controller._event(self, [0, value])

# ----------------------------------------------------------------------------------
class CSQAEControlLayout(QHBoxLayout):

    def __init__(self, controller, uiAEonIMG=None, uiAEoffIMG=None, stepE=0.2, maxE=5):

        super().__init__()

        # controller
        self._controller = controller

        # control of Exposure
        self._Ytarget = 0.5
        self._step = stepE
        self._max = maxE
        self._exposureON = 0.0
        self._exposureOFF = 0.0
        self._on_off = True

        # manage default Qicon
        if uiAEonIMG is None:
            uiAEonIMG = colorStudioUIBuilder.CSUIBuilder.uiAEonIMG
        if uiAEoffIMG is None:
            uiAEoffIMG = colorStudioUIBuilder.CSUIBuilder.uiAEoffIMG

        # bouton on/off de l'auto-exposure
        self._aeButton = CSQIMGSwitchButton(uiAEonIMG, uiAEoffIMG, (28, 28), name="switch AE")
        self._aeButton.setToolTip(
            "Active / desactive l'exposition automatique\n"
            "Cible : luminance moyenne = 0.5"
        )

        # boutons EV +/-
        self._ieButton = QPushButton("EV +")
        self._deButton = QPushButton("EV -")
        self._ieButton.setMinimumWidth(60)
        self._deButton.setMinimumWidth(60)
        self._ieButton.setToolTip(f"Augmenter l'exposition de {stepE:.1f} EV")
        self._deButton.setToolTip(f"Diminuer l'exposition de {stepE:.1f} EV")

        # label de la valeur d'exposition courante (avec unite + double-clic reset)
        self._exposureValueLabel = QLabel("+0.00 EV")
        self._exposureValueLabel.setMinimumWidth(60)
        self._exposureValueLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._exposureValueLabel.setObjectName("exposureLabel")
        self._exposureValueLabel.setToolTip(
            "Exposition supplementaire en EV (double-clic pour reset a 0)"
        )
        self._exposureValueLabel.mouseDoubleClickEvent = lambda e: self._resetExposure()

        # add button to layout
        self.addWidget(self._aeButton)
        self.addWidget(self._deButton)
        self.addWidget(self._exposureValueLabel)
        self.addWidget(self._ieButton)
        self.addStretch(1)  # boutons a gauche, pas etires
        self.setSpacing(10)

        # set onClick callback
        self._aeButton.clicked.connect(self.switch_on_off)
        self._ieButton.clicked.connect(self.incExposure)
        self._deButton.clicked.connect(self.decExposure)

    def switch_on_off(self):
        self._on_off = not self._on_off
        # update exposure value according on/off
        if self._on_off:
            exposure = self._exposureON
        else:
            exposure = self._exposureOFF
        self._exposureValueLabel.setText("{:+.2f} EV".format(exposure))

        # send event to controller
        self._controller._event(self, [0, self._on_off])

    def incExposure(self):
        if self._on_off:
            # autoExposure on
            self._exposureON = self._exposureON + self._step
            if self._exposureON > self._max:
                self._exposureON = self._max
            exposure = self._exposureON
            self._exposureValueLabel.setText("{:+.2f} EV".format(exposure))
            self._controller._event(self, [1, exposure])
        else:
            # autoExposure off
            self._exposureOFF = self._exposureOFF + self._step
            if self._exposureOFF > self._max:
                self._exposureOFF = self._max
            exposure = self._exposureOFF
            self._exposureValueLabel.setText("{:+.2f} EV".format(exposure))
            self._controller._event(self, [1, exposure])

    def decExposure(self):
        if self._on_off:
            # autoExposure on
            self._exposureON = self._exposureON - self._step
            if self._exposureON < -self._max:
                self._exposureON = -self._max
            exposure = self._exposureON
            self._exposureValueLabel.setText("{:+.2f} EV".format(exposure))
            self._controller._event(self, [-1, exposure])
        else:
            # autoExposure off
            self._exposureOFF = self._exposureOFF - self._step
            if self._exposureOFF < -self._max:
                self._exposureOFF = -self._max
            exposure = self._exposureOFF
            self._exposureValueLabel.setText("{:+.2f} EV".format(exposure))
            self._controller._event(self, [-1, exposure])

    def _resetExposure(self):
        """double-clic sur le label : remet a 0 EV (variante on/off correcte)"""
        if self._on_off:
            self._exposureON = 0.0
        else:
            self._exposureOFF = 0.0
        self._exposureValueLabel.setText("+0.00 EV")
        self._controller._event(self, [1, 0.0])

# ----------------------------------------------------------------------------------
class CSDisplayWidget(QWidget):
    """
    Widget d'affichage de l'image rendue.
    L'image est toujours scaled au widget en gardant le ratio d'aspect.
    Stocke le pixmap original pour pouvoir le rescaler lors d'un resize sans
    perdre la qualite et sans declencher de boucle de feedback de taille.
    """
    def __init__(self, controller, title=None):
        super().__init__()
        self._controller = controller
        if title:
            self.setWindowTitle(title)

        # IMPORTANT : on doit pouvoir SHRINKER le widget. Sans cette politique,
        # QLabel veut etre au moins de la taille de son pixmap -> bouble de feedback
        # entre _update() et le layout (l'image zoome a chaque render).
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(1, 1)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self._label = QLabel(self)
        self._label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        # politique Ignored = le label ne propage pas son sizeHint au layout.
        # C'est le widget parent qui decide sa taille, le label suit.
        self._label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self._label.setMinimumSize(1, 1)
        main_layout.addWidget(self._label)

        # cache du pixmap original (non scaled) pour pouvoir le rescaler dynamiquement
        self._originalPixmap = None

        # pixmap initial : fond gris fonce
        w, h = 800, 600
        try:
            w, h = colorStudioUIBuilder.CSUIBuilder.template['uiRenderWidget_size']
        except (KeyError, TypeError):
            pass
        img = (np.ones((h, w, 3)) * 30).astype(np.uint8)
        height, width, channel = img.shape
        bytesPerLine = channel * width
        qImg = QImage(img.tobytes(), width, height, bytesPerLine, QImage.Format.Format_RGB888)
        self._originalPixmap = QPixmap.fromImage(qImg)
        self._refreshScaledPixmap()

    def _refreshScaledPixmap(self):
        """re-scale le pixmap original a la taille courante du widget."""
        if self._originalPixmap is None:
            return
        target_size = self.size()
        if target_size.width() < 1 or target_size.height() < 1:
            return
        scaled = self._originalPixmap.scaled(
            target_size,
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation,
        )
        self._label.setPixmap(scaled)

    def _update(self, imgDouble):
        """met a jour l'image affichee a partir d'une numpy array RGB float [0,1]."""
        if imgDouble.max() > 1.0:
            imgDisplay = colorStudioUtils.toneMap(imgDouble)
        else:
            imgDisplay = imgDouble
        img = (imgDisplay * 255).astype(np.uint8)
        height, width, channel = img.shape
        bytesPerLine = channel * width
        qImg = QImage(img.tobytes(), width, height, bytesPerLine, QImage.Format.Format_RGB888)
        self._originalPixmap = QPixmap.fromImage(qImg)
        # IMPORTANT : on garde l'original (haute resolution) et on le re-scale a la taille
        # courante du widget. Sans ca, le widget zoomait progressivement parce que le
        # label adoptait la taille du pixmap (qui etait deja scaled) -> feedback layout.
        self._refreshScaledPixmap()

    def resizeEvent(self, event):
        # re-scale le pixmap quand la fenetre change de taille (drag du splitter)
        super().resizeEvent(event)
        self._refreshScaledPixmap()

# ----------------------------------------------------------------------------------
class CSQSaturationLayout(QVBoxLayout):

    def __init__(self, controller, range=100):
        """
        widget that controls saturation
        @params:
            controller  - Required                                  (CSSaturationController)
            range       - Optional  :  range [-range,range]         (Float)
        """
        super().__init__()
        # controller
        self._controller = controller

        # control of saturation
        self._linearSaturation = 0.0
        self._gammaSaturation = 0.0
        self._range = range

        # slider lineaire avec label valeur a droite
        self._linearSaturationValueLabel = QLabel("0")
        self._linearSaturationValueLabel.setMinimumWidth(40)
        self._linearSaturationValueLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._linearSaturationValueLabel.setObjectName("exposureLabel")
        self._linearSaturationValueLabel.setToolTip(
            "Saturation lineaire (-100 = noir et blanc, 0 = original, +100 = sature)\n"
            "Double-clic pour reset a 0"
        )
        self._linearSaturationValueLabel.mouseDoubleClickEvent = \
            lambda e: self._resetLinear()

        self._sliderLinearSaturation = QSlider(QtCore.Qt.Orientation.Horizontal)
        self._sliderLinearSaturation.setRange(0, 100)
        self._sliderLinearSaturation.setValue(50)
        self._sliderLinearSaturation.setToolTip(
            "Saturation lineaire (-100 = N&B, 0 = original, +100 = sature)"
        )

        linearRow = QHBoxLayout()
        linearLabel = QLabel("Lineaire")
        linearLabel.setMinimumWidth(60)
        linearRow.addWidget(linearLabel)
        linearRow.addWidget(self._sliderLinearSaturation, 1)
        linearRow.addWidget(self._linearSaturationValueLabel)

        # slider gamma avec label valeur
        self._gammaSaturationValueLabel = QLabel("0")
        self._gammaSaturationValueLabel.setMinimumWidth(40)
        self._gammaSaturationValueLabel.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._gammaSaturationValueLabel.setObjectName("exposureLabel")
        self._gammaSaturationValueLabel.setToolTip(
            "Saturation gamma / vibrance (-100 = N&B doux, 0 = original, +100 = vibrance)\n"
            "Double-clic pour reset a 0"
        )
        self._gammaSaturationValueLabel.mouseDoubleClickEvent = \
            lambda e: self._resetGamma()

        self._sliderGammaSaturation = QSlider(QtCore.Qt.Orientation.Horizontal)
        self._sliderGammaSaturation.setRange(0, 100)
        self._sliderGammaSaturation.setValue(50)
        self._sliderGammaSaturation.setToolTip(
            "Saturation gamma / vibrance (non lineaire, plus douce que la lineaire)"
        )

        gammaRow = QHBoxLayout()
        gammaLabel = QLabel("Vibrance")
        gammaLabel.setMinimumWidth(60)
        gammaRow.addWidget(gammaLabel)
        gammaRow.addWidget(self._sliderGammaSaturation, 1)
        gammaRow.addWidget(self._gammaSaturationValueLabel)

        # ajout au layout
        self.addLayout(linearRow)
        self.addLayout(gammaRow)

        # slider
        self._sliderLinearSaturation.valueChanged.connect(self.sliderLinearSaturationValueChanged)
        self._sliderGammaSaturation.valueChanged.connect(self.sliderGammaSaturationValueChanged)

    def sliderLinearSaturationValueChanged(self, value):
        self._linearSaturation = (2 * value / 100.0 - 1.0) * self._range
        self._linearSaturationValueLabel.setText("{:+.0f}".format(self._linearSaturation))
        self._controller._event(self, [0, self._linearSaturation])

    def sliderGammaSaturationValueChanged(self, value):
        self._gammaSaturation = (2 * value / 100.0 - 1.0) * self._range
        self._gammaSaturationValueLabel.setText("{:+.0f}".format(self._gammaSaturation))
        self._controller._event(self, [1, self._gammaSaturation])

    def _resetLinear(self):
        """double-clic sur le label : reset slider a 50 (= valeur 0)"""
        self._sliderLinearSaturation.setValue(50)

    def _resetGamma(self):
        """double-clic sur le label : reset slider a 50 (= valeur 0)"""
        self._sliderGammaSaturation.setValue(50)

# ----------------------------------------------------------------------------------
class CSQHDRControlLayout(QHBoxLayout):
    """
    case a cocher "HDR mode" : quand elle est cochee, la scene ne clippe plus les
    valeurs a 1.0 lors du render et le widget d'affichage applique un tone mapping.
    """
    def __init__(self, scene, displayWidgets):
        super().__init__()
        self._scene = scene
        self._displayWidgets = displayWidgets

        # case a cocher + label explicatif
        self._checkBox = QCheckBox("Activer le mode HDR")
        self._checkBox.setChecked(bool(scene._hdr))
        self._checkBox.setToolTip(
            "Quand active :\n"
            "  - les valeurs RGB ne sont plus clippees a 1.0\n"
            "  - l'affichage applique un tone mapping de Reinhard (x / (1+x))\n"
            "Raccourci : Ctrl+H"
        )
        self.addWidget(self._checkBox)
        self.addStretch(1)

        # callback
        self._checkBox.stateChanged.connect(self._onToggle)

    def _onToggle(self, state):
        # mise a jour du flag HDR de la scene
        self._scene._hdr = self._checkBox.isChecked()
        # re-render + refresh des widgets d'affichage
        img = self._scene.render()
        for w in self._displayWidgets:
            w._update(img)
