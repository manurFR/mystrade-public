import datetime
import logging
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.message import BadHeaderError

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

def send_notification_email(subject, message, from_email, to):
    if subject and from_email and to:
        try:
            email = EmailMessage('{}{}'.format(settings.EMAIL_SUBJECT_PREFIX, subject),
                                 message,
                                 from_email = from_email,
                                 to = to,
                                 bcc = settings.EMAIL_BCC_LIST)
            email.send()
        except BadHeaderError as err:
            logger.error("BadHeaderError in send_notification_email('{}', '{}', {}, {})".format(subject, message, from_email, to), exc_info = err)
