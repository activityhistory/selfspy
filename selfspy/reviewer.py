# -*- coding: utf-8 -*-
"""
Selfspy: Track your computer activity
Copyright (C) 2012 Bjarte Johansen
Modified 2014 by Adam Rule, Aurélien Tabard, and Jonas Keper

Selfspy is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Selfspy is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Selfspy. If not, see <http://www.gnu.org/licenses/>.
"""

import time
import datetime

from objc import IBAction, IBOutlet
from AppKit import *

from CBGraphView import CBGraphView

from selfspy.helpers import *


SCREENSHOT_WIDTH = 960
SCREENSHOT_HEIGHT = 600


class WindowListController(NSArrayController):

    @IBAction
    def updateAppCheckbox_(self, sender):
        """ update app checkbox when a window checkbox is clicked """

        row = self.review_controller.appList.selectedRow()
        view = self.review_controller.appList.viewAtColumn_row_makeIfNecessary_(0,row,False)

        if view:
            try:
                app_data = view.objectValue()
                num_rows = len(app_data['windows'])
                num_checked = 0

                for j in app_data['windows']:
                    if j['checked'] == 1:
                        num_checked += 1

                if num_checked == num_rows:
                    app_data['checked'] = 1
                elif num_checked == 0:
                    app_data['checked'] = 0
                else:
                    app_data['checked'] = -1

            except:
                print "Error: Could not update App Checkbox"


