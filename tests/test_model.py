# -*- coding: utf-8 -*-
"""
Tests pour colorstudio.model
"""
import os
import tempfile
import unittest
import numpy as np

from colorstudio import model


class TestPPClip(unittest.TestCase):
    """tests du post-process de clipping"""

    def test_clip_default_range(self):
        # par defaut clip entre 0 et 1
        clip = model.PPClip()
        img = np.array([[[-0.5, 0.5, 1.5]]])
        out = clip.postProcess(img)
        self.assertEqual(out.flatten().tolist(), [0.0, 0.5, 1.0])

    def test_clip_custom_range(self):
        clip = model.PPClip(minValue=-1.0, maxValue=2.0)
        img = np.array([[[-2.0, 0.0, 5.0]]])
        out = clip.postProcess(img)
        self.assertEqual(out.flatten().tolist(), [-1.0, 0.0, 2.0])


class TestLight(unittest.TestCase):
    """tests de la classe Light"""

    def setUp(self):
        # reset le compteur statique entre chaque test
        model.Light.lightNb = 0

    def test_default_name(self):
        l = model.Light()
        self.assertEqual(l._name, "Light0")

    def test_custom_name(self):
        l = model.Light(name="MaLumiere")
        self.assertEqual(l._name, "MaLumiere")

    def test_set_color_marks_update(self):
        l = model.Light()
        l._needUpdate = False
        l.setColor(np.array([0.5, 0.5, 0.5]))
        self.assertTrue(l._needUpdate)

    def test_render_applies_color_and_exposure(self):
        # une lumiere blanche * 0.5 vert et exposure +1 (donc x2)
        # sur une image toute blanche -> R=1.0, G=1.0, B=0
        l = model.Light(name="Test")
        l.setColor(np.array([0.5, 0.5, 0.0]))
        l.setExposure(1.0)  # 2^1 = x2

        # fake images array
        class FakeImgs:
            _images = [np.ones((2, 2, 3))]
            def len(self):
                return 1

        l.setImagesArray(FakeImgs())
        out = l.render()

        self.assertEqual(out.shape, (2, 2, 3))
        self.assertAlmostEqual(out[..., 0].mean(), 1.0)  # 0.5 * 2
        self.assertAlmostEqual(out[..., 1].mean(), 1.0)
        self.assertAlmostEqual(out[..., 2].mean(), 0.0)


class TestSaturation(unittest.TestCase):
    """test du post-process de saturation"""

    def test_no_op_when_zero(self):
        # quand les deux saturations sont a 0 l'image est inchangee
        sat = model.Saturation(linearSat=0, gammaSat=0)
        img = np.array([[[0.3, 0.6, 0.9]]])
        out = sat.postProcess(img)
        np.testing.assert_array_almost_equal(out, img)


class TestAEYmean(unittest.TestCase):
    """tests du post-process d'exposition automatique"""

    def test_black_image_no_crash(self):
        # bug historique : image toute noire -> Ymean = 0 -> division par zero
        # on verifie juste que le postProcess ne plante pas et retourne une image
        # au bon format (les valeurs peuvent etre clampees a 0 car img * grand = 0*grand = 0)
        ae = model.AE_Ymean(Ytarget=0.5, exposure=0.0)
        black = np.zeros((4, 4, 3), dtype=np.float64)
        out = ae.postProcess(black)
        self.assertEqual(out.shape, black.shape)
        # l'image noire reste noire apres AE (0 * nimporte quoi = 0)
        self.assertTrue(np.all(out == 0.0))

    def test_grey_image_lifted_to_ytarget(self):
        # une image grise uniforme a 0.25 avec Ytarget=0.5 doit doubler la luminance
        ae = model.AE_Ymean(Ytarget=0.5, exposure=0.0)
        grey = np.ones((4, 4, 3), dtype=np.float64) * 0.25
        out = ae.postProcess(grey)
        # Ymean d'un gris 0.25 = 0.25 (rgb2yuv conserve la luminance d'un gris)
        # donc gain = 0.5 / 0.25 = 2.0 -> out = 0.5
        self.assertAlmostEqual(out.mean(), 0.5, places=3)

    def test_off_uses_exposure_off(self):
        # quand on/off = False, on applique juste 2^exposureOFF sans passer par Ymean
        ae = model.AE_Ymean(Ytarget=0.5, exposure=1.0)
        ae.setOnOff(False)
        # setExposure en off met a jour _exposureOFF
        ae.setExposure(1.0)
        grey = np.ones((4, 4, 3), dtype=np.float64) * 0.25
        out = ae.postProcess(grey)
        # 0.25 * 2^1 = 0.5
        self.assertAlmostEqual(out.mean(), 0.5, places=3)


