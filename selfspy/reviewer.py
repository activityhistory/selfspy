# -*- coding: utf-8 -*-
"""
Selfspy: Track your computer activity
Copyright (C) 2012 Bjarte Johansen
Modified 2014 by Adam Rule, Aurélien Tabard, and Jonas Kemper

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

from objc import IBAction, IBOutlet, YES, NO
from AppKit import *

from CBGraphView import CBGraphView

from helpers import *

import time

SCREENSHOT_REVIEW_INTERVAL = 1
UI_SLIDER_MAX_VALUE = 100



class WindowListController(NSArrayController):

    @IBAction
    def updateAppCheckbox_(self, sender):
        print "updating checkbox"
        row = self.review_controller.appList.selectedRow()
        view = self.review_controller.appList.viewAtColumn_row_makeIfNecessary_(0,row,False)
        # w_view = sender.superview()
        #
        # if view and w_view:
        #     # get app and window arrays
        #     app = view.textField().stringValue()
        #     window = w_view.textField().stringValue()
        #     try:
        #         app_data = (a for a in self.review_controller.results if a['appName'] == app).next()
        #     except:
        #         app_data = None
        #
        #     if app_data:
        #         try:
        #             w_data = (a for a in app_data['windows'] if a['windowName'] == window).next()
        #         except:
        #             w_data = None
        #
        #     # update app and window arrays
        #     if app_data and w_data:
        #         print "updating arrays"
        #         w_data['checked'] = sender.state()
        #
        #         num_rows = len(app_data['windows'])
        #         num_checked = 0
        #         for j in app_data['windows']:
        #             if j['checked'] == 1:
        #                 num_checked += 1
        #         if num_checked == num_rows:
        #             app_data['checked'] = 1
        #         elif num_checked == 0:
        #             app_data['checked'] = 0
        #         else:
        #             app_data['checked'] = -1
        #         print "check value is " + str(app_data['checked'])


# Review window controller
class ReviewController(NSWindowController):

    NSMutableDictionary = objc.lookUpClass('NSMutableDictionary')

    # outlets for UI elements
    mainPanel = IBOutlet()
    tableView = IBOutlet()
    arrayController = IBOutlet()
    appList = IBOutlet()
    windowList = IBOutlet()

    # instance variables
    currentScreenshot = -1
    dateQuery = ""
    processNameQuery = ""

    # data for dynamic review tables
    results = []
    results_half = []
    results_windows = []

    # let activity_store write query results into those
    queryResponse = []
    queryResponse2 = []
    processTimesResponse = []
    processNameResponse = []

    # timeline
    timeline_value = 0
    slider_max = 1
    slider_min = 0
    normalized_max_value = 0

    timeline_view = None
    nested_timeline_views = []
    current_timeline_process = 7


    def createWindowListController(self):
        return WindowListController

    @IBAction
    def updateAppCheckbox_(self, sender):
        app = sender.superview().textField().stringValue()
        state = sender.state()
        app_data = (a for a in self.results if a['appName'] == app).next()

        if state == 1:
            try:
                old_half = (a for a in self.results_half if a['appName'] == app).next()
            except:
                old_half = None
            if old_half:
                old_half = app_data
            else:
                self.results_half.append(app_data)
            for w in app_data['windows']:
                w['checked'] = 1
        elif state == 0:
            for w in app_data['windows']:
                w['checked'] = 0
        elif state == -1:
            try:
                old_half = (a for a in self.results_half if a['appName'] == app).next()
            except:
                old_half = None
            if old_half:
                app_data = old_half
            else:
                for w in app_data['windows']:
                    w['checked'] = 0

        self.results_windows = app_data['windows']
        # print self.results_half


    def displayScreenshot(self, self2=None, s=None):
        experienceImage = NSImage.alloc().initByReferencingFile_(getScreenshotPath(self) + s)

        width = experienceImage.size().width
        height = experienceImage.size().height
        ratio = width / height
        if( width > 960 or height > 600 ):
            if (ratio > 1.6):
                width = 960
                height = 960 / ratio
            else:
                width = 600 * ratio
                height = 600
        experienceImage.setScalesWhenResized_(True)
        experienceImage.setSize_((width, height))
        self.reviewController.mainPanel.setImage_(experienceImage)

    def generateDictEntry(self, checked=None):
        return NSMutableDictionary({'appName': self.queryResponse2[0] if len(self.queryResponse2) > 0 else "",
                                    'image': self.queryResponse[0] if len(self.queryResponse) > 0 else "",
                                    'checked': 1})

    @IBAction
    def advanceReviewWindow_(self, sender):
        self.moveReviewWindow(direction=1)

    @IBAction
    def revertReviewWindow_(self, sender):
        self.moveReviewWindow(direction=-1)

    def tableViewSelectionDidChange_(self,sender):
        selected_row = self.appList.selectedRow()
        selected_view = self.appList.viewAtColumn_row_makeIfNecessary_(0,selected_row,False)

        # TODO for some reason, when we programatically select the 0 index
        # at launch, the selected_view is none
        if selected_view:
            selected_app = selected_view.textField().stringValue()
            app_index_in_dict = 0
            for i in range(len(self.results)):
                if self.results[i]["appName"] == selected_app:
                    app_index_in_dict = i
                    break
            self.results_windows = [ self.NSMutableDictionary.dictionaryWithDictionary_(x) for x in self.results[app_index_in_dict]['windows']]
            self.windowList.reloadData()


            self.current_timeline_process = app_index_in_dict # TODO potential future bug because we do not know if the order is always the same

            try:
                for view in self.nested_timeline_views:
                    view.removeFromSuperview()
                self.nested_timeline_views = []
            except StopIteration, TypeError:
                print('Error with array of views.')

            list_of_files = generateScreenshotList(self)
            self.manageTimeline(list_of_files) # TODO do not query file list and so on every time


    def moveReviewWindow(self, direction):
        list_of_files = generateScreenshotList(self)
        screenshot_found = False

        while (not screenshot_found):
            self.currentScreenshot = self.currentScreenshot + (SCREENSHOT_REVIEW_INTERVAL * direction)
            if (0 <= self.currentScreenshot < len(list_of_files)):

                generateDateQuery(list_of_files[self.currentScreenshot])

                # send message to activity_store so it can do the database query
                NSNotificationCenter.defaultCenter().postNotificationName_object_('queryMetadata',self)

                if len(self.queryResponse) > 0:
                     d = self.generateDictEntry(checked=1)
                     if d in self.results:
                         screenshot_found = True
                         filename = s=list_of_files[self.currentScreenshot]
                         self.displayScreenshot(self, s=filename)
                         normalized_current_value = mapFilenameDateToNumber(s=filename) - self.slider_min
                         self.timeline_value = normalized_current_value * UI_SLIDER_MAX_VALUE / self.normalized_max_value

                self.queryResponse = []
                self.queryResponse2 = []

            else:
                screenshot_found = True # so that it stops searching
                self.reviewController.close()

    def getApplicationsAndURLsForTable(self, list_of_files):
        NSNotificationCenter.defaultCenter().postNotificationName_object_('getAppsAndUrls',self)

    # TODO debug why window settings do not load
    def applyDefaults(self, defaults, results):
        # restore checkbox states saved in NSUserDefaults
        for d in defaults:
            try:
                result = (r for r in results if r['appName'] == d['appName']).next()
            except:
                result = False
            if result:
                result['checked'] = d['checked']
                for w in d['windows']:
                    result_w = (rw for rw in result['windows'] if rw['windowName'] == w['windowName']).next()
                    if result_w:
                        result_w['checked'] = w['checked']

    def getTimelineMinAndMax(self, list_of_files):
        self.slider_min = unixTimeFromString(self, s=mapFilenameDateToNumber(self, s=list_of_files[0]))
        for s in list_of_files:
            helper = unixTimeFromString(self, s=mapFilenameDateToNumber(self, s=s))
            if self.slider_max < helper:
                self.slider_max = helper
            if self.slider_min > helper:
                self.slider_min = helper

        self.normalized_max_value = self.slider_max - self.slider_min


    def manageTimeline(self, list_of_files):
        self.getTimelineMinAndMax(self, list_of_files)

        NSNotificationCenter.defaultCenter().postNotificationName_object_('getProcessTimes',self)

        bounds_detected = 0
        front_bound = 0
        drawn_textlabels = []
        for app in self.processTimesResponse:
            for time in app:
                process_id = time[3]
                if process_id < TIMELINE_MAX_ROWS:
                    if process_id not in drawn_textlabels:
                        drawn_textlabels.append(process_id)
                        addProcessNameTextLabelToTimeline(self, process_id, self)
                    if str(time[1]) == "Open" and bounds_detected == 0:
                        front_bound = unixTimeFromString(self, str(time[2]))
                        bounds_detected = 1

                    if str(time[1]) == "Close" and bounds_detected == 1:
                        back_bound = unixTimeFromString(self, str(time[2]))
                        bounds_detected = 2

                    if bounds_detected == 2:
                        addProcessTimelineSegment(self, process_id, front_bound, back_bound, self)
                        bounds_detected = 0


    def populateExperienceTable(self):
        list_of_files = generateScreenshotList(self)
        self.getApplicationsAndURLsForTable(self, list_of_files)
        defaults = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('appWindowList')
        self.applyDefaults(self, defaults, self.reviewController.results)
        self.manageTimeline(self, list_of_files)

        try:
            # re-sort list items and select the first item
            self.reviewController.arrayController.rearrangeObjects()
            index_set = NSIndexSet.indexSetWithIndex_(0)
            self.reviewController.appList.selectRowIndexes_byExtendingSelection_(index_set,False)
        except UnboundLocalError:
            pass

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)

    def windowWillClose_(self, notification):
        # save state of tables to user defaults
        NSUserDefaultsController.sharedUserDefaultsController().defaults().setObject_forKey_(self.results, 'appWindowList')

    # def awakeFromNib(self):
    #     if self.tableView:
    #         self.tableView.setTarget_(self)

    def show(self):
        try:
            if self.reviewController:
                self.reviewController.close()
        except AttributeError:
            pass

        # open window from NIB file, show front and center
        self.reviewController = ReviewController.alloc().initWithWindowNibName_("Reviewer")
        self.reviewController.showWindow_(None)
        self.reviewController.window().makeKeyAndOrderFront_(None)
        self.reviewController.window().center()
        self.reviewController.retain()
        # needed to show window on top of other applications
        NSNotificationCenter.defaultCenter().postNotificationName_object_('makeAppActive',self)

        # get cmd-w hotkey to close window
        self.reviewController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalentModifierMask_(NSCommandKeyMask)
        self.reviewController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalent_("w")

        # create controller for list of windows
        self.reviewController.windowArrayController = self.createWindowListController(self).alloc().init()
        self.reviewController.windowArrayController.review_controller = self.reviewController
        self.reviewController.windowList.setDelegate_(self.reviewController.windowArrayController)

        # sort app list in ascending order
        asc = NSSortDescriptor.alloc().initWithKey_ascending_('Data',True)
        descriptiorArray = [asc]
        self.reviewController.arrayController.setSortDescriptors_(descriptiorArray)
        self.reviewController.arrayController.rearrangeObjects()

        # generate the timeline view
        frame = NSRect(NSPoint(WINDOW_BORDER_WIDTH, 50), NSSize(TIMELINE_WIDTH, TIMELINE_HEIGHT))
        self.timeline_view = CBGraphView.alloc().initWithFrame_(frame)
        self.reviewController.window().contentView().addSubview_(self.timeline_view)
        self.timeline_view.drawRect_(frame)

        # get screenshots and app/window data
        self.populateExperienceTable(self)

    show = classmethod(show)
