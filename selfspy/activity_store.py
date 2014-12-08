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
import sys
import time
import datetime

import sqlalchemy
import re
import random

from Foundation import *
from AppKit import *

from Cocoa import NSNotificationCenter, NSTimer, NSWorkspace
import Quartz
from Quartz import (CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly,
                    kCGNullWindowID)

from selfspy import sniff_cocoa as sniffer
from selfspy import config as cfg
from selfspy import models
from selfspy.models import RecordingEvent, Process, ProcessEvent, Window, WindowEvent, Geometry, Click, Keys, Experience, Location, Debrief, Bookmark

from urlparse import urlparse

NOW = datetime.datetime.now
SKIP_MODIFIERS = {"", "Shift_L", "Control_L", "Super_L", "Alt_L", "Super_R", "Control_R", "Shift_R", "[65027]"}  # [65027] is AltGr in X for some ungodly reason.
SCROLL_BUTTONS = {4, 5, 6, 7}
SCROLL_COOLOFF = 10  # seconds


class Display:
    def __init__(self):
        self.proc_id = None
        self.win_id = None
        self.geo_id = None


class KeyPress:
    def __init__(self, key, time, is_repeat):
        self.key = key
        self.time = time
        self.is_repeat = is_repeat


class MouseMove:
    def __init__(self, xy, time):
        self.xy = xy
        self.time = time


