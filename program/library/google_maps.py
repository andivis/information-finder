import sys
import logging
import time

from . import helpers

from .helpers import get
from .api import Api

class GoogleMaps:
    def search(self, searchItem):
        results = []

        keyword = searchItem.get('keyword', '')

        places = self.getPages(searchItem, f'/maps/api/place/textsearch/json?query={keyword}&key={self.apiKey}')

        names = []

        for item in places:
            if self.inDatabase(item.get('place_id', '')):
                continue

            details = self.getPlaceDetails(item)
            
            phone = details.get('international_phone_number', '')

            name = item.get('name', '')

            # to avoid duplicates
            if name in names:
                continue
            
            names.append(name)                

            if not phone:
                continue

            result = {
                'id': item.get('place_id', ''),
                'site': helpers.getDomainName(self.url),
                'name': name,
                'email': '',
                'phone': phone,
                'address': get(item, 'formatted_address'),
                'url': details.get('website', ''),
                'google maps url': 'https://www.google.com/maps/place/?q=place_id:' + item.get('place_id', '')
            }

            results.append(result)

            logging.info(f'Site: maps.google.com. Keyword: {keyword}. Results: {len(results)}. Name: {name}. Phone: {phone}.')
            
            maximum = searchItem.get('maximumNewResults', self.options['maximumNewResults'])
            maximum = int(maximum)

            if len(results) >= maximum:
                logging.debug(f'Stopping for this keyword. Got {len(results)} new results.')
                break

        return results

    def getPlaceDetails(self, place):
        placeId = place.get('place_id', '')

        j = self.api.get(f'/maps/api/place/details/json?place_id={placeId}&fields=name,international_phone_number,website&key={self.apiKey}')

        self.handleError(j)

        return j.get('result', {})

    def getPages(self, searchItem, url):
        results = []
        
        nextPageToken = ''
        
        for i in range(0, 1000):
            logging.info(f'Getting page {i + 1} of Google Maps search results')

            nextPageTokenPart = ''
    
            if i > 0:
                nextPageTokenPart = f'&pagetoken={nextPageToken}'

            for attempt in range(0, 10):
                j = self.api.get(f'{url}{nextPageTokenPart}')

                # might need to wait for next page to be ready
                if j.get('status', '') == 'INVALID_REQUEST':
                    time.sleep(5)
                    continue
                
                break

            self.handleError(j)
    
            nextPageToken = j.get('next_page_token', '')

            results += j.get('results', [])

            logging.info(f'Found {len(results)} search results so far')

            maximum = searchItem.get('maximumSearchResults', self.options['maximumSearchResults'])
            maximum = int(maximum)

            if len(results) >= maximum:
                logging.info(f'Reached search result limit: {maximum}')
                break

            if not nextPageToken:
                # no more results
                break

            # give time for next page to get ready
            time.sleep(1)

        return results
    
    def inDatabase(self, id):
        result = False
        
        site = 'maps.google.com'
        
        row = self.database.getFirst('result', 'id', f"site = '{site}' and id = '{id}'", '', '')

        if row:
            logging.info(f'Skipping. Already have {id} in the database.')
            result = True

        return result
    
    def handleError(self, j):
        if j.get('status', '') != 'OK' and j.get('status', '') != 'ZERO_RESULTS':
            error = j.get('error_message', '')
            logging.error(f'Google Maps: {error}')

    def __init__(self, options, credentials, database):
        self.options = options
        self.database = database

        self.apiKey = helpers.getNested(credentials, ['google maps', 'apiKey'])

        if not self.apiKey:
            logging.error('You must put your Google Maps API key into credentials.ini')
            input("Press enter to exit...")
            exit()
        
        self.url = 'https://maps.google.com'
        self.api = Api('https://maps.googleapis.com')
        self.api.headers = {}