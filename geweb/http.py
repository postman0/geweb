import os
from urllib import parse as urlparse
from cgi import FieldStorage
from http.cookies import SimpleCookie as Cookie
from datetime import datetime, timedelta
import time
from hashlib import md5

from geweb import log
from geweb.template import render

import settings

class Request(object):
    def __init__(self, environ):
        self._headers = { h[5:].lower().replace('_', '-'): val \
                          for h, val in list(environ.items()) \
                          if h.startswith('HTTP_') }

        self.protocol = self.header('x-forwarded-proto') or \
                        environ['wsgi.url_scheme'] or 'http'

        self.host = environ['HTTP_HOST']
        self.method = environ['REQUEST_METHOD'].upper()
        self.path = environ['PATH_INFO']

        self.remote_host = self.header('X-Forwarded-For') or \
                           environ['REMOTE_ADDR']
        try:
            self.remote_port = int(environ['REMOTE_PORT'])
        except (TypeError, ValueError):
            self.remote_port = None

        self.user_agent = environ['HTTP_USER_AGENT']

        self.referer = environ['HTTP_REFERER'] if 'HTTP_REFERER' in environ else ''
        self.is_xhr = self.header('X-Requested-With') == 'XMLHttpRequest'

        self._args = {}
        self._files = {}

        self.query_string = environ['QUERY_STRING']

        self.uri = '%s?%s' % (self.path, self.query_string) \
                              if self.query_string else self.path

        if self.method in ('GET', 'HEAD'):
            self._args = urlparse.parse_qs(environ['QUERY_STRING'])

        elif self.method in ('POST', 'PUT', 'DELETE'):
            ctype = self.header('Content-Type') or environ['CONTENT_TYPE']

            if not ctype or ctype.startswith('application/x-www-form-urlencoded'):
                _buf = environ['wsgi.input'].read()
                self._args = urlparse.parse_qs(_buf)

            elif ctype.startswith('multipart/form-data'):
                form = FieldStorage(fp=environ['wsgi.input'],
                                    environ=environ,
                                    keep_blank_values=True)

                for field in form.list:
                    try:
                        if field.filename:
                            pos = field.filename.rfind('/')
                            if pos == -1:
                                pos = field.filename.rfind('\\')
                            filename = field.filename[pos+1:]
                            try:
                                if not isinstance(self._args[field.name], (list, tuple)):
                                    self._args[field.name] = [self._args[field.name]]
                                self._args[field.name].append(filename)
                            except KeyError:
                                self._args[field.name] = filename

                            tmpfile = md5("%s%s" % (filename, datetime.now().isoformat())).hexdigest()
                            try:
                                upload_dir = settings.upload_dir
                            except AttributeError:
                                upload_dir = '/tmp' # FIXME: get from environment

                            tmpfile_path = os.path.join(upload_dir, tmpfile)
                            try:
                                if not isinstance(self._files[field.name], (list, tuple)):
                                    self._files[field.name] = [self._files[field.name]]
                                self._files[field.name].append(tmpfile_path)
                            except KeyError:
                                self._files[field.name] = tmpfile_path
                            fd = open(tmpfile_path, 'w')
                            while True:
                                b = field.file.read(4096)
                                if b == '':
                                    break
                                fd.write(b)
                            fd.close()
                            log.info('Upload %s: %s' % (field.name, field.filename))
                        else:
                            if not field.value:
                                continue
                            try:
                                if not isinstance(self._args[field.name], (list, tuple)):
                                    self._args[field.name] = [self._args[field.name]]
                                self._args[field.name].append(field.value)
                            except KeyError:
                                self._args[field.name] = field.value
                    except IOError as e:
                        log.error('Cannot write %s: %s' % \
                                  (self._files[field.name], e.strerror))

                del form

        self._cookies = Cookie(self.header('Cookie'))
        for c, v in list(self._cookies.items()):
            log.debug('Cookie: %s=%s' % (c, v.value))

    def __str__(self):
        return '%s %s://%s%s' % (self.method, self.protocol, self.host, self.uri)

    def args(self, arg=None, default=None):
        if arg is None:
            return self._args
        try:
            if len(self._args[arg]) == 1:
                return self._args[arg][0]
            return self._args[arg]
        except KeyError:
            return default

    def files(self, filename):
        try:
            return self._files[filename]
        except KeyError:
            return None

    def header(self, name):
        try:
            return self._headers[name.lower()]
        except KeyError:
            return None

    def headers(self):
        return iter(list(self._headers.items()))

    def cookie(self, name, default=None):
        try:
            return self._cookies[name].value
        except KeyError:
            return default

class Response(object):
    def __init__(self, body='', template=None,
                       code=200, message='OK', mimetype='text/html',
                       redirect=None, headers={}, **kwargs):
        self.body = body
        self.template = template
        self.data = kwargs
        self.code = code
        self.message = message
        self.mimetype = mimetype
        self._headers = headers
        self._cookies = Cookie()

        self._redirect = redirect

    def header(self, name, value):
        self._headers[name] = value

    def set_cookie(self, name, value, domain=None, path=None, expires=None,
                         secure=False, httponly=False):
        self._cookies[name] = value
        if domain:
            self._cookies[name]['domain'] = domain

        if path:
            self._cookies[name]['path'] = path
        if expires:
            self._cookies[name]['expires'] = time.asctime(expires.timetuple())
        if secure:
            self._cookies[name]['secure'] = secure
        if httponly:
            self._cookies[name]['httponly'] = httponly

    def delete_cookie(self, name, domain=None, path=None):
        self.set_cookie(name, '', domain=domain, path=path,
                                  expires=datetime.now()-timedelta(days=30))

    def redirect(self, url=None):
        if url is None:
            return self._redirect
        self._redirect = url


    def render_headers(self):
        if self._redirect:
            self.code = 302
            self.message = 'Moved Temporarily'
            self.header('Location', str(self._redirect))

        status = '%d %s' % (self.code, self.message)

        self.header('Content-Type', self.mimetype)

        headers = []

        for h, val in list(self._headers.items()):
            headers.append((h, val))

        for c in self._cookies:
            headers.append(('Set-Cookie',
                            str(self._cookies[c].output(header='').strip())))

        return status, headers

    def render(self):
        if not self.template:
            return self.body

        self.body = render(self.template, **self.data)
        return self.body

