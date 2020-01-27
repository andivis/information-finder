import sys
import os
import io
import datetime
import logging
import traceback

def get(item, key):
    if not item:
        return ''

    result = item.get(key, '')

    # to avoid null values
    if not result:
        result = ''

    return result


def handleException(exception, prefix='Something went wrong'):
    logging.error(f'{prefix}: {exception}')
    logging.debug(traceback.format_exc())


def getFile(fileName, encoding=None):
    if not os.path.isfile(fileName):
        return ""

    f = open(fileName, "r", encoding='utf-8')

    return f.read()


def getBinaryFile(fileName):
    if not os.path.isfile(fileName):
        return ""

    f = open(fileName, "rb")

    return f.read()


def getJsonFile(fileName):
    result = {}

    try:
        import json

        file = getFile(fileName)
        result = json.loads(file)
    except Exception as e:
        handleException(e)

    return result


def getLines(fileName):
    if not os.path.isfile(fileName):
        return []

    with open(fileName) as f:
        return f.readlines()


def toFile(s, fileName):
    with io.open(fileName, "w", encoding="utf-8") as text_file:
        print(s, file=text_file)


def toBinaryFile(s, fileName):
    with io.open(fileName, "wb") as file:
        file.write(s)


def appendToFile(s, fileName):
    with io.open(fileName, "a", encoding="utf-8") as text_file:
        print(s, file=text_file)


def removeFile(fileName):
    try:
        if os.path.exists(fileName):
            os.remove(fileName)
    except Exception as e:
        handleException(e)


def substringIsInList(list, s):
    result = False

    for item in list:
        if item in s:
            result = True
            break

    return result


def numbersOnly(s):
    return ''.join(filter(lambda x: x.isdigit(), s))


def lettersAndNumbersOnly(s):
    return ''.join(filter(lambda x: x.isdigit() or x.isalpha(), s))


def lettersNumbersAndSpacesOnly(s):
    return ''.join(filter(lambda x: x.isdigit() or x.isalpha() or x == ' ', s))


def lettersOnly(s):
    return ''.join(filter(lambda x: x.isalpha(), s))


def lettersAndSpacesOnly(s):
    return ''.join(filter(lambda x: x.isalpha() or x == ' ', s))


def fixedDecimals(n, numberOfDecimalPlaces):
    result = ''

    try:
        formatString = f'{{:.{numberOfDecimalPlaces}f}}'

        result = formatString.format(n)
    except Exception as e:
        handleException(e)

    return result


def findBetween(s, first, last):
    start = 0

    if first and first in s:
        start = s.index(first) + len(first)

    end = len(s)

    if last and last in s[start:]:
        end = s.index(last, start)

    return s[start:end]


def replaceBetweenAll(s, first, last, replacement):
    import re

    first = re.escape(first)
    last = re.escape(last)

    # the question mark makes it non-greedy
    return re.sub(f'{first}.*?{last}', replacement, s)


def getLastAfterSplit(s, splitter):
    result = ''

    fields = s.split(splitter)

    if len(fields) > 0:
        result = fields[-1]

    return result


def squeezeWhitespace(s):
    import re

    return re.sub(r'\s\s+', ' ', s)

def addBeforeCapitalLetters(s, character=' '):
    result = ''

    for c in s:
        if c.isupper():
            result += character

        result += c

    return result

def firstLetterUppercase(s):
    result = ''

    for i, c in enumerate(s):
        if i == 0:
            result += c.upper()
        else:
            result += c

    return result

def getNested(j, keys):
    result = ''

    try:
        element = j

        i = 0

        for key in keys:
            if not element:
                break

            if not key in element:
                break

            element = element[key]

            if i == len(keys) - 1:
                return element

            i += 1
    except:
        return ''

    return result


def stringToFloatingPoint(s):
    result = 0.0

    temporary = ''

    for c in s:
        if c.isdigit() or c == '.':
            temporary += c

    try:
        result = float(temporary)
    except:
        result = 0.0

    return result


