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

from objc import IBAction, IBOutlet
from AppKit import *

from CBGraphView import CBGraphView

from helpers import *

import time
import datetime

SCREENSHOT_REVIEW_INTERVAL = 1
UI_SLIDER_MAX_VALUE = 100
TIMELINE_INTERVAL_IN_SECONDS = 600 # 1 day = 86400 seconds


class WindowListController(NSArrayController):

    # when a window checkbox is clicked, make sure the cooresponding app
    # checkbox changes to the appropriate state
    @IBAction
    def updateAppCheckbox_(self, sender):
        row = self.review_controller.appList.selectedRow()
        view = self.review_controller.appList.viewAtColumn_row_makeIfNecessary_(0,row,False)
        w_view = sender.superview()

        if view and w_view:
            app = view.textField().stringValue()
            window = w_view.textField().stringValue()
            try:
                app_data = (a for a in self.review_controller.results if a['appName'] == app).next()
                w_data = (a for a in app_data['windows'] if a['windowName'] == window).next()

                w_data['checked'] = sender.state()

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
                pass


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

    # lists of image files
    list_of_files = []
    filtered_files = []

    # timeline
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
    def updateAppCheckbox_(self, sender):
        # TODO select the row of the clicked checkbox if not already selected
        # TODO determine why window name sometimes goes to '{'

        app_data = sender.superview().objectValue()
        state = sender.state()
        appName = app_data['appName']

        if state == 1:
            app_data['windows_mixed'] = []
            for i in app_data['windows']:
                app_data['windows_mixed'].append(NSMutableDictionary(i))

            for w in app_data['windows']:
                w['checked'] = 1

        elif state == 0:
            for w in app_data['windows']:
                w['checked'] = 0

        elif state == -1:
            if app_data['windows_mixed'] != []:
                app_data['windows'] = []
                for i in app_data['windows_mixed']:
                    app_data['windows'].append(NSMutableDictionary(i))
            else:
                for w in app_data['windows']:
                    w['checked'] = 0

        self.results_windows = app_data['windows']


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


    @IBAction
    def filterFiles_(self, sender):
        x = 1
        # append datetime to screenshot array
        # get list of window active events, with appended datetime
        # append NOW to end of active events to make sure last active is processed
        # self.filtered_files = []
        # i = 0
        # for j in range(len(active events)-1):
        #   active = check if active[j][app] is active
        #   while time(file_list[i]) < time(active[j+1]):
        #       if time(file_list[i]) >= time(active[J]) and active:
        #           append file_list[i] to filtered_files
        #       i++
        # print len(self.filtered_files)


    def tableViewSelectionDidChange_(self,sender):
        selected_row = self.appList.selectedRow()
        selected_view = self.appList.viewAtColumn_row_makeIfNecessary_(0,selected_row,False)

        # self.nested_timeline_views[0].invokeFromOutside()

        # TODO for some reason, when we programatically select the 0 index
        # at launch, the selected_view is none
        if selected_view:
            # try:
            #     print("STA2: ", str(self.nested_timeline_labels[0]))
            #     self.nested_timeline_labels[0].setHidden_(YES)
            # except IndexError:
            #     pass  # TODO I'm stuck here. setHidden works when put above if "selected_view:" - but not here (invoked by selecting another item in the list).
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
                # for view in self.nested_timeline_views:
                #     view.removeFromSuperview()
                # self.nested_timeline_views = []
                for label in self.nested_timeline_labels:
                    x = 1 # dummy code
                    # print("attemping to hide: ", str(label))
                    # status = self
                    # print("STATUS: ", status)
                # self.nested_timeline_views = []
                # self.nested_timeline_labels = []
            except TypeError:
                print('Error with array of views.')

            # self.manageTimeline() # TODO do not query file list and so on every time


    def moveReviewWindow(self, direction):
        # list_of_files = generateScreenshotList(self)
        screenshot_found = False

        while (not screenshot_found):
            self.currentScreenshot = self.currentScreenshot + (SCREENSHOT_REVIEW_INTERVAL * direction)
            if (0 <= self.currentScreenshot < len(self.list_of_files)):
                generateDateQuery(self, s=self.list_of_files[self.currentScreenshot])
                # send message to activity_store so it can do the database query
                # NSNotificationCenter.defaultCenter().postNotificationName_object_('queryMetadata',self)
                # if len(self.queryResponse) > 0:
                #      d = self.generateDictEntry(checked=1)
                #      if d in self.results:
                screenshot_found = True
                filename = s=self.list_of_files[self.currentScreenshot]
                self.displayScreenshot(self, s=filename)
                         # normalized_current_value = mapFilenameDateToNumber(s=filename) - self.slider_min
                         # self.timeline_value = normalized_current_value * UI_SLIDER_MAX_VALUE / self.normalized_max_value

                self.queryResponse = []
                self.queryResponse2 = []

            else:
                screenshot_found = True # so that it stops searching
                self.reviewController.close()


    def getApplicationsAndURLsForTable(self):
        NSNotificationCenter.defaultCenter().postNotificationName_object_('getAppsAndUrls',self)


    def applyDefaults(self, defaults, results):
        # restore app and window checkbox states saved in NSUserDefaults
        for d in defaults:
            try:
                result = (r for r in results if r['appName'] == d['appName']).next()
                result['checked'] = d['checked']
                for w in d['windows']:
                    result_w = (rw for rw in result['windows'] if rw['windowName'] == w['windowName']).next()
                    if result_w:
                        result_w['checked'] = w['checked']
            except:
                pass

    def manageTimeline(self):
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

            # if process_id < TIMELINE_MAX_ROWS:
            #     if process_id not in drawn_textlabels:
            #         drawn_textlabels.append(process_id)
            #         addProcessNameTextLabelToTimeline(self, process_id, self)

            if str(event[1]) == "Active":
                if first_bound:
                    front_bound = event[2]
                    first_bound = False
                else:
                    back_bound = event[2]
                    next_front_bound = event[2]
                    addProcessTimelineSegment(self, process_id, front_bound, back_bound, self)

                    front_bound = next_front_bound

        # reordered_process_times = {}
        #
        # for entry in self.processTimesResponse[0]:
        #     if entry[3] not in reordered_process_times:
        #         reordered_process_times[entry[3]] = []
        #     reordered_process_times[entry[3]].append([entry[1], entry[2]])
        #
        # for process in reordered_process_times:
        #     process_id = process
        #
        #     if process_id < TIMELINE_MAX_ROWS:
        #         if process_id not in drawn_textlabels:
        #             drawn_textlabels.append(process_id)
        #             addProcessNameTextLabelToTimeline(self, process_id, self)
        #
        #     for event in reordered_process_times[process]:
        #         if str(event[0]) == "Open" and bounds_detected == 0:
        #             front_bound = unixTimeFromString(self, str(event[1]))
        #             bounds_detected = 1
        #
        #         if str(event[0]) == "Close" and bounds_detected == 1:
        #             back_bound = unixTimeFromString(self, str(event[1]))
        #             bounds_detected = 2
        #
        #         if bounds_detected == 2:
        #             addProcessTimelineSegment(self, process_id, front_bound, back_bound, self)
        #             bounds_detected = 0



    def populateExperienceTable(self):
        # get list of image files
        self.list_of_files = generateScreenshotList(self)

        # prepare data for app and window tables
        self.getApplicationsAndURLsForTable(self)
        defaults = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('appWindowList')
        self.applyDefaults(self, defaults, self.reviewController.results)

        # prepare timeline
        self.manageTimeline(self)

        # re-sort list items and select the first item
        try:
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


    def show(self):
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

        # TODO get window list to sort alphabetically
        # sort window list in ascending order
        asc = NSSortDescriptor.alloc().initWithKey_ascending_('windowName',True)
        descriptiorArray = [asc]
        self.reviewController.windowArrayController.setSortDescriptors_(descriptiorArray)
        self.reviewController.windowArrayController.rearrangeObjects()

        # generate the timeline view
        frame = NSRect(NSPoint(WINDOW_BORDER_WIDTH, 50), NSSize(TIMELINE_WIDTH, TIMELINE_HEIGHT))
        self.timeline_view = NSView.alloc().initWithFrame_(frame)
        frame = NSRect(NSPoint(0, 0), NSSize(TIMELINE_WIDTH, TIMELINE_HEIGHT))
        this_view = CBGraphView.alloc().initWithFrame_(frame)
        self.timeline_view.addSubview_(this_view)
        this_view.setBackgroundColor_(NSColor.whiteColor())
        this_view.setBorderColor_(NSColor.darkGrayColor())
        this_view.setWantsLayer_(YES)

        self.reviewController.window().contentView().addSubview_(self.timeline_view)
        #self.timeline_view.drawRect_(frame)

        # get screenshots and app/window data
        self.populateExperienceTable(self)


    show = classmethod(show)
