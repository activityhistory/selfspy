### What is Selfspy?
Selfspy is a daemon Mac OS X that continuously monitors and stores what you are doing on your computer. It was originally inspired by the [Quantified Self](http://en.wikipedia.org/wiki/Quantified_Self)-movement and [Stephen Wolfram's personal key logging](http://blog.stephenwolfram.com/2012/03/the-personal-analytics-of-my-life/).

This project is a fork of [selfspy](https://github.com/gurgeh/selfspy). We have modified the original project for research purposes by developing it into a Mac Application that captures additional, invasive information such as screenshots, document names and URLs.

Even though we keep most of the multi-platform code of the original selfspy, we're are not actively maintaining compatiblity with Unix/X11 and Windows. We are also working on advanced data visualizations tools and disabled the statistics part of Selfspy in the process of generating an application.

Since Selfspy takes frequent screenshots it can fill your hard drive pretty quickly. We recommend setting your Data storage to an external drive, such as a USB key or SD card. Simply copy the `selfspy.cfg` file to the root of your desired data storage volume and mount the device onto your computer. When you start Selfspy, it will automatically recognize the volume and save its data there.

### Installing Selfspy
We keep a compiled Mac OS X app in [Releases](https://github.com/aurelient/selfspy/releases), so go ahead and download it.

To install manually, either clone the repository from Github (git clone git://github.com/aurelient/selfspy), or click on the Download link on http://github.com/aurelient/selfspy/ to get the latest Python source.

With 10.9 you should do the following:

1. Install Xcode if you have not installed it already. Install the command line tools using:

```
xcode-select --install
```

and make sure you agree to Xcode's license agreement (e.g. by starting Xcode.)

2. Download Selfspy and its dependencies

```
git clone git://github.com/aurelient/selfspy
pip install -r osx-requirements.txt
cd selfspy
python setup.py py2app
```

This command sequence will build an .app in the /dist folder of your selfspy directory. Selfspy is only tested with Python 2.7.

Report issues here:
https://github.com/aurelient/selfspy/issues

#### Running on OS X
To use the full capabilities of Selfspy in OS X (e.g. keylogging) you need to give it access as an assistive device.
To do that in &lt;10.9 there is a checkbox in `System Preferences > Accessibility`, in 10.9 you have to add the correct application in
`System Preferences > Privacy > Accessability`.
