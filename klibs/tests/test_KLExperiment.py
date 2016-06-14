import pytest
import mock
import klibs

with mock.patch("os.path.exists") as path_exists:
	path_exists.return_value = True

@pytest.fixture
def experiment():
	from klibs.KLExperiment import Experiment
	return Experiment("TestProject", 13, None, False, False, False, False)


def test_Experiment(experiment):
	with pytest.raises(OSError):
		experiment.run()