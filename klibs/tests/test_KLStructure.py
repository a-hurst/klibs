# -*- coding: utf-8 -*-
import sys
import pytest
import random
from collections import Counter

import klibs.KLParams as P
from klibs.KLInternal import load_source
from klibs.KLStructure import FactorSet, Block
from klibs.KLTrialFactory import _generate_blocks, _load_structure, _parse_structure

from conftest import create_tempfile


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



class TestBlock(object):

    def test_init(self):

        factors = FactorSet({
            'cue_loc': ['left', 'right', 'none'],
            'easy_trial': [True, False],
        })

        # Test simple initialization
        P.trials_per_block = 0
        tst = Block(factors)
        assert tst.trialcount == 6
        assert tst.practice == False
        assert tst.label == None

        # Test initialization with dict
        tst = Block({'soa': [200, 800], 'target_loc': ['L', 'R']})
        assert tst.trialcount == 4
        assert isinstance(tst._factors, FactorSet)

        # Test defaulting trial count to P.trials_per_block
        P.trials_per_block = 30
        tst = Block(factors)
        assert tst.trialcount == 30

        # Test custom trial counts:
        tst = Block(factors, trials=36)
        assert tst.trialcount == 36

        # Test labels and practice flags
        tst = Block(factors, label='endo', practice=True)
        assert tst.label == 'endo'
        assert tst.practice == True

    
    def test_get_trials(self):

        factors = FactorSet({
            'cue_loc': ['left', 'right', 'none'],
            'easy_trial': [True, False],
        })

        # Test generating trials with specified trial count
        tst = Block(factors, trials=30)
        trials = tst.get_trials()
        assert len(trials) == 30
        assert isinstance(trials[0], dict)
        assert 'cue_loc' in list(trials[0].keys())

        # Test partial shuffling
        random.seed(308053045)
        trials = tst.get_trials()
        easy_count = 0
        left_count = 0
        for trial in trials[:6]:
            easy_count += int(trial['easy_trial'] == True)
            left_count += int(trial['cue_loc'] == 'left')
        assert easy_count == 3
        assert left_count == 2


    def test_factors(self):

        tst = Block({'a': [1, 2], 'b': [3, 4], 'c': [5, 6]})
        assert tst.factors == ['a', 'b', 'c']


def test_load_structure():
    # NOTE: Move to KLTrialFactory tests once created
    header = "from klibs.KLStructure import FactorSet, Block"

    # Test loading structure
    tmp = create_tempfile([
        header, "",
        "structure = [",
        "    Block({}, label='a', trials=10),",
        "    Block({}, label='B', trials=20)",
        "]"
    ])
    tst = _load_structure(load_source(tmp))
    assert len(tst) == 2
    assert isinstance(tst[0], Block)

    # Test loading missing structure
    tmp = create_tempfile([
        header, "",
        "exp_factors = FactorSet({})"
    ])
    tst = _load_structure(load_source(tmp))
    assert not tst

    # Test loading empty structure
    tmp = create_tempfile([
        header, "",
        "exp_factors = FactorSet({})",
        "",
        "structure = []",
    ])
    tst = _load_structure(load_source(tmp))
    assert not tst


def test_parse_structure():
    # NOTE: Move to KLTrialFactory tests once created
    exp_factors = {'fac1': ['a', 'b', 'c'], 'fac2': [True, False]}
    tst = [
        Block(exp_factors, label='a', trials=10, practice=True),
        Block(exp_factors, label='b', trials=20)
    ]
    blocks = _parse_structure(tst, exp_factors)
    assert len(blocks) == 2

    # Test exception if structure not made of Blocks
    with pytest.raises(TypeError):
        _parse_structure([exp_factors], exp_factors)

    # Test exception on missing factor level
    fac_missing = {'fac1': ['a', 'b', 'c']}
    tst_missing = [
        Block(fac_missing, trials=10),
        Block(exp_factors, trials=10)
    ]
    with pytest.raises(RuntimeError):
        _parse_structure(tst_missing, exp_factors)

    # Test exception on extra factor level
    fac_extra = exp_factors.copy()
    fac_extra['fac3'] = [200, 800]
    tst_extra = [
        Block(exp_factors, trials=10),
        Block(fac_extra, trials=10)
    ]
    with pytest.raises(RuntimeError):
        _parse_structure(tst_extra, exp_factors)

    # Test exception when factors given but exp_factors is empty
    with pytest.raises(RuntimeError):
        _parse_structure(tst, {})
