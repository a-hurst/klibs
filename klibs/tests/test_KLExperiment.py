import os
import mock
import pytest
from collections import OrderedDict

import klibs
from klibs.KLJSON_Object import AttributeDict
from klibs.KLTrialFactory import TrialIterator, TrialSet
from klibs.KLExceptions import TrialException
from klibs.KLExperiment import Experiment

from conftest import get_resource_path


class MockExperiment(Experiment):
    def __trial__(self, trial):
        pass

@pytest.fixture
def run_environment():
    from klibs import P
    template_path = get_resource_path('template')
    P.ind_vars_file_path = os.path.join(template_path, "independent_variables.py")
    P.ind_vars_file_local_path = os.path.join(template_path, "doesnt_exist.py")
    P.manual_trial_generation = True
    P.project_name = "PROJECT_NAME"

@pytest.fixture
def experiment(run_environment):
    exp = MockExperiment()
    exp.database = AttributeDict({'tables': []})
    return exp


def test_Experiment(experiment):
    with mock.patch.object(experiment, 'quit', return_value=None):
        experiment.blocks = []
        experiment.run()


def test_execute(run_environment):
    from klibs import P

    class TestExperiment(Experiment):

        def setup(self):
            self.last_block = 0
            self.last_trial = 0
            self.total_trials = 0
            self.was_recycled = False
            self.database = AttributeDict({'tables': []})
            self.blocks = []

        def block(self):
            # Check block number incrementing as expected
            assert P.block_number == (self.last_block + 1)
            self.last_block = P.block_number
            self.last_trial = 0
            # Check block label getting set as expected
            expected = 'test' if P.block_number == 1 else None
            assert self.block_label == expected

        def __trial__(self, trial):
            # Check trial id increments correctly
            self.total_trials += 1
            assert P.trial_id == self.total_trials
            # Check trial numbers increment correctly
            trial_num = self.last_trial + 1
            if P.recycle_count == 0:
                assert P.trial_number == trial_num
            else:
                assert trial_num == (P.trial_number + P.recycle_count)
            self.last_trial += 1
            # Test that trial factors getting passed properly
            assert isinstance(trial, dict)
            assert 'fac1' in list(trial.keys())
            assert 'fac2' in list(trial.keys())
            # Test that practice getting set correctly
            assert P.practicing == (P.block_number == 1)
            # Test trial recycling
            if self.was_recycled:
                assert P.recycle_count == 1
                self.was_recycled = False
            if trial_num == 3:
                self.was_recycled = True
                raise TrialException("recycling")

    # Initialize test blocks/trials
    trials = [
        {'fac1': True, 'fac2': 200},
        {'fac1': False, 'fac2': 200},
        {'fac1': True, 'fac2': 400},
        {'fac1': False, 'fac2': 400},
    ]

    # Test with blocks as list
    tst = TestExperiment()
    tst.setup()
    tst.blocks = [
        TrialSet(trials, label='test', practice=True),
        TrialIterator(trials), # alias for backwards compat
    ]
    tst.__execute_experiment__()
    assert tst.last_block == 2
    assert tst.last_trial == 5 # 4 + 1 recycled
    assert tst.total_trials == 10


def test_insert_practice_block(experiment):
    from klibs import P

    # Set dummy trial factors and generate trials
    P.trials_per_block = 30
    P.blocks_per_experiment = 1
    experiment.trial_factory.exp_factors = OrderedDict([
        ('fac1', [True, False]),
        ('fac2', [200, 400, 800]),
    ])
    experiment.trial_factory.generate()
    blocks_init = experiment.trial_factory.export_trials()
    assert len(blocks_init) == 1
    assert len(blocks_init[0]) == 30

    # Try adding a single practice block
    experiment.insert_practice_block(1, 12)
    blocks_a = experiment.trial_factory.export_trials()
    assert len(blocks_a) == 2
    assert len(blocks_a[0]) == 12
    assert len(blocks_a[1]) == 30

    # Try adding two more practice blocks with a factor mask
    mask = {'fac2': [800]}
    experiment.insert_practice_block([1, 3], 6, factor_mask=mask)
    blocks_b = experiment.trial_factory.export_trials()
    assert len(blocks_b) == 4
    assert len(blocks_b[0]) == 6
    assert len(blocks_b[1]) == 12
    assert len(blocks_b[2]) == 6
    for trial in blocks_b[0].trials:
        assert trial['fac2'] == 800

    # Test to make sure method does nothing if practice blocks disabled
    P.run_practice_blocks = False
    experiment.insert_practice_block(1)
    blocks_c = experiment.trial_factory.export_trials()
    assert len(blocks_c) == 4

    # Test that block count parameter updated when experiment run
    experiment.database = AttributeDict({'tables': []})
    experiment.__execute_experiment__()
    assert P.blocks_per_experiment == 4
