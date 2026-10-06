import pytest

from klibs.KLText import add_text_style
from klibs.KLQueries import QueryStyle, NumberQuery, ChoiceQuery, TextQuery


def test_query_style(with_text_init):
    add_text_style("querystyle-test", size = '30px', line_space = 2.0)
    # Test init for QueryStyles
    s1 = QueryStyle(align="left", registration=7, location=(100, 100))
    s2 = QueryStyle("querystyle-test", bg_color=(0, 0, 0), err_color=(0, 0, 255))
    s3 = QueryStyle("querystyle-test", input_offset=1.5)
    with pytest.raises(RuntimeError):
        QueryStyle("nonexistent-text-style")
    # Test that input offset calculated correctly
    end_pad = 60 - s3.style._lineskip_px
    assert s3.input_offset_px == (30 + end_pad)


def test_number_query(with_text_init):
    # Test init for NumberQueries
    q1 = NumberQuery("Which number is best?")
    q2 = NumberQuery("Enter a value:", min=-100, max=100, decimal=True)
    q3 = NumberQuery(["Multiple", "Lines"], allow_blank=True)
    with pytest.raises(ValueError):
        NumberQuery("bad min/max", min=100, max=10)

    # Test response validation
    assert q1._validate_response("3") == None
    assert q2._validate_response("3.6") == None
    assert q3._validate_response("") == None
    assert q1._validate_response("3.6") != None
    assert q1._validate_response("") != None
    assert q1._validate_response("99999") != None
    assert q1._validate_response("-1") != None
    assert q1._validate_response("text") != None
    assert q2._validate_response("text") != None

    # Test internal methods
    assert q1._format_input("  3 ") == "3"
    assert q1._format_response("4") == 4
    assert q2._format_response("5.24") == 5.24
    assert q3._format_response("") == None


def test_choice_query(with_text_init):
    # Test init for ChoiceQueries
    q1 = ChoiceQuery("Which one?", ["a", "b", "c"])
    q2 = ChoiceQuery("Enter a condition:", ["PP", "MI", "CC"], case="upper")
    q3 = ChoiceQuery(["Multiple", "Lines"], [1, 2, 3, 4, 5], case="lower")
    with pytest.raises(RuntimeError):
        ChoiceQuery("no choice", ["a"])
    with pytest.raises(RuntimeError):
        ChoiceQuery("bad case", ["a", "b"], case="cool")

    # Test response validation
    assert q1._validate_response("a") == None
    assert q1._validate_response("b") == None
    assert q1._validate_response("C") == None
    assert q1._validate_response("d") != None
    assert q2._validate_response("pp") == None
    assert q2._validate_response("PP") == None
    assert q3._validate_response("1") == None

    # Test internal methods
    assert q1._format_input("  a ") == "a "
    assert q2._format_input("test") == "TEST"
    assert q3._format_input("TEST") == "test"
    assert q1._format_response("A") == "a"
    assert q2._format_response("cc") == "CC"
    assert q3._format_response("5") == "5"


def test_text_query(with_text_init):
    # Test init for TextQueries
    q1 = TextQuery("Write something:", max_length=3)
    q2 = TextQuery("YELL SOMETHING:", min_length=5, max_length=5, case="upper")
    q3 = TextQuery(["Multiple", "Lines"], min_length=0, case="title")
    with pytest.raises(ValueError):
        TextQuery("bad min/max", min_length=10, max_length=5)
    with pytest.raises(RuntimeError):
        TextQuery("bad case", case="cool")

    # Test response validation
    assert q1._validate_response("a") == None
    assert q1._validate_response("abc") == None
    assert q1._validate_response("") != None
    assert q1._validate_response("abcd") != None
    assert q2._validate_response("12345") == None
    assert q2._validate_response("123456") != None
    assert q3._validate_response("123456") == None
    assert q3._validate_response("") == None

    # Test internal methods
    assert q1._format_input("  a ") == "a "
    assert q2._format_input("test") == "TEST"
    assert q3._format_input("TEST") == "Test"
    assert q1._format_response("A") == "A"
    assert q2._format_response("cc") == "CC"
    assert q3._format_response("") == ""
    assert q3._format_response("hello") == "Hello"