class ActivityStore:
    def __init__(self, db_name):

        # We check if a selfspy thumbdrive is plugged in and available
        # if so this is where we're storing the screenshots and DB
        # otherwise we store locally
        self.lookupThumbdrive()
        self.defineCurrentDrive()

        screenshot_directory = os.path.join(cfg.CURRENT_DIR, 'screenshots')
        try:
            os.makedirs(screenshot_directory)
        except OSError:
            pass

        audio_directory = os.path.join(cfg.CURRENT_DIR, 'audio')
        try:
            os.makedirs(audio_directory)
        except OSError:
            pass

        db_name = os.path.join(cfg.CURRENT_DIR, db_name)
        try:
            self.session_maker = models.initialize(db_name)
        except sqlalchemy.exc.OperationalError:
            print "Database operational error. Your storage device may be full. Exiting Selfspy..."

            alert = NSAlert.alloc().init()
            alert.addButtonWithTitle_("OK")
            alert.setMessageText_("Database operational error. Your storage device may be full. Exiting Selfspy.")
            alert.setAlertStyle_(NSWarningAlertStyle)
            alert.runModal()

            sys.exit()

        self.key_presses = []
        self.mouse_path = []

        self.current_window = Display()
        self.current_apps = []
        self.active_app = ''
        self.current_windows = []
        self.regularWindowsIds = []
        self.active_window = {'title': '', 'process': '', 'url': ''}

        self.last_scroll = {button: 0 for button in SCROLL_BUTTONS}

        self.last_key_time = time.time()
        self.last_move_time = time.time()
        self.last_commit = time.time()
        self.last_screenshot = time.time()
        self.last_experience = time.time()

        self.screenshots_active = True
        self.screenshot_time_min = 0.2
        self.screenshot_time_max = 60
        self.exp_time = 120         # time before first experience sample shows
        self.thumbdrive_time = 10

        self.addObservers()

        self.started = NOW()

    def addObservers(self):
        # Listen for events from the Preferences window
        s = objc.selector(self.checkMaxScreenshotOnPrefChange_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'changedMaxScreenshotPref', None)

        s = objc.selector(self.checkExperienceOnPrefChange_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'changedExperiencePref', None)

        s = objc.selector(self.toggleScreenshotMenuTitle_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'changedScreenshot', None)

        s = objc.selector(self.clearData_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'clearData', None)

        # Listen for events from the Experience sampling window
        s = objc.selector(self.gotExperience_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'experienceReceived', None)

        s = objc.selector(self.getPriorExperiences_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'getPriorExperiences', None)

        # Listen for events from the Debriefer window
        s = objc.selector(self.getDebriefExperiences_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'getDebriefExperiences', None)

        s = objc.selector(self.recordDebrief_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'recordDebrief', None)

        s = objc.selector(self.populateDebriefWindow_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'populateDebriefWindow', None)

        s = objc.selector(self.queryMetadata_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'queryMetadata', None)

        s = objc.selector(self.getAppsAndUrls_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'getAppsAndUrls', None)

        s = objc.selector(self.getProcess1times_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'getProcess1times', None)

        # Listen for events thrown by the Status bar menu
        s = objc.selector(self.checkLoops_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'checkLoops', None)

        s = objc.selector(self.recordBookmark_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'recordBookmark', None)

        s = objc.selector(self.noteRecordingState_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'noteRecordingState', None)

        # Listen for events from Sniff Cocoa
        s = objc.selector(self.checkDrive_,signature='v@:')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'checkDrive_', None)

        # Listen for close of Selfspy
        s = objc.selector(self.gotCloseNotification_,signature='v@:')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'closeNotification', None)

    def run(self):
        self.session = self.session_maker()

        self.sniffer = sniffer.Sniffer()
        self.sniffer.screen_hook = self.got_screen_change
        self.sniffer.key_hook = self.got_key
        self.sniffer.mouse_button_hook = self.got_mouse_click
        self.sniffer.mouse_move_hook = self.got_mouse_move

        self.sniffer.run()

    def checkLoops_(self, notification):
        recording = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('recording')
        if(recording):
            self.startLoops()
        else:
            self.stopLoops()

    def startLoops(self):
        # Timers for taking screenshots when idle, and showing experience-sample window
        s = objc.selector(self.runMaxScreenshotLoop,signature='v@:')
        self.screenshotTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(self.screenshot_time_max, self, s, None, False)

        s = objc.selector(self.runExperienceLoop,signature='v@:')
        self.experienceTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(self.exp_time, self, s, None, False)

        # Timer for checking if thumbdrive/memory card is available
        s = objc.selector(self.defineCurrentDrive,signature='v@:')
        self.thumbdriveTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(self.thumbdrive_time, self, s, None, True)
        self.thumbdriveTimer.fire() # get location immediately

    def stopLoops(self):
        try:
            if self.screenshotTimer:
                self.screenshotTimer.invalidate()
            if self.experienceTimer:
                self.experienceTimer.invalidate()
            if self.thumbdriveTimer:
                self.thumbdriveTimer.invalidate()
        except(AttributeError):
            pass

    def close(self):
        """ stops the sniffer and stores the latest keys and close of programs. To be used on shutdown of program"""
        self.sniffer.cancel()
        self.store_keys()

    def trycommit(self):
        self.last_commit = time.time()
        for _ in xrange(1000):
            try:
                self.session.commit()
                break
            except sqlalchemy.exc.OperationalError:
                if(NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('recording')):
                    self.sniffer.delegate.toggleLogging_(self)
                self.session.rollback()

                print "Database operational error. Your storage device may be full. Turning off Selfspy recording."

                alert = NSAlert.alloc().init()
                alert.addButtonWithTitle_("OK")
                alert.setMessageText_("Database operational error. Your storage device may be full. Turning off Selfspy recording.")
                alert.setAlertStyle_(NSWarningAlertStyle)
                alert.runModal()

                break
            except:
                print "Rollback"
                self.session.rollback()

    def got_screen_change(self, process_name, window_name, win_x, win_y, win_width, win_height, browser_url, regularApps, regularWindows):
        """ Receives a screen change and stores any changes. If the process or window has
            changed it will also store any queued pressed keys.
            process_name is the name of the process running the current window
            window_name is the name of the window
            win_x is the x position of the window
            win_y is the y position of the window
            win_width is the width of the window
            win_height is the height of the window """
        # find apps that have opened or become active since the last check
        for app in regularApps:
            db_process = self.session.query(Process).filter_by(name=app.localizedName()).scalar()
            if not db_process:
                process_to_add = Process(app.localizedName())
                self.session.add(process_to_add)
                self.trycommit()
                db_process = self.session.query(Process).filter_by(name=app.localizedName()).scalar()
            process_id = db_process.id

            if app not in self.current_apps:
                process_event = ProcessEvent(process_id, "Open")
                self.session.add(process_event)
                self.current_apps.append(app)

        # find apps that have closed since last time
        for app in self.current_apps:
            if app not in regularApps:
                db_process = self.session.query(Process).filter_by(name=app.localizedName()).scalar()
                process_id = db_process.id
                process_event = ProcessEvent(process_id, "Close")
                self.session.add(process_event)
                self.trycommit()
                try:
                    self.current_apps.remove(app)
                except ValueError:
                    print("Error: Can not remove app from list. It does not seem to exist.")

        for window in regularWindows:
            # get id of process in database
            process = self.session.query(Process).filter_by(name=window['process']).scalar()
            pid = process.id if process else 0
            geometry = window['geometry']

            # add new windows and tabs to the database
            db_window = self.session.query(Window).filter_by(title=window['title'], process_id=pid, browser_url=window['url']).scalar()
            if not db_window:
                window_to_add = Window(window['title'], pid, window['url'])
                self.session.add(window_to_add)
                self.trycommit()
                db_window = self.session.query(Window).filter_by(title=window['title'], process_id=pid, browser_url=window['url']).scalar()
            window_id = db_window.id
            self.regularWindowsIds.append(window_id)

            if window_id not in self.current_windows:
                window_event = WindowEvent(window_id, "Open")
                self.session.add(window_event)
                self.trycommit()
                self.current_windows.append(window_id)

            # add new geometries to the database
            db_geometry = self.session.query(Geometry).filter_by(xpos=geometry['X'], ypos=geometry['Y'], width=geometry['Width'], height=geometry['Height']).scalar()
            if not db_geometry:
                geometry_to_add = Geometry(geometry['X'], geometry['Y'], geometry['Width'], geometry['Height'])
                self.session.add(geometry_to_add)
                self.trycommit()
                db_geometry = self.session.query(Geometry).filter_by(xpos=geometry['X'], ypos=geometry['Y'], width=geometry['Width'], height=geometry['Height']).scalar()
            geometry_id = db_geometry.id

        for window_id in self.current_windows:
            if window_id not in self.regularWindowsIds:
                window_event = WindowEvent(window_id, "Close")
                self.session.add(window_event)
                self.trycommit()
                try:
                    self.current_windows.remove(window_id)
                except ValueError:
                    print("Error: Can not remove window_id from list. It does not seem to exist.")

        # check for current process, window, and geometry
        # if any of these are new, update currents, store keys, and take screenshot
        # if the event happened on a new process or window, update the current window

        #TODO this part is still buggy for newtabs and window events
        # may need to rename variables and not overwrite
        windows_to_ignore = ["Focus Proxy", "Clipboard"]
        if window_name not in windows_to_ignore:
            cur_process = self.session.query(Process).filter_by(name=process_name).scalar()
            if not cur_process:
                cur_process = Process(process_name)
                self.session.add(cur_process)
                self.trycommit()
                cur_process = self.session.query(Process).filter_by(name=process_name).scalar()

            if cur_process.name != self.active_app:
                process_event = ProcessEvent(cur_process.id, "Active")
                self.session.add(process_event)
                self.active_app = cur_process.name

            if browser_url == "NO_URL":
                cur_window = self.session.query(Window).filter_by(title=window_name, process_id=cur_process.id).scalar()
            else:
                cur_window = self.session.query(Window).filter_by(process_id=cur_process.id, title=window_name, browser_url=browser_url).scalar()
            if not cur_window:
                cur_window = Window(window_name, cur_process.id, browser_url)
                self.session.add(cur_window)
            if (cur_window.title != self.active_window['title'] or cur_window.process_id != self.active_window['process'] or cur_window.browser_url != self.active_window['url']):
                window_event = WindowEvent(cur_window.id, "Active")
                self.session.add(window_event)
                self.trycommit()
                self.active_window = {'title': window_name, 'process': cur_process.id, 'url': browser_url}


            cur_geometry = self.session.query(Geometry).filter_by(xpos=win_x, ypos=win_y, width=win_width, height=win_height).scalar()
            if not cur_geometry:
                cur_geometry = Geometry(win_x, win_y, win_width, win_height)
                self.session.add(cur_geometry)

            # if its a new window, commit changes and update ids
            if (self.current_window.proc_id != cur_process.id
                    or self.current_window.win_id != cur_window.id):
                self.trycommit()
                self.store_keys()  # happens before as these keypresses belong to the previous window
                self.current_window.proc_id = cur_process.id
                self.current_window.win_id = cur_window.id
                self.current_window.geo_id = cur_geometry.id
                self.take_screenshot()

    def filter_many(self):
        specials_in_row = 0
        lastpress = None
        newpresses = []

        for press in self.key_presses:
            key = press.key
            if specials_in_row and key != lastpress.key:
                if specials_in_row > 1:
                    lastpress.key = '%s]x%d>' % (lastpress.key[:-2], specials_in_row)
                newpresses.append(lastpress)
                specials_in_row = 0

            if len(key) > 1:
                specials_in_row += 1
                lastpress = press
            else:
                newpresses.append(press)

        if specials_in_row:
            if specials_in_row > 1:
                lastpress.key = '%s]x%d>' % (lastpress.key[:-2], specials_in_row)
            newpresses.append(lastpress)

        self.key_presses = newpresses

    def store_keys(self):
        """ Stores the current queued key-presses """
        self.filter_many()

        if self.key_presses:
            keys = [press.key for press in self.key_presses]
            timings = [press.time for press in self.key_presses]
            add = lambda count, press: count + (0 if press.is_repeat else 1)
            nrkeys = reduce(add, self.key_presses, 0)

            # we don't store the keys pressed for privacy reasons
            # but we do keep their timings and numbers.
            curtext = u""
            keys = []

            self.session.add(Keys(curtext.encode('utf8'),
                                  keys,
                                  timings,
                                  nrkeys,
                                  self.started,
                                  self.current_window.proc_id,
                                  self.current_window.win_id,
                                  self.current_window.geo_id))

            self.trycommit()

            self.started = NOW()
            self.key_presses = []
            self.last_key_time = time.time()

    def got_key(self, keycode, state, string, is_repeat):
        """ Receives key-presses and queues them for storage.
            keycode is the code sent by the keyboard to represent the pressed key
            state is the list of modifier keys pressed, each modifier key should be represented
                  with capital letters and optionally followed by an underscore and location
                  specifier, i.e: SHIFT or SHIFT_L/SHIFT_R, ALT, CTRL
            string is the string representation of the key press
            repeat is True if the current key is a repeat sent by the keyboard """
        now = time.time()

        if string in SKIP_MODIFIERS:
            return

        if len(state) > 1 or (len(state) == 1 and state[0] != "Shift"):
            string = '<[%s: %s]>' % (' '.join(state), string)
        elif len(string) > 1:
            string = '<[%s]>' % string

        self.key_presses.append(KeyPress(string, now - self.last_key_time, is_repeat))
        self.last_key_time = now

        self.take_screenshot()

    def store_click(self, button, x, y):
        """ Stores incoming mouse-clicks """

        #Put mouse locations and timings in arrays
        locs = [loc.xy for loc in self.mouse_path]
        timings = [loc.time for loc in self.mouse_path]

        self.session.add(Click(button,
                               True,
                               x, y,
                               len(self.mouse_path),
                               locs,
                               timings,
                               self.current_window.proc_id,
                               self.current_window.win_id,
                               self.current_window.geo_id))
        self.mouse_path = []
        self.trycommit()

    def got_mouse_click(self, button, x, y):
        """ Receives mouse clicks and sends them for storage.
            Mouse buttons: left: 1, middle: 2, right: 3, scroll up: 4, down:5, left:6, right:7
            x,y are the coordinates of the keypress
            press is True if it pressed down, False if released"""
        if button in [4, 5, 6, 7]:
            if time.time() - self.last_scroll[button] < SCROLL_COOLOFF:
                return
            self.last_scroll[button] = time.time()
        # it seems that the macpro trackpad triggers fake clicks when touched
        # elif button == 1: #if a "real" click happens we take a screenshot
        self.take_screenshot()
        self.store_click(button, x, y)

    def got_mouse_move(self, x, y):
        """ Queues mouse movements at 10Hz.
            x,y are the new coordinates on moving the mouse"""
        frequency = 10.0
        now = time.time()

        if now-self.last_move_time > 1/frequency:
            self.mouse_path.append(MouseMove([x,y], now - self.last_move_time))
            self.last_move_time = now

    # removed project
    def store_experience(self, message, screenshot, user_initiated, ignored):
        self.session.add(Experience( message, screenshot, user_initiated, ignored))
        self.trycommit()

    def gotExperience_(self, notification):
        # project = notification.object().projectText.stringValue()
        message = notification.object().experienceText.stringValue()
        screenshot = notification.object().currentScreenshot
        user_initiated = notification.object().user_initiated
        ignored = notification.object().ignored
        self.store_experience(message, screenshot, user_initiated, ignored)

    def recordDebrief_(self, notification):
        experience_id = notification.object().experiences[notification.object().currentExperience-1]['id']
        doing_report = notification.object().debriefController.doingText.stringValue()
        audio_file = notification.object().debriefController.audio_file
        memory_id = notification.object().debriefController.memoryStrength.intValue()

        self.session.add(Debrief(experience_id, doing_report, audio_file, memory_id))
        self.trycommit()

    def populateDebriefWindow_(self, notification):
        controller = notification.object().debriefController
        audio_file = controller.audio_file
        current_id = notification.object().experiences[notification.object().currentExperience]['id']
        controller.memoryStrength.setIntValue_(3)

        # populate page with responses to last debrief
        q = self.session.query(Debrief).filter(Debrief.experience_id == current_id ).all()

        if q:
            controller.doingText.setStringValue_(q[-1].doing_report)
            controller.audio_file = q[-1].audio_file
            if q[-1].memory_id:
                controller.memoryStrength.setIntValue_(q[-1].memory_id)

            if (q[-1].audio_file != '') & (q[-1].audio_file != None):
                controller.recordButton.setEnabled_(False)
                controller.existAudioText.setStringValue_("You've recorded an answer:")
                controller.playAudioButton.setHidden_(False)
                controller.deleteAudioButton.setHidden_(False)
            else:
                controller.recordButton.setEnabled_(True)
                controller.existAudioText.setStringValue_("Record your answer:")
                controller.playAudioButton.setHidden_(True)
                controller.deleteAudioButton.setHidden_(True)
        else:
            controller.doingText.setStringValue_('')
            controller.audio_file = ''
            controller.recordButton.setEnabled_(True)
            controller.existAudioText.setStringValue_("Record your answer:")
            controller.playAudioButton.setHidden_(True)
            controller.deleteAudioButton.setHidden_(True)


    def queryMetadata_(self, notification):
        controller = notification.object().reviewController
        try:
            q = self.session.query(Window).filter(Window.created_at.like(controller.dateQuery + "%")).add_column(Window.process_id).all()
            if len(q) > 0:
                p = self.session.query(Process).filter(Process.id == q[0][1]).add_column(Process.name).all()
                if p[0][1] == "Safari" or p[0][1] == "Google Chrome":
                    u = self.session.query(Window).filter(Window.created_at.like(controller.dateQuery + "%")).add_column(Window.browser_url).all()
                    controller.queryResponse2.append(u[0][1])
                controller.queryResponse.append(p[0][1])
        except UnicodeEncodeError:
                pass

    def getAppsAndUrls_(self, notification):
        controller = notification.object().reviewController
        controller.results = []

        try:
            q_apps = self.session.query(Process).all()
            q_windows = self.session.query(Window).all()

            for a in q_apps:
                app_dict = NSMutableDictionary({'checked':False, 'image':'', 'appName': a.name, 'windows':[]})
                controller.results.append(app_dict)

            for w in q_windows:
                if w.browser_url == 'NO_URL' or w.browser_url == '' or not w.browser_url:
                    windowName = w.title
                    if not windowName:
                        windowName = ''
                    window_dict = NSMutableDictionary({'checked':False, 'windowName':windowName, 'image':''})
                else:
                    short_url = urlparse(w.browser_url).hostname
                    window_dict = NSMutableDictionary({'checked':False, 'windowName':short_url, 'image':''})
                if not window_dict in controller.results[w.process_id-1]['windows']:
                    window_dict = NSMutableDictionary.dictionaryWithDictionary_(window_dict)
                    controller.results[w.process_id-1]['windows'].append(window_dict)

                # p = self.session.query(Process).filter(Process.id == q[0][1]).add_column(Process.name).all()
                # if p[0][1] == "Safari" or p[0][1] == "Google Chrome":
                #     u = self.session.query(Window).filter(Window.created_at.like(controller.dateQuery + "%")).add_column(Window.browser_url).all()
                #     controller.queryResponse2.append(u[0][1])
                # controller.queryResponse.append(p[0][1])
        except UnicodeEncodeError:
                pass


    def getProcess1times_(self, notification):
        controller = notification.object().reviewController
        process = controller.current_timeline_process
        try:
            q = self.session.query(ProcessEvent).filter(ProcessEvent.process_id == process).add_column(ProcessEvent.event_type).add_column(ProcessEvent.created_at).all()
            if len(q) > 0:
                controller.p1Response.append(q)
        except UnicodeEncodeError:
                pass

    def getPriorExperiences_(self, notification):
        prior_messages = self.session.query(Experience).distinct(Experience.message).group_by(Experience.message).order_by(Experience.id.desc()).limit(5)
        for m in prior_messages:
            if(m.message != ''):
                notification.object().experienceText.addItemWithObjectValue_(m.message)

    def runExperienceLoop(self):
        experienceLoop = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('experienceLoop')
        if(experienceLoop):
            NSLog("Showing Experience Sampling Window on Cycle...")
            expController = sniffer.ExperienceController.show()
            expController.user_initiated = False
            self.last_experience = time.time()

            s = objc.selector(self.runExperienceLoop,signature='v@:')
            self.exp_time = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('experienceTime')
            self.experienceTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(self.exp_time, self, s, None, False)

    def checkExperienceOnPrefChange_(self, notification):
        if(self.experienceTimer):
            self.experienceTimer.invalidate()

        self.exp_time = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('experienceTime')
        time_since_last_experience = time.time() - self.last_experience

        experienceLoop = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('experienceLoop')
        if(experienceLoop):
            if (time_since_last_experience > self.exp_time):
                self.runExperienceLoop()
            else:
                sleep_time = self.exp_time - time_since_last_experience + 0.01
                s = objc.selector(self.runExperienceLoop,signature='v@:')
                self.experienceTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(sleep_time, self, s, None, False)

    def getDebriefExperiences_(self, notification):
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        q = self.session.query(Experience).filter(Experience.created_at.like(today + '%')).all()
        m = []
        for row in q:
            m.append({'id': row.id, 'created_at': row.created_at, 'message':row.message, 'screenshot':row.screenshot})

        # get a random sample of up to 8 random experiences
        if len(m) > 7:
            e = random.sample(m, 7)
        else:
            e = random.sample(m, len(m))
        notification.object().experiences = e

    def checkMaxScreenshotOnPrefChange_(self, notification):
        self.screenshotTimer.invalidate()
        self.runMaxScreenshotLoop()

    def runMaxScreenshotLoop(self):
        self.screenshot_time_max = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('imageTimeMax')
        time_since_last_screenshot = time.time() - self.last_screenshot
        if (time_since_last_screenshot > self.screenshot_time_max):
            self.take_screenshot()
            time_since_last_screenshot = 0.0
        sleep_time = self.screenshot_time_max - time_since_last_screenshot + 0.01
        s = objc.selector(self.runMaxScreenshotLoop,signature='v@:')
        self.screenshotTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(sleep_time, self, s, None, False)

    def toggleScreenshotMenuTitle_(self,notification):
        screen = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('screenshots')
        if screen:
            self.sniffer.delegate.menu.itemWithTitle_("Record Screenshots").setTitle_("Pause Screenshots")
        else :
            self.sniffer.delegate.menu.itemWithTitle_("Pause Screenshots").setTitle_("Record Screenshots")

    def clearData_(self, notification):
        minutes_to_delete = notification.object().clearDataPopup.selectedItem().tag()
        text = notification.object().clearDataPopup.selectedItem().title()

        if minutes_to_delete == -1:
            delete_from_time = datetime.datetime.min
        else:
            delta = datetime.timedelta(minutes=minutes_to_delete)
            now = datetime.datetime.now()
            delete_from_time = now - delta

        # delete data from all tables
        q = self.session.query(Click).filter(Click.created_at > delete_from_time).delete()
        q = self.session.query(Debrief).filter(Debrief.created_at > delete_from_time).delete()
        q = self.session.query(Experience).filter(Experience.created_at > delete_from_time).delete()
        q = self.session.query(Geometry).filter(Geometry.created_at > delete_from_time).delete()
        q = self.session.query(Keys).filter(Keys.created_at > delete_from_time).delete()
        q = self.session.query(Location).filter(Location.created_at > delete_from_time).delete()
        q = self.session.query(Process).filter(Process.created_at > delete_from_time).delete()
        q = self.session.query(Window).filter(Window.created_at > delete_from_time).delete()

        screenshot_directory = os.path.expanduser(os.path.join(cfg.CURRENT_DIR,"screenshots"))
        screenshot_files = os.listdir(screenshot_directory)

        for f in screenshot_files:
            if f[0:19] > delete_from_time.strftime("%y%m%d-%H%M%S%f") or  minutes_to_delete == -1 :
                os.remove(os.path.join(screenshot_directory,f))

        print "You deleted the last " + text + " of your history"


    def take_screenshot(self):
      # We check whether the screenshot option is on and then limit the screenshot taking rate to user defined rate
      self.screenshots_active = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('screenshots')
      self.screenshot_time_min = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('imageTimeMin') / 1000.0

      if (self.screenshots_active
        and (time.time() - self.last_screenshot) > self.screenshot_time_min) :
          try:
              folder = os.path.join(cfg.CURRENT_DIR,"screenshots")
              filename = datetime.datetime.now().strftime("%y%m%d-%H%M%S%f")
              path = os.path.join(folder,""+filename+".jpg")

              self.sniffer.screenshot(path)
              self.last_screenshot = time.time()
          except:
              print "error with image backup"

    def lookupThumbdrive(self, namefilter=""):
        for dir in os.listdir('/Volumes') :
            if namefilter in dir :
                volume = os.path.join('/Volumes', dir)
                if (os.path.ismount(volume)) :
                    subDirs = os.listdir(volume)
                    for filename in subDirs:
                        if "selfspy.cfg" == filename :
                            print "backup drive found ", volume
                            cfg.THUMBDRIVE_DIR = volume
                            return cfg.THUMBDRIVE_DIR
        return None

    def defineCurrentDrive(self):
        if (self.isThumbdrivePlugged()) :
            cfg.CURRENT_DIR = cfg.THUMBDRIVE_DIR
        else :
            cfg.CURRENT_DIR = os.path.expanduser(cfg.LOCAL_DIR)

    def checkDrive_(self, notification):
        self.lookupThumbdrive_()
        self.defineCurrentDrive()

    def isThumbdrivePlugged(self):
        if (cfg.THUMBDRIVE_DIR != None and cfg.THUMBDRIVE_DIR != ""):
            if (os.path.ismount(cfg.THUMBDRIVE_DIR)):
                return True
            else :
                print "Thumbdrive defined but not plugged\n TODO: display alert message"
                cfg.THUMBDRIVE_DIR = None
                self.lookupThumbdrive()
                return False
        else :
            return False

    # Method to add "Close" entry to DB for each app open at the close of Selfspy, not yet working
    def gotCloseNotification_(self, notification):
        for app in self.current_apps:
            db_process = self.session.query(Process).filter_by(name=app.localizedName()).scalar()
            process_id = 0
            if db_process:
                process_id = db_process.id
            process_event = ProcessEvent(process_id, "Close")
            self.session.add(process_event)

        for window_id in self.current_windows:
            db_window = self.session.query(Window).filter_by(id=window_id).scalar()
            window_id = db_window.id if db_window else 0
            pid = db_window.process_id if db_window else 0
            window_event = WindowEvent(window_id, "Close")
            self.session.add(window_event)

        recording_event = RecordingEvent(NOW(), "Off")
        self.session.add(recording_event)
        self.trycommit()

    def noteRecordingState_(self, notification):
        value = "On"
        recording = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('recording')
        if not recording:
            value = "Off"
        recording_event = RecordingEvent(NOW(), value)
        self.session.add(recording_event)

    def recordBookmark_(self, notification):
        bookmark = Bookmark(NOW())
        self.session.add(bookmark)
