import sys
import logging
import random
import time

if not '../library' in sys.path:
    sys.path.insert(0, '../library')

import helpers

from helpers import get
from api import Api

class SalesQl:
    def search(self, item):
        result = {}

        searchTerm = item.get('id', '')

        if not searchTerm:
            return result

        urls = [
            f'/contacts/contact/{searchTerm}?is_sales=0&is_recruiter=0',
            f'/extension/add_contact'
        ]

        j = {}
        
        # sometimes it takes a while for the result to be ready
        maximumTries = 12
        done = False

        for i in range(0, maximumTries):
            for url in urls:
                if url.startswith('/contacts/'):
                    self.api.setHeadersFromHarFile('credentials/mlhacebjlefifkldmkbilohcaiednbik.har', 'api.salesql.com/')

                    j = self.api.get(url)

                    if not '--debug' in sys.argv:
                        time.sleep(1)
                elif url.startswith('/extension/'):
                    j = self.waitForContactInformation(url, item, searchTerm)            
            
                if get(j, 'person'):
                    done = True
                    break

            if done:
                break

            logging.info(f'No contact info yet. Waiting: {i + 1} of {maximumTries}.')
            helpers.wait(5)

        result = self.parseResult(searchTerm, j)
        
        return result

    def waitForContactInformation(self, url, item, searchTerm):
        result = {}

        body = helpers.getFile('resources/post.txt')
        body = body.replace('%profileId%', searchTerm)

        urn = item.get('urn', '')

        if not urn:
            logging.debug('Skipping. No urn.')
            return result

        self.api.setHeadersFromHarFile('credentials/mlhacebjlefifkldmkbilohcaiednbik.har', 'api.salesql.com/extension/add_contact')
        
        body = body.replace('%profileUrn%', urn)

        result = self.api.post(url, body)

        if not '--debug' in sys.argv:
            time.sleep(1)

        return result

    def parseResult(self, searchTerm, j):
        result = {}

        person = j.get('person', '')

        if not person:
            return result

        preferredTypes = ['main job', 'job', 'work', 'business']

        # this way the certain emails take priority over the uncertain ones
        emails = self.getList([], person, 'contact_emails', 'email', 'type', preferredTypes)
        # these seem to be emails they think are probably correct
        emails = self.getList(emails, person, 'email_patterns', 'pattern', 'type', preferredTypes)
        
        phoneNumbers = self.getList([], person, 'contact_phones', 'phone', 'phone_type', preferredTypes)

        if not emails.get('main') and not phoneNumbers.get('main', ''):
            logging.info(f'No email or phone number from SalesQL for {searchTerm}')
            return result

        result = {
            'name': person.get('name', ''),
            'job title': person.get('primary_job_title', ''),
            'company': helpers.getNested(person, ['primary_organization', 'name']),
            'email': emails.get('main', ''),
            'phone': phoneNumbers.get('main', ''),
            'allEmails': emails.get('list', []),
            'allPhoneNumbers': phoneNumbers.get('list', [])
        }

        return result

    def getList(self, existingResult, j, listName, keyName, typeKeyName, preferredTypes):
        result = {
            'main': '',
            'list': []
        }

        if existingResult:
            result = existingResult

        for item in j.get(listName, ''):
            value = item.get(keyName, '')
            type = item.get(typeKeyName, '')

            if not value:
                continue

            if 'phone' in listName and item.get('is_full_number', 'unknown') == False:
                logging.debug(f'Skipping phone number {value}. Not full phone number')
                continue

            newItem = {
                'value': value,
                'type': type
            }

            result['list'].append(newItem)

        # try to get the preferred type, starting from the beginning
        for type in preferredTypes:
            found = False

            for item in result['list']:
                if type in item.get('type'):
                    result['main'] = item.get('value', '')
                    found = True
                    break

            if found:
                break

        # default to first item
        if not result.get('main', '') and result.get('list', ''):
            result['main'] = result['list'][0].get('value', '')

        return result

    def __init__(self, options, proxies):
        self.options = options
        
        self.api = Api('https://api.salesql.com')

        self.api.proxies = proxies

