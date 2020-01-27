import os
import sys

if os.path.isdir('library'):
    sys.path.insert(0, os.getcwd() + '/library')

import logging

import helpers

from helpers import get
from database import Database

class Main:
    def run(self):
        for fileIndex, inputFile in enumerate(self.inputFiles):
            self.inputFile = inputFile

            self.items = self.items = helpers.getCsvFile(self.inputFile)
            
            for i, item in enumerate(self.items):
                try:
                    self.doItem(fileIndex, i, item)
                except Exception as e:
                    helpers.handleException(e)
    
        self.cleanUp()

    def doItem(self, fileIndex, i, item):
        keyword = get(item, 'keyword or url')

        logging.info(f'File {fileIndex + 1} of {len(self.inputFiles)}: {helpers.fileNameOnly(self.inputFile)}. Item {i + 1} of {len(self.items)}: {keyword}.')

    def cleanUp(self):
        logging.info('Done')

    def __init__(self):
        helpers.setUpLogging()
        
        logging.info('Starting')

        self.inputFiles = []
        
        for file in os.listdir('input'):
            self.inputFiles.append(os.path.join('input', file))

        self.options = {
        }

main = Main()
main.run()
