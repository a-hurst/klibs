import os
import pytest
from PIL import Image

from klibs import P
from klibs.KLGraphics import NumpySurface
from klibs.KLText import TextStyle
from klibs.KLCommunication import message


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
