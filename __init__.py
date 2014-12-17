#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# requirements: jmtpfs

import subprocess
import re
import os


class Destination(object):
    def __init__(self, dir, root=None):
        self.__dir = dir
        self.__root = root

    @property
    def dir(self):
        dir = self.__dir
        if not re.search('/', dir, flags=0):
            dir = os.path.join(self.root, dir)
        return os.path.abspath(dir)

    @property
    def root(self):
        if not self.__root:
            self.__root = subprocess.check_output("xdg-user-dir DESKTOP", shell=True).splitlines()[0]
        return self.__root

    @property
    def mounted(self):
        # return true if '[Errno 5] Input/output error' (probably mounted but not readable)
        try:
            os.stat(self.dir)
        except OSError as error:
            if error.errno==5:
                return True
        return os.path.ismount(self.dir)

    @property
    def exists(self):
        return os.path.exists(self.dir)

    @property
    def isdir(self):
        if self.exists and os.path.isdir(self.dir):
            return True
        return False

    @property
    def empty(self):
        if self.isdir and len(os.listdir(self.dir))==0:
            return True
        return False

    @property
    def canBeMounted(self):
        if not self.mounted and (not self.exists or self.empty):
            return True
        return False

    @property
    def canBeRemoved(self):
        if not self.mounted and self.empty:
            return True
        return False

    def getSafeDestination(self):
        destination = self
        while True:
            if destination.canBeMounted:
                return destination
            else:
                destination = Destination(destination.dir+'_')

    @property
    def dirCreated(self):
        if not self.exists:
            os.mkdir(self.dir)
        return self.dir


class JMTPFS(object):
    @property
    def devices(self):
        devices = []
        FNULL = open(os.devnull, 'w')
        jmtpfs_output = subprocess.check_output('jmtpfs -l', stderr=FNULL, shell=True)
        jmtpfs_lines = jmtpfs_output.splitlines()
        if len(jmtpfs_lines)>1:
            for i in range(1, len(jmtpfs_lines)):
                device = jmtpfs_lines[i].split(', ')
                devices.append(device)
        return devices

    def getDeviceById(self, a, b):
        for device in self.devices:
            if device[2]==a and device[3]==b:
                return device

    def getDeviceByName(self, name):
        for device in self.devices:
            if device[4]==name:
                return device

    def getDeviceByDescription(self, description):
        for device in self.devices:
            if device[5]==description:
                return device


if __name__=='__main__':
    import time
    import sys
    import argparse

    args = argparse.ArgumentParser(description='Mount device with jmtpfs, fork to background and wait for disconnect/unmount.')
    args.add_argument('-n', dest='name', help='Device name. (default: "Nexus 4/5/7/10 (MTP)")', default='Nexus 4/5/7/10 (MTP)')
    args.add_argument('-f', dest='foreground', help="Don't go to background.", default=False, action="store_true")
    args.add_argument('destination', help='Destination directory. (default: nexus5)', nargs='?', default='nexus5')
    arguments = args.parse_args()

    dst = Destination(arguments.destination)
    device = JMTPFS().getDeviceByName(arguments.name)

    if device:
        if dst.canBeMounted:
            subprocess.check_call('jmtpfs "%s" -device=%s,%s' % (dst.dirCreated, device[0], device[1]), shell=True)
        else:
            print "Can't be mounted to %s" % dst.dir
            sys.exit(1)
        fork_pid = os.fork()
        if fork_pid!=0:
            print 'Going to background with pid: %s' % fork_pid
            sys.exit(0)
        while dst.mounted:
            time.sleep(2)
            d = JMTPFS().getDeviceById(device[2], device[3])
            if not d:
                subprocess.check_call('fusermount -u "%s"' % dst.dir, shell=True)
                if dst.canBeRemoved:
                    os.rmdir(dst.dir)
    else:
        print 'No devices found!'
        sys.exit(1)
