import pytest
import mock
import klibs

from klibs.KLJSON_Object import AttributeDict


@pytest.fixture
def experiment():
	from klibs.KLExperiment import Experiment
	from klibs import P
	P.manual_trial_generation = True
	return Experiment()


def test_Experiment(experiment):
	with mock.patch.object(experiment, 'quit', return_value=None):
		experiment.blocks = []
		experiment.database = AttributeDict({'table_schemas': {}})
		experiment.run()
