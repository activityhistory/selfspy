# Copyright 2012 David Fendrich

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

import sys
import getpass

from Tkinter import Tk
from tkSimpleDialog import Dialog
# from Cocoa import *
# from Foundation import NSObject

# class SimpleXibDemoController(NSWindowController):
#     counterTextField = objc.IBOutlet()
     
#     def windowDidLoad(self):
#         NSWindowController.windowDidLoad(self)
         
#         # Start the counter
#         self.password = 0
     
#     @objc.IBAction
#     def increment_(self, sender):
#         self.count += 1
#         self.updateDisplay()
     
#     @objc.IBAction
#     def decrement_(self, sender):
#         self.count -= 1
#         self.updateDisplay()
     
#     def getPassword(self):
#         self.password = self.passwordField.getStringValue_()
#         return self.password
         

def get_password(verify=None, message=None):
    if (not verify):
        pw = get_user_password(verify, message)
    else:
        pw = get_keyring_password(verify)

    if pw == None:
        pw = get_user_password(verify, message)

    return pw


def get_user_password(verify, message=None, force_save=False):
    # if sys.stdin.isatty():
    #     pw = get_tty_password(verify, message, force_save)
    # else:
    pw = get_tk_password(verify, message, force_save)
    # pw = get_cocoa_password(verify, message, force_save)

    return pw


def get_keyring_password(verify, message=None):
    pw = None
    try:
        import keyring

        usr = getpass.getuser()
        pw = keyring.get_password('Selfspy', usr)

        if pw is not None:
            if (not verify) or not verify(pw):
                print 'The keyring password is not valid. Please, input the correct one.'
                pw = get_user_password(verify, message, force_save=True)
    except ImportError:
        print 'keyring library not found'

    return pw


def set_keyring_password(password):
    try:
        import keyring
        usr = getpass.getuser()
        keyring.set_password('Selfspy', usr, password)
    except ImportError:
        print 'Unable to save password to keyring (library not found)'
    except NameError:
        pass
    except:
        print 'Unable to save password to keyring'


def get_cocoa_password(verify, message=None, force_save=False):
    app = NSApplication.sharedApplication()
    # Initiate the contrller with a XIB
    viewController = SimpleXibDemoController.alloc().initWithWindowNibName_("SimpleXibDemo")
     
    # Show the window
    viewController.showWindow_(viewController)
     
    # Bring app to top
    # NSApp.activateIgnoringOtherApps_(True)
    # from PyObjCTools import AppHelper
    # AppHelper.runEventLoop()



def get_tty_password(verify, message=None, force_save=False):
    verified = False
    for i in xrange(3):
        if message:
            pw = getpass.getpass(message)
        else:
            pw = getpass.getpass()
        if (not verify) or verify(pw):
            verified = True
            break

    if not verified:
        print 'Password failed'
        sys.exit(1)

    if not force_save:
        while True:
            store = raw_input("Do you want to store the password in the keychain [Y/N]: ")
            if store.lower() in ['n', 'y']:
                break
        save_to_keychain = store.lower() == 'y'
    else:
        save_to_keychain = True

    if save_to_keychain:
        set_keyring_password(pw)

    return pw


def get_tk_password(verify, message=None, force_save=False):
    root = Tk()
    root.withdraw()
    if message is None:
        message = 'Password'

    while True:
        # pw, save_to_keychain = PasswordDialog(title='Selfspy encryption password',
        #                     prompt=message,
        #                     parent=root)
        pw = PasswordDialog(title='Selfspy encryption password',
                            prompt=message,
                            parent=root)

        if pw.result is None:
            return ""

        if (not verify) or verify(pw):
            break

    print pw.result

    # if save_to_keychain or force_save:
    set_keyring_password(pw.result)

    return pw.result


class PasswordDialog(Dialog):

    def __init__(self, title, prompt, parent):
        self.prompt = prompt
        Dialog.__init__(self, parent, title)

    def body(self, master):
        from Tkinter import Label
        from Tkinter import Entry
        from Tkinter import Checkbutton
        from Tkinter import IntVar
        from Tkinter import W

        self.checkVar = IntVar()

        Label(master, text=self.prompt).grid(row=0, sticky=W)

        self.e1 = Entry(master)

        self.e1.grid(row=0, column=1)

        # self.cb = Checkbutton(master, text="Save to keychain", variable=self.checkVar)
        # self.cb.pack()
        # self.cb.grid(row=1, columnspan=2, sticky=W)
        # self.configure(show='*')

    def apply(self):
        self.result = self.e1.get()# , self.checkVar.get() == 1)
        print "result", self.result


if __name__ == '__main__':
    print get_password()
