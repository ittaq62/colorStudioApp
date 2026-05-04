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

from colorstudio.utils import loadImage, printProgressBar, image2Ymean

import math
import numpy as np
import skimage

import xml.dom.minidom as miniXml
import json

# ----------------------------------------------------------------------------------
# Class(es)
# ----------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------
#  IMAGES
# ----------------------------------------------------------------------------------
class Images:
    """
    set of images
    """
    def __init__(self, pathImage, baseImageName, extImageName, nbImage, nbDigit, load=True, scale=0.5):

        # path to images data
        self._pathImage = pathImage
        self._baseImageName = baseImageName
        self._extImageName = extImageName
        self._nbImage = nbImage
        self._nbDigit = nbDigit
        # list of images
        self._images = []

        if load:
            self.loadImages(scale)

    def loadImages(self, scale=0.5):
        for i in range(self._nbImage):
            printProgressBar(i, self._nbImage - 1, prefix='', suffix='', decimals=1, length=50, fill='#')

            # create formated filename
            iStr = str(i).zfill(self._nbDigit)
            name = self._pathImage + self._baseImageName + iStr + self._extImageName

            # load image
            img = loadImage(name, scale)

            self._images.append(img)

    def clear(self):
        self._images.clear()

    def len(self):
        return self._nbImage

# ----------------------------------------------------------------------------------
#  LIGHT
# ----------------------------------------------------------------------------------
class Light:
    # class attribute
    lightNb = 0

    def __init__(self, name=None):
        if not name:
            self._name = "Light" + str(Light.lightNb)
        else:
            self._name = name

        Light.lightNb = Light.lightNb + 1

        # light color
        self._npColorRGB = np.asarray([1.0, 1.0, 1.0])

        # exposure
        self._exposure = 0

        # light orientation and idx
        self._imageIdx = 0
        self._maxIdx = 0

        # ref to render images
        self._ImagesArray = None

        # optimization
        self._needUpdate = False
        self._firstUpdate = True

        self._currentImage = None

    def setImagesArray(self, imgArray):
        self._ImagesArray = imgArray
        self._maxIdx = self._ImagesArray.len()

    def clear(self):
        self._ImagesArray.clear()

    def setExposure(self, expValue):
        self._exposure = expValue
        self._needUpdate = True

    def setColor(self, color):
        self._npColorRGB = color
        self._needUpdate = True

    def setImageIdx(self, idx):
        self._imageIdx = idx
        self._needUpdate = True

    def render(self):

        if self._firstUpdate or self._needUpdate:

            # get current active image
            img = self._ImagesArray._images[self._imageIdx]

            # color filter + exposure en une seule multiplication broadcast
            # numpy diffuse (3,) sur (h, w, 3) -> 1 seule allocation au lieu de 3
            factor = self._npColorRGB * math.pow(2, self._exposure)
            imgOut = img * factor

            self._currentImage = imgOut

            self._firstUpdate = False
            self._needUpdate = False
        else:
            # no change, just return current image
            imgOut = self._currentImage

        return imgOut

    def print(self):
        print("[ Light:", self._name, ",",
              "imgIdx:", self._imageIdx, "/", self._maxIdx, ",",
              "exposure:", self._exposure,
              "color:", "[ r:", self._npColorRGB[0], ", g:", self._npColorRGB[1], ",b:", self._npColorRGB[2], "]",
              "]")

    def toXML(self):

        lightMark = "LIGHT"
        inputFileMark = "INPUTFILE"
        idxPosMark = "IDXPOS"
        expMark = "EXP"
        colorMark = "COLOR"
        rMark = "R"
        gMark = "G"
        bMark = "B"

        outString = "<" + lightMark + " name=\"" + self._name + "\"" + ">" + "\n" + \
            "<" + inputFileMark + \
            " ext=\"" + \
            self._ImagesArray._extImageName + \
            "\" min=\"0\" max=\"" + str(self._ImagesArray._nbImage) + "\" " + \
            " digit=\"" + str(self._ImagesArray._nbDigit) + "\" >" + \
            self._ImagesArray._pathImage + self._ImagesArray._baseImageName + \
            "</" + inputFileMark + ">" + "\n" + \
            "<" + idxPosMark + ">" + str(self._imageIdx) + "</" + idxPosMark + ">" + "\n" + \
            "<" + expMark + ">" + str(self._exposure) + "</" + expMark + ">" + "\n" + \
            "<" + colorMark + " format=\"float\"" + ">" + "\n" + \
            "<" + rMark + ">" + str(self._npColorRGB[0]) + "</" + rMark + ">" + "\n" + \
            "<" + gMark + ">" + str(self._npColorRGB[1]) + "</" + gMark + ">" + "\n" + \
            "<" + bMark + ">" + str(self._npColorRGB[2]) + "</" + bMark + ">" + "\n" + \
            "</" + colorMark + ">" + "\n" + \
            "</" + lightMark + ">"
        return outString

    def toDict(self):
        """
        returns a dictionary representation of the light
        """
        return {
            "name": self._name,
            "inputFile": {
                "path": self._ImagesArray._pathImage + self._ImagesArray._baseImageName,
                "ext": self._ImagesArray._extImageName,
                "min": 0,
                "max": self._ImagesArray._nbImage,
                "digit": self._ImagesArray._nbDigit
            },
            "idxPos": self._imageIdx,
            "exposure": self._exposure,
            "color": self._npColorRGB.tolist()
        }

