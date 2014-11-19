### What is Selfspy?
This project is a fork of [selfspy](https://github.com/gurgeh/selfspy). We have modified the original project for research purposes by developing it into a Mac Application that captures additional, invasive information such as screenshots, document names and in the future, webcam pictures.

Even though we keep most of the multi-platform code of the original selfspy, we're are not actively maintaining compatiblity with Unix/X11 and Windows. We are also working on advanced visualizations tools for the data and disabled for the statistics part of selfspy in the process of generating an application.

Since Selfspy takes regular screenshots it can fill your hard drive pretty quickly. We recommend setting your Data storage to an external drive, such as a USB key or SD card. Simply copy the `selfspy.cfg` file to the root of your desired data storage volume and mount the device onto your computer. Selfspy will recognize the volume and save its data there.

Selfspy is a daemon Mac OS X that continuously monitors and stores what you are doing on your computer. It was originally inspired by the [Quantified Self](http://en.wikipedia.org/wiki/Quantified_Self)-movement and [Stephen Wolfram's personal key logging](http://blog.stephenwolfram.com/2012/03/the-personal-analytics-of-my-life/).



### Installing Selfspy
We keep a compiled Mac OS X app in Releases, so go ahead and download it.

To install manually, either clone the repository from Github (git clone git://github.com/activityhistory/selfspy), or click on the Download link on http://github.com/activityhistory/selfspy/ to get the latest Python source.

With 10.9 you should do the following:

1. If you do not have xcode installed, do it now. If you did not agree to its license agreement yet, do it know (e.g. by starting it.)

2. If you do not have brew installed yet, do it now.

3. brew install python

4. brew doctor
This will tell you modify your path with a oneliner. Do this. Then, open a new terminal session.

```
git clone git://github.com/activityhistory/selfspy
cd selfspy
pip install setuptools==3.4.1 && pip install -r requirements.txt
python setup.py py2app
```

A note on VirtualEnvs:

If you want to run the installation within a virtual environment, the file $PROJECT_ROOT/py2app-0.9-py2.7.egg/py2app/recipes/virtualenv.py

has to be manually edited such that the functions that line 52 looks like this:

    m = mf._load_module(m.identifier, fp, pathname, stuff)

and line 81 looks like this:

        mf._scan_code(co, m)

(Yes, this is only adding two underscores.)

This command sequence will build an .app in the /dist folder of your selfspy directory.

Selfspy is only tested with Python 2.7 and has a few dependencies on other Python libraries that need to be satisfied. These are documented in the requirements.txt file.

Report issues here:
https://github.com/activityhistory/selfspy/issues

#### Running on OS X
To run Selfspy in OS X you also need to enable access for assistive devices.
To do that in &lt;10.9 there is a checkbox in `System Preferences > Accessibility`,
in 10.9 you have to add the correct application in
`System Preferences > Privacy > Accessability`.

You may also want to grant Full Keyboard Access to All Controls in `system Preference > Keyboard > Shortcuts` to make it easier to tab through Selfspy's windows.
