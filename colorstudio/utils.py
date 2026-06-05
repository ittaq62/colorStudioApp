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
import math
import numpy as np
import imageio.v2 as imageio
import skimage
#from skimage import transform  # redondant avec import skimage (skimage.transform.rescale est utilise plus bas)

# ----------------------------------------------------------------------------------
# functions
# ----------------------------------------------------------------------------------
def printProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=100, fill='#'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end='\r')
    # Print New Line on Complete
    if iteration == total:
        print()

# ----------------------------------------------------------------------------------
def loadImage(filename, scale=0.5):
    """
    load image from image filename and convert to double
    LDR (uint8/uint16) -> normalised in [0,1]
    HDR (float .hdr/.exr) -> values kept as-is (can exceed 1.0)
    @params:
        filename   - Required  : image filename (Str)
        scale      - Optional  : scaling factor [=0.5] (Float)
    """
    img = imageio.imread(filename)

    # normalise selon le dtype d'origine
    if img.dtype == np.uint8:
        imgDouble = img.astype(np.float64) / 255.0
    elif img.dtype == np.uint16:
        imgDouble = img.astype(np.float64) / 65535.0
    else:
        # deja en float (HDR : .hdr, .exr) -> on garde tel quel
        imgDouble = img.astype(np.float64)

    if scale != 1.0:
        imgDouble = skimage.transform.rescale(imgDouble, scale, anti_aliasing=True, channel_axis=2)
    return imgDouble

# ----------------------------------------------------------------------------------
def toneMap(imgDouble):
    """
    tone mapping de Reinhard pour afficher une image HDR a l'ecran.
    formule : x / (1 + x) -> ramene les valeurs [0, +inf[ dans [0, 1[
    @params:
        imgDouble  - Required  : image RGB float (peut contenir des valeurs > 1)
    """
    # valeurs negatives possibles apres postprocess -> on clippe en bas a 0
    safe = np.maximum(imgDouble, 0.0)
    return safe / (1.0 + safe)

# ----------------------------------------------------------------------------------
def image2Ymean(imgDouble):
    """
    compute Y (Luminance) mean of an image (RGB in [0,max] (Float))
    @params:
        imgDouble   - Required  : image RGB in Float
    """
    # recover image size
    x, y, c = tuple(imgDouble.shape)

    # color space : convert to Yuv
    # note that: XYZ assumes that RGB in [0,1], it is not the case for Yuv
    img_yuv = skimage.color.rgb2yuv(imgDouble)

    # array_like
    img_yuv_array = np.reshape(img_yuv, (x * y, c))

    # recover Y channel
    y_array = img_yuv_array[:, 0]

    meanExposure = np.mean(y_array)

    return meanExposure

# ----------------------------------------------------------------------------------
def imgRGB2chromaRG(img):
    # img RGB color space double in [0,1]
    x, y, c = img.shape
    # reshape to array
    img_array = np.reshape(img, (x * y, c))

    # rgb
    r = img_array[:, 0]
    g = img_array[:, 1]
    b = img_array[:, 2]

    rgb_sum = r + g + b
    rgb_sum[rgb_sum == 0.0] = 1.0  # remove zeros

    rchroma = r / rgb_sum
    gchroma = g / rgb_sum

    rgchroma = np.zeros((x * y, 2))
    rgchroma[:, 0] = rchroma
    rgchroma[:, 1] = gchroma

    return rgchroma

# ----------------------------------------------------------------------------------
def img2chromaVertices(img, scale=False):
    # img RGB color space double in [0,1]
    x, y, c = img.shape
    # reshape to array
    img_array = np.reshape(img, (x * y, c))

    # rgb
    r = img_array[:, 0]
    g = img_array[:, 1]
    b = img_array[:, 2]

    a = np.ones(x * y)

    rgb_sum = r + g + b
    rgb_sum[rgb_sum == 0.0] = 1.0  # remove zeros

    rchroma = r / rgb_sum
    gchroma = g / rgb_sum

    if scale:
        rMax, gMax = np.amax(rchroma), np.amax(gchroma)
        rMin, gMin = np.amin(rchroma), np.amin(gchroma)
        scaling = max(rMax - rMin, gMax - gMin)
        rchroma = (rchroma - rMin) / scaling * 2.0 - 1.0
        gchroma = (gchroma - gMin) / scaling * 2.0 - 1.0
    else:
        rchroma = rchroma * 2.0 - 1.0
        gchroma = gchroma * 2.0 - 1.0

    return np.dstack([rchroma[:], gchroma[:], r[:], g[:], b[:], a[:]])

