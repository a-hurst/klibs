# -*- coding: utf-8 -*-
import os
import shutil
import pytest
from mock import patch

from klibs import cli


# Helper functions and fixtures

_input_queue = []

def tst_err(err_string):
    raise RuntimeError(err_string)

def tst_getinput(prompt):
    global _input_queue
    return _input_queue.pop(0)

def tst_cso(string, print_string=False):
    return string

def create_experiment(name, path):

    global _input_queue
    _input_queue += ["Test Name", "Y"]

    with patch("klibs.cli.getinput", tst_getinput):
        with patch("klibs.cli.err", tst_err):
            with patch("klibs.cli.cso", tst_cso):
                cli.create(name, str(path))
                expt_path = os.path.join(path, name)
                assert os.path.isdir(expt_path)

    return expt_path


# Actual tests

def test_create(tmpdir):

    global _input_queue

    with patch("klibs.cli.getinput", tst_getinput):
        with patch("klibs.cli.err", tst_err):
            with patch("klibs.cli.cso", tst_cso):

                # Test creating a new project
                _input_queue += ["Test Name", "Y"]
                cli.create("TestExperiment", str(tmpdir))
                assert os.path.isdir(os.path.join(tmpdir, "TestExperiment"))

                # Test cancelling project creation
                _input_queue += ["Test Name", "Q"]
                cli.create("TestExperiment2", str(tmpdir))
                assert not os.path.isdir(os.path.join(tmpdir, "TestExperiment2"))

                # Test error on invalid name
                with pytest.raises(RuntimeError) as exc_info:
                    cli.create("bad name", str(tmpdir))
                assert "valid project name" in exc_info.value.args[0]

                # Test error on existing project name
                with pytest.raises(RuntimeError) as exc_info:
                    cli.create("TestExperiment", str(tmpdir))
                assert "already exists" in exc_info.value.args[0]


def test_ensure_directory_structure(tmpdir):

    global _input_queue
    dir_structure = {
		"ExpAssets": {
			".versions": None,
			"Config": None,
			"Resources": {"audio": None, "code": None, "font": None, "image": None},
			"Local": {"logs": None},
			"Data": {"incomplete": None},
			"EDF": {"incomplete": None}
		}
	}
    exp_path = create_experiment("TestExpt", tmpdir)

    # Make sure no folders missing from freshly-created project
    missing = cli.ensure_directory_structure(dir_structure, exp_path)
    assert len(missing) == 0

    # Remove some folders and make sure they're noticed
    logpath = os.path.join(exp_path, "ExpAssets", "Local", "logs")
    datapath = os.path.join(exp_path, "ExpAssets", "Data")
    shutil.rmtree(logpath)
    shutil.rmtree(datapath)
    missing = cli.ensure_directory_structure(dir_structure, exp_path)
    assert len(missing) == 3
    assert "logs" in [os.path.basename(f) for f in missing]
    assert "Data" in [os.path.basename(f) for f in missing]

    # Try creating the missing folders
    cli.ensure_directory_structure(dir_structure, exp_path, create_missing=True)
    missing = cli.ensure_directory_structure(dir_structure, exp_path)
    assert len(missing) == 0
    assert os.path.isdir(logpath)
    assert os.path.isdir(datapath)


def test_initialize_path(tmpdir):

    with patch("klibs.cli.err", tst_err):

        # Test the most basic use case
        expt_path = create_experiment("TestExpt", tmpdir)
        expt_name = cli.initialize_path(expt_path)
        assert expt_name == "TestExpt"

        # Test with a name containing an underscore
        expt_path = create_experiment("Test_Expt", tmpdir)
        expt_name = cli.initialize_path(expt_path)
        assert expt_name == "Test_Expt"

        # Test error on missing experiment.py
        exp_py_path = os.path.join(expt_path, "experiment.py")
        config_path = os.path.join(expt_path, "ExpAssets", "Config")
        os.rename(exp_py_path, os.path.join(expt_path, "tmp.py"))
        with pytest.raises(RuntimeError) as exc_info:
            cli.initialize_path(expt_path)
        assert "experiment.py" in exc_info.value.args[0]
        os.rename(os.path.join(expt_path, "tmp.py"), exp_py_path)

        # Test error on missing config folder
        os.rename(config_path, os.path.join(expt_path, "ExpAssets", "tmp"))
        with pytest.raises(RuntimeError) as exc_info:
            cli.initialize_path(expt_path)
        assert "ExpAssets/Config" in exc_info.value.args[0]
        os.rename(os.path.join(expt_path, "ExpAssets", "tmp"), config_path)

@pytest.mark.skip("not implemented")
def test_run(tmpdir):
    # NOTE: will require a lot of patching
    pass
