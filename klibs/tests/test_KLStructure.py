# -*- coding: utf-8 -*-
import sys
import pytest
import random
from collections import Counter

from klibs.KLStructure import FactorSet
from klibs.KLTrialFactory import _generate_blocks


class TestFactorSet(object):

    def test_init(self):
        # Test single factor
        tst = FactorSet({'test': ['a', 'b']})
        assert tst.set_length == 2
        assert 'test' in tst.names

        # Test multiple factors
        tst = FactorSet({
            'cue_loc': ['left', 'right', 'none'],
            'easy_trial': [True, False],
            'soa': [0, 200, 400, 800],
        })
        assert tst.set_length == 24
        assert len(tst.names) == 3
        assert 'cue_loc' in tst.names

        # Test 'repeated level' shorthand
        tst = FactorSet({
            'target_loc': ['left', 'right'],
            'cue_validity': [('valid', 3), 'invalid'],
        })
        assert tst.set_length == 8

        # Test exception on invalid tuple input
        with pytest.raises(RuntimeError):
            tst = FactorSet({
                'target_loc': ['left', 'right'],
                'colour': [(0, 0, 0), (255, 255, 255)],
            })

        # Test creating empty factor set
        tst = FactorSet({})
        assert tst._get_combinations() == [{}]
        assert tst.set_length == 1

    def test_get_combinations(self):
        # Ensure factor set contains no duplicates
        tst = FactorSet({
            'cue_validity': ['valid', 'invalid', 'neutral'],
            'easy_trial': [True, False],
            'soa': [0, 200, 400, 800],
        })
        unique_combos = tst._get_combinations()
        combo_counter = Counter([str(c) for c in unique_combos])
        assert len(list(combo_counter.elements())) == 24
        assert len(combo_counter.keys()) == 24

        # Ensure factor set handles repeated levels correctly
        tst = FactorSet({
            'cue_validity': ['valid', 'valid', 'invalid'],
            'easy_trial': [True, False],
            'soa': [0, 200, 400, 800],
        })
        unique_combos = tst._get_combinations()
        combo_counter = Counter([str(c) for c in unique_combos])
        assert len(list(combo_counter.elements())) == 24
        assert len(combo_counter.keys()) == 16

    def test_override(self):
        tst = FactorSet({
            'cue_loc': ['left', 'right', 'none'],
            'easy_trial': [True, False],
            'soa': [0, 200, 400, 800],
        })
        tst2 = tst.override({'soa': [400]})
        assert tst2.set_length == 6
        assert tst2.names == tst.names
        assert len(tst2._factors['soa']) == 1

        # Ensure original factor set wasn't modified
        assert len(tst._factors['soa']) == 4

        # Test override with non-iterable
        tst3 = tst.override({'easy_trial': True})
        assert tst3.set_length == 12
        assert tst3.names == tst.names
        assert len(tst3._factors['easy_trial']) == 1

        # Test override with repeated level tuple
        tst4 = tst.override({'easy_trial': [True, (False, 2)]})
        assert tst4.set_length == 36
        assert tst4.names == tst.names
        assert len(tst4._factors['easy_trial']) == 3

        # Test error on non-existant factor
        with pytest.raises(ValueError):
            tst.override({'alerting_trial': [True, False]})


def test_generate_blocks():
    # Create a FactorSet and IndependentVariableSet for testing
    tst = FactorSet({
        'cue_loc': ['left', 'right', 'none'],
        'easy_trial': [True, False],
        'soa': [0, 200, 400, 800],
    })

    # Try generating a block of 20 trials
    blocks = _generate_blocks(tst._factors, 1, 20)
    assert len(blocks) == 1
    assert len(blocks[0]) == 20
    assert isinstance(blocks[0][0], dict)

    # Try generating a block with the default factor set size
    blocks = _generate_blocks(tst._factors, 1, 0)
    assert len(blocks) == 1
    assert len(blocks[0]) == 24

    # Try generating a block an empty factor set
    blocks = _generate_blocks({}, 1, 0)
    assert len(blocks) == 1
    assert len(blocks[0]) == 1
    assert blocks[0][0] == {}

    # Try generating multiple blocks
    blocks = _generate_blocks({}, 4, 48)
    assert len(blocks) == 4
    assert all(len(b) == 48 for b in blocks)

    # Test whether random seed works as expected
    random.seed(308053045)
    block = _generate_blocks(tst._factors, 1, 20)[0]
    assert block[0]['soa'] == 200 and block[0]['cue_loc'] == 'none'
    assert block[1]['soa'] == 0 and block[1]['easy_trial'] == True
    assert block[2]['soa'] == 800 and block[2]['cue_loc'] == 'right'
