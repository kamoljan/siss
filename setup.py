#!/usr/bin/python2.7

from distutils.core import setup

setup(name='siss',
      version='1.0',
      description='a simple file storage service',
      author='Kamol Mavlonov',
      author_email='kamoljan@gmail.com',
      url='http://www.kamol.org',
      py_modules=['siss', ],
      data_files=[('/usr/local/bin', ['sissd.py', 'sissd']),
                  ('/etc', ['sissd.conf'])]
)