class TestScene(unittest.TestCase):
    """test basique de Scene"""

    def setUp(self):
        model.Light.lightNb = 0

    def test_add_light(self):
        scene = model.Scene()
        l = model.Light(name="L0")
        scene.addLight(l)
        self.assertEqual(len(scene._lights), 1)
        self.assertIs(scene.getLightByName("L0"), l)

    def test_get_light_by_name_not_found(self):
        scene = model.Scene()
        self.assertIsNone(scene.getLightByName("inconnue"))

    def test_render_empty_scene_no_crash(self):
        # une scene sans lumiere ne doit pas crasher
        scene = model.Scene()
        out = scene.render()
        self.assertEqual(len(out.shape), 3)
        self.assertTrue(np.all(out == 0.0))


class TestSceneFromXML(unittest.TestCase):
    """tests de Scene.fromXML pour le mode HDR"""

    # XML minimal : 1 light avec max="0" pour ne charger aucune image
    _XML_TEMPLATE = (
        '<?xml version="1.0"?>\n'
        '<LIGHTSETTUP{hdrAttr}>\n'
        '  <LIGHTS>\n'
        '    <LIGHT name="L0">\n'
        '      <INPUTFILE ext=".jpg" min="0" max="0" digit="4">./fake/no_</INPUTFILE>\n'
        '      <IDXPOS>0</IDXPOS>\n'
        '      <EXP>0.0</EXP>\n'
        '      <COLOR format="float"><R>1.0</R><G>1.0</G><B>1.0</B></COLOR>\n'
        '    </LIGHT>\n'
        '  </LIGHTS>\n'
        '</LIGHTSETTUP>\n'
    )

    def setUp(self):
        model.Light.lightNb = 0
        self._tmpFiles = []

    def tearDown(self):
        for p in self._tmpFiles:
            if os.path.exists(p):
                os.unlink(p)

    def _writeXml(self, hdrAttr):
        fd, path = tempfile.mkstemp(suffix=".xml")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self._XML_TEMPLATE.format(hdrAttr=hdrAttr))
        self._tmpFiles.append(path)
        return path

    def test_default_scene_is_ldr(self):
        # pas d'attribut hdr -> _hdr reste a False
        path = self._writeXml(hdrAttr="")
        scene = model.Scene()
        scene.fromXML(path)
        self.assertFalse(scene._hdr)

    def test_xml_hdr_true(self):
        # attribut hdr="true" -> _hdr passe a True
        path = self._writeXml(hdrAttr=' hdr="true"')
        scene = model.Scene()
        scene.fromXML(path)
        self.assertTrue(scene._hdr)


class TestSceneFromJSON(unittest.TestCase):
    """tests de Scene.fromJSON"""

    # JSON minimal : 1 light, pas d'images a charger (max=0)
    _JSON_LDR = '{"hdr": false, "lights": [{"name": "L0", "inputFile": {"path": "./fake/no_", "ext": ".jpg", "min": 0, "max": 0, "digit": 4}, "idxPos": 0, "exposure": 1.5, "color": [1.0, 0.5, 0.0]}]}'
    _JSON_HDR = '{"hdr": true, "lights": [{"name": "Lhdr", "inputFile": {"path": "./fake/no_", "ext": ".jpg", "min": 0, "max": 0, "digit": 4}, "idxPos": 10, "exposure": 2.0, "color": [0.8, 0.8, 1.0]}]}'

    def setUp(self):
        model.Light.lightNb = 0
        self._tmpFiles = []

    def tearDown(self):
        for p in self._tmpFiles:
            if os.path.exists(p):
                os.unlink(p)

    def _writeJson(self, content):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        self._tmpFiles.append(path)
        return path

    def test_json_ldr(self):
        # charge un JSON sans HDR, verifie les attributs de base
        path = self._writeJson(self._JSON_LDR)
        scene = model.Scene()
        scene.fromJSON(path)
        self.assertFalse(scene._hdr)
        self.assertEqual(len(scene._lights), 1)
        self.assertEqual(scene._lights[0]._name, "L0")
        self.assertAlmostEqual(scene._lights[0]._exposure, 1.5)

    def test_json_hdr(self):
        # charge un JSON avec hdr=true
        path = self._writeJson(self._JSON_HDR)
        scene = model.Scene()
        scene.fromJSON(path)
        self.assertTrue(scene._hdr)
        self.assertEqual(scene._lights[0]._name, "Lhdr")

    def test_json_light_color(self):
        # verifie que la couleur est correctement lue
        path = self._writeJson(self._JSON_LDR)
        scene = model.Scene()
        scene.fromJSON(path)
        color = scene._lights[0]._npColorRGB
        np.testing.assert_array_almost_equal(color, [1.0, 0.5, 0.0])


if __name__ == "__main__":
    unittest.main()
