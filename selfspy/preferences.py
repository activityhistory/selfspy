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


class PreferencesController(NSWindowController):
    """ Preferences window controller """

    # outlets for UI elements
    screenshotSizePopup = IBOutlet()
    screenshotSizeMenu = IBOutlet()
    clearDataPopup = IBOutlet()
    popover = IBOutlet()
    popButton = IBOutlet()

    @IBAction
    def changedMaxScreenshot_(self,sender):
        """ tells Selfspy to restart screnshot loop on preference change """

        NSNotificationCenter.defaultCenter().postNotificationName_object_('changedMaxScreenshot',self)

    @IBAction
    def clearData_(self,sender):
        """ tells Selfspy to delete recent data based on selected preference """

        NSNotificationCenter.defaultCenter().postNotificationName_object_('clearData',self)

    def windowDidLoad(self):
        """ manage screenshot size preferences when the window opens """

        # do the default behavior
        NSWindowController.windowDidLoad(self)

        # Set screenshot size preference options based on screen's native height
        self.prefController.screenshotSizeMenu.removeAllItems()
        nativeHeight = int(NSScreen.mainScreen().frame().size.height)
        menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(str(nativeHeight)+' px', '', '')
        menuitem.setTag_(nativeHeight)
        self.prefController.screenshotSizeMenu.addItem_(menuitem)

        # add standard sizes
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
        """ show the new window front and center """

        # destroy any open Preference windows
        try:
            if self.prefController:
                self.prefController.close()
        except:
            pass

        # open window from NIB file, show front and center, show on top
        self.prefController = PreferencesController.alloc().initWithWindowNibName_("Preferences")
        self.prefController.showWindow_(None)
        self.prefController.window().makeKeyAndOrderFront_(None)
        self.prefController.window().center()
        self.prefController.retain()
        NSNotificationCenter.defaultCenter().postNotificationName_object_('makeAppActive',self)

        # make window close on Cmd-w
        self.prefController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalentModifierMask_(NSCommandKeyMask)
        self.prefController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalent_("w")

    show = classmethod(show)