# ----------------------------------------------------------------------------------
#  SCENE
# ----------------------------------------------------------------------------------
class Scene:
    def __init__(self, hdr=False):
        self._lights = []           # set of lights
        self._postProcesses = []    # set of postprocessing
        self._hdr = hdr

    def addLight(self, light):
        self._lights.append(light)

    def addPostProcess(self, postProcess):
        self._postProcesses.append(postProcess)

    def clear(self):
        self._lights.clear()
        self._postProcesses.clear()

    def getLightByName(self, name):
        returnLight = None
        for light in self._lights:
            if light._name == name:
                returnLight = light
                break
        return returnLight

    def render(self):
        # init avec une copie du premier light pour eviter np.zeros + une addition
        # .copy() pour ne pas modifier le cache _currentImage du light
        imgOut = self._lights[0].render().copy()

        # ajout des autres lights en place (evite de creer une nouvelle array a chaque iter)
        for light in self._lights[1:]:
            imgOut += light.render()

        # applyPostProcess
        for pp in self._postProcesses:
            imgOut = pp.postProcess(imgOut)

        if not self._hdr:
            # clipping values en place
            np.clip(imgOut, 0.0, 1.0, out=imgOut)
        return imgOut

    def toXML(self):
        # create XML string
        # <LIGHTS>
        lsMark = "LIGHTS"
        outString = "<" + lsMark + ">" + "\n"
        for l in self._lights:
            outString = outString + l.toXML() + "\n"
        # add </LIGHTS>
        outString = outString + "</" + lsMark + ">" + '\n'
        return outString

    def toDict(self):
        """
        returns a dictionary representation of the scene
        """
        return {
            "hdr": self._hdr,
            "lights": [l.toDict() for l in self._lights]
        }

    def toJSON(self, filename):
        """
        save the scene to a JSON file
        """
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.toDict(), f, indent=4)

    def fromJSON(self, filename, scale=0.5):
        """
        load the scene from a JSON file
        """
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._hdr = data.get('hdr', False)
        
        # dict {'filename':[light]} to avoid multiple rendered-image file loads
        filenameLight = {}

        for lData in data.get('lights', []):
            light = Light(name=lData['name'])
            light.setExposure(lData['exposure'])
            light.setColor(np.asarray(lData['color']))
            light.setImageIdx(lData['idxPos'])
            
            inf = lData['inputFile']
            imagesFile = inf['path']
            images = Images('', imagesFile, inf['ext'], inf['max'], inf['digit'], load=False)
            light.setImagesArray(images)
            
            self._lights.append(light)
            
            if imagesFile in filenameLight:
                filenameLight[imagesFile].append(light)
            else:
                filenameLight[imagesFile] = [light]

        # rendered-image files management (same logic as in fromXML)
        for k in filenameLight.keys():
            lights = filenameLight[k]
            firstLight = lights[0]
            imgs = Images(
                firstLight._ImagesArray._pathImage,
                firstLight._ImagesArray._baseImageName,
                firstLight._ImagesArray._extImageName,
                firstLight._ImagesArray._nbImage,
                firstLight._ImagesArray._nbDigit,
                load=True, scale=scale)

            for li in lights:
                li.setImagesArray(imgs)

    def fromXML(self, xmlFile, scale=0.5):
        # parse XML file
        xdoc = miniXml.parse(xmlFile)

        # mode HDR : attribut optionnel sur la racine, ex: <LIGHTSETTUP hdr="true">
        root = xdoc.documentElement
        if root.hasAttribute('hdr'):
            self._hdr = root.getAttribute('hdr').lower() == 'true'

        # recover <LIGHT> tag
        xLights = xdoc.getElementsByTagName('LIGHT')

        # dict {'filename':[light]} to avoid multiple rendered-image file loads
        filenameLight = {}

        # for each light TAG
        for xl in xLights:
            # recover light name
            lightName = xl.attributes['name'].value

            # input file : <INPUTFILE ext=".jpg" min="0" max="100"  digit="4" >./images/set02/arnold_pass</INPUTFILE>
            inputNode = xl.getElementsByTagName('INPUTFILE')[0]
            ext = inputNode.attributes['ext'].value
            nbMin = int(inputNode.attributes['min'].value)
            nbMax = int(inputNode.attributes['max'].value)
            digit = int(inputNode.attributes['digit'].value)
            imagesFile = inputNode.firstChild.data

            # index light position : <IDXPOS>36</IDXPOS>
            idxPos = int(xl.getElementsByTagName('IDXPOS')[0].firstChild.data)

            # exposure : <EXP>0.0</EXP>
            exp = float(xl.getElementsByTagName('EXP')[0].firstChild.data)

            # color : <COLOR format="float"> <R>1.0</R> <G>1.0</G> <B>1.0</B> </COLOR>
            color = xl.getElementsByTagName('COLOR')[0]
            rr = float(color.getElementsByTagName('R')[0].firstChild.data)
            gg = float(color.getElementsByTagName('G')[0].firstChild.data)
            bb = float(color.getElementsByTagName('B')[0].firstChild.data)

            # create light
            light = Light(name=lightName)
            light.setExposure(exp)
            light.setColor(np.asarray([rr, gg, bb]))
            light.setImageIdx(idxPos)
            images = Images('', imagesFile, ext, nbMax, digit, load=False)
            light.setImagesArray(images)

            # add current light to allLights
            self._lights.append(light)

            # filenameLight
            if imagesFile in filenameLight:
                filenameLight[imagesFile].append(light)
            else:
                filenameLight.update({imagesFile: [light]})

        # recover <POSTPROCESS> tag
        xPosts = xdoc.getElementsByTagName('POSTPROCESS')

        # explore postprocess (in order they will be applyed in the same order (!))
        for xp in xPosts:
            children = xp.childNodes  # all children
            for child in children:
                childNodeIsElement = (child.nodeType == miniXml.Node.ELEMENT_NODE)
                if childNodeIsElement:
                    # child is ELEMENT
                    if child.tagName == 'CHROMA':
                        # <CHROMA type="AWB"|"SATURATION">
                        # get type attribute value
                        typeString = child.attributes['type'].value
                        if typeString == 'AWB':
                            pass
                        if typeString == 'saturation':
                            pass

        # rendered-image files management
        # just load once rendered-image files
        for k in filenameLight.keys():
            # lights that uses filenameLight
            lights = filenameLight[k]
            firstLight = lights[0]  # at least one light uses this rendered-images file set
            # load images
            imgs = Images(
                firstLight._ImagesArray._pathImage,
                firstLight._ImagesArray._baseImageName,
                firstLight._ImagesArray._extImageName,
                firstLight._ImagesArray._nbImage,
                firstLight._ImagesArray._nbDigit,
                load=True, scale=scale)

            # light share rendered-image files
            for li in lights:
                li.setImagesArray(imgs)

    def print(self):
        print(" -------- LIGHTS -------- ")
        for l in self._lights:
            l.print()

