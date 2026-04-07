# -*- coding: utf-8 -*-
"""
Color Studio - Rémi Cozot 2019
----------------------------------
new version of
Color Studio - Rémi Cozot 2019
"""
# ----------------------------------------------------------------------------------
# main changes
# ----------------------------------------------------------------------------------
# GUI lib: pygame to pyqt6
# include 3d color point cloud (modernGL)
# ----------------------------------------------------------------------------------

# import(s)
# ----------------------------------------------------------------------------------
import sys

from PyQt6.QtWidgets import QApplication, QFileDialog

from colorstudio import model as colorStudioModel
from colorstudio import widget as colorStudioWidget
from colorstudio import ui_builder as colorStudioUIBuilder

# ----------------------------------------------------------------------------------
print("ColorStudio - Rémi Cozot - 2019")
print("-------------------------------")
screenX, screenY = colorStudioWidget.getScreenSize()
print("screen resolution: ", screenX, "x", screenY)
colorStudioUIBuilder.CSUIBuilder.setTemplate(screenX, screenY)

# Qt init
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

# select input file name
# defaut : scene legere qui n'utilise que light01_* (les seuls images presentes dans le repo)
# l'ancien defaut xml-2019-6-7-22-47-1.xml referencait light02_* qui manque -> crash si on annule la dialog
defaultFilename = "./xml-postProcess-test.xml"
inputFilename, _ = QFileDialog.getOpenFileName(
    None,
    "Color Studio — select light-setup file",
    "",
    "XML files (*.xml)"
)
print("ColorStudio: input file>", inputFilename)

if not inputFilename:
    inputFilename = defaultFilename
    print("ColorStudio: input file>", inputFilename)

# scene object
lightsScene = colorStudioModel.Scene()
# load scene from xml
lightsScene.fromXML(inputFilename, colorStudioUIBuilder.CSUIBuilder.template['scale'])
# print scene
lightsScene.print()

# build GUI according to scene
ui = colorStudioUIBuilder.CSUIAllBuilder(lightsScene)

# run app for event management
app.exec()