def getCsvFile(fileName, asDictionary=True):
    result = []

    import csv

    encodings = ['utf8', 'latin-1']

    for encoding in encodings:
        try:
            with open(fileName, encoding=encoding) as inputFile:
                if asDictionary:
                    csvReader = csv.DictReader(inputFile, delimiter=',')
                else:
                    csvReader = csv.reader(inputFile, delimiter=',')
                    # skip the headers
                    next(csvReader, None)

                for row in csvReader:
                    if len(row) == 0:
                        continue

                    result.append(row)

                return result
        except Exception as e:
            # start again
            result = []
            logging.debug(e)

    return result


def appendCsvFile(list, fileName):
    import csv

    with open(fileName, "a", newline='\n', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file, delimiter=',')
        writer.writerow(list)


# d1 takes priority
def mergeDictionaries(d1, d2):
    result = d1.copy()

    # only overwrite if value is empty or absent
    for key in d2:
        if not get(d1, key):
            result[key] = d2[key]

    return result


def makeDirectory(directoryName):
    import pathlib

    pathlib.Path(directoryName).mkdir(parents=True, exist_ok=True)


def run(command):
    try:
        import subprocess

        subprocess.run(command)
    except Exception as e:
        handleException(e)


def getStandardOutput(command):
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE)
    except Exception as e:
        handleException(e)
        return ''

    return result.stdout.decode('utf-8')


def runWithInput(command, input):
    try:
        result = subprocess.run(command, input=input, encoding='ascii')
    except Exception as e:
        handleException(e)
        return None

    return result


def setOptions(fileName, options, sectionName='main'):
    try:
        if '--optionsFile' in sys.argv:
            index = sys.argv.index('--optionsFile')
            if index < len(sys.argv) - 1:
                fileName = sys.argv[index + 1]

        import configparser

        optionsReader = configparser.ConfigParser(interpolation=None)
        optionsReader.optionxform = str
        optionsReader.read(fileName)

        for section in optionsReader.sections():
            if sectionName and section != sectionName:
                continue

            if not sectionName:
                options[section] = {}

            for key in optionsReader[section]:
                # default value is digit?
                if isinstance(options.get(key, ''), int):
                    if not sectionName:
                        options[section][key] = int(optionsReader[section][key])
                    else:
                        options[key] = int(optionsReader[section][key])
                else:
                    if not sectionName:
                        options[section][key] = optionsReader[section][key]
                    else:
                        options[key] = optionsReader[section][key]
    except Exception as e:
        handleException(e)


def getParameterIfExists(self, existingValue, parameterName):
    result = existingValue

    if not parameterName in sys.argv:
        return

    result = helpers.getParameter(parameterName, False)

    return result


def getParameter(name, required, default=''):
    result = default

    try:
        if name in sys.argv:
            index = sys.argv.index(name)
            if index < len(sys.argv) - 1:
                result = sys.argv[index + 1]

    except Exception as e:
        handleException(e)

    if required and not result:
        logging.error(f'Parameter {name} is required')
        input("Press enter to exit...")
        exit()

    return result


def timeAgo(time=False):
    """
    Get a datetime object or a int() Epoch timestamp and return a
    pretty string like 'an hour ago', 'Yesterday', '3 months ago',
    'just now', etc
    """
    diff = 0

    now = datetime.datetime.now()
    if type(time) is float:
        diff = now - datetime.datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = now - now
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff / 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff / 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff / 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff / 30) + " months ago"
    return str(day_diff / 365) + " years ago"


