import os
import platform
import sys

from setuptools import setup

OPTIONS = {#'argv_emulation': True,
          'includes' : ['sqlalchemy.dialects.sqlite'],
          'iconfile':'assets/eye.icns',
          }

DATA_FILES = ['./assets/eye-48.png',
              './assets/eye_gray-48.png',
              './assets/eye_photo-48.png',
              './assets/eye_photo_gray-48.png',
              './assets/bookmark-64.png',
              './assets/cursor.png',
              './assets/record.png',
              './assets/stop.png',
              './selfspy/Preferences.xib',
              './selfspy/Experience.xib',
              './selfspy/Debriefer.xib']

setup(
    name="selfspy",
    app=['selfspy/__init__.py'],
    version='0.2.0',
    setup_requires=["py2app"],
    options={'py2app': OPTIONS},
    data_files=DATA_FILES,
    # packages=['selfspy'],
    # author="David Fendrich",
    description= 'Log your computer activity!',
    # entry_points=dict(console_scripts=['selfspy=selfspy:main']),
    install_requires=["SQLAlchemy",
        "lockfile",
        "pycrypto",
        "pyobjc-core",
        "pyobjc-framework-Cocoa",
        "pyobjc-framework-Quartz",
        "keyring"
    ]
)
