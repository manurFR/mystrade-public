import datetime
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from utils import roundTimeToMinute
from utils import send_notification_email

class UtilsTest(TestCase):
    def test_roundTimeToMinute(self):
        self.assertEqual(datetime.datetime(2012, 11, 9, 14, 45), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 51), 15))
        self.assertEqual(datetime.datetime(2012, 11, 9, 14, 45), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 43), 15))
        self.assertEqual(datetime.datetime(2012, 11, 9, 15, 00), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 57), 15))
        self.assertEqual(datetime.datetime(2012, 11, 9, 14, 00, 0, 0), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 7, 18, 324), 15))
        self.assertEqual(datetime.datetime(2012, 11, 9, 14, 15), 
                         roundTimeToMinute(datetime.datetime(2012, 11, 9, 14, 8), 15))

    @override_settings(EMAIL_SUBJECT_PREFIX = '[test] ', EMAIL_BCC_LIST = ['bcc@test.com'])
    def test_send_notification_email(self):
        send_notification_email('my subject', 'First line.\nSecond line.', 'from@test.com', ['to1@test.com', 'to2@test.com'])

        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[test] my subject', email.subject)
        self.assertEqual('First line.\nSecond line.', email.body)
        self.assertEqual('from@test.com', email.from_email)
        self.assertEqual(['to1@test.com', 'to2@test.com'], email.to)
        self.assertEqual(['bcc@test.com'], email.bcc)

    def test_send_notification_email_without_from_or_to_or_subject_doesnt_send_any_message(self):
        send_notification_email('', 'First line.', 'from@test.com', ['to1@test.com', 'to2@test.com'])
        self.assertEqual(0, len(mail.outbox))

        send_notification_email('my subject', 'First line.', None, ['to1@test.com', 'to2@test.com'])
        self.assertEqual(0, len(mail.outbox))

        send_notification_email('my subject', 'First line.', 'from@test.com', None)
        self.assertEqual(0, len(mail.outbox))

        send_notification_email('my subject', 'First line.', 'from@test.com', [])
        self.assertEqual(0, len(mail.outbox))


