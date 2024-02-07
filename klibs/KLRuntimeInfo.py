# -*- coding: utf-8 -*-

__author__ = 'Jonathan Mulle & Austin Hurst'

import os
import re
import sys
import platform
from datetime import datetime

from klibs import P


session_info_schema = """
CREATE TABLE session_info (
    id integer primary key autoincrement not null,
    participant_id integer not null references participants(id),
    condition text,
    session_number integer not null,
    complete integer not null, /* false by default, set to true at very end */
    
    date text not null,
    time text not null,
    klibs_commit text not null,
    random_seed integer not null,

    trials_per_block integer not null,
    blocks_per_session integer not null,
    session_count integer not null,
    
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


def _linux_dict_from_config(path):
    out = {}
    if os.path.isfile(path):
        with open(path, "r") as f:
            for line in f.read().split("\n"):
                if len(line.split("=")) == 2:
                    key, value = line.split("=")
                    out[key] = value.strip('"')
    return out


def _linux_get_distro():

    # Gather distro info from os-release and lsb-release files
    lsb_release = _linux_dict_from_config('/etc/lsb-release')
    os_release = _linux_dict_from_config('/usr/lib/os-release')
    os_release_etc =  _linux_dict_from_config('/etc/os-release')
    os_release.update(os_release_etc)

    # For distros with missing/inaccurate os-release files, use lsb-release
    if "DISTRIB_DESCRIPTION" in lsb_release.keys():
        os_release["PRETTY_NAME"] = lsb_release["DISTRIB_DESCRIPTION"]
    if "DISTRIB_RELEASE" in lsb_release.keys():
        os_release["VERSION_ID"] = lsb_release["DISTRIB_RELEASE"]

    # Try to assemble distro name/version from collected info
    if "PRETTY_NAME" in os_release.keys():
        distro = os_release["PRETTY_NAME"]
        distro = re.sub(r" \(.*\)", "", distro) # Strip parts in parentheses
        if "VERSION_ID" in os_release.keys():
            ver_num = os_release["VERSION_ID"]
            if ver_num not in distro:
                distro += " " + ver_num
    else:
        distro = "Linux"

    return distro


def get_sysinfo():

    # Get python info string
    bit = "64" if sys.maxsize > 2**32 else "32"
    py_version = "{0} ({1}-bit)".format(platform.python_version(), bit)
    if platform.python_implementation() != 'CPython':
        py_version = " ".join([platform.python_implementation(), py_version])

    # Get OS info string
    if platform.system() == 'Darwin':
        release, _, arch = platform.mac_ver()
        version = [int(n) for n in release.split('.')]
        if version[0] > 10:
            arch = "Intel" if arch == "x86_64" else "Apple Silicon"
            os_version = "macOS {0} ({1})".format(release, arch)
        else:
            major_release = version[1]
            if major_release < 8:
                prefix = 'Mac OS X '
            elif major_release > 11:
                prefix = 'macOS '
            else:
                prefix = 'OS X '
            os_version = prefix + release

    elif platform.system() == 'Linux':
        distro = _linux_get_distro()
        kernel = platform.release().split("-")[0]
        arch = platform.machine()
        os_version = "{0} (Kernel {1}, {2})".format(distro, kernel, arch)

    elif platform.system() == 'Windows':
        version, build, sp = platform.win32_ver()[:3]
        if int(build.split(".")[-1]) > 22000:
            version = "11"
        arch = platform.architecture()[0].replace("bit", "-bit")
        build = build.replace("10.0.", "")
        if sp in ('', 'SP0'): # if no service pack
            os_version = "Windows {0} (Build {1}) ({2})".format(version, build, arch)
        else:
            os_version = "Windows {0} {1} (Build {2}) ({3})".format(version, sp, build, arch)
    
    else:
        arch = platform.machine()
        if arch == "":
            arch = platform.architecture()[0].replace("bit", "-bit")
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
