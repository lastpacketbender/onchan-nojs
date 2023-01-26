import logging
from datetime import datetime
from functools import wraps
from bottle import request, response

from config import config

logger = logging.getLogger(config['branding'])
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(f"{config['branding']}.log")
formatter = logging.Formatter('%(msg)s')
file_handler.setLevel(logging.DEBUG if config['server']['debug'] else logging.INFO)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def log_to_logger(fn):
    '''
    Wrap a Bottle request so that a log line is emitted after it's handled.
    (This decorator can be extended to take the desired logger as a param.)
    '''
    @wraps(fn)
    def _log_to_logger(*args, **kwargs):
        request_time = datetime.now()
        actual_response = fn(*args, **kwargs)
        # modify this to log exactly what you need:
        logger.info('%s %s %s %s %s' % (request.remote_addr,
                                        request_time,
                                        request.method,
                                        request.url,
                                        response.status))
        return actual_response
    return _log_to_logger

