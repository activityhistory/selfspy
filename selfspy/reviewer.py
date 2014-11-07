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
import os
from os import listdir
from os.path import isfile, join

from objc import IBAction, IBOutlet
from AppKit import *

import config as cfg

from datetime import datetime

import mutagen.mp4

# Experience Sampling window controller
class ReviewController(NSWindowController):

    # outlets for UI elements
    mainPanel = IBOutlet()
    doingText = IBOutlet()
    #progressLabel = IBOutlet()
    progressButton = IBOutlet()
    #errorMessage = IBOutlet()
    #recordButton = IBOutlet()
    #existAudioText = IBOutlet()
    #playAudioButton = IBOutlet()
    #deleteAudioButton = IBOutlet()
    #memoryStrength = IBOutlet()
    tableView = IBOutlet()
    arrayController = IBOutlet()

    # instance variables
    #experiences = None
    currentScreenshot = -1
    dateQuery = ""
    #recordingAudio = False
    #playingAudio = False
    audio_file = ''

    # images for audio recording button
    #recordImage = NSImage.alloc().initByReferencingFile_('../Resources/record.png')
    #recordImage.setScalesWhenResized_(True)
    #recordImage.setSize_((11, 11))
#
    #stopImage = NSImage.alloc().initByReferencingFile_('../Resources/stop.png')
    #stopImage.setScalesWhenResized_(True)
    #stopImage.setSize_((11, 11))

    # dynamic review filter table

    list = []
    NSMutableDictionary = objc.lookUpClass('NSMutableDictionary')
    NSNumber = objc.lookUpClass('NSNumber')
    results = [ NSMutableDictionary.dictionaryWithDictionary_(x) for x in list]
    #dict = NSMutableDictionary()
    d = NSMutableDictionary({'Data': "abc", 'Datab': "def", 'checkb': NSNumber.numberWithBool_(0)})
    results.append(NSDictionary.dictionaryWithDictionary_(d))
    #dict['checkb'] = True
    results.append(NSDictionary.dictionaryWithDictionary_(d))
    queryResponse = []
    queryResponse2 = []

    @IBAction
    def advanceExperienceWindow_(self, sender):

        for value in self.results:
            try:
                print value['checkb']
            except KeyError:
                print "NO BOOLEAN"

        controller = self.reviewController
        i = self.currentScreenshot

        path = os.path.expanduser(u'~/.selfspy/screenshots/')
        list_of_files = [ f for f in listdir(path) if isfile(join(path,f)) ]
        # TODO will this now still work on a thumbdrive?

        if (i <= len(list_of_files)):

            if i == 0:
                self.populateExperienceTable(self)

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

            self.currentScreenshot += 5


        else:
            controller.mainPanel.setImage_(None)
            self.currentScreenshot += 1
            #self.reviewController.close()


    def populateExperienceTable(self, self2=None):

        path = os.path.expanduser(u'~/.selfspy/screenshots/')
        list_of_files = [ f for f in listdir(path) if isfile(join(path,f)) ]
        # TODO will this now still work on a thumbdrive?


        for s in list_of_files:
            self.dateQuery = '20' + s[0:2] + '-' + s[2:4] + '-' + s[4:6] + ' ' + s[7:9] + ':' + s[9:11] + ':' + s[11:13] + '.'

            NSNotificationCenter.defaultCenter().postNotificationName_object_('queryMetadata',self)

            lenstr = len(self.queryResponse)

            if lenstr > 0:
                 d = NSMutableDictionary({'Data': str(self.queryResponse2)[2:lenstr-3], 'Datab': str(self.queryResponse)[2:lenstr-3], 'checkb': NSNumber.numberWithBool_(1)})
                 if d not in self.results:
                    self.results.append(NSDictionary.dictionaryWithDictionary_(d))

            self.queryResponse = []
            self.queryResponse2 = []
        try:
            self.reviewController.arrayController.rearrangeObjects()
        except UnboundLocalError:
            pass

    def windowDidLoad(self):
        NSWindowController.windowDidLoad(self)

    def awakeFromNib(self):
        if self.tableView:
            self.tableView.setTarget_(self)

    def show(self):

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


        self.currentScreenshot = 0

        desc = NSSortDescriptor.alloc().initWithKey_ascending_('Data',False)
        descriptiorArray = [desc]
        self.reviewController.arrayController.setSortDescriptors_(descriptiorArray)
        self.reviewController.arrayController.rearrangeObjects()

        self.advanceExperienceWindow_(self, self)

    show = classmethod(show)
