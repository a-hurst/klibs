import os
import pytest
from PIL import Image

from klibs import P
from klibs.KLGraphics import NumpySurface
from klibs.KLText import TextStyle
from klibs.KLCommunication import message, _get_demographics_queries
from klibs.KLJSON_Object import import_json, AttributeDict

from conftest import get_resource_path, db_test_path, db


def test_get_demograpics_queries(db):

    # Test basic loading and parsing of demographic queries
    qpath = get_resource_path('template/user_queries.json')
    qset = import_json(qpath).demographic
    queries = _get_demographics_queries(db, qset)
    assert len(queries) == len(qset)
    assert "age" in list(queries.keys())
    assert queries["age"].database_field == "age"

    # Test error when missing query for a required column
    with pytest.raises(RuntimeError):
        _get_demographics_queries(db, qset[:-1])
    
    # Test non-failure if extra query exists
    extra_q = AttributeDict({
        "title": "test",
        "database_field": "non_existant"
    })
    qset.append(extra_q)
    queries = _get_demographics_queries(db, qset)
    assert len(queries) < len(qset)


def test_message(with_text_init):
    # TODO: Figure out how to test blit behaviour?

    # Test basic text rendering
    msg = message("Hello!")
    assert isinstance(msg, NumpySurface)

    # Test multi-line rendering
    msg2 = message("Hello!\nHello!")
    msg3 = message("Hello!\n\nHello!")
    assert msg.width == msg2.width
    assert msg2.height > msg.height
    assert msg3.height > msg2.height

    # Test rendering with different text styles
    tst = TextStyle(color = (0, 255, 0, 255))
    msg = message("AAAAA", style="default")
    msg2 = message("AAAAA", style="alert")
    msg3 = message("AAAAA", style=tst)
    assert msg.average_color[:3] == P.default_color[:3]
    assert msg.average_color != msg2.average_color
    assert msg3.average_color[:3] == (0, 255, 0)

    # Test text wrap
    msg = message("This is a very long message")
    msg2 = message("This is a very long message", wrap_width=300)
    assert msg2.height > msg.height

    # Test alignment
    x_offset = {}
    for align in ("left", "right", "center"):
        msg = message("This is a very long message\n\nABC", wrap_width=300, align=align)
        half_height = int(msg.height / 2)
        img = Image.fromarray(msg.content[half_height:, :, :])
        x_offset[align] = img.getbbox()[0]
    assert x_offset["center"] > x_offset["left"]
    assert x_offset["right"] > x_offset["center"]
