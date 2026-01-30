import os
import mock
import pytest

import klibs
from klibs.KLJSON_Object import AttributeDict

from conftest import get_resource_path


@pytest.fixture
def experiment():
    from klibs.KLExperiment import Experiment
    from klibs import P
    template_path = get_resource_path('template')
    P.ind_vars_file_path = os.path.join(template_path, "independent_variables.py")
    P.ind_vars_file_local_path = os.path.join(template_path, "doesnt_exist.py")
    P.demographics_collected = True
    P.manual_trial_generation = True
    P.project_name = "PROJECT_NAME"
    return Experiment()


def test_Experiment(experiment):
    with mock.patch.object(experiment, 'quit', return_value=None):
        experiment.blocks = []
        experiment.database = AttributeDict({'tables': []})
        experiment.run()
