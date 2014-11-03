# -*- coding: utf-8 -*-
"""
Selfspy: Track your computer activity
Copyright (C) 2012 Bjarte Johansen
Modified 2014 by Adam Rule, Aurélien Tabard, and Jonas Kemper

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
from os import listdir
from os.path import isfile, join

from objc import IBAction, IBOutlet
from sqlalchemy.sql import select

from Foundation import *
from AppKit import *

from Cocoa import (NSURL, NSString, NSTimer, NSInvocation, NSNotificationCenter)

import config as cfg

from datetime import datetime

import mutagen.mp4

# Experience Sampling window controller
class ReviewController(NSWindowController):

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
    currentScreenshot = -1
    dateQuery = ""
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

    # dynamic review filter table

    tableView = IBOutlet()
    arrayController = objc.IBOutlet()
    list = []
    results = [ NSDictionary.dictionaryWithDictionary_(x) for x in list]
    dict = {}
    dict['Data'] = "foo"
    dict['Datab'] = "4242"
    results.append(NSDictionary.dictionaryWithDictionary_(dict))
    results.append(NSDictionary.dictionaryWithDictionary_(dict))

    @IBAction
    def toggleAudioPlay_(self, sender):
        if self.playingAudio:
            self.stopAudioPlay()

        else:
            self.playingAudio = True
            self.reviewController.playAudioButton.setTitle_("Stop Audio")
            s = NSAppleScript.alloc().initWithSource_("set filePath to POSIX file \"" + self.audio_file + "\" \n tell application \"QuickTime Player\" \n open filePath \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n play the front document \n end tell")
            s.executeAndReturnError_(None)

            # Stop playback once end of audio file is reached
            length = mutagen.mp4.MP4(self.audio_file).info.length
            s = objc.selector(self.stopAudioPlay,signature='v@:')
            self.playbackTimer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(length, self, s, None, False)

    def stopAudioPlay(self):
        self.playingAudio = False
        self.reviewController.playAudioButton.setTitle_("Play Audio")
        s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n stop the front document \n close the front document \n end tell")
        s.executeAndReturnError_(None)

    @IBAction
    def deleteAudio_(self, sender):
        if (self.audio_file != '') & (self.audio_file != None) :
            if os.path.exists(self.audio_file):
                os.remove(self.audio_file)
        self.audio_file = ''

        # reset controls
        controller = self.reviewController
        controller.recordButton.setEnabled_(True)
        controller.existAudioText.setStringValue_("Record your answer here:")
        controller.playAudioButton.setHidden_(True)
        controller.deleteAudioButton.setHidden_(True)

    @IBAction
    def toggleAudioRecording_(self, sender):
        controller = self.reviewController

        if self.recordingAudio:
            self.recordingAudio = False
            print "Stop Audio recording"

            audioName = str(controller.mainPanel.image().name())[0:-4]
            if (audioName == None) | (audioName == ''): # seems to miss reading the image name sometimes
                audioName = datetime.now().strftime("%y%m%d-%H%M%S%f") + '-audio'
            audioName = str(os.path.join(cfg.CURRENT_DIR, "audio/")) + audioName + '.m4a'
            self.audio_file = audioName
            audioName = string.replace(audioName, "/", ":")
            audioName = audioName[1:]

            s = NSAppleScript.alloc().initWithSource_("set filePath to \"" + audioName + "\" \n set placetosaveFile to a reference to file filePath \n tell application \"QuickTime Player\" \n set mydocument to document 1 \n tell document 1 \n stop \n end tell \n set newRecordingDoc to first document whose name = \"untitled\" \n export newRecordingDoc in placetosaveFile using settings preset \"Audio Only\" \n close newRecordingDoc without saving \n quit \n end tell")
            s.executeAndReturnError_(None)

            # reset controls
            controller.recordButton.setEnabled_(False)
            controller.existAudioText.setStringValue_("You've recorded an answer:")
            controller.playAudioButton.setHidden_(False)
            controller.deleteAudioButton.setHidden_(False)

        else:
            self.recordingAudio = True
            print "Start Audio Recording"

            s = NSAppleScript.alloc().initWithSource_("tell application \"QuickTime Player\" \n set new_recording to (new audio recording) \n tell new_recording \n start \n end tell \n tell application \"System Events\" \n set visible of process \"QuickTime Player\" to false \n repeat until visible of process \"QuickTime Player\" is false \n end repeat \n end tell \n end tell")
            s.executeAndReturnError_(None)


    @IBAction
    def advanceExperienceWindow_(self, sender):

        controller = self.reviewController
        i = self.currentScreenshot
        list_of_files = [ f for f in listdir(u'/Users/jonas/.selfspy/screenshots/') if isfile(join(u'/Users/jonas/.selfspy/screenshots/',f)) ] # TODO make it not only work for jonas

        if (i <= len(list_of_files)):

            s = list_of_files[i]

            self.dateQuery = '20' + s[0:2] + '-' + s[2:4] + '-' + s[4:6] + ' ' + s[7:9] + ':' + s[9:11] + ':' + s[11:13] + '.'

            experienceImage = NSImage.alloc().initByReferencingFile_(u'/Users/jonas/.selfspy/screenshots/' + s)
            NSNotificationCenter.defaultCenter().postNotificationName_object_('populateReviewWindow',self)

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
            controller.mainPanel.setImage_(experienceImage)

            self.populateExperienceTable(self)
            self.currentScreenshot += 5


        else:
            controller.mainPanel.setImage_(None)
            self.currentScreenshot += 1
            #self.reviewController.close()

    def populateExperienceTable(self, self2=None):
        dict = {}
        dict['Data'] = "foo"
        dict['Datab'] = "4242"
        self.results.append(NSDictionary.dictionaryWithDictionary_(dict))
        self.reviewController.arrayController.rearrangeObjects()

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)

    def awakeFromNib(self):
        if self.tableView:
            self.tableView.setTarget_(self)

    def show(self):

        if self.experiences:
            l = len(self.experiences)
        try:
            if self.reviewController:
                self.reviewController.close()
        except:
            pass

        # open window from NIB file, show front and center
        self.reviewController = ReviewController.alloc().initWithWindowNibName_("Reviewer")
        self.reviewController.showWindow_(None)
        self.reviewController.window().makeKeyAndOrderFront_(None)
        self.reviewController.window().center()
        self.reviewController.retain()

        # needed to show window on top of other applications
        NSNotificationCenter.defaultCenter().postNotificationName_object_('makeAppActive',self)
        # get cmd-w to close window
        self.reviewController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalentModifierMask_(NSCommandKeyMask)
        self.reviewController.window().standardWindowButton_(NSWindowCloseButton).setKeyEquivalent_("w")

        # get random set of experiences
        NSNotificationCenter.defaultCenter().postNotificationName_object_('getReviewExperiences',self)

        self.currentScreenshot = 0

        desc = NSSortDescriptor.alloc().initWithKey_ascending_('Data',False)
        descriptiorArray = [desc]
        self.reviewController.arrayController.setSortDescriptors_(descriptiorArray)
        self.reviewController.arrayController.rearrangeObjects()

        self.advanceExperienceWindow_(self, self)

    show = classmethod(show)
