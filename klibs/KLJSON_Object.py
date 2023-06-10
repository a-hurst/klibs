__author__ = 'Jonathan Mulle & Austin Hurst'

import io
import re
import json


class AttributeDict(dict):
    """A Python dictionary that lets you access items like you would object attributes.
    For example, for the following AttributeDict::
    
         d = {'one': 1, 'two': 2}
    
    you could get the value of 'one' through either d['one'] or d.one.
    
    """
    def __getattr__(self, key):
        return self[key]

    def __setattr__(self, key, value):
        self[key] = value


def _json_to_attributedict(dict_obj):
    # Private method for helping json.load() return an attributedict
    # Check if JSON object name is a valid Python class attribute name
    valid_attr_name = re.compile(r"^[A-Za-z_]+([A-Za-z0-9_]+)?$")
    for key in dict_obj.keys():
        if re.match(valid_attr_name, key) == None:
            e = u"'{0}' is not a valid Python class attribute name ".format(key)
            e += u"(try removing spaces and special characters)."
            raise AttributeError(e)
    return AttributeDict(dict_obj)


class JSON_Object(AttributeDict):
    # Deprecated: replaced by the more-flexible import_json function
    def __init__(self, json_file_path):
        try:
            json_file = io.open(json_file_path, encoding='utf-8')
            json_dict = json.load(json_file, object_hook=_json_to_attributedict)
            for key in json_dict:
                setattr(self, key, json_dict[key])
        except ValueError:
            err = "'{0}' is not a valid JSON file.".format(json_file_path)
            raise RuntimeError(err)
        except AttributeError as e:
            raise ValueError(e)


def import_json(filepath):
    """Imports a JSON file into a Python-friendly format.

    This function converts the imported JSON structure into :obj:`AttributeDict`
    objects where possible, allowing elements to be accessed as Python object
    attributes as well as traditional dictionary keys.

    For example, if you imported a .json file with the following contents:
    
    .. code-block:: json

        {
        "study_words": [
            {"word":"cognition", "syllables":3, "type":"noun"},
            {"word":"experimental", "syllables":5, "type":"verb"}
            ],
        "foil_words": [
            {"word":"cognitive", "syllables":3, "type":"adjective"},
            {"word":"experiment", "syllables":4, "type":"noun"}
            ]
        }

    you could then import and access its contents like this::

        # Import the JSON file
        wordbank_path = os.path.join('path', 'to', 'wordbank.json')
        wordbank = import_json(wordbank_path)

        # Access the elements of the JSON_Object as object attributes
        for word in wordbank.study_words:
            print(word.word, word.syllables, word.type)

    Alternatively, you can access the contents like you would a Python dictonary::

        for word in wordbank['foil_words']:
            print(word['word'], word['syllables'], word['type'])

    Note that all key names in the imported JSON must be valid Python attribute names
    (i.e. no spaces, periods, special characters, etc.). If a non-valid key is
    encountered, a ValueError will be raised.

    Args:
        filepath (:obj:`str`): The path of the JSON file to import.

    """
    try:
        json_io = io.open(filepath, encoding='utf-8')
        converted = json.load(json_io, object_hook=_json_to_attributedict)
    except ValueError:
        err = "'{0}' is not a valid JSON file.".format(filepath)
        raise RuntimeError(err)
    except AttributeError as e:
        raise ValueError(e)
    
    return converted