# ----------------------------------------------------------------------------------
#  POST PROCESS
# ----------------------------------------------------------------------------------
class PostProcess:

    def __init__(self):
        pass

    def postProcess(self, img):
        return img

# ----------------------------------------------------------------------------------
#  POST PROCESS : SATURATION -VIBRANCE
# ----------------------------------------------------------------------------------
class Saturation(PostProcess):

    def __init__(self, linearSat=0, gammaSat=0):
        self._linearSaturation = linearSat  # in [-100,100]
        self._gammaSaturation = gammaSat    # in [-100,100]
        self._saturationRange = 1.0

    def setLinearSaturation(self, saturation):
        self._linearSaturation = saturation

    def setGammaSaturation(self, vibrance):
        self._gammaSaturation = vibrance

    def postProcess(self, img):
        if self._linearSaturation != 0:
            # linearSat to u in [-1,1]
            u = self._linearSaturation / 100
            # convert to hsv
            imgHSV = skimage.color.rgb2hsv(img)
            satChannel = imgHSV[:, :, 1]
            one = np.ones(satChannel.shape)
            if u > 0.0:
                new_satChannel = (1 - u) * satChannel + u * self._saturationRange * one
            else:
                new_satChannel = (1 + u) * satChannel
            imgHSV[:, :, 1] = new_satChannel[:, :]
            # back to rgb
            img = skimage.color.hsv2rgb(imgHSV)

        if self._gammaSaturation != 0:
            # convert to hsv
            imgHSV = skimage.color.rgb2hsv(img)
            satChannel = imgHSV[:, :, 1]
            if self._gammaSaturation > 0.0:
                # gamma value
                gamma = 1 + (self._gammaSaturation / 25)
                new_satChannel = np.power(satChannel, 1 / gamma)
            elif self._gammaSaturation < 0.0:
                # gamma value
                gamma = 1 + (-self._gammaSaturation / 25)
                new_satChannel = np.power(satChannel, gamma)
            imgHSV[:, :, 1] = new_satChannel[:, :]
            # back to rgb
            img = skimage.color.hsv2rgb(imgHSV)
        imgOut = img

        return imgOut

