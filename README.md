### What is this?
This is a fork of [selfspy](https://github.com/gurgeh/selfspy). We turend it into an Mac Application and are working on  capturing extra invasive information such as screenshots, webcam pics, document names, for research purposes. Since every screenshot takes between 1 and 2MB, your hard drive is going to be filled pretty quickly.

Even though we keep most of the multi-platform code of the original selfspy, we're are not actively maintaining compatiblity with Unix/X11 and Windows. We are also working on advanced visualizations tools for the data and disabled for the statistics part of selfspy in the process of generating an application.

Selfspy is a daemon for Unix/X11, (thanks to @ljos!) Mac OS X and (thanks to @Foxboron) Windows, that continuously monitors and stores what you are doing on your computer. This way, you can get all sorts of nifty statistics and reminders on what you have been up to. It is inspired by the [Quantified Self](http://en.wikipedia.org/wiki/Quantified_Self)-movement and [Stephen Wolfram's personal key logging](http://blog.stephenwolfram.com/2012/03/the-personal-analytics-of-my-life/).



### Installing Selfspy

There is a now a Mac OS X app so go ahead and downloard it.


To install manually, either clone the repository from Github (git clone git://github.com/aurelient/selfspy), or click on the Download link on http://github.com/aurelient/selfspy/ to get the latest Python source.

Selfspy is only tested with Python 2.7 and has a few dependencies on other Python libraries that need to be satisfied. These are documented in the requirements.txt file. If you are on Linux, you will need subversion installed for pip to install python-xlib. If you are on Mac, you will not need to install python-xlib at all. Python-xlib is currently a tricky package to include in the requirements since it is not on PyPi.

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

