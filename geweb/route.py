from geweb import log
from geweb.exceptions import NotFound

try:
    import re2 as re
except ImportError:
    import re

import settings

urls_list = []

for app in settings.apps:
    urls = __import__("%s.urls" % app, globals(), locals(), 'urls', -1)
    for regex, view in urls.urls:
        urls_list.append((re.compile(regex), view))

def route(path):
    if not urls_list:
        return welcome()

    for regex, view in urls_list:
        m = re.match(regex, path)
        if m:
            return view(**m.groupdict())

    raise NotFound

def welcome():
    from geweb.template import render
    return render('geweb/welcome.html')