class LinkedIn:
    def search(self, item):
        results = []

        keyword = item.get('keyword', '')

        # profile
        if keyword.startswith('https://www.linkedin.com/in/'):
            results = self.getProfileInformation(keyword)
        # search term
        else:
            import urllib.parse
            query = keyword
            query = urllib.parse.quote(query)

            results = self.getSearchResults(item, query)

        results = self.addContactInformation(item, results)

        return results

    def getProfileInformation(self, keyword):
        results = []

        profileId = helpers.findBetween(keyword, 'https://www.linkedin.com/in/', '/')

        if self.inDatabase(profileId):
            return

        j = self.api.get(f'/voyager/api/identity/profiles/{profileId}/profileView')            

        urn = helpers.getNested(j, ['data', 'entityUrn'])
        urn = helpers.getLastAfterSplit(urn, ':')        

        newItem = {
            'id': profileId,
            'linkedin url': 'https://www.linkedin.com/in/' + profileId + '/',
            'urn': urn,
            'positions': [],
            'companies': []
        }

        # find the right types of elements
        for included in j.get('included'):
            if included.get('$type', '') == 'com.linkedin.voyager.identity.profile.Position':
                newPosition = {}

                fields = {
                    'title': 'title',
                    'companyName': 'company',
                    'description': 'description',
                    'companyUrn': 'companyUrn'
                }

                for field in fields:
                    nameToUse = fields[field]
                    newPosition[nameToUse] = get(included, field)

                newPosition['companyUrn'] = helpers.getLastAfterSplit(get(newPosition, 'companyUrn'), ':')        
                
                newPosition['startYear'] = helpers.getNested(included, ['timePeriod', 'startDate', 'year'])
                newPosition['endYear'] = helpers.getNested(included, ['timePeriod', 'endDate', 'year'])

                # no end date means they currently work there
                if newPosition['startYear'] and not helpers.getNested(included, ['timePeriod', 'endDate', 'year']):
                    newItem['job title'] = get(included, 'title')
                    newItem['company'] = get(included, 'companyName')

                newItem['positions'].append(newPosition)
            elif included.get('$type', '') == 'com.linkedin.voyager.identity.profile.Profile':
                fields = ['firstName', 'lastName', 'headline', 'summary', 'geoLocationName', 'geoCountryName', 'industryName']

                fields = {
                    'firstName': 'first name',
                    'lastName': 'last name',
                    'headline': 'headline',
                    'summary': 'summary',
                    'geoLocationName': 'location',
                    'geoCountryName': 'country',
                    'industryName': 'industry'
                }

                for field in fields:
                    nameToUse = fields[field]
                    newItem[nameToUse] = get(included, field)

                    if field == 'firstName':
                        # this leaves out middle names and initials                        
                        newItem[nameToUse] = helpers.findBetween(get(included, field), '', ' ')                        
            elif included.get('$type', '') == 'com.linkedin.voyager.identity.profile.Education':
                # just want most recent school
                if get(newItem, 'school'):
                    continue

                fields = {
                    'schoolName': 'school',
                    'fieldOfStudy': 'field of study'
                }

                for field in fields:
                    nameToUse = fields[field]
                    newItem[nameToUse] = get(included, field)
        
        newItem['positions'] = sorted(newItem['positions'], key=lambda k: k['startYear'], reverse=True) 

        # get company details
        for position in get(newItem, 'positions'):
            company = self.getCompanyInformation(j, get(position, 'companyUrn'))
        
            newItem['companies'] = self.addIfNotExists(newItem['companies'], company, 'universalName')

            position['company id'] = get(company, 'id')
            position['company linkedin url'] = get(company, 'linkedin url')
        
        results.append(newItem)

        return results

    def getCompanyInformation(self, profileResponse, companyUrn):
        result = {}

        universalName = ''

        # need universal name for the search
        for included in profileResponse.get('included'):
            if included.get('$type', '') == 'com.linkedin.voyager.entities.shared.MiniCompany':
                urn = get(included, 'entityUrn')
                urn = helpers.getLastAfterSplit(urn, ':')

                if urn == companyUrn:
                    universalName = get(included, 'universalName')
                    break

        if not universalName:
            return result

        result['id'] = universalName

        import urllib
        suffix = urllib.parse.quote_plus(universalName);

        j = self.api.get(f'/voyager/api/organization/companies?decorationId=com.linkedin.voyager.deco.organization.web.WebFullCompanyMain-20&q=universalName&universalName={suffix}')            

        # find the right types of elements
        for included in get(j, 'included'):
            urn = get(included, 'entityUrn')
            urn = helpers.getLastAfterSplit(urn, ':')

            if included.get('$type', '') == 'com.linkedin.voyager.organization.Company':
                # can be other companies, such as followers or following
                if urn != companyUrn:
                    continue

                fields = {
                    'name': 'name',
                    'companyPageUrl': 'website',
                    'tagline': 'headline'
                }

                for field in fields:
                    nameToUse = fields[field]
                    result[nameToUse] = get(included, field)

                result['minimum employees'] = helpers.getNested(included, ['staffCountRange', 'start'])
                result['maximum employees'] = helpers.getNested(included, ['staffCountRange', 'end'])
                result['company type'] = helpers.getNested(included, ['companyType', 'localizedName'])
                result['linkedin url'] = 'https://www.linkedin.com/in/' + universalName + '/'

                result['city'] = helpers.getNested(included, ['headquarter', 'city'])
                result['region'] = helpers.getNested(included, ['headquarter', 'geographicArea'])
                result['country'] = helpers.getNested(included, ['headquarter', 'country'])

            elif included.get('$type', '') == 'com.linkedin.voyager.common.Industry':
                # might be more than one industry
                if not get(result, 'industry'):
                    result['industry'] = get(included, 'localizedName')

        return result

    def getPositionsAsString(self, item):
        values = []

        for position in get(item, 'positions'):
            title = get(position, 'title')
            company = get(position, 'company')
            startYear = get(position, 'startYear')
            endYear = get(position, 'endYear')

            s = f'{title} at {company} ({startYear} to {endYear})'

            values.append(s)

        return '; '.join(values)

    def addIfNotExists(self, list, newItem, key):
        if not newItem:
            return

        found = False
        
        for item in list:
            if not get(item, key) or not get(newItem, key):
                continue

            if get(item, key) == get(newItem, key):
                found = True
                break

        if not found:
            list.append(newItem)

        return list

    def getName(self, item):
        result = item.get('name', '')

        # prefer these fields if available
        if get(item, 'firstName'):
            result = get(item, 'firstName') + ' ' + get(item, 'lastName')

        return result

    def addContactInformation(self, searchItem, results):
        newResults = []

        keyword = get(searchItem, 'keyword')

        i = 0

        for item in results:
            salesQlResult = self.salesQl.search(item)

            i += 1

            if not salesQlResult:
                continue

            email = salesQlResult.get('email', '')
            phone = salesQlResult.get('phone', '')

            newItem = item

            for key in salesQlResult:
                # don't need both versions of name
                if key == 'name' and get(newItem, 'firstName'):
                    continue

                # add the new information
                if not newItem.get(key, ''):
                    newItem[key] = salesQlResult[key]

            newResults.append(newItem)

            logging.info(f'Site: linkedin.com. Keyword: {keyword}. Results: {len(newResults)}. Name: {self.getName(newItem)}. Email: {email}. Phone: {phone}.')
            
            maximum = searchItem.get('maximumNewResults', self.options['maximumNewResults'])
            maximum = int(maximum)

            if len(newResults) >= maximum:
                logging.info(f'Stopping for this keyword. Got {len(newResults)} new results.')
                break

        return newResults

    def getSearchResults(self, searchItem, keyword):
        results = []

        keyword = searchItem.get('keyword', '')

        start = 0
        count = 10

        onSearchResultIndex = 0
        anyResultsForThisPage = False

        for i in range(0, 100):
            logging.info(f'Getting page {i + 1} of search results')

            j = self.api.get(f'/voyager/api/search/blended?count={count}&filters=List()&keywords={keyword}&origin=GLOBAL_SEARCH_HEADER&q=all&queryContext=List(spellCorrectionEnabled-%3Etrue,relatedSearchesEnabled-%3Etrue,kcardTypes-%3EPROFILE%7CCOMPANY%7CJOB_TITLE)&start={start}')
            
            elements = helpers.getNested(j, ['data', 'elements'])

            # find the right types of elements
            for element in elements:
                if self.hitPaywall(element):
                    logging.info(f'Found {onSearchResultIndex} search results')
                    return results

                if element.get('type', '') != 'SEARCH_HITS':
                    continue

                for item in element.get('elements', ''):
                    anyResultsForThisPage = True

                    maximum = searchItem.get('maximumSearchResults', self.options['maximumSearchResults'])
                    maximum = int(maximum)

                    if onSearchResultIndex >= maximum:
                        logging.info(f'Reached search result limit: {onSearchResultIndex}')
                        return results
                    
                    onSearchResultIndex += 1

                    url = item.get('navigationUrl', '')

                    # needed for salesql
                    urn = item.get('targetUrn', '')

                    fields = urn.split(':')

                    if fields:
                        urn = fields[-1]
                    
                    if not url or not urn:
                        continue

                    newItem = {
                        'id': helpers.findBetween(url, '/in/', '/'),
                        'url': url,
                        'urn': urn,
                        'name': helpers.getNested(item, ['title', 'text'])
                    }

                    if not newItem.get('id', ''):
                        logging.debug('Skipping. No id found.')
                        continue

                    if newItem.get('id', '') == 'UNKNOWN':
                        logging.debug('Skipping. Id is UNKNOWN.')
                        continue

                    if self.inDatabase(newItem.get('id', '')):
                        continue

                    results.append(newItem)

            logging.info(f'Found {onSearchResultIndex} search results so far')
            
            if anyResultsForThisPage:
                logging.info('Stopping search. No search results on this page.')
                break
            
            # wait after each page
            seconds = random.randrange(5, 10)

            if '--debug' in sys.argv:
                seconds = 1

            logging.info(f'Waiting {seconds} seconds')
            time.sleep(seconds)

            start += count

        return results

    def hitPaywall(self, element):
        result = False
        
        for extendedElement in get(element, 'extendedElements'):
            type = get(extendedElement, 'type')

            if type == 'PAYWALL' or type == 'BLURRED_HIT':
                logging.error('Stopping search. Hit paywall. This probably means your LinkedIn account reached the commercial use limit. Search for "linkedin commercial use limit" for more information.')
                result = True
                break

        return result


    def inDatabase(self, id):
        result = False
        
        site = helpers.getDomainName(self.api.urlPrefix)
        
        row = self.database.getFirst('result', 'id', f"site = '{site}' and id = '{id}'", '', '')

        if row:
            logging.info(f'Skipping. Already have {id} in the database.')
            result = True

        return result

    def isProfileUrl(self, item):
        return get(item, 'keyword').startswith('https://www.linkedin.com/in/')

    def __init__(self, options, database):
        self.options = options
        self.database = database
        
        self.api = Api('https://www.linkedin.com')

        if self.options.get('proxy', ''):
            self.api.proxies = {
                'http': self.options.get('proxy', ''),
                'https': self.options.get('proxy', '')
            }

        self.salesQl = SalesQl(options, self.api.proxies)

        self.api.setHeadersFromHarFile('user-data/credentials/www.linkedin.com.har', 'linkedin.com/voyager/api/search/blended?')