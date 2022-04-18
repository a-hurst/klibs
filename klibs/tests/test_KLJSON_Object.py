# -*- coding: utf-8 -*-
import pytest
import os
from klibs import KLJSON_Object as json_obj


def test_AttributeDict():

    attrdict = json_obj.AttributeDict()
    attrdict['k'] = 'value'
    assert attrdict.k == 'value'

    testdict = {'a': 1, 'b': 2, 'c': 3}
    attrdict = json_obj.AttributeDict(testdict)
    assert attrdict.a == 1
    assert attrdict['b'] == 2
    assert sum(attrdict.values()) == 6


def test_JSON_Object(tmpdir):

    test1 = tmpdir.join("test1.json")
    test1.write(u"""
    {
        "one": {
            "a": false,
            "b": null,
            "c": [1, 2, 3, 4, 5]
        },
        "two": "hello",
        "three": "well done 測試 ✓"
    }
    """.encode('utf-8'), mode='wb')
    testpath = os.path.join(test1.dirname, test1.basename)
    t1 = json_obj.JSON_Object(testpath)
    assert isinstance(t1.one, dict)
    assert t1.two == "hello"
    assert sum(t1.one.c) == 15
    assert not t1['one'].a
    assert t1.one.b == None

    # Test checking for bad variable names
    test2 = tmpdir.join("test3.json")
    test2.write("""
    {
        "invalid name": 5,
        "2": "hello"
    }
    """)
    testpath = os.path.join(test2.dirname, test2.basename)
    with pytest.raises(AttributeError):
        t2 = json_obj.JSON_Object(testpath)

    # Test error handling of non-JSON files
    test3 = tmpdir.join("test3.json")
    test3.write("""
    [this is not a json file]
    not = a
    json != file
    """)
    testpath = os.path.join(test3.dirname, test3.basename)
    with pytest.raises(RuntimeError):
        t3 = json_obj.JSON_Object(testpath)
