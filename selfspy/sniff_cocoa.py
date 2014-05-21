# Copyright 2012 Bjarte Johansen

# This file is part of Selfspy

# Selfspy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Selfspy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Selfspy.  If not, see <http://www.gnu.org/licenses/>.


import string 
import objc, re, os

from Foundation import *
from AppKit import *
from PyObjCTools import NibClassBuilder, AppHelper

from Cocoa import (NSEvent,
                   NSKeyDown, NSKeyDownMask, NSKeyUp, NSKeyUpMask,
                   NSLeftMouseUp, NSLeftMouseDown, NSLeftMouseUpMask, NSLeftMouseDownMask,
                   NSRightMouseUp, NSRightMouseDown, NSRightMouseUpMask, NSRightMouseDownMask,
                   NSMouseMoved, NSMouseMovedMask,
                   NSScrollWheel, NSScrollWheelMask,
                   NSFlagsChanged, NSFlagsChangedMask,
                   NSAlternateKeyMask, NSCommandKeyMask, NSControlKeyMask,
                   NSShiftKeyMask, NSAlphaShiftKeyMask,
                   NSApplicationActivationPolicyProhibited,
                   NSURL, NSString)
from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID

import config as cfg
import Quartz
import LaunchServices
import Quartz.CoreGraphics as CG
# import Quartz.CoreImage as CI

import time
from datetime import datetime
NOW = datetime.now

start_time = NSDate.date()


class Sniffer:
    def __init__(self):
        self.key_hook = lambda x: True
        self.mouse_button_hook = lambda x: True
        self.mouse_move_hook = lambda x: True
        self.screen_hook = lambda x: True

    def createAppDelegate(self):
        sc = self

        class AppDelegate(NSObject):
            statusbar = None
            state = 'pause'
            screenshot = True

            def applicationDidFinishLaunching_(self, notification):
                NSLog("Application did finish launching.")

                self.createStatusMenu()

                mask = (NSKeyDownMask
                        | NSKeyUpMask
                        | NSLeftMouseDownMask
                        | NSLeftMouseUpMask
                        | NSRightMouseDownMask
                        | NSRightMouseUpMask
                        | NSMouseMovedMask
                        | NSScrollWheelMask
                        | NSFlagsChangedMask)
                NSEvent.addGlobalMonitorForEventsMatchingMask_handler_(mask, sc.handler)

                # self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
                # self.statusItem.setTitle_(u"Selfspy")
                # self.statusItem.setHighlightMode_(TRUE)
                # self.statusItem.setEnabled_(TRUE)
                # self.statusItem.retain()

            def applicationWillTerminate_(self, application):
                # need to release the lock here as when the
                # application terminates it does not run the rest the
                # original main, only the code that has crossed the
                # pyobc bridge.
                if cfg.LOCK.is_locked():
                    cfg.LOCK.release()
                print "Exiting ..."

            def toggleLogging_(self, notification):
                NSLog("todo : pause logging")

            def toggleScreenshots_(self, notification):
                print "toggleScreenshots"
                if self.screenshot:
                  self.menu.itemWithTitle_("Pause screenshots").setTitle_("Record screenshots")
                else :
                  self.menu.itemWithTitle_("Record screenshots").setTitle_("Pause screenshots")
                self.screenshot = not self.screenshot

            def createStatusMenu(self):
                NSLog("Creating app menu")
                statusbar = NSStatusBar.systemStatusBar()

                # Create the statusbar item
                self.statusitem = statusbar.statusItemWithLength_(NSVariableStatusItemLength)
                # self.statusitem.setTitle_(u"Selfspy")

                # Load all images
                self.icon = NSImage.alloc().initByReferencingFile_('../Resources/eye-32.png')
                self.icon.setScalesWhenResized_(True)
                self.icon.setSize_((20, 20))
                self.statusitem.setImage_(self.icon)

                # Let it highlight upon clicking
                self.statusitem.setHighlightMode_(1)
                # Set a tooltip
                self.statusitem.setToolTip_('Selfspy')

                # Build a very simple menu
                self.menu = NSMenu.alloc().init()
                self.menu.setAutoenablesItems_(False)

                menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Pause Logging', 'toggleLogging:', '')
                menuitem.setEnabled_(False)
                self.menu.addItem_(menuitem)

                if self.screenshot:
                  menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Pause screenshots', 'toggleScreenshots:', '')
                  self.menu.addItem_(menuitem)
                else :
                  menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Record screenshots', 'toggleScreenshots:', '')
                  self.menu.addItem_(menuitem)

                menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Quit Selfspy', 'terminate:', '')
                self.menu.addItem_(menuitem)

                # Bind it to the status item
                self.statusitem.setMenu_(self.menu)

                self.statusitem.setEnabled_(TRUE)                
                self.statusitem.retain()

            def isScreenshotActive(self):
              # print "state", self.state
              return self.screenshot

        return AppDelegate

    def run(self):
        app = NSApplication.sharedApplication()
        self.delegate = self.createAppDelegate().alloc().init()
        app.setDelegate_(self.delegate)
        app.setActivationPolicy_(NSApplicationActivationPolicyProhibited)
        self.workspace = NSWorkspace.sharedWorkspace()
        AppHelper.runEventLoop()

    def cancel(self):
        AppHelper.stopEventLoop()

    def handler(self, event):
        try:
            activeApps = self.workspace.runningApplications()
            #Have to look into this if it is too slow on move and scoll,
            #right now the check is done for everything.
            for app in activeApps:
                if app.isActive():
                    options = kCGWindowListOptionOnScreenOnly
                    windowList = CGWindowListCopyWindowInfo(options,
                                                            kCGNullWindowID)
                    for window in windowList:
                        if (window['kCGWindowNumber'] == event.windowNumber()
                            or (not event.windowNumber()
                                and window['kCGWindowOwnerName'] == app.localizedName())):
                            geometry = window['kCGWindowBounds']
                            self.screen_hook(window['kCGWindowOwnerName'],
                                             window.get('kCGWindowName', u''),
                                             geometry['X'],
                                             geometry['Y'],
                                             geometry['Width'],
                                             geometry['Height'])
                            break
                    break

            loc = NSEvent.mouseLocation()
            if event.type() == NSLeftMouseDown:
                self.mouse_button_hook(1, loc.x, loc.y)
            # elif event.type() == NSLeftMouseUp:
            #     self.mouse_button_hook(1, loc.x, loc.y)
            elif event.type() == NSRightMouseDown:
                self.mouse_button_hook(3, loc.x, loc.y)
