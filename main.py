import os
import sys
import logging

if os.path.isdir('program/library'):
    sys.path.insert(0, os.getcwd() + '/program/library')

import helpers

from program.library.helpers import get
from program.library.database import Database
from program.other.information_finder import InformationFinder

class Main:
    def run(self):
        for fileIndex, inputFile in enumerate(self.inputFiles):
            self.inputFile = inputFile

            self.inputRows = helpers.getCsvFile(self.inputFile)
            
            for i, inputRow in enumerate(self.inputRows):
                try:
                    self.showStatus(fileIndex, i, inputRow)
                    self.doItem(inputRow)
                except Exception as e:
                    helpers.handleException(e)
    
        self.cleanUp()

    def doItem(self, inputRow):
        newItems = self.informationFinder.run(inputRow)

        self.output(newItems)

    def output(self, newItems):
        for newItem in newItems:
            outputFile = os.path.join(self.outputDirectory, 'output.csv')
            
            line = self.informationFinder.getAsLine(newItem)
            helpers.appendCsvFile(line, outputFile)

    def showStatus(self, fileIndex, i, inputRow):
        keyword = get(inputRow, 'keyword or url')
        logging.info(f'File {fileIndex + 1} of {len(self.inputFiles)}: {helpers.fileNameOnly(self.inputFile)}. Item {i + 1} of {len(self.inputRows)}: {keyword}.')

    def cleanUp(self):
        logging.info('Done')

    def __init__(self):
        helpers.setUpLogging()
        
        logging.info('Starting')

        self.inputDirectory = 'user-data/input'
        self.outputDirectory = 'user-data/output'
        self.inputFiles = []
        
        for file in os.listdir(self.inputDirectory):
            self.inputFiles.append(os.path.join(self.inputDirectory, file))

        self.options = {
        }

        self.database = Database('user-data/database.sqlite')

        self.informationFinder = InformationFinder(self.options, self.database)

main = Main()
main.run()
