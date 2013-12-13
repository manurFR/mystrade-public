import datetime
import logging
import re
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail.message import BadHeaderError
from django.template import Context
from django.template.loader import get_template
from django.utils.timezone import now, utc

logger = logging.getLogger(__name__)

def roundTimeToMinute(dt = None, roundToMinutes = 1):
    """ Round a datetime object to any time laps in minutes
         dt : datetime.datetime object, default now.
         roundTo : Closest number of minutes to round to, default 1 minute.
    """
    if dt is None:
        dt = now()
    dt = dt.replace(second = 0, microsecond = 0)
    if dt.minute % roundToMinutes <= roundToMinutes / 2:
        return dt - datetime.timedelta(minutes = dt.minute % roundToMinutes)
    else:
        return dt + datetime.timedelta(minutes = roundToMinutes - dt.minute % roundToMinutes)

def get_timestamp(dt = now()):
    """ Returns the number of seconds since Jan. 1st, 1970, midnight """
    return int((dt - utc.localize(datetime.datetime(1970, 1, 1, 0, 0, 0))).total_seconds())

def send_notification_email(template_name, recipients, data = None):
    """ Templates : the first line must be the subject, all subsequent lines the body. No line(s) of separation should be added.
            A template_name 'myfile' will need a template named 'templates/notification/myfile.txt'.

        Recipients : one can pass one user to send the notification to, or a list of users.
           Each user can be given as a MystradeUser instance or as an email address (a string).
           MystradeUser instances will have their profile checked to verify the person accepts to receive email notifications,
            and those who don't will be automatically suppressed from the recipients list.
     """
    try:
        _send_notification_email(get_template('notification/{0}.txt'.format(template_name)), recipients, data)
    except BadHeaderError as err:
        logger.error("BadHeaderError in send_notification_email({0}, {1}, {2})".format(template_name, recipients, data), exc_info = err)

def _send_notification_email(template, recipients, data = None):
    if recipients:
        if type(recipients) is not list:
            recipients = [recipients]

        to = []
        for email_or_user in recipients:
            if isinstance(email_or_user, basestring):
                to.append(email_or_user)
            elif email_or_user.send_notifications: # check if the recipient agree to receive email notifications
                to.append(email_or_user.email)
        if len(to) == 0: # no one left to receive notifications
            return

        message = template.render(Context(data))
        lines = message.splitlines()
        subject = lines[0]
        body = _limit_line_breaks('\n'.join(lines[1:]))

        if subject:
            email = EmailMessage(u'{0}{1}'.format(settings.EMAIL_SUBJECT_PREFIX, subject),
                                 body,
                                 from_email = settings.EMAIL_MYSTRADE,
                                 to = to,
                                 bcc = [settings.EMAIL_MYSTRADE])
            email.send()

def _limit_line_breaks(text):
    """ Blocks of 3 or more line breaks are crushed to 2 line breaks """
    return '\n\n'.join(re.split('\\n{3,}', text))