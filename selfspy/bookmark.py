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

import string
import objc, re, os
from objc import IBAction, IBOutlet

from Foundation import *
from AppKit import *

from Cocoa import (NSURL, NSString, NSTimer, NSInvocation, NSNotificationCenter)

import config as cfg

from datetime import datetime

import mutagen.mp4


# Preferences window controller
class BookmarkController(NSWindowController):

    # outlets for UI elements
    doingText = IBOutlet()
    existAudioText = IBOutlet()
    timeRadioButtons = IBOutlet()
    recordButton = IBOutlet()
    playAudioButton = IBOutlet()
    deleteAudioButton = IBOutlet()
    bookmarkButton = IBOutlet()

    # images for audio recording button
    recordImage = NSImage.alloc().initByReferencingFile_('../Resources/record.png')
    recordImage.setScalesWhenResized_(True)
    recordImage.setSize_((11, 11))

    stopImage = NSImage.alloc().initByReferencingFile_('../Resources/stop.png')
    stopImage.setScalesWhenResized_(True)
    stopImage.setSize_((11, 11))

    #instance variables
    t = None
    recordingAudio = False
    playingAudio = False
    audio_file = ''

    @IBAction
    def toggleAudioPlay_(self, sender):
        if self.playingAudio:
            self.stopAudioPlay()

        else:
            self.playingAudio = True
            self.bookController.playAudioButton.setTitle_("Stop Audio")
            s = NSAppleScript.alloc().initWithSource_("set filePath to POSIX file \"" + self.audio_file + "\" \n tell application \"QuickTime Player\" \n open filePath \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n play the front document \n end tell")
            s.executeAndReturnError_(None)

            # Stop playback once end of audio file is reached
            length = mutagen.mp4.MP4(self.audio_file).info.length
            s = objc.selector(self.stopAudioPlay,signature='v@:')
            self.playbackTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(length, self, s, None, False)

    def stopAudioPlay(self):
        self.playingAudio = False
        self.bookController.playAudioButton.setTitle_("Play Audio")
        s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n stop the front document \n close the front document \n end tell")
        s.executeAndReturnError_(None)

    @IBAction
    def deleteAudio_(self, sender):
        if (self.audio_file != '') & (self.audio_file != None) :
            if os.path.exists(self.audio_file):
                os.remove(self.audio_file)
        self.audio_file = ''

        # reset controls
        controller = self.bookController
        controller.recordButton.setEnabled_(True)
        controller.existAudioText.setStringValue_("Record audio commentary:")
        controller.playAudioButton.setEnabled_(False)
        controller.deleteAudioButton.setEnabled_(False)

    @IBAction
    def toggleAudioRecording_(self, sender):
        controller = self.bookController

        if self.recordingAudio:
            self.recordingAudio = False
            print "Stop Audio recording"

            audioName = datetime.now().strftime("%y%m%d-%H%M%S%f") + '-audio'
            audioName = str(os.path.join(cfg.CURRENT_DIR, "audio/")) + audioName + '.m4a'
            self.audio_file = audioName
            audioName = string.replace(audioName, "/", ":")
            audioName = audioName[1:]

            s = NSAppleScript.alloc().initWithSource_("set filePath to \"" + audioName + "\" \n set placetosaveFile to a reference to file filePath \n tell application \"QuickTime Player\" \n set mydocument to document 1 \n tell document 1 \n stop \n end tell \n set newRecordingDoc to first document whose name = \"untitled\" \n export newRecordingDoc in placetosaveFile using settings preset \"Audio Only\" \n close newRecordingDoc without saving \n quit \n end tell")
            s.executeAndReturnError_(None)

            # reset controls
            controller.recordButton.setImage_(self.recordImage)
            controller.recordButton.setEnabled_(False)
            controller.existAudioText.setStringValue_("You've recorded commentary:")
            controller.playAudioButton.setEnabled_(True)
            controller.deleteAudioButton.setEnabled_(True)

        else:
            self.recordingAudio = True
            print "Start Audio Recording"

            s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n set new_recording to (new audio recording) \n tell new_recording \n start \n end tell \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n end tell")
            s.executeAndReturnError_(None)

            self.bookController.recordButton.setImage_(self.stopImage)


    @IBAction
    def saveBookmark_(self, sender):
        NSNotificationCenter.defaultCenter().postNotificationName_object_('recordBookmark',self)

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)


    def show(self):
        try:
            if self.bookController:
                self.bookController.close()
        except:
            pass

        # open window from NIB file, show front and center, show on top
        self.bookController = BookmarkController.alloc().initWithWindowNibName_("Bookmark")
        self.bookController.showWindow_(None)

        bookmarkSize = self.bookController.window().frame().size
        bookmarkWidth = bookmarkSize.width
        bookmarkHeight = bookmarkSize.height

        screenSize = self.bookController.window().screen().frame().size
        screenWidth = screenSize.width
        screenHeight = screenSize.height

        point = NSPoint(screenWidth - bookmarkWidth - 12, screenHeight - bookmarkHeight - 34)
        self.bookController.window().setFrameOrigin_(point)

        # self.bookController.window().makeKeyAndOrderFront_(None)
        # self.bookController.window().center()
        # self.bookController.retain()
        # NSNotificationCenter.defaultCenter().postNotificationName_object_('makeAppActive',self)

        # make window close on Cmd-w
        self.bookController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalentModifierMask_(NSCommandKeyMask)
        self.bookController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalent_("w")

        self.bookController.t = datetime.now()

    show = classmethod(show)