def addToStartup(fileName):
    import getpass

    userName = getpass.getuser()

    directoryName = os.path.abspath(fileName)
    directoryName = os.path.dirname(directoryName)

    batFileName = fileNameOnly(fileName, False) + '.bat'

    # uses same file name twice
    startupScriptFileName = os.path.join(directoryName, batFileName)

    batPath = r'C:\Users\%s\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup' % userName

    with open(batPath + '\\' + batFileName, 'w+') as file:
        file.write(os.path.splitdrive(directoryName)[0] + '\n')
        file.write('cd ' + directoryName + '\n')
        file.write(r'start /min %s' % startupScriptFileName)


def setUpLogging(fileNameSuffix='', useDatabase=False):
    import logging
    import logging.handlers

    threadIndicator = ''

    if fileNameSuffix:
        threadIndicator = '[' + fileNameSuffix.replace('-', '') + '] '

    logger = logging.getLogger()
    formatter = logging.Formatter(f'{threadIndicator}[%(asctime)s] [%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
    logger.setLevel(logging.DEBUG)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    logFileName = os.path.join('logs', f'log{fileNameSuffix}.txt')

    makeDirectory(os.path.dirname(logFileName))

    if '--debug' in sys.argv:
        # clear the file
        open(logFileName, 'w').close()

    file_handler = logging.handlers.RotatingFileHandler(logFileName, maxBytes=5 * 1000 * 1000, backupCount=1, encoding='utf-8')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    if useDatabase:
        from sqlite_handler import SQLiteHandler

        sqliteHandler = SQLiteHandler('resources/database.sqlite')
        sqliteHandler.setLevel(logging.INFO)

        logger.addHandler(sqliteHandler)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

def getDateStringSecondsAgo(secondsAgo, useGmTime):
    now = None

    if useGmTime:
        now = datetime.datetime.utcnow()
    else:
        now = datetime.datetime.now()

    result = now - datetime.timedelta(seconds=secondsAgo)

    return str(result)


def wait(seconds):
    import datetime
    import time
    
    seconds = int(seconds)

    if '--debug' in sys.argv:
        seconds = 3

    started = datetime.datetime.utcnow()

    logging.info(f'Waiting {seconds} seconds')

    while True:
        elapsed = datetime.datetime.utcnow() - started
        elapsed = elapsed.total_seconds()

        remaining = seconds - elapsed

        if remaining <= 0:
            break

        remaining = '{0:.1f}'.format(remaining)

        if seconds > 5:
            print(f'{remaining} seconds remaining             ', end='\r')

        time.sleep(0.05)

    if seconds > 5:
        print('')

def waitUntil(date):
    import datetime
    import time
    
    difference = date - datetime.datetime.utcnow()

    seconds = difference.total_seconds()
    hours = difference.total_seconds() / 3600

    logging.info(f'Waiting until {date} GMT ({hours} from now)')

    if '--debug' in sys.argv:
        seconds = 3

    time.sleep(seconds)

def getDomainName(url):
    result = ''

    from urllib.parse import urlparse

    parsed_uri = urlparse(url)
    location = '{uri.netloc}'.format(uri=parsed_uri)

    result = location

    fields = location.split('.')

    if len(fields) >= 3 and fields[0] == 'www':
        result = '.'.join(fields[1:])

    return result


def fileNameOnly(fileName, includeExtension=True):
    result = os.path.basename(fileName)

    if not includeExtension:
        result = os.path.splitext(result)[0]

    return result


def listFiles(directory, includeDirectories=True):
    result = []

    root = directory

    for dirname, dirnames, filenames in os.walk(root):
        # print path to all subdirectories first.
        if includeDirectories:
            for subdirname in dirnames:
                result.append(os.path.join(dirname, subdirname))

        # print path to all filenames.
        for filename in filenames:
            result.append(os.path.join(dirname, filename))

    return result


def obj_to_string(obj, extra='    '):
    return str(obj.__class__) + '\n' + '\n'.join((extra + (str(item) + ' = ' + (obj_to_string(obj.__dict__[item], extra + '    ') if hasattr(obj.__dict__[item], '__dict__') else str(obj.__dict__[item]))) for item in sorted(obj.__dict__)))
