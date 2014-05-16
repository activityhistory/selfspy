### What is this?
This is a fork of [selfspy](https://github.com/gurgeh/selfspy). The changes will mostly involve capturing extra invasive information such as screenshots, webcam pics, document names, for research purposes.

Since every screenshot takes between 1 and 2MB, your hard drive is going to be filled pretty quickly.

The focus right now is on making a stable MacOS X logging application. Even though we keep most of the multi-platform code of the original selfspy, we're not focusing on multiplatform.

Selfspy is a daemon for Unix/X11, (thanks to @ljos!) Mac OS X and (thanks to @Foxboron) Windows, that continuously monitors and stores what you are doing on your computer. This way, you can get all sorts of nifty statistics and reminders on what you have been up to. It is inspired by the [Quantified Self](http://en.wikipedia.org/wiki/Quantified_Self)-movement and [Stephen Wolfram's personal key logging](http://blog.stephenwolfram.com/2012/03/the-personal-analytics-of-my-life/).

We are working on advanced visualizations tools for the data, and broke down the statics part of selfspy on the way.


### Installing Selfspy

There is a now a Mac OS X app so go ahead and downloard it.


To install manually, either clone the repository from Github (git clone git://github.com/aurelient/selfspy), or click on the Download link on http://github.com/aurelient/selfspy/ to get the latest Python source.

Selfspy is only tested with Python 2.7 and has a few dependencies on other Python libraries that need to be satisfied. These are documented in the requirements.txt file. If you are on Linux, you will need subversion installed for pip to install python-xlib. If you are on Mac, you will not need to install python-xlib at all. Python-xlib is currently a tricky package to include in the requirements since it is not on PyPi.
```
pip install svn+https://python-xlib.svn.sourceforge.net/svnroot/python-xlib/tags/xlib_0_15rc1/ # Only do this step on Linux!
python setup.py install
```

You will also need the ``Tkinter`` python libraries. On ubuntu and debian

```
sudo apt-get install python-tk
```

On FreeBSD

```
cd /usr/ports/x11-toolkits/py-tkinter/
sudo make config-recursive && sudo make install clean
```


There is also a simple Makefile. Run `make install` as root/sudo, to install the files in /var/lib/selfspy and also create the symlinks /usr/bin/selfspy and /usr/bin/selfstats.

Report issues here:
https://github.com/gurgeh/selfspy/issues

General discussion here:
http://ost.io/gurgeh/selfspy

#### OS X
In OS X you also need to enable access for assistive devices.
To do that in &lt;10.9 there is a checkbox in `System Preferences > Accessibility`,
in 10.9 you have to add the correct application in
`System Preferences > Privacy > Accessability`.

With 10.9 you should do the following: 

```
git clone git://github.com/aurelient/selfspy
cd selfspy
sudo easy_install -U pyobjc-core
python setup.py py2app
```


### Running Selfspy
This fork of selfpy runs as an application, simply double click

### Email
To monitor that Selfspy works as it should and to continuously get feedback on yourself, it is good to  regularly mail yourself some statistics. I think the easiest way to automate this is using [sendEmail](http://www.debianadmin.com/how-to-sendemail-from-the-command-line-using-a-gmail-account-and-others.html), which can do neat stuff like send through your Gmail account.

For example, put something like this in your weekly [cron](http://clickmojo.com/code/cron-tutorial.html) jobs:
`/(PATH_TO_FILE)/selfstats --back 1 w --ratios 900 --periods 900 | /usr/bin/sendEmail -q -u "Weekly selfstats" <etc..>`
This will give you some interesting feedback on how much and when you have been active this last week and how much you have written vs moused, etc.
