import datetime
import logging
from django.conf import settings
from django.contrib.auth.models import User
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

def send_notification_email(template_name, recipients, data = None):
    """ Templates : the first line must be the subject, all subsequent lines the body. No line(s) of separation should be added.
            A template_name 'myfile' will need a template named 'templates/notification/myfile.txt'.

        Recipients : one can pass one user to send the notification to, or a list of users.
           Each user can be given as a Django User instance or as an email address (a string).
           Django User instances will have their userprofile checked to verify the person accepts to receive email notifications,
            and those who don't will be automatically suppressed from the recipients list.
     """
    try:
        _send_notification_email(get_template('notification/{}.txt'.format(template_name)), recipients, data)
    except BadHeaderError as err:
        logger.error("BadHeaderError in send_notification_email({}, {}, {})".format(template_name, recipients, data), exc_info = err)

def _send_notification_email(template, recipients, data = None):
    if recipients:
        if type(recipients) is not list:
            recipients = [recipients]

        to = []
        for email_or_user in recipients:
            if isinstance(email_or_user, basestring):
                to.append(email_or_user)
            elif email_or_user.get_profile().send_notifications: # check if the recipient agree to receive email notifications
                to.append(email_or_user.email)
        if len(to) == 0: # no one left to receive notifications
            return

        message = template.render(Context(data)).splitlines()
        subject = message[0]
        body = '\n'.join(message[1:])
        if subject:
            email = EmailMessage('{}{}'.format(settings.EMAIL_SUBJECT_PREFIX, subject),
                                 body,
                                 from_email = settings.EMAIL_MYSTRADE,
                                 to = to,
                                 bcc = [settings.EMAIL_MYSTRADE])
            email.send()

