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
    return

def create_experiment(name, path):

    global _input_queue
    _input_queue += ["Test Name", "Y"]

    with patch("klibs.cli.getinput", tst_getinput):
        with patch("klibs.cli.err", tst_err):
            with patch("klibs.cli.cso", tst_cso):
                cli.create(name, path)
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
                cli.create("TestExperiment", tmpdir)
                assert os.path.isdir(os.path.join(tmpdir, "TestExperiment"))

                # Test errors on bad input
                with pytest.raises(RuntimeError):
                    cli.create("bad name", tmpdir)


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

    # Test the most basic use case
    expt_path = create_experiment("TestExpt", tmpdir)
    with patch("klibs.cli.err", tst_err):
        expt_name = cli.initialize_path(expt_path)
        assert expt_name == "TestExpt"
