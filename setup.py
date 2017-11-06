#!/usr/bin/python

from setuptools import setup

setup(
    name='PyAIG',
    version='1.0.1',
    license='MIT',
    description='A simple Python AIG package',
    platforms='any',
    author='Baruch Sterin',
    author_email='pyaig@bsterin.com',
    install_requires=[
        'click',
        'future'
    ],
    packages=['pyaig'],
)
