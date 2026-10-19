import pytest

from klibs import P
from klibs.KLConstants import STROKE_INNER, STROKE_OUTER, STROKE_CENTER
from klibs.KLGraphics import KLDraw as kld
from klibs.KLGraphics.colorspaces import (
    COLORSPACE_CONST, COLORSPACE_CIELUV, COLORSPACE_RGB
)

WIDTH = 100
HEIGHT = 150
SIZE = WIDTH
THICKNESS = 10

RED = (255, 0, 0, 255)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TRANSLUCENT_BLUE = (0, 0, 255, 128)

STROKE_MAP = {
    'none': None,
    'legacy': [4, WHITE, STROKE_INNER],
    'inner': kld.Stroke(2, RED, 'inner'),
    'center': kld.Stroke(4, BLACK, 'center'),
    'outer': kld.Stroke(2, TRANSLUCENT_BLUE, 'outer')
}


def test_drift_correct_target():
    P.screen_x = 1920
    P.screen_y = 1080
    tst = kld.drift_correct_target()

def test_Stroke():
    # Test Stroke initialization
    s1 = kld.Stroke(4, BLACK)
    s2 = kld.Stroke(2, WHITE, 'outer')
    s3 = kld.Stroke(3, TRANSLUCENT_BLUE, align='center')
    with pytest.raises(ValueError):
        kld.Stroke(-2, WHITE)
    with pytest.raises(ValueError):
        kld.Stroke(4, WHITE, 'other')
    # Test stroke attributes
    assert s1.width == 4
    assert s2.color == (255, 255, 255, 255)
    assert s3.color == TRANSLUCENT_BLUE
    assert s3.alignment == 'center'

def test_FixationCross():
    a = kld.FixationCross(SIZE, THICKNESS, fill=WHITE)
    b = kld.FixationCross(SIZE, THICKNESS, stroke=STROKE_MAP['outer'])
    c = kld.FixationCross(SIZE, THICKNESS, fill=BLACK, stroke=STROKE_MAP['inner'])

def test_Ellipse():
    tst = kld.Ellipse(SIZE, fill=WHITE)
    tst2 = kld.Ellipse(WIDTH, HEIGHT, fill=WHITE)

def test_Circle():
    tst = kld.Circle(SIZE, fill=WHITE)
    tst = kld.Circle(SIZE, stroke=STROKE_MAP['inner'])
    tst = kld.Circle(SIZE, fill=WHITE, stroke=STROKE_MAP['center'])

def test_Annulus():
    tst = kld.Annulus(SIZE, THICKNESS, fill=WHITE)

def test_Rectangle():
    a = kld.Rectangle(SIZE, fill=WHITE)
    b = kld.Rectangle(HEIGHT, WIDTH, fill=WHITE)
    # Test stroke getting/setting
    c = kld.Rectangle(SIZE, stroke=STROKE_MAP['legacy'])
    d = kld.Rectangle(SIZE, stroke=STROKE_MAP['inner'])
    assert c.stroke.width == 4
    assert c.stroke.color == (255, 255, 255, 255)
    assert c.stroke.alignment == 'inner'
    assert d.stroke.width == 2
    assert d.stroke.color == (255, 0, 0, 255)
    assert d.stroke.alignment == 'inner'
    # Test legacy stroke getting/setting
    assert a.stroke == None
    a.stroke = [2, BLACK]
    assert a.stroke.width == 2
    assert a.stroke.color == (0, 0, 0, 255)
    assert a.stroke.alignment == 'outer'
    b.stroke = STROKE_MAP['legacy']
    assert b.stroke.width == 4
    assert b.stroke.alignment == 'inner'

def test_Asterisk():
    for spokes in [3, 6, 12]:
        tst = kld.Asterisk(SIZE, THICKNESS, fill=WHITE, spokes=spokes)

def test_SquareAsterisk():
    tst = kld.SquareAsterisk(SIZE, THICKNESS, fill=WHITE)

def test_Line():
    for r in [0, 45, 90]:
        tst = kld.Line(SIZE, WHITE, THICKNESS, rotation=r)

def test_Triangle():
    a = kld.Triangle(SIZE, SIZE, fill=WHITE)
    b = kld.Triangle(SIZE, SIZE // 2, stroke=STROKE_MAP['inner'])

def test_Arrow():
    headsize = THICKNESS * 4
    tst = kld.Arrow(
        SIZE, THICKNESS, headsize, headsize, fill=WHITE
    )

def test_ColorWheel():
    colorspaces = [COLORSPACE_CONST, COLORSPACE_CIELUV, COLORSPACE_RGB]
    for colors in colorspaces:
        tst = kld.ColorWheel(SIZE, THICKNESS, colors=colors)
