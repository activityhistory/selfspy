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
from datetime import datetime
NOW = datetime.now

import sqlalchemy
import urllib
import re

from Foundation import *
from AppKit import *

from Cocoa import NSNotificationCenter

from threading import Thread

from selfspy import sniff_cocoa as sniffer

from selfspy import models
from selfspy.models import Process, Window, Geometry, Click, Keys, Experience, Location
from selfspy import config as cfg


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
    def __init__(self, db_name, encrypter=None, store_text=True, screenshots=True):
        self.session_maker = models.initialize(db_name)

        models.ENCRYPTER = encrypter

        self.store_text = store_text
        self.curtext = u""

        self.key_presses = []
        self.mouse_path = []

        self.current_window = Display()

        self.last_scroll = {button: 0 for button in SCROLL_BUTTONS}

        self.last_key_time = time.time()
        self.last_move_time = time.time()
        self.last_commit = time.time()
        
        self.screenshots_active = True
        self.last_screenshot = time.time()
        self.screenshot_time_min = 0.2
        self.screenshot_time_max = 60
        self.sample_time = 1800

        # If there is no activity we take a screenshot every so often as specified by user
        t = Thread(target=self.take_screenshots_every, args=())
        t.start()          

        geoloc = True
        if (geoloc) : 
            t_geoloc = Thread(target=self.take_geoloc_every, args=(5*60,))
            t_geoloc.start()

        # listen for experience sample events sent by OK button on Experience window
        s = objc.selector(self.gotExperience_,signature='v@:@')
        NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(self, s, 'experienceReceived', None)
        
        self.started = NOW()

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

    def run(self):
        self.session = self.session_maker()

        self.sniffer = sniffer.Sniffer()
        self.sniffer.screen_hook = self.got_screen_change
        self.sniffer.key_hook = self.got_key
        self.sniffer.mouse_button_hook = self.got_mouse_click
        self.sniffer.mouse_move_hook = self.got_mouse_move

        self.sniffer.run()
        

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

            curtext = u""
            if not self.store_text:
                keys = []
            else:
                curtext = ''.join(keys)

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

    def store_experience(self, message):
        self.session.add(Experience(message))
        self.trycommit()

    def gotExperience_(self, notification):
        message = notification.object().experienceText.stringValue()
        self.store_experience(message)

    def close(self):
        """ stops the sniffer and stores the latest keys. To be used on shutdown of program"""
        self.sniffer.cancel()
        self.store_keys()

    def change_password(self, new_encrypter):
        self.session = self.session_maker()
        keys = self.session.query(Keys).all()
        for k in keys:
            dtext = k.decrypt_text()
            dkeys = k.decrypt_keys()
            k.encrypt_text(dtext, new_encrypter)
            k.encrypt_keys(dkeys, new_encrypter)
        self.session.commit()


    def take_geoloc_every(self,n):
        while True:
            self.take_geoloc()
            time.sleep(n)

    def take_geoloc(self):
        # TODO check if skyhook api is a better alternative
        response = urllib.urlopen('http://api.hostip.info/get_html.php').read()
        m = re.search('City: (.*)', response)
        if m:
            print m.group(1)


    def take_screenshots_every(self):
        while True:
            self.screenshot_time_max = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('imageTimeMax')
            time_since_last_screenshot = time.time() - self.last_screenshot
            if (time_since_last_screenshot > self.screenshot_time_max):
                self.take_screenshot()
                time_since_last_screenshot = 0.0
            time.sleep(self.screenshot_time_max - time_since_last_screenshot + 0.1)


    def take_screenshot(self):
      # We check whether the screenshot option is on and then 
      # limit the screenshot taking rate to user defined rate
      self.screenshots_active = self.sniffer.isScreenshotActive()
      self.screenshot_time_min = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('imageTimeMin') / 1000.0

      if (self.screenshots_active
        and (time.time() - self.last_screenshot) > self.screenshot_time_min) : 
          try:
              folder = os.path.join(cfg.DATA_DIR,"screenshots")
              filename = datetime.now().strftime("%y%m%d-%H%M%S%f")
              path = os.path.join(folder,""+filename+".jpg")
              print path

              self.sniffer.screenshot(path)
              self.last_screenshot = time.time()
          except:
              print "error with image backup"


    def lookupThumbdriveDrive(self, namefilter=""):
        for dir in os.listdir('/Volumes') :
            # print dir
            # print "namefilter: ", namefilter
            if namefilter in dir :
                volume = os.path.join('/Volumes', dir)
                if (os.path.ismount(volume)) :
                    subDirs = os.listdir(volume)
                    for filename in subDirs:
                        if "selfspy.cfg" == filename :
                            print "backup drive found"
                            return os.path.join(volume, filename)
        return None