""" Copyright 2012 Bjarte Johansen
Modified 2014 by Aurélien Tabard and Adam Rule
This file is part of Selfspy

Selfspy is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Selfspy is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details. You should have
received a copy of the GNU General Public License along with Selfspy.
If not, see <http://www.gnu.org/licenses/>.
"""


import os
import time
import datetime

import sqlalchemy
import urllib
import re
import random

from Foundation import *
from AppKit import *

from Cocoa import NSNotificationCenter, NSTimer

from selfspy import sniff_cocoa as sniffer
from selfspy import config as cfg
from selfspy import models
from selfspy.models import Process, Window, Geometry, Click, Keys, Experience, Location, Debrief


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
        print "ActivityStore ", self, db_name

        # We check if a selfspy thumbdrive is plugged in and available
        # if so this is where we're storing the screenshots and DB
        # otherwise we store locally
        self.lookupThumbdrive()
        self.defineCurrentDrive()

        screenshot_directory = os.path.join(cfg.CURRENT_DIR, 'screenshots')
        try:
            if not(os.path.exists(screenshot_directory)):
                os.makedirs(screenshot_directory)
        except OSError:
            pass

        self.session_maker = models.initialize(os.path.join(cfg.CURRENT_DIR, db_name))

        self.key_presses = []
        self.mouse_path = []

        self.current_window = Display()

        self.last_scroll = {button: 0 for button in SCROLL_BUTTONS}

        self.last_key_time = time.time()
        self.last_move_time = time.time()
        self.last_commit = time.time()
        self.last_screenshot = time.time()
        self.last_experience = time.time()

        self.screenshots_active = True
        self.screenshot_time_min = 0.2
        self.screenshot_time_max = 60
        self.exp_time = 60         # time before first experience sample shows
        self.thumbdrive_time = 10

        self.addObservers()

        self.started = NOW()

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
        self.screenshotTimer.invalidate()
        self.experienceTimer.invalidate()
        self.thumbdriveTimer.invalidate()

    def checkLoops_(self, notification):
        recording = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('recording')
        if(recording):
            self.startLoops()
        else:
            self.stopLoops()

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

            # Listen for events from the Experience samplin window
            s = objc.selector(self.gotExperience_,signature='v@:@')
            NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'experienceReceived', None)

            s = objc.selector(self.getPrior_,signature='v@:@')
            NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'getPriorExperiences', None)

            # Listen for events from the Debriefer window
            s = objc.selector(self.getDebriefExperiences_,signature='v@:@')
            NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'getDebriefExperiences', None)

            s = objc.selector(self.recordDebrief_,signature='v@:@')
            NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'recordDebrief', None)

            # Listen for events thrown by the Status bar menu
            s = objc.selector(self.checkLoops_,signature='v@:@')
            NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'checkLoops', None)


    def run(self):
        self.session = self.session_maker()

        self.sniffer = sniffer.Sniffer()
        self.sniffer.screen_hook = self.got_screen_change
        self.sniffer.key_hook = self.got_key
        self.sniffer.mouse_button_hook = self.got_mouse_click
        self.sniffer.mouse_move_hook = self.got_mouse_move

        self.sniffer.run()

    def close(self):
        """ stops the sniffer and stores the latest keys. To be used on shutdown of program"""
        self.sniffer.cancel()
        self.store_keys()

    def trycommit(self):
        self.last_commit = time.time()
        for _ in xrange(1000):
            try:
                self.session.commit()
                break
            except sqlalchemy.exc.OperationalError:
                time.sleep(1)
            except:
               self.session.rollback()

    def got_screen_change(self, process_name, window_name, win_x, win_y, win_width, win_height):
        """ Receives a screen change and stores any changes. If the process or window has
            changed it will also store any queued pressed keys.
            process_name is the name of the process running the current window
            window_name is the name of the window
            win_x is the x position of the window
            win_y is the y position of the window
            win_width is the width of the window
            win_height is the height of the window """
        # print "got_screen_change"
        cur_process = self.session.query(Process).filter_by(name=process_name).scalar()
        if not cur_process:
            cur_process = Process(process_name)
            self.session.add(cur_process)

        cur_geometry = self.session.query(Geometry).filter_by(xpos=win_x,
                                                              ypos=win_y,
                                                              width=win_width,
                                                              height=win_height).scalar()
        if not cur_geometry:
            cur_geometry = Geometry(win_x, win_y, win_width, win_height)
            self.session.add(cur_geometry)

        cur_window = self.session.query(Window).filter_by(title=window_name,
                                                          process_id=cur_process.id).scalar()
        if not cur_window:
            cur_window = Window(window_name, cur_process.id)
            self.session.add(cur_window)

        # print self.current_window.proc_id, cur_process.id, self.current_window.win_id, cur_window.id
        # print process_name, window_name, win_x, win_y, win_width, win_height
        if not (self.current_window.proc_id == cur_process.id
                and self.current_window.win_id == cur_window.id):
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
        """ Queues mouse movements.
            x,y are the new coordinates on moving the mouse"""
        frequency = 10.0
        now = time.time()

        if now-self.last_move_time > 1/frequency:
            self.mouse_path.append(MouseMove([x,y], now - self.last_move_time))
            self.last_move_time = now

    def store_experience(self, message, screenshot):
        self.session.add(Experience(message, screenshot))
        self.trycommit()

    def gotExperience_(self, notification):
        message = notification.object().experienceText.stringValue()
        screenshot = notification.object().currentScreenshot
        self.store_experience(message, screenshot)

    def recordDebrief_(self, notification):
        doing_report = notification.object().debriefController.doingText.stringValue()
        next_report = notification.object().debriefController.nextText.stringValue()
        experience_id = notification.object().experiences[notification.object().currentExperience-1]['id']

        self.session.add(Debrief(experience_id, doing_report, next_report))
        self.trycommit()

    def getPrior_(self, notification):
        prior_experiences = self.session.query(Experience).distinct(Experience.message).order_by(Experience.id.desc()).limit(5).all()
        for e in prior_experiences:
            notification.object().experienceText.addItemWithObjectValue_(e.message)

    def runExperienceLoop(self):
        experienceLoop = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('experienceLoop')
        if(experienceLoop):
            NSLog("Showing Experience Sampling Window on Cycle...")
            sniffer.ExperienceController.show()
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
        # .add_columns(Experience.id, Experience.created_at, Experience.message, Experience.screenshot)
        # get a random sample of up to 8 random experiences
        if len(m) > 8:
            e = random.sample(m, 8)
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
              # print path

              self.sniffer.screenshot(path)
              self.last_screenshot = time.time()
          except:
              print "error with image backup"

    def lookupThumbdrive(self, namefilter=""):
        for dir in os.listdir('/Volumes') :
            # print dir
            # print "namefilter: ", namefilter
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
