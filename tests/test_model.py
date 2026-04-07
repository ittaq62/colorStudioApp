# -*- coding: utf-8 -*-
"""
Tests pour colorstudio.model
"""
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


if __name__ == "__main__":
    unittest.main()
