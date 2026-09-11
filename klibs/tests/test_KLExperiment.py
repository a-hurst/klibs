import os
import mock
import pytest
import tempfile
from collections import OrderedDict

import klibs
from klibs.KLJSON_Object import AttributeDict
from klibs.KLTrialFactory import TrialIterator, TrialSet
from klibs.KLExceptions import TrialException, TerminateBlock
from klibs.KLExperiment import Experiment

from conftest import get_resource_path


mock_idvars = """
from klibs.KLStructure import FactorSet, Block

exp_factors = FactorSet({
    'fac1': [True, False],
    'fac2': [100, 200, 400],
})

"""

class MockExperiment(Experiment):
    def __trial__(self, trial):
        pass

@pytest.fixture
def run_environment_manual():
    # Creates a runtime environment with no factors and manual trial generation
    from klibs import P
    template_path = get_resource_path('template')
    P.ind_vars_file_path = os.path.join(template_path, "independent_variables.py")
    P.ind_vars_file_local_path = os.path.join(template_path, "doesnt_exist.py")
    P.manual_trial_generation = True
    P.demographics_collected = True
    P.project_name = "PROJECT_NAME"

@pytest.fixture
def run_environment(tmp_path):
    # Creates a runtime environment with a test idvars file
    from klibs import P
    config = tmp_path / "Config"
    idvars = config / "independent_variables.py"
    if not os.path.exists(config):
        config.mkdir()
        idvars.write_text(mock_idvars)
    P.ind_vars_file_path = idvars
    P.ind_vars_file_local_path = os.path.join(config, "doesnt_exist.py")
    P.manual_trial_generation = False
    P.demographics_collected = True
    P.project_name = "PROJECT_NAME"

@pytest.fixture
def experiment(run_environment_manual):
    exp = MockExperiment()
    exp.database = AttributeDict({'tables': []})
    return exp


def test_Experiment(experiment):
    with mock.patch.object(experiment, 'quit', return_value=None):
        experiment.blocks = []
        experiment.run()


def test_execute(run_environment_manual):
    from klibs import P

    class TestExperiment(Experiment):

        def setup(self):
            self.last_block = 0
            self.last_trial = 0
            self.total_trials = 0
            self.was_recycled = False
            self.database = AttributeDict({'tables': []})
            self.test_type = "default"
            self.blocks = []

        def block(self):
            # Check block number incrementing as expected
            assert P.block_number == (self.last_block + 1)
            self.last_block = P.block_number
            self.last_trial = 0
            # Check block label getting set as expected
            expected = 'test' if P.block_number == 1 else None
            assert self.block_label == expected
            # Check trials_per_block is updated based on trial count
            if not P.max_trials_per_block:
                assert P.trials_per_block == 4

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
            # Test block termination
            if self.test_type == "terminate" and P.block_number == 2:
                if trial_num == 3:
                    raise TerminateBlock()
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
    blocks = [
        TrialSet(trials, label='test', practice=True),
        TrialIterator(trials), # alias for backwards compat
    ]

    # Test with blocks as list
    P.trials_per_block = 30
    tst = TestExperiment()
    tst.setup()
    tst.blocks = blocks
    tst.__execute_experiment__()
    assert tst.last_block == 2
    assert tst.last_trial == 5 # 4 + 1 recycled
    assert tst.total_trials == 10

    # Test setting max trials per block
    P.max_trials_per_block = 2
    tst = TestExperiment()
    tst.setup()
    tst.blocks = blocks
    tst.__execute_experiment__()
    P.max_trials_per_block = False
    assert tst.last_block == 2
    assert tst.last_trial == 2
    assert tst.total_trials == 4

    # Test terminating blocks early
    tst = TestExperiment()
    tst.setup()
    tst.test_type = "terminate"
    tst.blocks = blocks
    tst.__execute_experiment__()
    assert tst.last_block == 2
    assert tst.last_trial == 3
    assert tst.total_trials == 8 # Last two trials skipped


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


def test_trials_txt(experiment, tmp_path):
    from klibs import P

    # Set dummy trial factors and generate trials
    P.trials_per_block = 12
    P.blocks_per_experiment = 2
    P.run_practice_blocks = True
    experiment.trial_factory.exp_factors = OrderedDict([
        ('fac1', [True, False]),
        ('fac2', [200, 400, 800]),
    ])
    experiment.trial_factory.generate()
    experiment.insert_practice_block(1, 6)

    # Try exporting to a temporary file
    tmpfile = os.path.join(tmp_path, "trials.txt")
    assert not os.path.exists(tmpfile)
    experiment.write_trials_txt(tmpfile)
    assert os.path.exists(tmpfile)

    # Check file to make sure it's working
    with open(tmpfile, "r") as f:
        output = f.read()
        assert "Blocks:" in output
        assert "Factors:" in output
        assert "Block 1 (6 trials" in output
        assert "Block 2 (12 trials" in output


def test_exp_factors(run_environment):
    exp = MockExperiment()
    assert len(exp.exp_factors.keys()) == 2
    assert len(exp.exp_factors['fac1']) == 2
    assert len(exp.exp_factors['fac2']) == 3
    assert exp.exp_factors['fac2'][0] == 100


def test_participant_info(run_environment, db):
    from klibs import P
    exp = MockExperiment()
    exp.database = db
    tst = {
        'userhash': 'ABCD', 'gender': 'n', 'age': 20, 'handedness': 'l', 'created': ''
    }
    P.p_id = db.insert(tst, table='participants')
    demographics = exp.participant_info
    assert 'gender' in demographics.keys()
    assert 'handedness' in demographics.keys()
    assert not 'id' in demographics.keys()
    assert demographics['age'] == 20
    assert demographics['handedness'] == "l"
    # Test that access fails when demographics not collected yet
    P.demographics_collected = False
    with pytest.raises(RuntimeError):
        age = exp.participant_info["age"]
