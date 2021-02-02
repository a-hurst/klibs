import pytest
import mock
import os
from pkg_resources import resource_filename

import klibs
from klibs.KLJSON_Object import AttributeDict


@pytest.fixture
def experiment():
	from klibs.KLExperiment import Experiment
	from klibs import P
	template_path = resource_filename('klibs', 'resources/template')
	P.ind_vars_file_path = os.path.join(template_path, "independent_variables.py")
	P.ind_vars_file_local_path = os.path.join(template_path, "doesnt_exist.py")
	P.manual_trial_generation = True
	P.project_name = "PROJECT_NAME"
	return Experiment()


def test_Experiment(experiment):
	with mock.patch.object(experiment, 'quit', return_value=None):
		experiment.blocks = []
		experiment.database = AttributeDict({'table_schemas': {}})
		experiment.run()
