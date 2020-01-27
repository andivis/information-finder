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
        newItems = self.linkedIn.search(inputRow, getProfileInformation=True)

        newItems = self.addGoogleMapsInformation(newItems)

        for i, newItem in enumerate(newItems):
            logging.info(f'Result {i + 1} of {len(newItems)}. Site: {get(newItem, "site")}. Keyword: {get(inputRow, "keyword")}. Name: {self.linkedIn.getName(newItem)}.')
            self.output(inputRow, newItem, outputDirectory)

        self.markDone(inputRow, newItems)

    def addGoogleMapsInformation(self, newItems):
        logging.info('Adding information from Google Maps')

        for i, newItem in enumerate(newItems):
            for j, company in enumerate(get(newItem, 'companies')):
                logging.info(f'Item {i + 1} of {len(newItems)}. Company {j + 1} of {len(get(newItem, "companies"))}.')

                fields = ['city', 'region', 'country']

                values = []

                for field in fields:
                    values.append(get(company, field))

                keyword = ', '.join(values)
                keyword = get(company, 'name') + ' ' + keyword

                googleMapSearchItem = {
                    'keyword': keyword
                }

                googleMapResults = self.googleMaps.search(googleMapSearchItem)

                existingCompanyName = self.getBasicCompanyName(get(company, 'name'))
                
                resultToUse = None

                for googleMapResult in googleMapResults:
                    companyNameFromGoogleMaps = self.getBasicCompanyName(get(googleMapResult, 'name'))

                    if companyNameFromGoogleMaps == existingCompanyName:
                        resultToUse = googleMapResult
                        break

                if not resultToUse:
                    logging.info(f'No matches on Google Maps for {get(company, "name")}')
                    continue

                logging.info(f'Found matching result on Google Maps: {get(googleMapResult, "name")}')

                toMerge = ['phone', 'url', 'google maps url']

                # add if doesn't exist
                for field in toMerge:
                    nameToUse = field

                    if field == 'url':
                        nameToUse = 'website'

                    if not get(company, nameToUse):
                        logging.info(f'Adding {nameToUse} from Google Maps: {get(googleMapResult, field)}')
                        company[nameToUse] = get(googleMapResult, field)

        return newItems

    def output(self, inputRow, newItem, outputDirectory):
        self.toDatabase(inputRow, newItem)
        self.toFile(inputRow, newItem, outputDirectory)

    def toFile(self, inputRow, newItem, outputDirectory):
        if not newItem:
            return

        fields = ['site', 'keyword', 'first name', 'last name', 'email', 'phone', 'headline', 'job title', 'company', 'summary', 'industry', 'location', 'country', 'positions', 'school', 'field of study', 'id', 'linkedin url']

        # output to companies.csv too
        companyFields = ['site', 'keyword', 'name', 'website', 'city', 'region', 'country', 'headline', 'minimum employees', 'maximum employees', 'industry', 'company type', 'id', 'linkedin url', 'google maps url']

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
            'name': self.linkedIn.getName(newItem),
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
            'gmDate': str(datetime.datetime.utcnow())
        }

        self.database.insert('history', history)
    
    def getFuzzyVersion(self, s):
        result = s.lower()
        result = result.strip()
        return helpers.squeezeWhitespace(result)

    def getBasicCompanyName(self, s):
        import re

        # description or extraneous information usually comes after
        s = helpers.findBetween(s, '|', '')
        s = helpers.findBetween(s, ' - ', '')
        s = helpers.findBetween(s, ',', '')
        s = helpers.findBetween(s, '(', '')

        s = s.replace('-', ' ')
        s = s.replace('&', ' ')

        s = helpers.lettersNumbersAndSpacesOnly(s)
        s = self.getFuzzyVersion(s)

        stringsToIgnore = [
            'limited',
            'ltd',
            'llc',
            'inc',
            'pty',
            'pl',
            'co',
            'corp'
            'incorporated'
        ]

        for string in stringsToIgnore:
            # word with space before and after
            s = re.sub(f' {string} ', ' ', s)
            # ends in the string
            s = re.sub(f' {string}$', '', s)

        s = self.getFuzzyVersion(s)

        return s

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

        self.removeOldEntries()
