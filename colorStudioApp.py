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

import easygui

from PyQt6.QtWidgets import QApplication

import colorStudioModel
import colorStudioWidget
import colorStudioUIBuilder

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
defaultFilename = "./xml-2019-6-7-22-47-1.xml"
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
