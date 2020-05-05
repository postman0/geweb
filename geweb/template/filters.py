from jinja2 import environmentfilter
import urllib.request, urllib.parse, urllib.error
from pprint import pformat

@environmentfilter
def strftime(env, time, format):
    """
    Datetime format filter.
    
    Usage:
    {{ dt|strftime("%Y-%m-%d %H:%M:%s") }}
    """
    if not time:
        return ''
    return time.strftime(format)

@environmentfilter
def urlencode(env, s):
    return urllib.parse.quote_plus(s.encode('utf-8'))

@environmentfilter
def pprint(env, s):
    return pformat(s)

filters = {
    'strftime': strftime,
    'urlencode': urlencode,
    'pprint': pprint,
}
