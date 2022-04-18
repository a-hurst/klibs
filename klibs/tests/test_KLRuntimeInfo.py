import pytest
import klibs
import klibs.KLParams as P


def test_get_sysinfo():

    sysinfo = klibs.KLRuntimeInfo.get_sysinfo()
    assert isinstance(sysinfo['python'], str)
    assert isinstance(sysinfo['os'], str)
    print("System Info:")
    print(" - OS: " + sysinfo['os'])
    print(" - Python: " + sysinfo['python'])


def test_runtime_info_init():

    P.screen_diagonal_in = 21.5
    P.participant_id = 1
    P.session_number = 1
    P.random_seed = 1234
    P.trials_per_block = 120
    P.blocks_per_experiment = 3
    P.view_distance = 57
    P.screen_x, P.screen_y, P.refresh_rate = (1920, 1080, 60)

    info = klibs.KLRuntimeInfo.runtime_info_init()
    assert isinstance(info, dict) # anything else really need testing?
