# -*- coding: utf-8 -*-
import pytest
import numpy as np
from PIL import Image, ImageDraw
from aggdraw import Draw
from pkg_resources import resource_filename
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics import aggdraw_to_numpy_surface
from klibs.KLGraphics.KLNumpySurface import NumpySurface


def maketestsurface():
    testarr = np.zeros((100, 100, 4), dtype=np.uint8)
    testarr[0:50, 0:50, :] = 255
    return testarr

def filled_nps(width, height, fill):
    if len(fill) == 3:
        img = Image.new('RGB', (width, height), color=tuple(fill))
        img = img.convert('RGBA')
    else:
        img = Image.new('RGBA', (width, height), color=tuple(fill))
    return NumpySurface(img)


def test_aggdraw_to_nps():
    aggsurf = Draw("RGB", [50, 50], (0, 0, 255))
    surf = aggdraw_to_numpy_surface(aggsurf)
    assert surf.height == 50 and surf.width == 50
    assert surf.foreground[0][0][3] == 255


class TestSurfaceInit(object):

    def test_init_ndarray(self):
        nparr = maketestsurface()
        surf = NumpySurface(nparr)
        assert surf.height == 100 and surf.width == 100
        assert surf.foreground[0][0][0] == 255

    def test_init_nps(self):
        nps = filled_nps(width=100, height=100, fill=[255, 0, 0])
        surf = NumpySurface(nps)
        assert surf.height == 100 and surf.width == 100
        assert surf.foreground[0][0][0] == 255

    def test_init_pillow_rgba(self):
        img = Image.new('RGBA', (100, 100), color=(255, 0, 0, 255))
        surf = NumpySurface(img)
        assert surf.height == 100 and surf.width == 100
        assert surf.foreground[0][0][0] == 255

    def test_init_pillow_rgb(self):
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        surf = NumpySurface(img)
        assert surf.height == 100 and surf.width == 100
        assert surf.foreground[0][0][0] == 255

    def test_init_kldraw(self):
        d = kld.Ellipse(100, fill=(255, 255, 255))
        surf = NumpySurface(d)
        assert d.surface_height == surf.height and d.surface_width == surf.width
        assert surf.foreground[50][50][0] == 255

    def test_init_aggdraw(self):
        aggsurf = Draw("RGBA", [100, 100], (255, 0, 0))
        surf = NumpySurface(aggsurf)
        assert surf.height == 100 and surf.width == 100
        assert surf.foreground[0][0][0] == 255

    def test_init_file(self):
        logo_file_path = resource_filename('klibs', 'resources/splash.png')
        surf = NumpySurface(logo_file_path)
        assert surf.height == 123 and surf.width == 746
        assert surf.foreground[0][0][0] == 0
        assert surf.foreground[12][12][2] == 163  # Blue part of 'K'

    def test_init_err(self):
        with pytest.raises(TypeError):
            surf = NumpySurface(0)


def test_render():

    surf = filled_nps(width=100, height=100, fill=[255, 0, 0])
    rendered = surf.render()
    assert rendered.dtype == np.uint8
    assert rendered[0][0][0] == 255 and rendered[0][0][1] == 0


def test_blit():

    # Initialize different test surfaces
    surf_clear = filled_nps(width=100, height=100, fill=[0, 0, 0, 0])
    test_surf = maketestsurface()
    test_square = filled_nps(width=50, height=50, fill=(255, 255, 255))

    # Test registrations
    expected_bounds = {
        '1': (50, 0, 100, 50), '2': (25, 0, 75, 50), '3': (0, 0, 50, 50),
        '4': (50, 25, 100, 75), '5': (25, 25, 75, 75), '6': (0, 25, 50, 75),
        '7': (50, 50, 100, 100), '8': (25, 50, 75, 100), '9': (0, 50, 50, 100),
    }
    for r in [1, 2, 3, 4, 5, 6, 7, 8, 9]:
        surf_clear = filled_nps(width=100, height=100, fill=[0, 0, 0, 0])
        surf = NumpySurface(surf_clear)
        sc = (surf.width // 2, surf.height // 2)
        surf.blit(test_square, registration=r, location=sc)
        surf_np = surf.render()
        img = Image.fromarray(surf_np)
        assert expected_bounds[str(r)] == img.getbbox()

    # Test blending behaviour
    surf = filled_nps(width=100, height=100, fill=[0, 0, 0, 255])
    surf.blit(test_surf, registration=7, location=(0, 0))
    surf.render()
    assert surf.rendered[0][0][3] == 255 and surf.rendered[-1][-1][3] == 0

    # Test blit exceptions
    surf_clear = filled_nps(width=100, height=100, fill=[0, 0, 0, 0])
    with pytest.raises(TypeError):
        surf = surf_clear
        surf.blit(1, location=(0, 0))
    with pytest.raises(ValueError):
        surf = surf_clear
        surf.blit(test_square, location=(150, 150))
    with pytest.raises(ValueError):
        surf = surf_clear
        surf.blit(test_square, location=(75, 75))
    with pytest.raises(ValueError):
        surf = test_square
        surf.blit(surf_clear, location=(0, 0))


def test_mask():

    # Initialize test surface and masks
    surface = filled_nps(width=100, height=100, fill=[255, 0, 0])
    nps_mask = filled_nps(width=50, height=50, fill=[255, 255, 255])
    np_mask = nps_mask.render()

    # Test different mask types
    for mask in [nps_mask, np_mask]:
        surf = filled_nps(width=100, height=100, fill=[255, 0, 0])
        surf.mask(mask, location=(0, 0))
        surf.render()
        assert surf.rendered[49][49][3] == 0
        assert surf.rendered[50][50][3] == 255

    # Test exception for invalid mask type
    with pytest.raises(TypeError):
        surf = filled_nps(width=100, height=100, fill=[255, 0, 0])
        surf.mask(1)


@pytest.mark.skip("not implemented")
def test_scale():
    pass


def test_getpixelvalue():
    surf = filled_nps(width=50, height=50, fill=[255, 0, 0])
    assert tuple(surf.get_pixel_value((1, 1))) == (255, 0, 0, 255)


@pytest.mark.skip("not implemented")
def test_avg_colour():
    pass
