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


import os
from os import listdir
from os.path import isfile, join

from objc import IBAction, IBOutlet
from AppKit import *

SCREENSHOT_REVIEW_INTERVAL = 1
UI_SLIDER_MAX_VALUE = 100

# Review window controller
class ReviewController(NSWindowController):

    # outlets for UI elements
    mainPanel = IBOutlet()
    tableView = IBOutlet()
    arrayController = IBOutlet()

    # instance variables
    currentScreenshot = -1
    dateQuery = ""

    # dynamic review table
    list = []
    NSMutableDictionary = objc.lookUpClass('NSMutableDictionary')
    NSNumber = objc.lookUpClass('NSNumber')
    results = [ NSMutableDictionary.dictionaryWithDictionary_(x) for x in list]

    # let activity_store write query results into those
    queryResponse = []
    queryResponse2 = []

    # timeline
    timeline_value = 0
    slider_max = 1
    slider_min = 0
    normalized_max_value = 0


    # For Debugging purposes
    def printBools(self, self2=None):
        for value in self.results:
            try:
                print value['checkb']
            except KeyError:
                print "NO BOOLEAN"


    def getScreenshotPath(self, self2=None):
        path = os.path.expanduser(u'~/.selfspy/screenshots/')
        # TODO will this now still work on a thumbdrive?
        return path


    def generateScreenshotList(self, self2=None):
        path = self.getScreenshotPath(self)
        list_of_files = [ f for f in listdir(path) if isfile(join(path,f)) ]
        return list_of_files


    def displayScreenshot(self, self2=None, s=None):
        experienceImage = NSImage.alloc().initByReferencingFile_(self.getScreenshotPath(self) + s)

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
        return NSMutableDictionary({'Data': self.queryResponse2[0] if len(self.queryResponse2) > 0 else "",
                                    'Datab': self.queryResponse[0] if len(self.queryResponse) > 0 else "",
                                    'checkb': NSNumber.numberWithBool_(checked)})


    def generateDateQuery(self, s=None):
        self.dateQuery = '20' + s[0:2] + '-' + s[2:4] + '-' + s[4:6] + ' ' + s[7:9] + ':' + s[9:11] + ':' + s[11:13] + '.'


    @IBAction
    def advanceReviewWindow_(self, sender):
        self.moveReviewWindow(direction=1)

    @IBAction
    def revertReviewWindow_(self, sender):
        self.moveReviewWindow(direction=-1)

    def moveReviewWindow(self, direction):
        list_of_files = self.generateScreenshotList(self)
        screenshot_found = False

        while (not screenshot_found):
            self.currentScreenshot = self.currentScreenshot + (SCREENSHOT_REVIEW_INTERVAL * direction)
            if (0 <= self.currentScreenshot < len(list_of_files)):

                self.generateDateQuery(list_of_files[self.currentScreenshot])

                # send message to activity_store so it can do the database query
                NSNotificationCenter.defaultCenter().postNotificationName_object_('queryMetadata',self)

                if len(self.queryResponse) > 0:
                     d = self.generateDictEntry(checked=1)
                     if d in self.results:
                         screenshot_found = True
                         filename = s=list_of_files[self.currentScreenshot]
                         self.displayScreenshot(self, s=filename)
                         normalized_current_value = self.mapFilenameDateToNumber(s=filename) - self.slider_min
                         self.timeline_value = normalized_current_value * UI_SLIDER_MAX_VALUE / self.normalized_max_value

                self.queryResponse = []
                self.queryResponse2 = []

            else:
                screenshot_found = True # so that it stops searching
                self.reviewController.close()

    def mapFilenameDateToNumber(self, s=None):
        return int('20' + s[0:2] + s[2:4] + s[4:6] + s[7:9] + s[9:11] + s[11:13])

    def getApplicationsAndURLsForTable(self, list_of_files):
        for s in list_of_files:
            self.generateDateQuery(self, s=s)

            # send message to activity_store so it can do the database query
            NSNotificationCenter.defaultCenter().postNotificationName_object_('queryMetadata',self)

            if len(self.queryResponse) > 0:
                 d = self.generateDictEntry(self, checked=0)
                 d2 = self.generateDictEntry(self, checked=1)
                 if d not in self.results and d2 not in self.results:
                    self.results.append(NSMutableDictionary.dictionaryWithDictionary_(d))

            self.queryResponse = []
            self.queryResponse2 = []

    def manageTimeline(self, list_of_files):
        self.slider_min = self.mapFilenameDateToNumber(self, s=list_of_files[0])

        for s in list_of_files:
            self.generateDateQuery(self, s=s)
            helper = self.mapFilenameDateToNumber(self, s=s)
            if self.slider_max < helper:
                self.slider_max = helper
            if self.slider_min > helper:
                self.slider_min = helper

        self.normalized_max_value = self.slider_max - self.slider_min

    def populateExperienceTable(self):

        list_of_files = self.generateScreenshotList(self)
        self.getApplicationsAndURLsForTable(self, list_of_files)
        self.manageTimeline(self, list_of_files)

        try:
            self.reviewController.arrayController.rearrangeObjects()
        except UnboundLocalError:
            pass

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)

    def awakeFromNib(self):
        if self.tableView:
            self.tableView.setTarget_(self)

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

        # get cmd-w to close window
        self.reviewController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalentModifierMask_(NSCommandKeyMask)
        self.reviewController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalent_("w")

        # get arrayController read for Table
        desc = NSSortDescriptor.alloc().initWithKey_ascending_('Data',False)
        descriptiorArray = [desc]
        self.reviewController.arrayController.setSortDescriptors_(descriptiorArray)
        self.reviewController.arrayController.rearrangeObjects()

        self.populateExperienceTable(self)

    show = classmethod(show)
