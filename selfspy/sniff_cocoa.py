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

#Modified in 2014 by Aurélien Tabard and Adam Rule

import string 
import objc, re, os
from objc import IBAction, IBOutlet

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

import time
from datetime import datetime
NOW = datetime.now

start_time = NSDate.date()

#Preferences window launcher
class PreferencesController(NSWindowController):

    @IBAction
    def changeImageSize_(self, notification):
        height = notification.tag()
        print height
        print NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('imageSize')

    def windowDidLoad(self):
		NSWindowController.windowDidLoad(self)

    def show(self):
        try:
            if self.prefController:
                self.prefController.close()
        except:
            pass

        #open window from NIB file, show front and center
        self.prefController = NSWindowController.alloc().initWithWindowNibName_("Preferences")
        self.prefController.showWindow_(None)
        self.prefController.window().makeKeyAndOrderFront_(None) # not working
        self.prefController.window().center()
             
        self.prefController.retain() # needed to keep window from disappearing

    show = classmethod(show)

#Preferences window launcher
class ExperienceController(NSWindowController):
    
    experienceText = IBOutlet()

    @IBAction
    def changeExperienceText_(self, notification):
        print "hello"

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)

    def show(self):
        try:
            if self.expController:
                self.expController.close()
        except:
            pass
        
        #open window from NIB file, show front and center
        self.expController = NSWindowController.alloc().initWithWindowNibName_("Experience")
        self.expController.showWindow_(None) 
        self.expController.window().makeKeyAndOrderFront_(None) # not working
        self.expController.window().center()
        
             
        self.expController.retain() # needed to keep window from disappearing

    show = classmethod(show)


