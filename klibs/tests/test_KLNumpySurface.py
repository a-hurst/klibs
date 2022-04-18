# -*- coding: utf-8 -*-
import pytest
import numpy as np
from PIL import Image, ImageDraw
from aggdraw import Draw
from pkg_resources import resource_filename
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import NumpySurface, aggdraw_to_numpy_surface


def maketestsurface():
    testarr = np.zeros((100, 100, 4), dtype=np.uint8)
    testarr[0:50, 0:50, :] = 255
    return testarr


def test_aggdraw_to_nps():
    aggsurf = Draw("RGB", [50, 50], (0, 0, 255))
    surf = aggdraw_to_numpy_surface(aggsurf)
    assert surf.height == 50 and surf.width == 50
    assert surf.content[0][0][3] == 255


class TestSurfaceInit(object):

    def test_init_empty(self):
        surf = NumpySurface(width=50, height=100, fill=[255, 0, 0])
        assert surf.height == 100 and surf.width == 50
        assert surf.content[0][0][0] == 255

    def test_init_ndarray(self):
        nparr = maketestsurface()
        surf = NumpySurface(nparr)
        assert surf.height == 100 and surf.width == 100
        assert surf.content[0][0][0] == 255

    def test_init_nps(self):
        nps = NumpySurface(width=100, height=100, fill=[255, 0, 0])
        surf = NumpySurface(nps)
        assert surf.height == 100 and surf.width == 100
        assert surf.content[0][0][0] == 255

    def test_init_pillow_rgba(self):
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 255))
        surf = NumpySurface(img)
        assert surf.height == 100 and surf.width == 100
        assert surf.content[0][0][0] == 255

    def test_init_pillow_rgb(self):
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        surf = NumpySurface(img)
        assert surf.height == 100 and surf.width == 100
        assert surf.content[0][0][0] == 255

    def test_init_pillow_oddball(self):
        img = Image.new('L', (100, 100), color=255)
        surf = NumpySurface(img)
        assert surf.height == 100 and surf.width == 100
        assert surf.content[0][0][0] == 255

    def test_init_kldraw(self):
        d = kld.Ellipse(100, fill=(255, 255, 255))
        surf = NumpySurface(d)
        assert d.surface_height == surf.height and d.surface_width == surf.width
        assert surf.content[50][50][0] == 255

    def test_init_aggdraw(self):
        aggsurf = Draw("RGBA", [100, 100], (255, 0, 0))
        surf = NumpySurface(aggsurf)
        assert surf.height == 100 and surf.width == 100
        assert surf.content[0][0][0] == 255

    def test_init_file(self):
        logo_file_path = resource_filename('klibs', 'resources/splash.png')
        surf = NumpySurface(logo_file_path)
        assert surf.height == 123 and surf.width == 746
        assert surf.content[0][0][0] == 0
        assert surf.content[12][12][2] == 163  # Blue part of 'K'

    def test_init_err(self):
        with pytest.raises(TypeError):
            surf = NumpySurface(0)


def test_render():

    surf = NumpySurface(width=100, height=100, fill=[255, 0, 0])
    rendered = surf.render()
    assert rendered.dtype == np.uint8
    assert rendered[0][0][0] == 255 and rendered[0][0][1] == 0


def test_copy():

    surf = NumpySurface(width=100, height=100, fill=[0, 0, 0])
    surf_copy = surf.copy()
    assert isinstance(surf_copy, NumpySurface)

    surf.content[0][0][0] = 255
    assert surf.content[0][0][0] != surf_copy.content[0][0][0]


def test_blit():

    # Initialize different test surfaces
    surf_clear = NumpySurface(width=100, height=100, fill=[0, 0, 0, 0])
    surf_black = NumpySurface(width=100, height=100, fill=[0, 0, 0, 255])
    test_surf = maketestsurface()
    test_square = NumpySurface(width=50, height=50, fill=(255, 255, 255))

    # Test registrations
    expected_bounds = {
        '1': (50, 0, 100, 50), '2': (25, 0, 75, 50), '3': (0, 0, 50, 50),
        '4': (50, 25, 100, 75), '5': (25, 25, 75, 75), '6': (0, 25, 50, 75),
        '7': (50, 50, 100, 100), '8': (25, 50, 75, 100), '9': (0, 50, 50, 100),
    }
    for r in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
        for blendmode in [True, False]:
            surf = surf_clear.copy()
            sc = surf.surface_c
            surf.blit(test_square, registration=r, location=sc, blend=blendmode)
            img = Image.fromarray(surf.content)
            assert expected_bounds[str(r)] == img.getbbox()

    # Test blending behaviour
    surf = surf_black.copy()
    surf.blit(test_surf, registration=7, location=(0, 0), blend=True)
    assert surf.content[0][0][3] == 255 and surf.content[-1][-1][3] == 255
    surf = surf_black.copy()
    surf.blit(test_surf, registration=7, location=(0, 0), blend=False)
    assert surf.content[0][0][3] == 255 and surf.content[-1][-1][3] == 0

    # Test clipping behaviour
    for blendmode in [True, False]:
        surf = surf_clear.copy()
        surf.blit(test_square, location=(75, 75), blend=blendmode, clip=True)
        surf.blit(test_square, location=(-25, -25), blend=blendmode, clip=True)
        assert surf.content[24][24][0] == 255 and surf.content[25][25][0] == 0
        assert surf.content[75][75][0] == 255 and surf.content[74][74][0] == 0

    # Test blit exceptions
    with pytest.raises(TypeError):
        surf = surf_clear.copy()
        surf.blit(1, location=(0, 0))
    with pytest.raises(ValueError):
        surf = surf_clear.copy()
        surf.blit(test_square, location=(150, 150))
    with pytest.raises(ValueError):
        surf = surf_clear.copy()
        surf.blit(test_square, location=(75, 75), clip=False)
    with pytest.raises(ValueError):
        surf = test_square.copy()
        surf.blit(surf_clear, location=(0, 0), clip=False)


