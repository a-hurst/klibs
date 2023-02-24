import pytest

from klibs import P
from klibs.KLText import TextStyle, add_text_style


def test_add_text_style(with_txtm):
    from klibs import env

    add_text_style("custom", "40px", color=(255, 0, 0), font="Roboto-Medium")
    font = env.txtm.styles["custom"]
    assert font.size_px == 40
    assert font.color == (255, 0, 0, 255)
    assert font.fontname == "Roboto-Medium"

    add_text_style("triple_space", line_space=3.0)
    font = env.txtm.styles["triple_space"]
    assert font.line_space == 3.0


def test_TextStyle(with_text_init):

    # Test basic init with no arguments
    tst = TextStyle()
    assert tst.fontname == P.default_font_name
    assert tst.color == P.default_color

    # Test init w/ specific font
    tst = TextStyle(font="Roboto-Medium")
    assert tst.fontname == "Roboto-Medium"
    with pytest.raises(RuntimeError):
        TextStyle(font="Non-Existant-Semibold")

    # Test init w/ specific colour
    tst = TextStyle(color=(0, 255, 0))
    assert tst.color == (0, 255, 0, 255)
    tst = TextStyle(color=(255, 0, 0, 64))
    assert tst.color == (255, 0, 0, 64)

    # Test init w/ custom line spacing
    tst = TextStyle(line_space=1.0)
    assert tst.line_space == 1.0
    with pytest.raises(ValueError):
        TextStyle(line_space=0.5)

    # Test init w/ custom size in px
    tst = TextStyle(size='20px')
    assert tst.size_px == 20
    P.default_font_unit = 'px'
    tst = TextStyle(size=20)
    assert tst.size_px == 20

    # Test init w/ custom size in pt
    tst = TextStyle(size='20pt')
    assert tst._size_pt == 20
    P.default_font_unit = 'pt'
    tst = TextStyle(size=20)
    assert tst._size_pt == 20

    # Test init w/ custom size in deg
    tst = TextStyle(size='0.5deg')
    assert tst.size_px == int(round(P.ppd * 0.5))
    P.default_font_unit = 'deg'
    tst = TextStyle(size=1.0)
    assert tst.size_px == int(round(P.ppd * 1.0))
