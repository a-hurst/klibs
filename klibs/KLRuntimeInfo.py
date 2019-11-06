# -*- coding: utf-8 -*-

__author__ = 'Jonathan Mulle & Austin Hurst'

import platform
from datetime import datetime

from klibs import P
from klibs.KLUtilities import now


session_info_schema = """
CREATE TABLE session_info (
	id integer primary key autoincrement not null,
	participant_id integer not null references participants(id),
	session_number integer not null,
	complete integer not null, /* false by default, set to true at very end */
	
	date text not null,
    time text not null,
	klibs_commit text not null,
	random_seed text not null,

	trials_per_block integer not null,
	blocks_per_session integer not null,
	
	os_version text not null,
	python_version text not null,
	
	screen_size text not null,
	screen_res text not null,
	viewing_dist text not null,
	
	eyetracker text, /* not available until el.setup() is run */
	el_velocity_thresh integer,
	el_accel_thresh integer,
	el_motion_thresh float
	
)"""


def get_sysinfo():

    # Get python info string
    py_version = platform.python_version()
    if platform.python_implementation() != 'CPython':
        py_version = " ".join([platform.python_implementation(), py_version])
    
    # Get OS info string
    if platform.system() == 'Darwin':
        release = platform.mac_ver()[0]
        major_release = int(release.split('.')[1])
        if major_release < 8:
            prefix = 'Mac OS X '
        elif major_release > 11:
            prefix = 'macOS '
        else:
            prefix = 'OS X '
        os_version = prefix + release

    elif platform.system() == 'Linux':
        try:
            release = " ".join(platform.linux_distribution()[:2])
        except AttributeError:
            release = " "
        if release == " ":
            release = " ".join(['Linux', platform.release()])
        os_version = release + " ({0})".format(platform.architecture()[0])

    elif platform.system() == 'Windows':
        version, build, sp = platform.win32_ver()[:3]
        arch = platform.architecture()[0]
        if sp == '': # if no service pack
            os_version = "Windows {0} (Build {1}) ({2})".format(version, build, arch)
        else:
            os_version = "Windows {0} {1} (Build {2}) ({3})".format(version, sp, build, arch)
    
    else:
        arch = platform.architecture()[0]
        os_version = "{0} {1} ({2})".format(platform.system(), platform.version(), arch)

    return {'python': py_version, 'os': os_version}


def runtime_info_init():
    """Returns a dict containing the initial runtime info for the current participant.

    """
    sysinfo = get_sysinfo()
    scrsize = P.screen_diagonal_in

    info = {
        'participant_id': P.participant_id,
        'session_number': P.session_number,
        'complete': False,
        'date': datetime.now().strftime("%Y-%m-%d"),
        'time': datetime.now().strftime("%H:%M:%S"),
        'klibs_commit': P.klibs_commit,
        'random_seed': P.random_seed,
        'trials_per_block': P.trials_per_block,
        'blocks_per_session': P.blocks_per_experiment,
        'os_version': sysinfo['os'],
        'python_version': sysinfo['python'],
        'screen_size': '{0}" diagonal'.format(int(scrsize) if int(scrsize) == scrsize else scrsize),
        'screen_res': '{0}x{1} @ {2}Hz'.format(P.screen_x, P.screen_y, P.refresh_rate),
        'viewing_dist': '{0} cm'.format(int(round(P.view_distance)))
    }

    if P.eye_tracking:
        from klibs.KLEnvironment import el
        info['eyetracker'] = el.version if el.initialized else 'NA'
        info['el_velocity_thresh'] = P.saccadic_velocity_threshold
        info['el_accel_thresh'] = P.saccadic_acceleration_threshold
        info['el_motion_thresh'] = P.saccadic_motion_threshold
    
    return info
