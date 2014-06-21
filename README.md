### What is Selfspy?
This project is a fork of [selfspy](https://github.com/gurgeh/selfspy). We have modified the original project for research purposes by turning it into a Mac Application that captures extra invasive information such as screenshots, document names and in the future, webcam pictures. Since Selfspy takes regular screenshots it can fill your hard drive pretty quickly. We recommend setting your Data storage to an external drive, such as a USB key. 

Even though we keep most of the multi-platform code of the original selfspy, we're are not actively maintaining compatiblity with Unix/X11 and Windows. We are also working on advanced visualizations tools for the data and disabled for the statistics part of selfspy in the process of generating an application.

Selfspy is a daemon for Unix/X11, (thanks to @ljos!) Mac OS X and (thanks to @Foxboron) Windows, that continuously monitors and stores what you are doing on your computer. This way, you can get all sorts of nifty statistics and reminders on what you have been up to. It is inspired by the [Quantified Self](http://en.wikipedia.org/wiki/Quantified_Self)-movement and [Stephen Wolfram's personal key logging](http://blog.stephenwolfram.com/2012/03/the-personal-analytics-of-my-life/).



### Installing Selfspy
We keep a compiled Mac OS X app in Releases, so go ahead and download it.

To install manually, either clone the repository from Github (git clone git://github.com/aurelient/selfspy), or click on the Download link on http://github.com/aurelient/selfspy/ to get the latest Python source.

With 10.9 you should do the following: 

```
git clone git://github.com/aurelient/selfspy
cd selfspy
sudo easy_install -U pyobjc-core
python setup.py py2app
```

Selfspy is only tested with Python 2.7 and has a few dependencies on other Python libraries that need to be satisfied. These are documented in the requirements.txt file.

Report issues here:
https://github.com/aurelient/selfspy/issues

#### Running on OS X
To run Selfspy in OS X you also need to enable access for assistive devices.
To do that in &lt;10.9 there is a checkbox in `System Preferences > Accessibility`,
in 10.9 you have to add the correct application in
`System Preferences > Privacy > Accessability`.