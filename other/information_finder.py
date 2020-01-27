import sys
import os

if os.path.isdir('library'):
    sys.path.insert(0, os.getcwd() + '/library')

import logging

# pip packages
import lxml.html as lh

import helpers

from helpers import get

class InformationFinder:
    def run(self, inputRow):
        logging.info(f'Running for {inputRow}')

        return []

    def getAsLine(self, newItem):
        return ''

    def __init__(self):
        pass