class Sniffer:
    def __init__(self):
        self.key_hook = lambda x: True
        self.mouse_button_hook = lambda x: True
        self.mouse_move_hook = lambda x: True
        self.screen_hook = lambda x: True
        self.screenSize = [NSScreen.mainScreen().frame().size.width, NSScreen.mainScreen().frame().size.height]
        self.screenRatio = self.screenSize[0]/self.screenSize[1]
        #self.screenshotSize = [self.screenSize[0],self.screenSize[1]]


    def createAppDelegate(self):
        sc = self

        class AppDelegate(NSObject):
            statusbar = None
            state = 'pause'
            screenshot = True
            
            def applicationDidFinishLaunching_(self, notification):
                NSLog("Application did finish launching.")

                self.createStatusMenu()
                self.createStatusButton()

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

                #Register preferance defaults
                prefDictionary = {}
                prefDictionary[u'imageSize'] = 720
                prefDictionary[u"imageFreq"] = 50
                prefDictionary[u"experienceFreq"] = 30
                #Not sure if next line encodes the file URL correctly, 
                #see https://developer.apple.com/library/ios/documentation/Cocoa/Conceptual/UserDefaults/AccessingPreferenceValues/AccessingPreferenceValues.html
                prefDictionary[u"dbLocation"] = NSKeyedArchiver.archivedDataWithRootObject_('file:///Users/adamrule/.selfspy')
                #following preferences not exposed to the user in the Preferences window
                prefDictionary[u"maxScreenshotDelay"] = 100
                prefDictionary[u"dbName"] = 'selfspy.sqlite'
                prefDictionary[u"lockFile"] = 'selfspy.pid'
                prefDictionary[u"lock"] = None

                NSUserDefaultsController.sharedUserDefaultsController().setInitialValues_(prefDictionary)
                #NSUserDefaults.registerDefaults_(prefDictionary)

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

            '''
            def setScreenshotSize_(self, notification):
            	height = notification.tag()
            	sc.screenshotSize[0] = height*sc.screenRatio
            	sc.screenshotSize[1] = height
            	notification.setState_(1)
            	print("Change screenshot size to " + str(sc.screenshotSize[1]) + " x " + str(sc.screenshotSize[0]))
            '''

            def bookmarkEvent_(self, sender):
                print "Hello again, World!"

            def showPreferences_(self, notification):
            	NSLog("Showing Preference Window...")
            	PreferencesController.show()

            def showExperience_(self, notification):
                NSLog("Showing Experience Sampling Window...")
                ExperienceController.show()

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

                menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Experience Sample', 'showExperience:', '')
                self.menu.addItem_(menuitem)
            	
            	menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Preferences...', 'showPreferences:', '')
                self.menu.addItem_(menuitem)

                menuitem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_('Quit Selfspy', 'terminate:', '')
                self.menu.addItem_(menuitem)

                # Bind it to the status item
                self.statusitem.setMenu_(self.menu)

                self.statusitem.setEnabled_(TRUE)                
                self.statusitem.retain()

            def createStatusButton(self):
                NSLog("Creating status button")
                statusbar = NSStatusBar.systemStatusBar()

                # Create the statusbar item
                self.statusitem2 = statusbar.statusItemWithLength_(NSVariableStatusItemLength)
                # self.statusitem.setTitle_(u"Selfspy")

                # Load all images
                self.bookmarkIcon = NSImage.alloc().initByReferencingFile_('../Resources/bookmark-64.png')
                self.bookmarkIcon.setScalesWhenResized_(True)
                self.bookmarkIcon.setSize_((20, 20))
                self.statusitem2.setImage_(self.bookmarkIcon)


                # Let it highlight upon clicking
                self.statusitem2.setHighlightMode_(1)
                # Set a tooltip
                self.statusitem2.setToolTip_('Selfspy')

                # https://developer.apple.com/library/mac/documentation/cocoa/reference/applicationkit/classes/NSButtonCell_Class/Reference/Reference.html
                self.hel = NSButton.alloc().initWithFrame_ (((0.0, 0.0), (18.0, 22.0)))
                self.hel.setBezelStyle_(6)
                # self.hel.setTransparent_(True)
                self.hel.setButtonType_(0)
                self.hel.setBackgroundColor_(0)
                self.hel.setBordered_(False)
                self.hel.setTitle_( 'Bookmark' )
                self.hel.setImage_(self.bookmarkIcon)
                # self.hel.setTarget_( self )
                self.hel.setAction_( "bookmarkEvent:" )

                # Bind to the status item
                self.statusitem2.setView_(self.hel)

                self.statusitem2.setEnabled_(TRUE)       
                self.statusitem2.retain()


            def isScreenshotActive(self):
              # print "state", self.state
              return self.screenshot

        return AppDelegate

    def run(self):
        app = NSApplication.sharedApplication()
        self.delegate = self.createAppDelegate().alloc().init()
        app.setDelegate_(self.delegate)
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
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
        scale = 1.0

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
        width = self.screenRatio * NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('imageSize')
        height = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('imageSize')

        mouseLoc = NSEvent.mouseLocation()
        # Get cursor information
        x = int(mouseLoc.x *scale)
        y = int(mouseLoc.y *scale)
        w = int(width *scale)
        h = int(height *scale)
        org_x = x
        org_y = y

        print "cursor :", x, y, w, h
        
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

        # Adding Mouse cursor to the screenshot
        # https://stackoverflow.com/questions/8008630/not-displaying-mouse-cursor
        # NSImage *overlay = [[[NSCursor arrowCursor] image] copy]        
        # # arrowCursor grabs the arrow cursor
        # # currentSystemCursor grabs the image of the current cursor, 
        # overlay = NSCursor.arrowCursor().image().copy()

        # # Now convert NSImage into CGImage
        # # Gave up on this, I don't understand why it doesn't work...
        # # objc : [overlay CGImageForProposedRect: NULL context: NULL hints: NULL]
        # # pyobjc : overlay(CGImageForProposedRect: NULL context: NULL hints: NULL]
        # cursorRectangle = NSMakeRect(0, 0, w, h)
        # overlay2 = overlay.CGImageForProposedRect_context_hints_(None,None,None)
        # overlay2 = overlay.CGImageForProposedRect_context_(cursorRectangle,None)

        # Adding Mouse cursor to the screenshot
        # Alternative 1 : load a cursor image 
        print "test"
        # Convert path to url for saving image
        cursorPath = "../Resources/cursor.png"
        cursorPathStr = NSString.stringByExpandingTildeInPath(cursorPath)
        cursorURL = NSURL.fileURLWithPath_(cursorPathStr)

        # Create a CGImageSource object from 'url'.
        cursorImageSource = Quartz.CGImageSourceCreateWithURL(cursorURL, None)

        # Create a CGImage object from the first image in the file. Image
        # indexes are 0 based.
        cursorOverlay = Quartz.CGImageSourceCreateImageAtIndex(cursorImageSource, 0, None)

        print "test"
        Quartz.CGContextDrawImage(bitmapContext,
          CG.CGRectMake(org_x, org_y, w, h), 
          cursorOverlay)

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