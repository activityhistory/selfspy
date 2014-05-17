import os
import platform
import sys

# dep_link = []
# if platform.system() == 'Darwin':
#     req_file = 'osx-requirements.txt'
# elif platform.system() == "Windows":
#     req_file = "win-requirements.txt"
# else:
#     req_file = 'requirements.txt'
    #dep_link = ['http://python-xlib.svn.sourceforge.net/viewvc/python-xlib/tags/xlib_0_15rc1/?view=tar#egg=pyxlib']

# with open(os.path.join(os.path.dirname(__file__), req_file)) as f:
#     requires = list(f.readlines())

# print '"%s"' % requires

# import ez_setup
# ez_setup.use_setuptools()

from setuptools import setup

# setup(
#       name="selfspy",
#       app='myapp.app',
#       setup_requires=['py2app'],
#       version='0.3.0',
#       packages=['selfspy'],
#       author="David Fendrich",
#       # author_email='',
#       description=''.join("""
#           Log everything you do on the computer, for statistics,
#           future reference and all-around fun!
#       """.strip().split('\n')),
#       install_requires=["SQLAlchemy==0.7.6",
#           "lockfile==0.9.1",
#           "pycrypto==2.5",
#           "pyobjc-core==2.5.1",
#           "pyobjc-framework-Cocoa==2.5.1",
#           "keyring==1.2.2",
#           "pyobjc-framework-Quartz==2.5.1"
#       ],
#       #dependency_links=dep_link,
#       entry_points=dict(console_scripts=['selfspy=selfspy:main'])
#       )

OPTIONS = {#'argv_emulation': True,
          'includes' : ['sqlalchemy.dialects.sqlite'],
          'iconfile':'assets/eye.icns',
          }
setup(
  name="selfspy",
  app=['selfspy/__init__.py'],
  version='0.3.1',
  # setup_requires=['py2app', ],
  options={'py2app': OPTIONS},
  data_files=['./assets/eye-32.png'],
  # packages=['selfspy'],
  author="David Fendrich",
  description=''.join("""
      Log everything you do on the computer, for statistics,
      future reference and all-around fun!
  """.strip().split('\n')),
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