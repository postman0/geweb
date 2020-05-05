import os
import smtplib
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.audio import MIMEAudio
from email.mime.base import MIMEBase

from geweb import log

import settings

def mail(to, body, subject='', template=None, html=False, \
         attachments=None, **context):
    """
    E-mail sender.

    Required settings: smtp_host, smtp_port, smtp_from, smtp_auth_required.
    If smtp_auth_required is set to true, you should also define
    smtp_login and smtp_password.
    """
    smtp = smtplib.SMTP(settings.smtp_host, port=settings.smtp_port)
    smtp.ehlo()

    if settings.smtp_auth_required:
        smtp.starttls()
        smtp.ehlo()
        smtp.login(settings.smtp_login, settings.smtp_password)
    else:
        smtp.ehlo()

    if attachments:
        msg = MIMEMultipart()

        for path in attachments:
            try:
                fp = open(path, 'rb')
                data = fp.read()
                fp.close()
            except IOError as e:
                log.error('Attach %s: %s' % (path, e.message))
                continue

            ctype, encoding = mimetypes.guess_type(path)
            if ctype is None or encoding is not None:
                ctype = 'application/octet-stream'
            maintype, subtype = ctype.split('/', 1)

            if maintype == 'text':
                part = MIMEText(data)
            elif maintype == 'image':
                part = MIMEImage(data)
            elif maintype == 'audio':
                part = MIMEAudio(data)
            else:
                part = MIMEBase(maintype, subtype)
                part.set_payload(data)

            part.add_header('Content-Disposition', 'attachment',
                            filename=os.path.basename(path))
            msg.attach(part)

    elif html:
        if isinstance(body, str):
            body = body.encode('utf-8')
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(body, 'html', 'utf-8'))

    else:
        msg = MIMEText(body)

    msg['Subject'] = subject
    msg['From'] = settings.smtp_from
    msg['To'] = to

    result = smtp.sendmail(settings.smtp_from, to, msg.as_string())

    if result:
        log.error('SMTP', result)

    smtp.quit()

