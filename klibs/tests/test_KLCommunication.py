import os
import pytest

from klibs.KLCommunication import message


def test_message(with_text_init):
    msg = message("Hello!")
