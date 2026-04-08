# -*- coding: utf-8 -*-
"""
Tests pour colorstudio.utils
"""
import os
import tempfile
import unittest
import numpy as np
import imageio.v2 as imageio

from colorstudio import utils


class TestLoadImage(unittest.TestCase):
    """tests de loadImage : LDR (uint8) et HDR (float)"""

    def setUp(self):
        # liste des fichiers temp a nettoyer apres chaque test
        self._tmpFiles = []

    def tearDown(self):
        for p in self._tmpFiles:
            if os.path.exists(p):
                os.unlink(p)

    def _makeTmp(self, suffix):
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        self._tmpFiles.append(path)
        return path

    def test_load_ldr_uint8_normalised(self):
        # une image uint8 a 128 doit etre normalisee a ~0.502
        arr = (np.ones((4, 4, 3), dtype=np.uint8) * 128)
        path = self._makeTmp(".png")
        imageio.imwrite(path, arr)

        img = utils.loadImage(path, scale=1.0)

        self.assertEqual(img.dtype, np.float64)
        self.assertAlmostEqual(img.min(), 128 / 255.0, places=4)
        self.assertAlmostEqual(img.max(), 128 / 255.0, places=4)

    def test_load_hdr_float_keeps_values_above_one(self):
        # une image HDR a 2.5 doit garder ses valeurs (pas de division par 255)
        arr = np.ones((4, 4, 3), dtype=np.float32) * 2.5
        path = self._makeTmp(".hdr")
        imageio.imwrite(path, arr)

        img = utils.loadImage(path, scale=1.0)

        self.assertEqual(img.dtype, np.float64)
        # tolerance car .hdr fait un encodage RGBE qui n'est pas exact au bit pres
        self.assertAlmostEqual(img.min(), 2.5, places=2)
        self.assertAlmostEqual(img.max(), 2.5, places=2)
        self.assertGreater(img.max(), 1.0)


class TestToneMap(unittest.TestCase):
    """tests de toneMap (Reinhard x / (1+x))"""

    def test_zero_stays_zero(self):
        # un pixel noir doit rester noir
        img = np.zeros((2, 2, 3), dtype=np.float64)
        out = utils.toneMap(img)
        self.assertTrue(np.allclose(out, 0.0))

    def test_one_becomes_half(self):
        # 1.0 / (1 + 1.0) = 0.5
        img = np.ones((2, 2, 3), dtype=np.float64)
        out = utils.toneMap(img)
        self.assertTrue(np.allclose(out, 0.5))

    def test_large_values_stay_below_one(self):
        # meme une valeur HDR enorme doit rester strictement < 1
        img = np.ones((2, 2, 3), dtype=np.float64) * 1000.0
        out = utils.toneMap(img)
        self.assertTrue(np.all(out < 1.0))
        self.assertTrue(np.all(out > 0.99))  # 1000/1001 ~ 0.999

    def test_negative_values_clipped_to_zero(self):
        # des valeurs negatives (possibles apres post-process) -> 0
        img = np.ones((2, 2, 3), dtype=np.float64) * -0.5
        out = utils.toneMap(img)
        self.assertTrue(np.allclose(out, 0.0))


if __name__ == "__main__":
    unittest.main()
