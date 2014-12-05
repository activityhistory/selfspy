import calendar
from dateutil.parser import parse

import os
from os import listdir
from os.path import isfile, join

def unixTimeFromString(self, s=None):
    # print("attempting unixTimeFromString")
    front_bound = parse(str(s), fuzzy=True)
    ts = calendar.timegm(front_bound.utctimetuple())
    # print("before returning unixTimeFromString")
    return ts

def getScreenshotPath(self, self2=None):
     path = os.path.expanduser(u'~/.selfspy/screenshots/')
     # TODO will this now still work on a thumbdrive?
     return path

def generateScreenshotList(self, self2=None):
     path = getScreenshotPath(self)
     list_of_files = [ f for f in listdir(path) if isfile(join(path,f)) ]
     return list_of_files

def generateDateQuery(self, s=None):
    self.dateQuery = '20' + s[0:2] + '-' + s[2:4] + '-' + s[4:6] + ' ' + s[7:9] + ':' + s[9:11] + ':' + s[11:13] + '.'

def mapFilenameDateToNumber(self, s=None):
    return int('20' + s[0:2] + s[2:4] + s[4:6] + s[7:9] + s[9:11] + s[11:13])