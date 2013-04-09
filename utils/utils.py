import datetime
import logging
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.message import BadHeaderError
from django.template import Context
from django.template.loader import get_template

logger = logging.getLogger(__name__)

def roundTimeToMinute(dt = None, roundToMinutes = 1):
    """ Round a datetime object to any time laps in minutes
         dt : datetime.datetime object, default now.
         roundTo : Closest number of minutes to round to, default 1 minute.
    """
    if dt is None:
        dt = datetime.datetime.now()
    dt = dt.replace(second = 0, microsecond = 0)
    if dt.minute % roundToMinutes <= roundToMinutes / 2:
        return dt - datetime.timedelta(minutes = dt.minute % roundToMinutes)
    else:
        return dt + datetime.timedelta(minutes = roundToMinutes - dt.minute % roundToMinutes)

def send_notification_email(template_name, from_email, to, data = None):
    """ Templates : the first line must be the subjects, all subsequent lines the body. No line(s) of separation should be added.
            A template_name 'myfile' will need a template named 'templates/notification/myfile.txt'.
     """
    _send_notification_email(get_template('notification/{}.txt'.format(template_name)), from_email, to, data)

def _send_notification_email(template, from_email, to, data = None):
    if from_email and to:
        message = template.render(Context(data)).splitlines()
        subject = message[0]
        body = '\n'.join(message[1:])
        if subject:
            try:
                email = EmailMessage('{}{}'.format(settings.EMAIL_SUBJECT_PREFIX, subject),
                                     body,
                                     from_email = from_email,
                                     to = to,
                                     bcc = settings.EMAIL_BCC_LIST)
                email.send()
            except BadHeaderError as err:
                logger.error("BadHeaderError in send_notification_email('{}', '{}', {}, {})".format(subject, message, from_email, to), exc_info = err)
