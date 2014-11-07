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


import objc

from objc import IBAction, IBOutlet

from Foundation import *
from AppKit import *

from Cocoa import NSNotificationCenter


# Preferences window controller
class PreferencesController(NSWindowController):

    # outlets for UI elements
    screenshotSizePopup = IBOutlet()
    screenshotSizeMenu = IBOutlet()
    clearDataPopup = IBOutlet()

    # notifications sent to Activity Store
    @IBAction
    def clearData_(self,sender):
        NSNotificationCenter.defaultCenter().postNotificationName_object_('clearData',self)

    @IBAction
    def changedScreenshot_(self,sender):
        NSNotificationCenter.defaultCenter().postNotificationName_object_('changedScreenshot',self)

    @IBAction
    def changedMaxScreenshot_(self,sender):
        NSNotificationCenter.defaultCenter().postNotificationName_object_('changedMaxScreenshotPref',self)

    @IBAction
    def changedExperienceRate_(self,sender):
        NSNotificationCenter.defaultCenter().postNotificationName_object_('changedExperiencePref',self)

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)

        # Set screenshot size options based on screen's native height
        self.prefController.screenshotSizeMenu.removeAllItems()
        nativeHeight = int(NSScreen.mainScreen().frame().size.height)
        menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(str(nativeHeight)+' px', '', '')
        menuitem.setTag_(nativeHeight)
        self.prefController.screenshotSizeMenu.addItem_(menuitem)

        sizes = [1080,720,480]
        for x in sizes:
            if x < nativeHeight:
                menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(str(x)+' px', '', '')
                menuitem.setTag_(x)
                self.prefController.screenshotSizeMenu.addItem_(menuitem)

        # update newly created screenshot size dropdown to select saved preference or default size
        selectedSize = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('imageSize')
        selectedMenuItem = self.prefController.screenshotSizeMenu.itemWithTag_(selectedSize)
        if(selectedMenuItem):
            self.prefController.screenshotSizePopup.selectItemWithTag_(selectedSize)
        else:
            nativeMenuItem = self.prefController.screenshotSizeMenu.itemWithTag_(nativeHeight)
            NSUserDefaultsController.sharedUserDefaultsController().defaults().setInteger_forKey_(nativeHeight,'imageSize')
            self.prefController.screenshotSizePopup.selectItemWithTag_(nativeHeight)

    def show(self):
        try:
            if self.prefController:
                self.prefController.close()
        except:
            pass

        # open window from NIB file, show front and center
        self.prefController = PreferencesController.alloc().initWithWindowNibName_("Preferences")
        self.prefController.showWindow_(None)
        self.prefController.window().makeKeyAndOrderFront_(None)
        self.prefController.window().center()
        self.prefController.retain()

        # needed to show window on top of other applications
        NSNotificationCenter.defaultCenter().postNotificationName_object_('makeAppActive',self)

        # make window close on Cmd-w
        self.prefController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalentModifierMask_(NSCommandKeyMask)
        self.prefController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalent_("w")

    show = classmethod(show)
