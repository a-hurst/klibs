#!/usr/bin/env python
__author__ = 'jono'
import subprocess
import os
import shutil
import re
import time
import stat

try:
	os.remove("/Library/Caches/Homebrew/klibs-0.9.1.4.tar.gz")
	os.remove("/KLAB/Non-Annual/SoftwareRepo/klibs-0.9.1.4.tar.gz")
except OSError:
	pass

# tar = "tar -zcvf /KLAB/Non-Annual/SoftwareRepo/klibs-0.9.1.4.tar.gz /KLAB/Non-Annual/SoftwareRepo/klibs"
tar = "tar -zcvf /KLAB/Non-Annual/SoftwareRepo/klibs-0.9.1.4.tar.gz klibs"
sha1 = "shasum /Library/Caches/Homebrew/klibs-0.9.1.4.tar.gz"
# process1 = subprocess.Popen("cd /KLAB/Non-Annual/SoftwareRepo/klibs tar -zcvf klibs-0.9.1.4.tar.gz klibs".split(), stdout=subprocess.PIPE)
tar_process = subprocess.Popen(tar.split(), stdout=subprocess.PIPE)
tar_output = tar_process.communicate()[0]
os.chmod("/KLAB/Non-Annual/SoftwareRepo/klibs-0.9.1.4.tar.gz", stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IWOTH |  stat.S_IXOTH )
shutil.copyfile("/KLAB/Non-Annual/SoftwareRepo/klibs-0.9.1.4.tar.gz", "/Library/Caches/Homebrew/klibs-0.9.1.4.tar.gz")

sha1_process = subprocess.Popen(sha1.split(), stdout=subprocess.PIPE)
shasum = sha1_process.communicate()[0].split()[0]

f = open("/usr/local/Library/Formula/klibs.rb", "r+")
new_f = re.sub('version "0.9.1.4"\n[ ]*sha1 "([a-z0-9]{40})"', 'version "0.9.1.4"\n  sha1 "{0}"'.format(shasum), f.read())
f.seek(0)
f.write(new_f)
f.truncate()
f.close()