# Review window controller
class ReviewController(NSWindowController):

    # outlets for UI elements
    mainPanel = IBOutlet()
    tableView = IBOutlet()
    slider = IBOutlet()
    arrayController = IBOutlet()
    windowListController = IBOutlet()
    appList = IBOutlet()
    windowList = IBOutlet()

    # instance variables
    currentScreenshot = -1
    dateQuery = ""
    processNameQuery = ""

    # data for app and window tables
    results = []

    # let activity_store write query results into those
    queryResponse = []
    queryResponse2 = []
    processTimesResponse = []
    processNameResponse = []

    # lists of image files
    list_of_files = []

    # timeline values in UTC seconds
    timeline_value = 0
    slider_max = 1
    slider_min = 0
    normalized_max_value = 0

    timeline_view = None
    nested_timeline_views = []
    nested_timeline_labels = []
    current_timeline_process = 7


    def createWindowListController(self):
        return WindowListController


    @IBAction
    def updateWindowCheckboxes_(self, sender):
        """ update window checboxes when app checkbox clicked """

        # TODO select the row of the clicked checkbox if not already selected
        # TODO determine why window name sometimes goes to '{'
        app_data = sender.superview().objectValue()
        state = sender.state()

        if state == 1:
            app_data['windows_mixed'] = NSMutableArray([])
            for i in app_data['windows']:
                app_data['windows_mixed'].append(NSMutableDictionary(i))

            for w in app_data['windows']:
                w['checked'] = 1

        elif state == 0:
            for w in app_data['windows']:
               w['checked'] = 0

        elif state == -1:
            if app_data['windows_mixed']:
                app_data['windows'] = NSMutableArray([])
                for i in app_data['windows_mixed']:
                    app_data['windows'].append(NSMutableDictionary(i))
            else:
                for w in app_data['windows']:
                    w['checked'] = 0

        self.windowListController.setContent_(app_data['windows'])
        self.windowList.reloadData()


    @IBAction
    def advanceReviewWindow_(self, sender):
        """ move to next screenshot """

        self.moveReviewWindow(direction=1)


    @IBAction
    def revertReviewWindow_(self, sender):
        """ move to previous screenshot """

        self.moveReviewWindow(direction=-1)


    def moveReviewWindow(self, direction):
        """ move to next or previous screenshot """

        # list_of_files = generateScreenshotList(self)
        screenshot_found = False

        while (not screenshot_found):
            self.currentScreenshot = self.currentScreenshot + direction # (SCREENSHOT_REVIEW_INTERVAL * direction)
            if (0 <= self.currentScreenshot < len(self.list_of_files)):
                generateDateQuery(self, s=self.list_of_files[self.currentScreenshot])

                screenshot_found = True
                filename = s=self.list_of_files[self.currentScreenshot]
                self.displayScreenshot(self, s=filename)
                normalized_current_value =  unixTimeFromString(self, mapFilenameDateToNumber(self, s=filename)) - self.slider_min
                self.timeline_value = normalized_current_value

                self.queryResponse = []
                self.queryResponse2 = []

            else:
                screenshot_found = True # so that it stops searching
                # self.reviewController.close()


    @IBAction
    def filterWindowEvents_(self, sender):

        NSNotificationCenter.defaultCenter().postNotificationName_object_('getFilteredWindowEvents',self)


    def displayScreenshot(self, self2=None, s=None):
        """ draw screenshot at right size """

        image = NSImage.alloc().initByReferencingFile_(getScreenshotPath(self) + s)
        width = image.size().width
        height = image.size().height
        ratio = width / height

        if( width > SCREENSHOT_WIDTH or height > SCREENSHOT_HEIGHT ):
            if (ratio > SCREENSHOT_WIDTH/SCREENSHOT_HEIGHT):
                width = SCREENSHOT_WIDTH
                height = SCREENSHOT_WIDTH / ratio
            else:
                width = SCREENSHOT_HEIGHT * ratio
                height = SCREENSHOT_HEIGHT

        image.setScalesWhenResized_(True)
        image.setSize_((width, height))
        self.reviewController.mainPanel.setImage_(image)


    def getApplicationsAndWindowsForTable(self):
        """ query database for apps and windows """

        NSNotificationCenter.defaultCenter().postNotificationName_object_('getAppsAndWindows',self)


    def applyDefaults(self, defaults, results):
        """ restore app and window checkbox states saved in NSUserDefaults """

        for d in defaults:
            try:
                result = (r for r in results if r['appName'] == d['appName']).next()
                result['checked'] = d['checked']
                # apply settings saved for all windows
                for w in d['windows']:
                    result_w = (rw for rw in result['windows'] if rw['windowName'] == w['windowName']).next()
                    if result_w:
                        result_w['checked'] = int(w['checked'])
                # if app is checked or unchecked, apply to all windows
                if d['checked'] == 0 or d['checked'] == 1:
                    for w in result['windows']:
                        w['checked'] = d['checked']
            except:
                pass


    def manageTimeline(self):
        """ get timeline limits and draw elements """

        bounds_detected = 0
        front_bound = 0
        drawn_textlabels = []

        NSNotificationCenter.defaultCenter().postNotificationName_object_('getProcessTimes', self)

        self.slider_min = unixTimeFromString(self, s=str(datetime.datetime.now()))

        for app in self.processTimesResponse:
            for time in app:
                if unixTimeFromString(self, str(time[2])) < self.slider_min:
                    self.slider_min = unixTimeFromString(self, str(time[2]))

                if unixTimeFromString(self, str(time[2])) > self.slider_max:
                    self.slider_max = unixTimeFromString(self, str(time[2]))

        self.normalized_max_value = self.slider_max - self.slider_min
        self.reviewController.slider.setMaxValue_(self.normalized_max_value)

        reordered_process_times = []

        for entry in self.processTimesResponse[0]:
            reordered_process_times.append([entry[3], entry[1], unixTimeFromString(self, str(entry[2]))])

        # reorder list
        reordered_process_times.sort(key=lambda tup: tup[2])

        first_bound = True
        front_bound = 0
        back_bound = 0

        for event in reordered_process_times:
            process_id = event[0]
            event_type = event[1]
            time = event[2]

            if str(event[1]) == "Active":
                if first_bound:
                    front_bound = event[2]
                    first_bound = False
                else:
                    back_bound = event[2]
                    next_front_bound = event[2]
                    addProcessTimelineSegment(self, process_id, front_bound, back_bound, self)

                    front_bound = next_front_bound


    def populateElements(self):
        """ get app/window data, list of screenshots, and draw timeline """

        # prepare data for app and window tables
        self.getApplicationsAndWindowsForTable(self)
        defaults = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('appWindowList')
        self.applyDefaults(self, defaults, self.reviewController.results)

        # get list of image files
        self.list_of_files = generateScreenshotList(self)

        # prepare timeline
        self.manageTimeline(self)

        # re-sort list items
        self.reviewController.arrayController.rearrangeObjects()


    def tableViewSelectionDidChange_(self,sender):
        """ change window list based on app selelction """

        selected_row = self.appList.selectedRow()
        selected_view = self.appList.viewAtColumn_row_makeIfNecessary_(0,selected_row,False)

        if selected_view:
            app_data = selected_view.objectValue()
            self.windowListController.setContent_(app_data['windows'])
            self.windowList.reloadData()

            # self.current_timeline_process = app_index_in_dict # TODO potential future bug because we do not know if the order is always the same
            # self.manageTimeline() # TODO do not query file list and so on every time


    def windowWillClose_(self, notification):
        """ save state of tables to user defaults when window closes """

        NSUserDefaultsController.sharedUserDefaultsController().defaults().setObject_forKey_(self.results, 'appWindowList')


    def show(self):
        """ create the necessary elements and show the reviewer window """

        try:
            if self.reviewController:
                self.reviewController.close()
        except AttributeError:
            pass

        # open window from NIB file, show front and center, and on top
        self.reviewController = ReviewController.alloc().initWithWindowNibName_("Reviewer")
        self.reviewController.showWindow_(None)
        self.reviewController.window().makeKeyAndOrderFront_(None)
        self.reviewController.window().center()
        self.reviewController.retain()
        NSNotificationCenter.defaultCenter().postNotificationName_object_('makeAppActive',self)

        # get cmd-w hotkey to close window
        self.reviewController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalentModifierMask_(NSCommandKeyMask)
        self.reviewController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalent_("w")

        # create controller for list of windows
        self.reviewController.windowArrayController = self.createWindowListController(self).alloc().init()
        self.reviewController.windowArrayController.review_controller = self.reviewController
        self.reviewController.windowList.setDelegate_(self.reviewController.windowArrayController)

        # sort app list in ascending order
        asc = NSSortDescriptor.alloc().initWithKey_ascending_('appName',True)
        descriptiorArray = [asc]
        self.reviewController.arrayController.setSortDescriptors_(descriptiorArray)
        self.reviewController.arrayController.rearrangeObjects()

        # sort window list in ascending order
        asc = NSSortDescriptor.alloc().initWithKey_ascending_('windowName',True)
        descriptiorArray = [asc]
        self.reviewController.windowListController.setSortDescriptors_(descriptiorArray)
        self.reviewController.windowListController.rearrangeObjects()

        # generate the timeline view, add background and border
        # TODO change to scrollable view with different interactions than CBGraphView
        frame = NSRect(NSPoint(WINDOW_PADDING, 36), NSSize(TIMELINE_WIDTH, TIMELINE_HEIGHT))
        self.timeline_view = NSView.alloc().initWithFrame_(frame)

        frame = NSRect(NSPoint(0, 0), NSSize(TIMELINE_WIDTH, TIMELINE_HEIGHT))
        timeline_fill = CBGraphView.alloc().initWithFrame_(frame)
        timeline_fill.setBackgroundColor_(NSColor.whiteColor())
        timeline_fill.setAssignedColor_(NSColor.whiteColor())
        timeline_fill.setDrawBorder_(True)
        timeline_fill.setWantsLayer_(YES)
        self.timeline_view.addSubview_(timeline_fill)

        self.reviewController.window().contentView().addSubview_(self.timeline_view)

        # get screenshots and app/window data
        self.populateElements(self)


    show = classmethod(show)
