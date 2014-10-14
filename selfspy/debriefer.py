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


import string
import objc, re, os

from objc import IBAction, IBOutlet

from Foundation import *
from AppKit import *

from Cocoa import (NSURL, NSString, NSTimer,NSInvocation, NSNotificationCenter)

import config as cfg

from datetime import datetime

import mutagen.mp4


# Experience Sampling window controller
class DebriefController(NSWindowController):

    # outlets for UI elements
    mainPanel = IBOutlet()
    doingText = IBOutlet()
    progressLabel = IBOutlet()
    progressButton = IBOutlet()
    errorMessage = IBOutlet()
    recordButton = IBOutlet()
    existAudioText = IBOutlet()
    playAudioButton = IBOutlet()
    deleteAudioButton = IBOutlet()
    memoryStrength = IBOutlet()

    # instance variables
    experiences = None
    currentExperience = -1
    recordingAudio = False
    playingAudio = False
    audio_file = ''

    # images for audio recording button
    recordImage = NSImage.alloc().initByReferencingFile_('../Resources/record.png')
    recordImage.setScalesWhenResized_(True)
    recordImage.setSize_((11, 11))

    stopImage = NSImage.alloc().initByReferencingFile_('../Resources/stop.png')
    stopImage.setScalesWhenResized_(True)
    stopImage.setSize_((11, 11))

    @IBAction
    def toggleAudioPlay_(self, sender):
        if self.playingAudio:
            self.playingAudio = False
            s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n stop the front document \n close the front document \n end tell")
            s.executeAndReturnError_(None)

            self.debriefController.playAudioButton.setTitle_("Play Audio")

        else:
            self.playingAudio = True

            audio = mutagen.mp4.MP4(self.audio_file)
            length = audio.info.length

            s = NSAppleScript.alloc().initWithSource_("set filePath to POSIX file \"" + self.audio_file + "\" \n tell application \"QuickTime Player\" \n open filePath \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n play the front document \n end tell")
            s.executeAndReturnError_(None)

            s = objc.selector(self.stopAudioPlay,signature='v@:')
            self.exp_time = NSUserDefaultsController.sharedUserDefaultsController().values().valueForKey_('experienceTime')
            self.experienceTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(length, self, s, None, False)

            self.debriefController.playAudioButton.setTitle_("Stop Audio")

    def stopAudioPlay(self):
        self.playingAudio = False
        s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n stop the front document \n close the front document \n end tell")
        s.executeAndReturnError_(None)

        self.debriefController.playAudioButton.setTitle_("Play Audio")

    @IBAction
    def deleteAudio_(self, sender):
        controller = self.debriefController

        if (self.audio_file != '') & (self.audio_file != None) :
            if os.path.exists(self.audio_file):
                os.remove(self.audio_file)
        self.audio_file = ''

        controller.recordButton.setEnabled_(True)
        controller.existAudioText.setStringValue_("Record your answer here:")
        controller.playAudioButton.setHidden_(True)
        controller.deleteAudioButton.setHidden_(True)

    @IBAction
    def toggleAudioRecording_(self, sender):
        controller = self.debriefController

        if self.recordingAudio:
            self.recordingAudio = False

            print "Stop Audio recording"
            # seems to miss reading the name sometimes
            imageName = str(controller.mainPanel.image().name())[0:-4]
            print "Audio name should be " + imageName
            if (imageName == None) | (imageName == ''):
                imageName = datetime.now().strftime("%y%m%d-%H%M%S%f") + '-audio'
            imageName = str(os.path.join(cfg.CURRENT_DIR, "audio/")) + imageName + '.m4a'
            self.audio_file = imageName
            imageName = string.replace(imageName, "/", ":")
            imageName = imageName[1:]

            s = NSAppleScript.alloc().initWithSource_("set filePath to \"" + imageName + "\" \n set placetosaveFile to a reference to file filePath \n tell application \"QuickTime Player\" \n set mydocument to document 1 \n tell document 1 \n stop \n end tell \n set newRecordingDoc to first document whose name = \"untitled\" \n export newRecordingDoc in placetosaveFile using settings preset \"Audio Only\" \n close newRecordingDoc without saving \n quit \n end tell")
            s.executeAndReturnError_(None)

            # self.recorder.stop()

            controller.recordButton.setImage_(self.recordImage)

            controller.recordButton.setEnabled_(False)
            controller.existAudioText.setStringValue_("You've recorded an answer:")
            controller.playAudioButton.setHidden_(False)
            controller.deleteAudioButton.setHidden_(False)

        else:
            self.recordingAudio = True

            print "Start Audio Recording"
            s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n set new_recording to (new audio recording) \n tell new_recording \n start \n end tell \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n end tell")
            s.executeAndReturnError_(None)

            self.debriefController.recordButton.setImage_(self.stopImage)

            # audioPath = "/Users/adamrule/Desktop/test.m4a"
            # audioPathStr = NSString.stringByExpandingTildeInPath(audioPath)
            # audioURL = NSURL.fileURLWithPath_(audioPathStr)
            # print str(audioURL)
            #
            # audioSettings = {"AVFormatIDKey": "kAudioFormatAppleIMA4"} # "AVSampleRateKey": 1600, "AVNumberOfChannelsKey": 1
            # print audioSettings
            # audioDict = NSDictionary.dictionaryWithDictionary_(audioSettings)

            # (self.recorder, error) = AVAudioRecorder.alloc().initWithURL_settings_error_(audioURL, audioSettings, None)
            # print self.recorder
            # print error
            # self.recorder.record()

    @IBAction
    def advanceExperienceWindow_(self, sender):
        controller = self.debriefController

        # close if user clicked Finish on window with no experiences to comment
        if self.currentExperience == -2:
            self.debriefController.close()
            return

        l = len(self.experiences)
        if (not self.experiences) or (l == 0):
            controller.errorMessage.setHidden_(False)
            controller.doingText.setEnabled_(False)
            controller.recordButton.setEnabled_(False)
            controller.progressLabel.setStringValue_("0/0")
            controller.progressButton.setTitle_("Finish")
            self.currentExperience -= 1
            return

        self.currentExperience += 1
        i = self.currentExperience

        if i > 0:
            NSNotificationCenter.defaultCenter().postNotificationName_object_('recordDebrief',self)

        if i == l-1:
            controller.progressButton.setTitle_("Finish")

        if i < l:
            NSNotificationCenter.defaultCenter().postNotificationName_object_('populateDebriefWindow',self)

            path = self.experiences[i]['screenshot'][:]
            path = os.path.expanduser(path)
            experienceImage = NSImage.alloc().initByReferencingFile_(path)
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
            experienceImage.setName_(path.split("/")[-1])
            controller.mainPanel.setImage_(experienceImage)

            controller.progressLabel.setStringValue_( str(i + 1) + '/' + str(l) )

        else:
            self.debriefController.close()

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)

    def show(self):
        try:
            if self.debriefController:
                self.debriefController.close()
        except:
            pass

        # open window from NIB file, show front and center
        self.debriefController = DebriefController.alloc().initWithWindowNibName_("Debriefer")
        self.debriefController.showWindow_(None)
        self.debriefController.window().makeKeyAndOrderFront_(None)
        self.debriefController.window().center()
        self.debriefController.retain()

        self.currentExperience = -1

        # needed to show window on top of other applications
        NSNotificationCenter.defaultCenter().postNotificationName_object_('makeAppActive',self)

        # get random set of experiences
        NSNotificationCenter.defaultCenter().postNotificationName_object_('getDebriefExperiences',self)

        self.advanceExperienceWindow_(self, self)

        self.debriefController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalentModifierMask_(NSCommandKeyMask)
        self.debriefController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalent_("w")

    show = classmethod(show)
