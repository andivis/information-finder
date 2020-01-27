import logging
import sys
import lxml.html as lh

if not '../library' in sys.path:
    sys.path.insert(0, '../library')

import helpers

from api import Api
from website import Website

class Google:
    def search(self, query, numberOfResults, urlPrefix=None, acceptAll=False):
        self.captchaOnLastSearch = False
        
        if urlPrefix:
            self.api.urlPrefix = urlPrefix
        else:
            self.api.urlPrefix = 'https://www.google.com'

        parameters = {
            'q': query,
            'hl': 'en'
        }

        page = self.api.get('/search', parameters, False)

        if '--debug' in sys.argv:
            helpers.toFile(page, 'logs/page.html')

        result = self.getSearchResults(page, query, numberOfResults, acceptAll)

        return result

    def getSearchResults(self, page, query, numberOfResults, acceptAll):
        result = ''

        if numberOfResults > 1:
            result = []

        if 'detected unusual traffic from your computer network.' in page:
            logging.error(f'There is a captcha')
            self.captcha = True
            self.captchaOnLastSearch = False
            return result

        if 'google.' in page and 'did not match any documents' in page:
            toDisplay = query.replace('+', ' ')
            logging.debug(f'No search results for {toDisplay}')

            if numberOfResults == 1:
                return 'no results'
            else:
                return ['no results']

        xpaths = [
            ["//a[contains(@class, ' ') and (contains(@href, '/url?')  or contains(@ping, '/url?'))]", 'href'],
            ["//a[contains(@href, '/url?') or contains(@ping, '/url?')]", 'href']
        ]

        document = lh.fromstring(page)

        for xpath in xpaths:
            elements = self.website.getXpathInElement(document, xpath[0], False)

            attribute = xpath[1]

            for element in elements:
                url = element

                if not attribute:
                    url = element.text_content()
                else:
                    url = element.attrib[attribute]

                if self.shouldAvoid(url, acceptAll):
                    continue

                if numberOfResults == 1:
                    result = url
                    break
                else:
                    result.append(url)

                    if len(result) >= numberOfResults:
                        break

            if numberOfResults == 1 and result:
                break
            elif len(result) >= numberOfResults:
                break

        return result

    def shouldAvoid(self, url, acceptAll):
        result = False

        if not url:
            return True

        # avoids internal links
        if not url.startswith('http:') and not url.startswith('https:'):
            return True

        if helpers.substringIsInList(self.avoidPatterns, url):
            return True

        if not acceptAll:
            if helpers.substringIsInList(self.userAvoidPatterns, url):
                return True

            if self.domainMatchesList(url, self.userAvoidDomains):
                return True

            if self.domainMatchesList(url, self.avoidDomains):
                return True

        return result

    def domainMatchesList(self, url, list):
        result = False
        
        domain = helpers.getDomainName(url)

        if domain in list:
            logging.debug(f'Skipping. Domain is {domain}.')
            return True

        for item in list:
            toFind = f'.{item}'
            
            if domain.endswith(toFind):
                logging.debug(f'Skipping. Domain ends with {item}.')
                return True

        return result

    def __init__(self):
        self.api = Api('')
        self.website = Website()
        self.proxies = None
        self.captcha = False
        self.captchaOnLastSearch = False
        self.avoidDomains = []
        self.userAvoidPatterns = []
        self.userAvoidDomains = []