import sys
import os
import logging
import datetime
import json

from ..library import helpers

from ..library.helpers import get
from ..library.api import Api

class Internet:
    def getRandomProxy(self):
        if not self.proxies:
            if os.path.exists('proxies.csv'):
                self.proxies = helpers.getCsvFileAsDictionary('proxies.csv')
            elif self.proxyListUrl:            
                self.proxies = self.getProxiesFromApi()

            if not self.proxies:
                logging.info('No proxies found')

        if not self.proxies:
            return None

        import random

        item = random.choice(self.proxies)

        url = item.get('url', '')
        port = item.get('port', '')
        userName = item.get('username', '')
        password = item.get('password', '')

        proxy = f'http://{userName}:{password}@{url}:{port}'

        if not userName or not password:
            proxy = f'http://{url}:{port}'

        proxies = {
            'http': proxy,
            'https': proxy
        }

        logging.debug(f'Using proxy http://{url}:{port}')

        return proxies

    def getProxiesFromApi(self):
        result = None

        externalApi = Api('')
        apiKey = externalApi.getPlain(self.proxyListUrl)

        if not apiKey:
            return result

        api = Api('https://api.myprivateproxy.net')

        # get allowed ip's
        allowedIps = api.get(f'/v1/fetchAuthIP/{apiKey}')

        if not allowedIps:
            return result

        ipInfoApi = Api('')

        currentIp = ipInfoApi.get('https://ipinfo.io/json')

        if not currentIp or not currentIp.get('ip', ''):
            logging.error('Can\'t find current ip address')
            return result

        currentIp = currentIp.get('ip', '')

        # check if it's already allowed
        if not currentIp in allowedIps:
            toKeep = 3
            newAllowedIps = allowedIps[0:toKeep]
            newAllowedIps.append(currentIp)

            # add current ip to allowed ip's
            response = api.post(f'/v1/updateAuthIP/{apiKey}', json.dumps(newAllowedIps))

            if response.get('result', '') != 'Success':
                logging.error('Failed to update allowed ip addresses')

        response = api.get(f'/v1/fetchProxies/json/full/{apiKey}')

        if not response:
            return result

        result = []

        for item in response:
            newItem = {
                'url': item.get('proxy_ip', ''),
                'port': item.get('proxy_port', ''),
                'username': item.get('username', ''),
                'password': item.get('password', ''),
            }

            result.append(newItem)

        return result

    def __init__(self, options):
        self.options = options

        self.proxies = None
        self.proxyListUrl = get(self.options, 'proxyListUrl')