# ----------------------------------------------------------------------------------
#  POST PROCESS : AE_YMEAN - Automatic Exposure Ymean-> Ytarget
# ----------------------------------------------------------------------------------
class AE_Ymean(PostProcess):

    def __init__(self, Ytarget=0.5, exposure=0.0):
        self._Ytarget = Ytarget
        self._exposureON = exposure
        self._exposureOFF = exposure
        self._on_off = True

    def setOnOff(self, on_off):
        self._on_off = on_off

    def setExposure(self, exposureValue):
        if self._on_off:
            self._exposureON = exposureValue
        else:
            self._exposureOFF = exposureValue

    def postProcess(self, img):
        if self._on_off:
            # compute mean Y (Luminance)
            ymeanb = image2Ymean(img)
            # protection division par zero : une image presque noire donnait
            # ymeanb ~ 0 et faisait exploser le gain (ou un NaN)
            if ymeanb < 1e-6:
                ymeanb = 1e-6
            imgOut = img * (self._Ytarget / ymeanb) * math.pow(2, self._exposureON)
        else:
            imgOut = img * math.pow(2, self._exposureOFF)

        return imgOut

# ----------------------------------------------------------------------------------
class PPClip(PostProcess):

    def __init__(self, minValue=0.0, maxValue=1.0):
        self._minValue = minValue
        self._maxValue = maxValue

    def postProcess(self, img):
        return np.clip(img, self._minValue, self._maxValue)
