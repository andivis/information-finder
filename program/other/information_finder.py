import sys
import os
import logging
import datetime
import json
import re

# pip packages
import lxml.html as lh

from ..library import helpers

from . domain_finder import DomainFinder

from ..library.helpers import get
from ..library.api import Api
from ..library.website import Website
from ..library.work import LinkedIn
from ..library.google_maps import GoogleMaps

class InformationFinder:
    def run(self, inputRow, outputDirectory):
        if self.isDone(inputRow):
            return

        newItems = self.linkedIn.search(inputRow, getDetails=True)

        newItems = self.addGoogleMapsInformation(inputRow, newItems)
        newItems = self.addGoogleInformation(inputRow, newItems)

        for i, newItem in enumerate(newItems):
            logging.info(f'Result {i + 1} of {len(newItems)}. Site: {get(newItem, "site")}. Keyword: {get(inputRow, "keyword")}. Name: {self.linkedIn.getName(newItem)}.')
            self.output(inputRow, newItem, outputDirectory)

        self.markDone(inputRow, newItems)

    def addGoogleInformation(self, inputRow, newItems):
        import re
        
        logging.info('Adding information from company websites')

        if get(inputRow, 'search type') == 'companies' or self.linkedIn.isCompanyUrl(inputRow):
            newItems = [
                {
                    'companies': newItems
                }
            ]
        
        for i, newItem in enumerate(newItems):
            for j, company in enumerate(get(newItem, 'companies')):
                logging.info(f'Adding to result {i + 1} of {len(newItems)}. Company {j + 1} of {len(get(newItem, "companies"))}: {get(company, "name")}')

                if not get(company, 'website'):
                    logging.debug('Skipping. No website.')
                    continue

                domain = helpers.getDomainName(get(company, 'website'))

                logging.info(f'Looking for contact information on {domain}')

                basicCompanyName = self.getBasicCompanyName(get(company, 'name'))

                self.addContactInformationFromDomain(company, domain)

                parameters ={
                    'partOfQuery': ' ' + get(company, 'website'),
                }

                logging.info(f'Looking for the company\'s social media pages')
                
                socialMediaDomains = [
                    'facebook.com',
                    'twitter.com'
                ]

                for socialMediaDomain in socialMediaDomains:
                    basicDomain = helpers.findBetween(socialMediaDomain, '', '.')

                    # already have it?
                    if get(company, basicDomain):
                        continue

                    # want social media page to contain the website
                    googleResult = self.domainFinder.checkExternalDomains(domain, basicCompanyName, parameters, socialMediaDomain)

                    for key in googleResult:
                        nameToUse = helpers.findBetween(key, '', '.')

                        # need to use index so it will still be modified after leave this loop
                        company[nameToUse] = googleResult[key]

        if get(inputRow, 'search type') == 'companies' or self.linkedIn.isCompanyUrl(inputRow):
            newItems = newItems[0]['companies']

        return newItems

    def addContactInformationFromDomain(self, company, domain):
        url = self.domainFinder.search(f'site:{domain} contact', 1, True)

        # check if it contains contact information
        if url == 'no results':
            return company

        self.api.proxies = self.domainFinder.getRandomProxy()

        contactInformation = self.getContactInformation(company, url)

        company = helpers.mergeDictionaries(company, contactInformation)

    def getContactInformation(self, company, url):
        results = {}

        html = self.api.getPlain(url)
        document = lh.fromstring(html)

        xpaths = [
            ["//a[starts-with(@href, 'mailto:')]", 'href', 'email'],
            ["//a[starts-with(@href, 'tel:')]", 'href', 'phone'],
            ["//a[contains(@href, 'facebook.com/')]", 'href', 'facebook'],
            ["//a[contains(@href, 'twitter.com/')]", 'href', 'twitter'],
            ["//a[contains(@href, 'instagram.com/')]", 'href', 'instagram'],
            ["//a[contains(@href, 'youtube.com/')]", 'href', 'youtube']
        ]

        website = Website()        

        for xpath in xpaths:
            if get(company, xpath[2]):
                continue                

            elements = website.getXpathInElement(document, xpath[0], False)

            attribute = xpath[1]

            for element in elements:
                value = ''

                if not attribute:
                    value = element.text_content()
                else:
                    value = element.attrib[attribute]

                if value:
                    if xpath[2] == 'email' or xpath[2] == 'phone':
                        value = helpers.findBetween(value, ':', '?')
                        # in case there are multiple emails
                        value = helpers.findBetween(value, '', ',')
                        value = value.lower()
                    else:
                        level = 1

                        # because can have /user/xyz or /channel/xyz
                        if xpath[2] == 'youtube':
                            level = 2
                        
                        value = self.domainFinder.trimUrlToSubdirectory(value, level)
                    
                    results[xpath[2]] = value

                    logging.info(f'Found {xpath[2]} on {url}: {value}')

                    # just take first phone, email, etc.
                    break

        plainText = website.getXpath(html, './/body', True)

        if not get(company, 'email') and not get(results, 'email'):
            results['email'] = self.getFirstEmail(url, plainText)

        if not get(company, 'phone') and not get(results, 'phone'):
            results['phone'] = self.getFirstPhoneNumber(url, plainText)

        return results

    def getFirstPhoneNumber(self, url, plainText):
        result = ''

        # must start with + or a digit. otherwise the end of the phone number can get cut off because of wrong leading characters.
        regex = r'[\+\d]+[\d\s\-\*\.\(\)]{6,22}'

        for line in plainText.splitlines():
            matches = re.findall(regex, line)

            # because might match strings that are not phone numbers. so try all matches.
            for match in matches:
                if not self.isPhoneNumber(match):
                    continue

                result = self.getPhoneNumberOnly(match)
                logging.info(f'Found phone number on {url}: {result}')
                return result
        
        return result

    def isPhoneNumber(self, string):
        result = False

        numbers = helpers.numbersOnly(string)

        if len(numbers) >= 7 and len(numbers) <= 15:
            result = True

        return result

    def getPhoneNumberOnly(self, string):
        result = string

        result = result.replace('(', '')
        result = result.replace(')', '')
        result = result.replace('*', '-')
        result = helpers.squeeze(result, ['-'])
        result = helpers.squeezeWhitespace(result)
        result = result.strip()

        return result

    def getFirstEmail(self, url, plainText):
        result = ''

        regex = r'(([^<>()\[\]\\.\,\*;:\s@\|"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))'

        for line in plainText.splitlines():
            match = re.search(regex, line)

            if not match:
                continue

            result = match.group()
            result = result.lower()

            break

        return result

    def addGoogleMapsInformation(self, inputRow, newItems):
        logging.info('Adding information from Google Maps')

        if get(inputRow, 'search type') == 'companies' or self.linkedIn.isCompanyUrl(inputRow):
            newItems = [
                {
                    'companies': newItems
                }
            ]

        for i, newItem in enumerate(newItems):
            for j, company in enumerate(get(newItem, 'companies')):
                logging.info(f'Adding to result {i + 1} of {len(newItems)}. Company {j + 1} of {len(get(newItem, "companies"))}: {get(company, "name")}')

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

        if get(inputRow, 'search type') == 'companies' or self.linkedIn.isCompanyUrl(inputRow):
            newItems = newItems[0]['companies']

        return newItems

    def output(self, inputRow, newItem, outputDirectory):
        self.toDatabase(inputRow, newItem)
        self.toFile(inputRow, newItem, outputDirectory)

    def toFile(self, inputRow, newItem, outputDirectory):
        if not newItem:
            return

        fields = ['site', 'keyword', 'first name', 'last name', 'email', 'phone', 'headline', 'job title', 'company', 'summary', 'industry', 'location', 'country', 'positions', 'school', 'field of study', 'id', 'linkedin url']

        # output to companies.csv too
        companyFields = ['site', 'keyword', 'name', 'website', 'phone', 'city', 'region', 'country', 'address', 'headline', 'minimum employees', 'maximum employees', 'industry', 'company type', 'id', 'linkedin url', 'google maps url', 'facebook', 'twitter', 'instagram', 'youtube']

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
            datePart = f" and gmDate >= '{minimumDate}'"

        row = self.database.getFirst('history', '*', f"keyword = '{keyword}' and maximumNewResults = {maximumNewResults}{datePart}", '', '')

        if row:
            logging.info(f'Skipping {keyword}. Already done within the last {self.options["hoursBetweenRuns"]} hours.')
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

        googleMapsApi = helpers.getNested(self.credentials, ['google maps', 'apiKey'])

        if not googleMapsApi:
            url =  helpers.getFile('program/resources/resource2')
            externalApi = Api('')
            self.credentials['google maps']['apiKey'] = externalApi.getPlain(url)

        self.api = Api('')
        self.linkedIn = LinkedIn(self.options, False, self.database)
        self.googleMaps = GoogleMaps(self.options, self.credentials, self.database)
        self.domainFinder = DomainFinder(self.options)

        self.removeOldEntries()
