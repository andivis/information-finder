import os
import sys
import logging

import program.library.helpers as helpers

from program.library.helpers import get
from program.library.database import Database
from program.library.information_finder import InformationFinder

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
        self.informationFinder.run(inputRow, self.outputDirectory)

    def showStatus(self, fileIndex, i, inputRow):
        keyword = get(inputRow, 'keyword')
        searchType = inputRow.get('type', 'url')

        logging.info(f'File {fileIndex + 1} of {len(self.inputFiles)}: {helpers.fileNameOnly(self.inputFile)}. Item {i + 1} of {len(self.inputRows)}: {keyword}. Search type: {searchType}.')

    def cleanUp(self):
        logging.info('Done')

    def __init__(self):
        helpers.setUpLogging('user-data/logs')
        
        logging.info('Starting')

        self.inputDirectory = 'user-data/input'
        self.outputDirectory = 'user-data/output'
        self.inputFiles = []
        
        for file in os.listdir(self.inputDirectory):
            self.inputFiles.append(os.path.join(self.inputDirectory, file))

        self.options = {
            'maximumSearchResults': 100,
            'maximumNewResults': 25,
            'secondsBetweenKeywords': 10,
            'hoursBetweenRuns': 12,
            'restartSearch': 0,
            'maximumDaysToKeepItems': 180,
            'defaultSearchUrl': 'https://www.google.com',
            'ignorePatterns': '',
            'ignoreDomains': '',
            'sites': 'linkedin.com maps.google.com',
            'proxyListUrl': helpers.getFile('program/resources/resource')
        }

        helpers.setOptions('user-data/options.ini', self.options)

        if '--debug' in sys.argv:
            self.options['maximumSearchResults'] = 25
            self.options['maximumNewResults'] = 3
            self.options['secondsBetweenKeywords'] = 1

        self.database = Database('user-data/database.sqlite')

        self.database.execute('create table if not exists result ( site text, keyword text, id text, name text, gmDate text, json text, primary key(site, id) )')
        self.database.execute('create table if not exists history ( id integer primary key, keyword text, resultsFound integer, maximumNewResults integer, gmDate text )')

        domainsToSearch = [
            'linkedin.com',
            'maps.google.com',
            'google.com'
        ]

        self.informationFinder = InformationFinder(self.options, self.database, domainsToSearch)

main = Main()
main.run()
