import pytest
import random
from klibs import P


# Helpers and fixtures

_path_vars = [
	"project_name",
	"database_path",
	"database_backup_path",
	"params_file_path",
	"params_local_file_path",
	"ind_vars_file_path",
	"ind_vars_file_local_path",
	"schema_file_path",
	"user_queries_file_path",
	"log_file_path",
]
_runtime_vars = [
	"random_seed",
	"klibs_commit",
	"database_local_path",
	"logo_file_path",
	"font_dirs",
]

def _reset_params():
    for var in _path_vars + _runtime_vars:
        setattr(P, var, None)

@pytest.fixture
def with_clean_params():
    _reset_params()
    yield
    _reset_params()


# Actual tests

def test_initialize_paths(with_clean_params):

    # Make sure paths aren't initialized already
    assert P.project_name == None
    assert P.database_path == None

    # Test initializing paths
    P.initialize_paths("Test")
    assert P.project_name == "Test"
    for var in _path_vars:
        if var == "project_name":
            continue
        val = getattr(P, var)
        assert P.asset_dir in val


def test_initialize_runtime(with_clean_params):

    # Make sure paths and attributes aren't initialized already
    assert P.project_name == None
    assert P.database_path == None
    assert P.klibs_commit == None

    # Test initializing the full runtime params
    P.initialize_runtime("Test", 530453080)

    # Check that project name and paths initialized properly
    assert P.project_name == "Test"
    for var in _path_vars:
        if var == "project_name":
            continue
        val = getattr(P, var)
        assert P.asset_dir in val

    # Check that the random seed was set correctly
    assert P.random_seed == 530453080
    assert [random.randint(0, 100) for i in range(0, 5)] == [16, 28, 22, 2, 6]

    # Check that the resources and paths loaded correctly
    assert P.klibs_commit and len(P.klibs_commit) > 7
    assert type(P.klibs_commit) == str
    assert P.project_name in P.database_local_path
    assert ".png" in P.logo_file_path
    assert len(P.font_dirs) >= 2
