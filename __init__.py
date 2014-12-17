#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# requirements: jmtpfs
#
# примонтировать, уйти в бэкграунд, ждать отмонтирования

import subprocess
import re
import os
import time
import sys


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
        # если директория не читабельная - она не монтируема
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
    #TODO: запуск через опт
    dst = Destination('nexus5')
    device = JMTPFS().getDeviceByName('Nexus 4/5/7/10 (MTP)')
    if device:
        if dst.canBeMounted:
            subprocess.check_call('jmtpfs "%s" -device=%s,%s' % (dst.dirCreated, device[0], device[1]), shell=True)
        fpid = os.fork()
        if fpid!=0:
            # Running as daemon now. PID is fpid
            sys.exit(0)
        while dst.mounted:
            time.sleep(1)
            d = JMTPFS().getDeviceById(device[2], device[3])
            if not d:
                subprocess.check_call('fusermount -u "%s"' % dst.dir, shell=True)
                if dst.canBeRemoved:
                    os.rmdir(dst.dir)