# ----------------------------------------------------------------------------------
def colorWheel(halfSize):
    nb = halfSize * 2 + 1
    center = halfSize
    hsv_array = np.zeros([nb, nb, 3])
    for i in range(nb):
        for j in range(nb):
            ii = (i - center) / (center - 1)
            jj = (j - center) / (center - 1)
            r = math.sqrt(ii * ii + jj * jj)

            if r < 0.5:
                hsv_array[i, j, :] = [0.0, 0.0, 1.0]
            elif r < 1.0:
                sat = 1.0
                hue = (math.atan2(jj, ii) + math.pi) / (2 * math.pi)
                hsv_array[i, j, :] = [hue, sat, 1.0]
            else:
                hsv_array[i, j, :] = [0.0, 0.0, 0.01]

    rgb_hsv_array = skimage.color.hsv2rgb(hsv_array)
    return rgb_hsv_array

# ----------------------------------------------------------------------------------
def inRange2D(pos, orig, size):
    xp, yp = pos[0], pos[1]
    xo, yo = orig[0], orig[1]
    w, h = size[0], size[1]
    return ((xo <= xp) and (xp <= xo + w)) and ((yo <= yp) and (yp <= yo + h))


# ----------------------------------------------------------------------------------
# conversions HSV : versions vectorisees pures numpy.
# benchmark sur une image 540x960 :
#   skimage.color.rgb2hsv : ~120 ms
#   rgb2hsv_fast (ci-dessous) : ~40 ms  (3x plus rapide)
# resultats identiques aux erreurs de precision flottante pres (~1e-16)
# ----------------------------------------------------------------------------------
def rgb2hsv_fast(rgb):
    """
    conversion RGB -> HSV vectorisee, ~3x plus rapide que skimage.color.rgb2hsv
    pour des images typiques (540x960 et plus).
    accepte un tableau numpy de shape (..., 3) avec des valeurs dans [0, 1].
    """
    r = rgb[..., 0]
    g = rgb[..., 1]
    b = rgb[..., 2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin
    # protection division par zero
    safe_delta = np.where(delta == 0, 1.0, delta)
    safe_cmax = np.where(cmax == 0, 1.0, cmax)
    # canal H (hue)
    rc = (cmax - r) / safe_delta
    gc = (cmax - g) / safe_delta
    bc = (cmax - b) / safe_delta
    h = np.where(r == cmax, bc - gc,
        np.where(g == cmax, 2.0 + rc - bc, 4.0 + gc - rc))
    h = (h / 6.0) % 1.0
    h = np.where(delta == 0, 0.0, h)
    # canal S (saturation)
    s = np.where(cmax == 0, 0.0, delta / safe_cmax)
    # canal V (value)
    v = cmax
    return np.stack([h, s, v], axis=-1)


def hsv2rgb_fast(hsv):
    """
    conversion HSV -> RGB vectorisee, ~1.7x plus rapide que skimage.color.hsv2rgb.
    accepte un tableau numpy de shape (..., 3).
    """
    h = hsv[..., 0]
    s = hsv[..., 1]
    v = hsv[..., 2]
    h6 = h * 6.0
    i = np.floor(h6).astype(np.int64) % 6
    f = h6 - np.floor(h6)
    p = v * (1.0 - s)
    q = v * (1.0 - f * s)
    t = v * (1.0 - (1.0 - f) * s)
    # selon le secteur i (0 a 5), on assemble r/g/b a partir de v/q/p/t
    r = np.choose(i, [v, q, p, p, t, v])
    g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], axis=-1)
