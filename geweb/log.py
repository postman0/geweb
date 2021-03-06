import logging
from logging.handlers import TimedRotatingFileHandler

import settings

levels = {
    'error': logging.ERROR,
    'warn': logging.WARN,
    'info': logging.INFO,
    'debug': logging.DEBUG
}
level = levels[settings.loglevel.lower()]

try:
    format = settings.logformat
except AttributeError:
    format = '%(asctime)s %(levelname)s: %(message)s'

#_log = logging.getLogger(settings.logger)
_log = None

#info = _log.info
#error = _log.error
#warn = _log.warn
#debug = _log.debug

def init():
    global _log
    if _log:
        return

    logging.basicConfig(format=format, filename=settings.logfile, level=level)
    _log = logging.getLogger(settings.logger)
    if settings.logfile:
        try:
            interval = settings.logrotate
            if isinstance(interval, str):
                when = interval[-1]
                interval = int(interval[:-1])
            else:
                interval = 1
                when = 'midnight'
            try:
                count = settings.logcount
            except AttributeError:
                count = 0
            handler = TimedRotatingFileHandler(settings.logfile,
                                          when=when, interval=interval,
                                          backupCount=count)
            _log.addHandler(handler)
        except AttributeError:
            pass

    global info
    global error
    global warn
    global debug
    info = _log.info
    error = _log.error
    warn = _log.warn
    debug = _log.debug

init()
