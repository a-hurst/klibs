import os
import mock
import pytest

import klibs
from klibs.KLJSON_Object import AttributeDict
from klibs.KLTrialFactory import BlockIterator, TrialIterator
from klibs.KLExceptions import TrialException

from conftest import get_resource_path


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
    from klibs.KLExperiment import Experiment
    return Experiment()


def test_Experiment(experiment):
    with mock.patch.object(experiment, 'quit', return_value=None):
        experiment.blocks = []
        experiment.database = AttributeDict({'tables': []})
        experiment.run()


def test_execute(run_environment):
    from klibs import P
    from klibs.KLExperiment import Experiment

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
        TrialIterator(trials, practice=True),
        TrialIterator(trials),
    ]
    tst.__execute_experiment__()

    # Test with blocks as BlockIterator
    tst = TestExperiment()
    tst.setup()
    tst.blocks = BlockIterator([trials])
    tst.blocks.insert(0, trials, practice=True)
    tst.__execute_experiment__()
