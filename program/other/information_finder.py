import sys
import os
import logging
import datetime
import json

# pip packages
import lxml.html as lh

from ..library import helpers

from ..library.helpers import get
from ..library.work import LinkedIn
from ..library.google_maps import GoogleMaps

class InformationFinder:
    def run(self, inputRow, outputDirectory):
        newItems = self.linkedIn.search(inputRow)

        for newItem in newItems:
            self.output(inputRow, newItem, outputDirectory)

        self.markDone(inputRow, newItems)

    def output(self, inputRow, newItem, outputDirectory):
        self.toDatabase(inputRow, newItem)
        self.toFile(inputRow, newItem, outputDirectory)

    def toFile(self, inputRow, newItem, outputDirectory):
        if not newItem:
            return

        fields = ['site', 'keyword', 'first name', 'last name', 'email', 'phone', 'headline', 'job title', 'company', 'summary', 'industry', 'location', 'country', 'positions', 'school', 'field of study', 'id', 'linkedin url']

        # output to companies.csv too?
        if self.linkedIn.isProfileUrl(inputRow):            
            companyFields = ['site', 'keyword', 'name', 'website', 'city', 'region', 'country', 'headline', 'minimum employees', 'maximum employees', 'industry', 'company type', 'id', 'linkedin url']

            companiesOutputFile = os.path.join(outputDirectory, 'companies.csv')

            for company in get(newItem, 'companies'):
                self.toCsvFile(inputRow, company, companyFields, companiesOutputFile)

        outputFile = os.path.join(outputDirectory, 'output.csv')

        self.toCsvFile(inputRow, newItem, fields, outputFile)

    def toCsvFile(self, inputRow, newItem, fields, outputFile):
        helpers.makeDirectory(os.path.dirname(outputFile))

        # write header
        if not os.path.exists(outputFile):
            helpers.toFile(','.join(fields), outputFile)

        file = helpers.getFile(outputFile)

        id = newItem.get('id', '')

        if id and f',{id},' in file:
            logging.info(f'Skipping. {id} is already in the output file.')
            return

        values = [newItem.get('site', ''), inputRow.get('keyword', '')]

        for field in fields[2:]:
            value = ''
            
            if field == 'positions':
                value = self.linkedIn.getPositionsAsString(newItem)
            else:
                value = newItem.get(field, '')

            values.append(value)

        helpers.appendCsvFile(values, outputFile)

    def toDatabase(self, inputRow, newItem):
        item = {
            'site': newItem.get('site', ''),
            'keyword': inputRow.get('keyword', ''),
            'id': newItem.get('id', ''),
            'name': newItem.get('name', ''),
            'email': newItem.get('email', ''),
            'phone': newItem.get('phone', ''),
            'destinations': inputRow.get('destinations', ''),
            'gmDate': str(datetime.datetime.utcnow()),
            'json': json.dumps(newItem)
        }

        self.database.insert('result', item)

    def isDone(self, inputRow):
        result = False

        if self.options['restartSearch']:
            return result

        keyword = inputRow.get('keyword', '')
        maximumNewResults = inputRow.get('maximumNewResults', self.options['maximumNewResults'])

        datePart = ''

        if self.options['hoursBetweenRuns'] > 0:
            minimumDate = helpers.getDateStringSecondsAgo(self.options['hoursBetweenRuns'] * 60 * 60, True)
            datePart = f" and gmDateCompleted >= '{minimumDate}'"

        row = self.database.getFirst('history', '*', f"keyword = '{keyword}' and maximumNewResults = {maximumNewResults}{datePart}", '', '')

        if row:
            logging.info(f'Skipping. Already done this item.')
            result = True

        return result
    
    def markDone(self, inputRow, newItems):
        if not newItems:
            return

        history = {
            'keyword': inputRow.get('keyword', ''),
            'resultsFound': len(newItems),
            'maximumNewResults': self.options['maximumNewResults'],
            'gmDate': datetime.datetime.utcnow()
        }

        self.database.insert('history', history)
    
    def removeOldEntries(self):
        maximumDaysToKeepItems = self.options['maximumDaysToKeepItems']

        minimumDate = helpers.getDateStringSecondsAgo(maximumDaysToKeepItems * 24 * 60 * 60, True)
        
        logging.debug(f'Deleting entries older than {maximumDaysToKeepItems} days')
        self.database.execute(f"delete from history where gmDate < '{minimumDate}'")

    def __init__(self, options, database):
        self.options = options
        self.database = database
        self.credentials = {}
        
        helpers.setOptions('user-data/credentials/credentials.ini', self.credentials, '')

        self.linkedIn = LinkedIn(self.options, False, self.database)
        self.googleMaps = GoogleMaps(self.options, self.credentials, self.database)

        self.database.removeOldEntries()