#           elif event.type() == NSRightMouseUp:
#               self.mouse_button_hook(2, loc.x, loc.y)
            elif event.type() == NSScrollWheel:
                if event.deltaY() > 0:
                    self.mouse_button_hook(4, loc.x, loc.y)
                elif event.deltaY() < 0:
                    self.mouse_button_hook(5, loc.x, loc.y)
                if event.deltaX() > 0:
                    self.mouse_button_hook(6, loc.x, loc.y)
                elif event.deltaX() < 0:
                    self.mouse_button_hook(7, loc.x, loc.y)
#               if event.deltaZ() > 0:
#                   self.mouse_button_hook(8, loc.x, loc.y)
#               elif event.deltaZ() < 0:
#                   self.mouse_button_hook(9, loc.x, loc.y)
            elif event.type() == NSKeyDown:
                flags = event.modifierFlags()
                modifiers = []  # OS X api doesn't care it if is left or right
                if flags & NSControlKeyMask:
                    modifiers.append('Ctrl')
                if flags & NSAlternateKeyMask:
                    modifiers.append('Alt')
                if flags & NSCommandKeyMask:
                    modifiers.append('Cmd')
                if flags & (NSShiftKeyMask | NSAlphaShiftKeyMask):
                    modifiers.append('Shift')
                character = event.charactersIgnoringModifiers()
                # these two get a special case because I am unsure of
                # their unicode value
                if event.keyCode() is 36:
                    character = "Enter"
                elif event.keyCode() is 51:
                    character = "Backspace"
                self.key_hook(event.keyCode(),
                              modifiers,
                              keycodes.get(character,
                                           character),
                              event.isARepeat())
            elif event.type() == NSMouseMoved:
                self.mouse_move_hook(loc.x, loc.y)
        except (SystemExit, KeyboardInterrupt):
            AppHelper.stopEventLoop()
            return
        except:
            AppHelper.stopEventLoop()
            raise

    def isScreenshotActive(self):
      return self.delegate.isScreenshotActive()
        
    def screenshot2(self, path, region = None):
        # -t tiff saves to tiff format, should be faster
        # -C captures the mouse cursor.
        # -x removes the screenshot sound
        command = "screencapture -C -x " + path
        print command
        os.system(command)

    def screenshot(self, path, region = None):
    #https://pythonhosted.org/pyobjc/examples/Quartz/Core%20Graphics/CGRotation/index.html
      try:
        #For testing how long it takes to take screenshot
        start = time.time()
        scale = 0.5

        #Set to capture entire screen, including multiple monitors
        if region is None:  
          region = CG.CGRectInfinite

        # Create CGImage, composite image of windows in region
        image = CG.CGWindowListCreateImage(
          region,
          CG.kCGWindowListOptionOnScreenOnly,
          CG.kCGNullWindowID,
          CG.kCGWindowImageDefault
        )

        #Get size of image    
        width = CG.CGImageGetWidth(image)
        height = CG.CGImageGetHeight(image)
        
        #Allocate image data and create context for drawing image
        imageData = LaunchServices.objc.allocateBuffer(int(4 * width * height))

        bitmapContext = Quartz.CGBitmapContextCreate(
          imageData, # image data we just allocated...
          width*scale, 
          height*scale, 
          8, # 8 bits per component
          4 * width, # bytes per pixel times number of pixels wide
          Quartz.CGImageGetColorSpace(image), # use the same colorspace as the original image
          Quartz.kCGImageAlphaPremultipliedFirst # use premultiplied alpha
        ) 

        #Draw image on context at new scale
        rect = CG.CGRectMake(0.0,0.0,width*scale,height*scale)
        Quartz.CGContextDrawImage(bitmapContext, rect, image)

        #Recreate image from context
        imageOut = Quartz.CGBitmapContextCreateImage(bitmapContext)

        #Image properties dictionary
        dpi = 72 # FIXME: Should query this from somewhere, e.g for retina display
        properties = {
          Quartz.kCGImagePropertyDPIWidth: dpi,
          Quartz.kCGImagePropertyDPIHeight: dpi,
          Quartz.kCGImageDestinationLossyCompressionQuality: 0.6,
        }

        #Convert path to url for saving image
        pathStr = NSString.stringByExpandingTildeInPath(path)
        url = NSURL.fileURLWithPath_(pathStr)

        #Set image destination (where it will be saved)
        dest = Quartz.CGImageDestinationCreateWithURL(
          url,
          LaunchServices.kUTTypeJPEG, # file type
          1, # 1 image in file
          None
        )

        # Add the image to the destination, with certain properties
        Quartz.CGImageDestinationAddImage(dest, imageOut, properties)

        # finalize the CGImageDestination object. 
        Quartz.CGImageDestinationFinalize(dest)

        #For testing how long it takes to take screenshot
        stop = time.time()
        print str(stop-start)[:5] + ' seconds to save image'

      except KeyboardInterrupt:
        AppHelper.stopEventLoop()
      except:
        print "couldn't save image"


