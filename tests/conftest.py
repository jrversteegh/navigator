import os
from os import path
import logging
import sys
import time
import errno
from datetime import datetime
import json

import pytest


import __main__ as main

scriptdir = os.path.dirname(os.path.realpath(__file__))
_module_path = scriptdir + '/..'
sys.path.insert(0, _module_path)
from navigator._classes import JSONEncoder, Http

_log = logging.getLogger('test')


def log_line():
    _log.info('==============================================')


def file_exists(filename):
    return os.path.exists(filename)


def file_age(filename):
    return time.time() - os.path.getmtime(filename)


@pytest.fixture
def log_value(request):
    def logger(value):
        _log.debug(f'***** VALUE FROM TEST FUNCTION: {request.node.name}')
        _log.debug(json.dumps(value, indent=2, cls=JSONEncoder))
    return logger


@pytest.fixture(scope='module')
def log():
    def logger(*args, **kwargs):
        _log.debug(*args, **kwargs)
    return logger


@pytest.fixture
async def http():
    yield Http.instance()
    await Http.destroy()



logdir = scriptdir + '/logs'
try:
    os.mkdir(logdir)
except (OSError, FileExistsError) as e:
    if e.errno != errno.EEXIST:
        print(e.errno, errno.EEXIST)
        raise e
except Exception as e:
    print(e)

_logname = f'{logdir}/{path.splitext(path.basename(main.__file__))[0]}.log'

logging.basicConfig(
    filename=_logname,
    level=logging.DEBUG,
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s'
)

os.chdir(scriptdir)
resultsdir = scriptdir + '/results'
try:
    os.mkdir(resultsdir)
except (OSError, FileExistsError) as e:
    if e.errno != errno.EEXIST:
        print(e.errno, errno.EEXIST)
        raise e
except Exception as e:
    print(e)

log_line()
_log.info('Started logging: %s' % str(datetime.now()))
log_line()
