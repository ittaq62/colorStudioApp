# -*- coding: utf-8 -*-
"""
Color Studio - Rémi Cozot 2019
----------------------------------
new version of
Color Studio - Rémi Cozot 2019
"""

# import(s)
# ----------------------------------------------------------------------------------

import skimage

from PyQt6.QtWidgets import (
    QLabel, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QSplitter, QScrollArea, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, QFile, QTextStream
#from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QHBoxLayout, QSlider  # plus utilises dans ce fichier
from PyQt6.QtGui import QIcon
#from PyQt6.QtGui import QPixmap, QImage  # plus utilises dans ce fichier
#from PyQt6 import QtCore  # plus utilise dans ce fichier

from colorstudio import model as colorStudioModel
from colorstudio import widget as colorStudioWidget
from colorstudio import controller as colorStudioController
#from colorstudio import utils as colorStudioUtils  # plus utilise dans ce fichier

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
        # color wheel widget
        'uiColorWheelWidget_pos': (1440, 540),
        'uiColorWheelWidget_size': (480, 480),
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
        # color wheel widget
        'uiColorWheelWidget_pos': (3000 - 480, 540 + 60),
        'uiColorWheelWidget_size': (480, 480),
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
        if pathUIimg is None:
            pathUIimg = './colorstudio/icons/'
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
    def __init__(self, title="Color Studio 2026"):
        super().__init__()
        self.setWindowTitle(title)
        
        # Determine a sensible size based on screen
        s_width, s_height = colorStudioWidget.getScreenSize()
        w = min(1400, int(s_width * 0.9))
        h = min(800, int(s_height * 0.9))
        self.resize(w, h)
        
        self.apply_style()

    def apply_style(self):
        style_file = QFile("./colorstudio/styles.qss")
        if style_file.open(QFile.OpenModeFlag.ReadOnly | QFile.OpenModeFlag.Text):
            stream = QTextStream(style_file)
            self.setStyleSheet(stream.readAll())

# ----------------------------------------------------------------------------------
class CSUIAllBuilder(CSUIBuilder):
    def __init__(self, lightsScene):
        # (0) load qIcon images
        CSUIBuilder.uiLoadIcon()

        # (1) Main Window Init
        self.mainWindow = CSMainWindow("Color Studio — Pro Edition")
        
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
        self._color3DWidget.setMinimumHeight(100) # Reduced to avoid pushing bottom
        
        # Color Wheel
        self._colorWheelWidget = colorStudioWidget.CSDisplayColorWheel(None, 300)
        self._colorWheelWidget.setMinimumHeight(100) # Reduced to avoid pushing bottom
        
        # Controllers
        colorWheelController = colorStudioController.CSColorWheelController(
            lightsScene, None, [self._renderWidget, self._color3DWidget], self._colorWheelWidget)
        self._colorWheelWidget._controller = colorWheelController

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
            
            lightController = colorStudioController.CSLightController(lightsScene, light, [self._renderWidget, self._color3DWidget])
            lightController._colorWheelController = colorWheelController
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
        bottom_layout.addWidget(self._colorWheelWidget)
        
        right_splitter.addWidget(bottom_analytics)
        
        # Initial proportions
        right_splitter.setStretchFactor(0, 10)
        right_splitter.setStretchFactor(1, 1)
        right_splitter.setSizes([600, 200])

        # Main Splitter Assembly
        self.splitter.addWidget(sidebar)
        self.splitter.addWidget(right_splitter)
        self.splitter.setStretchFactor(1, 1)

        # Show
        self.mainWindow.show()

        # (end) init render
        self._renderWidget._update(lightsScene.render())
