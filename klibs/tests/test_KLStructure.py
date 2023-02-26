# -*- coding: utf-8 -*-
import pytest
from collections import Counter

from klibs.KLStructure import FactorSet


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

        # Test override with non-iterable
        tst3 = tst.override({'easy_trial': True})
        assert tst3.set_length == 12
        assert tst3.names == tst.names
        assert len(tst3._factors['easy_trial']) == 1

        # Test error on non-existant factor
        with pytest.raises(ValueError):
            tst.override({'alerting_trial': [True, False]})
