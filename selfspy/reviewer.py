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
import os
from os import listdir
from os.path import isfile, join

from selfspy import config as cfg


import time
import datetime

from objc import IBAction, IBOutlet
from AppKit import *

SCREENSHOT_WIDTH = 960
SCREENSHOT_HEIGHT = 600


class WindowListController(NSArrayController):
    """ Controller for list of windows """

    @IBAction
    def updateAppCheckbox_(self, sender):
        """ update app checkbox when a window checkbox is clicked """

        # find the selected app
        row = self.review_controller.appList.selectedRow()
        view = self.review_controller.appList.viewAtColumn_row_makeIfNecessary_(0,row,False)

        if view:
            try:
                # get the underlying data
                app_data = view.objectValue()
                num_rows = len(app_data['windows'])
                num_checked = 0

                # count the number of checked windows
                for j in app_data['windows']:
                    if j['checked'] == 1:
                        num_checked += 1

                # udpate the app checkbox based on number of checked windows
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
    tableView = IBOutlet()
    arrayController = IBOutlet()
    windowListController = IBOutlet()
    appList = IBOutlet()
    windowList = IBOutlet()

    # data for app/window table and list of image files, populated by database query
    results = []
    list_of_files = []

    def createWindowListController(self):
        return WindowListController

    @IBAction
    def updateWindowCheckboxes_(self, sender):
        """ update window checboxes when app checkbox clicked """

        # TODO select the row of the clicked checkbox if not already selected
        # get the underlying data object and state of the checkbox
        app_data = sender.superview().objectValue()
        state = sender.state()

        # if checked, save last mixed state and check all window boxes
        if state == 1:
            app_data['windows_mixed'] = NSMutableArray([])
            for i in app_data['windows']:
                app_data['windows_mixed'].append(NSMutableDictionary(i))

            for w in app_data['windows']:
                w['checked'] = 1

        # if unchecked, uncheck all window boxes
        elif state == 0:
            for w in app_data['windows']:
               w['checked'] = 0

        # if mixed, load saved mixed state, or leave all windows unchecked
        elif state == -1:
            if app_data['windows_mixed']:
                app_data['windows'] = NSMutableArray([])
                for i in app_data['windows_mixed']:
                    app_data['windows'].append(NSMutableDictionary(i))
            else:
                for w in app_data['windows']:
                    w['checked'] = 0

        # reload window list
        self.windowListController.setContent_(app_data['windows'])
        self.windowList.reloadData()

    @IBAction
    def filterWindowEvents_(self, sender):
        """ write database table of events for selected app/windows and close"""

        NSNotificationCenter.defaultCenter().postNotificationName_object_('getFilteredWindowEvents',self)
        self.reviewController.close()

    def getApplicationsAndWindowsForTable(self):
        """ query database for list of recorded apps and windows """

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

    def populateElements(self):
        """ get app/window data, list of screenshots, and draw timeline """

        # prepare data for app and window tables
        self.getApplicationsAndWindowsForTable(self)
        defaults = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('appWindowList')
        self.applyDefaults(self, defaults, self.reviewController.results)

        # get list of image files
        self.list_of_files = self.generateScreenshotList(self)

        # re-sort list items
        self.reviewController.arrayController.rearrangeObjects()

    def generateScreenshotList(self):
        """ get list of all screenshots taken by Selfspy """

        path = os.path.join(cfg.CURRENT_DIR, 'screenshots/')
        path = os.path.expanduser(path)
        list_of_files = [ f for f in listdir(path) if isfile(join(path,f)) ]
        return list_of_files

    def tableViewSelectionDidChange_(self,sender):
        """ change window list based on app selelction """

        selected_row = self.appList.selectedRow()
        selected_view = self.appList.viewAtColumn_row_makeIfNecessary_(0,selected_row,False)

        if selected_view:
            app_data = selected_view.objectValue()
            self.windowListController.setContent_(app_data['windows'])
            self.windowList.reloadData()


    def windowWillClose_(self, notification):
        """ save state of tables to user defaults when window closes """

        NSUserDefaultsController.sharedUserDefaultsController().defaults().setObject_forKey_(self.results, 'appWindowList')


    def show(self):
        """ create the necessary elements and show the reviewer window """

        # close any open reviewer windows
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

        # get screenshots and app/window data
        self.populateElements(self)


    show = classmethod(show)
