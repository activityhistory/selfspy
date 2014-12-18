import calendar
from dateutil.parser import parse

import os
from os import listdir
from os.path import isfile, join

from selfspy import config as cfg

from objc import YES, NO
from AppKit import *
from CBGraphView import CBGraphView


TIMELINE_WIDTH = 960
TIMELINE_HEIGHT = 20
WINDOW_PADDING = 18


def unixTimeFromString(self, s=None):
    fuzzy_ts = parse(str(s), fuzzy=True)
    ts = calendar.timegm(fuzzy_ts.utctimetuple())
    return ts

def getScreenshotPath(self, self2=None):
    path = os.path.join(cfg.CURRENT_DIR, 'screenshots')
    path = os.path.expanduser(path)
    return path + '/'

def generateScreenshotList(self, self2=None):
     path = getScreenshotPath(self)
     list_of_files = [ f for f in listdir(path) if isfile(join(path,f)) ]
     return list_of_files

def generateDateQuery(self, s=None):
    self.dateQuery = '20' + s[0:2] + '-' + s[2:4] + '-' + s[4:6] + ' ' + s[7:9] + ':' + s[9:11] + ':' + s[11:13] + '.'

def mapFilenameDateToNumber(self, s=None):
    return int('20' + s[0:2] + s[2:4] + s[4:6] + s[7:9] + s[9:11] + s[11:13])

def addProcessTimelineSegment(self, process_id, front_bound, back_bound, reviewer):
    if front_bound >= reviewer.slider_min and back_bound <= reviewer.slider_max:

        # generate unique grayscale color for timeline segment
        gray = (30*process_id) % 255
        color = NSColor.colorWithCalibratedRed_green_blue_alpha_(gray/255.0, gray/255.0, gray/255.0, 1.0)

        # get bounds of segment and draw segment
        normalized_front_bound = front_bound - reviewer.slider_min
        width_scale_factor = TIMELINE_WIDTH / (reviewer.normalized_max_value*1.0)
        segment_x = normalized_front_bound * width_scale_factor
        segment_y = 1
        segment_height = TIMELINE_HEIGHT-2
        segment_width = (back_bound - front_bound) * width_scale_factor

        frame = NSRect(NSPoint(segment_x, segment_y),
                       NSSize(segment_width, segment_height))

        # TODO change to scrollable view with different interactions than CBGraphView
        this_view = CBGraphView.alloc().initWithFrame_(frame)
        reviewer.timeline_view.addSubview_(this_view)
        this_view.setBorderColor_(color)
        this_view.setAssignedColor_(color)
        this_view.setBackgroundColor_(color)
        this_view.setWantsLayer_(YES)

        # add tooltip to segment
        self.processNameQuery = process_id
        NSNotificationCenter.defaultCenter().postNotificationName_object_('getProcessNameFromID', self)
        this_view.setToolTip_(str(self.processNameResponse[0]))
        self.processNameResponse = []
        reviewer.nested_timeline_views.append(this_view)

## TIMELINE HELPERS
# def addProcessNameTextLabelToTimeline(self, process_id, reviewer):
#     self.processNameQuery = process_id
#     NSNotificationCenter.defaultCenter().postNotificationName_object_('getProcessNameFromID', self)
#
#     textField_frame = NSRect(NSPoint(0, TIMELINE_HEIGHT / TIMELINE_MAX_ROWS * process_id),
#                              NSSize(TEXTLABEL_WIDTH, TEXTLABEL_HEIGHT))
#     textField = NSTextField.alloc().initWithFrame_(textField_frame)
#     textField.setEditable_(NO)
#     textField.setDrawsBackground_(NO)
#     textField.setSelectable_(NO)
#     textField.setBezeled_(NO)
#     textField.setStringValue_(str(self.processNameResponse[0]))
#
#     self.processNameResponse = []
#
#     reviewer.timeline_view.addSubview_(textField)
#     reviewer.nested_timeline_labels.append(textField)
