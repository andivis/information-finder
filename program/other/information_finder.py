import sys
import os
import logging

# pip packages
import lxml.html as lh

if os.path.isdir('program/library'):
    sys.path.insert(0, os.getcwd() + 'program/library')

import helpers

from helpers import get
from work import LinkedIn
from google_maps import GoogleMaps

class InformationFinder:
    def run(self, inputRow):
        logging.info(f'Running for {inputRow}')

        return []

    def getAsLine(self, newItem):
        return ''

    def __init__(self, options, database):
        self.options = options
        self.database = database
        self.credentials = {}
        
        helpers.setOptions('user-data/credentials/credentials.ini', self.credentials, '')

        self.linkedIn = LinkedIn(self.options, self.database)
        self.googleMaps = GoogleMaps(self.options, self.credentials, self.database)