def test_mask():

    # Initialize test surface and masks
    # NOTE: Testing KLDraw objects further down, since KLD rectangles have 1px
    # transparent padding that breaks this test loop's logic
    surface = NumpySurface(width=100, height=100, fill=[255, 0, 0])
    nps_mask = NumpySurface(width=50, height=50, fill=[255, 255, 255])
    np_mask = nps_mask.render()
    greyscale_mask = Image.new('L', (50, 50), 0)
    ImageDraw.Draw(greyscale_mask).rectangle((0, 0, 50, 50), fill=255)
    rgb_mask = Image.new('RGB', (50, 50), (0, 0, 0))
    ImageDraw.Draw(rgb_mask).rectangle((0, 0, 50, 50), fill=(255, 0, 0))

    # Test different mask types
    for mask in [nps_mask, np_mask, greyscale_mask, rgb_mask]:
        surf = surface.copy()
        surf.mask(mask, registration=7, location=(0, 0))
        assert surf.content[49][49][3] == 0
        assert surf.content[50][50][3] == 255

    # Test legacy positioning
    surf = surface.copy()
    surf.mask(nps_mask, (25, 25))
    assert surf.content[0][0][3] == 255 and surf.content[25][25][3] == 0
 
    # Test with mask partially off surface
    surf = surface.copy()
    surf.mask(nps_mask, registration=3, location=(25, 25))
    assert surf.content[24][24][3] == 0 and surf.content[25][25][3] == 255
    surf.mask(nps_mask, registration=7, location=(75, 75))
    assert surf.content[74][74][3] == 255 and surf.content[75][75][3] == 0

    # Test inverse/non-inverse modes and complete masking
    circle_mask = kld.Ellipse(50, fill=(255, 255, 255))
    for complete in [True, False]:
        surf = surface.copy()
        surf.mask(circle_mask, location=(0, 0), invert=True, complete=complete)
        assert surf.content[0][0][3] == 255 and surf.content[25][25][3] == 0
        assert surf.content[-1][-1][3] == (0 if complete else 255)
        surf = surface.copy()
        surf.mask(circle_mask, location=(0, 0), invert=False, complete=complete)
        assert surf.content[0][0][3] == 0 and surf.content[25][25][3] == 255
        assert surf.content[-1][-1][3] == (0 if complete else 255)

    # Test exception for invalid mask type
    with pytest.raises(TypeError):
        surf = surface.copy()
        surf.mask("hello")


def test_scale():

    surface = NumpySurface(width=200, height=100, fill=[0, 0, 0])
    red_box = NumpySurface(width=100, height=50, fill=[255, 0, 0])
    surface.blit(red_box, location=(0, 0), blend=False)

    surf = surface.copy()
    surf.scale(width=300)
    assert surf.height == 150
    assert surf.content[0][149][0] > 128 and surf.content[74][0][0] > 128
    assert surf.content[0][150][0] < 64 and surf.content[75][0][0] < 64

    surf = surface.copy()
    surf.scale(height=50)
    assert surf.width == 100
    assert surf.content[0][49][0] > 128 and surf.content[24][0][0] > 128
    assert surf.content[0][50][0] < 64 and surf.content[25][0][0] < 64

    surf = surface.copy()
    surf.scale(width=500, height=500)
    assert surf.height == 500 and surf.width == 500
    assert surf.content[0][249][0] > 128 and surf.content[249][0][0] > 128
    assert surf.content[0][250][0] < 128 and surf.content[250][0][0] < 128

    with pytest.raises(ValueError):
        surf.scale()


def test_trim():

    surf = NumpySurface(maketestsurface())
    surf.trim()
    assert surf.height == 50 and surf.width == 50

    surf = NumpySurface(width=50, height=50, fill=(0, 0, 0, 0))
    with pytest.raises(RuntimeError):
        surf.trim()


def test_flip_left():

    surf = NumpySurface(maketestsurface())
    surf.flip_left()
    assert surf.content[0][0][0] == 0
    assert surf.content[-1][0][0] == 255

    surf.flip_left()
    assert surf.content[-1][0][0] == 0
    assert surf.content[-1][-1][0] == 255


def test_flip_right():

    surf = NumpySurface(maketestsurface())
    surf.flip_right()
    assert surf.content[0][0][0] == 0
    assert surf.content[0][-1][0] == 255

    surf.flip_right()
    assert surf.content[0][-1][0] == 0
    assert surf.content[-1][-1][0] == 255


def test_flip_x():

    surf = NumpySurface(maketestsurface())
    surf.flip_x()
    assert surf.content[0][0][0] == 0
    assert surf.content[0][-1][0] == 255


def test_flip_y():

    surf = NumpySurface(maketestsurface())
    surf.flip_y()
    assert surf.content[0][0][0] == 0
    assert surf.content[-1][0][0] == 255


def test_getpixelvalue():

    surf = NumpySurface(width=50, height=50, fill=[255, 0, 0])
    assert surf.get_pixel_value((1, 1)) == (255, 0, 0, 255)

    with pytest.raises(ValueError):
        surf.get_pixel_value((1, 100))


def test_avg_colour():

    surf1 = NumpySurface(width=100, height=100, fill=[200, 0, 0])
    surf2 = NumpySurface(width=50, height=100, fill=[0, 200, 0])
    surf1.blit(surf2)
    assert surf1.average_color == (100, 100, 0, 255)