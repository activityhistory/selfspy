import calendar
from dateutil.parser import parse

import os
from os import listdir
from os.path import isfile, join

from objc import IBAction, IBOutlet, YES, NO
from AppKit import *
from CBGraphView import CBGraphView


TIMELINE_WIDTH = 800
TIMELINE_HEIGHT = 400
WINDOW_BORDER_WIDTH = 30
TEXTLABEL_WIDTH = 80
TEXTLABEL_HEIGHT = 15
TIMELINE_MAX_ROWS = TIMELINE_WIDTH / (TEXTLABEL_HEIGHT * 3)
SEGMENT_SECTION_WIDTH = TIMELINE_WIDTH - TEXTLABEL_WIDTH


def unixTimeFromString(self, s=None):
    fuzzy_ts = parse(str(s), fuzzy=True)
    ts = calendar.timegm(fuzzy_ts.utctimetuple())
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


## TIMELINE HELPERS

def addProcessNameTextLabelToTimeline(self, process_id, reviewer):
    self.processNameQuery = process_id
    NSNotificationCenter.defaultCenter().postNotificationName_object_('getProcessNameFromID', self)

    textField_frame = NSRect(NSPoint(0, TIMELINE_HEIGHT / TIMELINE_MAX_ROWS * process_id),
                             NSSize(TEXTLABEL_WIDTH, TEXTLABEL_HEIGHT))
    textField = NSTextField.alloc().initWithFrame_(textField_frame)
    textField.setEditable_(NO)
    textField.setDrawsBackground_(NO)
    textField.setSelectable_(NO)
    textField.setBezeled_(NO)
    textField.setStringValue_(str(self.processNameResponse[0]))

    self.processNameResponse = []

    reviewer.timeline_view.addSubview_(textField)


def addProcessTimelineSegment(self, process_id, front_bound, back_bound, reviewer):
    normalized_min_value = front_bound - reviewer.slider_min
    frame = NSRect(NSPoint(TEXTLABEL_WIDTH + normalized_min_value * SEGMENT_SECTION_WIDTH / reviewer.normalized_max_value,
                           TIMELINE_HEIGHT / TIMELINE_MAX_ROWS * process_id),
                   NSSize(back_bound - front_bound, TIMELINE_HEIGHT / (TIMELINE_MAX_ROWS * 2)))
    this_view = CBGraphView.alloc().initWithFrame_(frame)
    reviewer.timeline_view.addSubview_(this_view)
    this_view.drawRect_(frame)
    reviewer.nested_timeline_views.append(this_view)