# Cocoa does not provide a good api to get the keycodes, therefore we
# have to provide our own.
keycodes = {
   u"\u0009": "Tab",
   u"\u001b": "Escape",
   u"\uf700": "Up",
   u"\uF701": "Down",
   u"\uF702": "Left",
   u"\uF703": "Right",
   u"\uF704": "F1",
   u"\uF705": "F2",
   u"\uF706": "F3",
   u"\uF707": "F4",
   u"\uF708": "F5",
   u"\uF709": "F6",
   u"\uF70A": "F7",
   u"\uF70B": "F8",
   u"\uF70C": "F9",
   u"\uF70D": "F10",
   u"\uF70E": "F11",
   u"\uF70F": "F12",
   u"\uF710": "F13",
   u"\uF711": "F14",
   u"\uF712": "F15",
   u"\uF713": "F16",
   u"\uF714": "F17",
   u"\uF715": "F18",
   u"\uF716": "F19",
   u"\uF717": "F20",
   u"\uF718": "F21",
   u"\uF719": "F22",
   u"\uF71A": "F23",
   u"\uF71B": "F24",
   u"\uF71C": "F25",
   u"\uF71D": "F26",
   u"\uF71E": "F27",
   u"\uF71F": "F28",
   u"\uF720": "F29",
   u"\uF721": "F30",
   u"\uF722": "F31",
   u"\uF723": "F32",
   u"\uF724": "F33",
   u"\uF725": "F34",
   u"\uF726": "F35",
   u"\uF727": "Insert",
   u"\uF728": "Delete",
   u"\uF729": "Home",
   u"\uF72A": "Begin",
   u"\uF72B": "End",
   u"\uF72C": "PageUp",
   u"\uF72D": "PageDown",
   u"\uF72E": "PrintScreen",
   u"\uF72F": "ScrollLock",
   u"\uF730": "Pause",
   u"\uF731": "SysReq",
   u"\uF732": "Break",
   u"\uF733": "Reset",
   u"\uF734": "Stop",
   u"\uF735": "Menu",
   u"\uF736": "User",
   u"\uF737": "System",
   u"\uF738": "Print",
   u"\uF739": "ClearLine",
   u"\uF73A": "ClearDisplay",
   u"\uF73B": "InsertLine",
   u"\uF73C": "DeleteLine",
   u"\uF73D": "InsertChar",
   u"\uF73E": "DeleteChar",
   u"\uF73F": "Prev",
   u"\uF740": "Next",
   u"\uF741": "Select",
   u"\uF742": "Execute",
   u"\uF743": "Undo",
   u"\uF744": "Redo",
   u"\uF745": "Find",
   u"\uF746": "Help",
   u"\uF747": "ModeSwitch"}
