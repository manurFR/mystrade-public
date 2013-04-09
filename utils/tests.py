import datetime
from django.core import mail
from django.template import Template
from django.test import TestCase
from django.test.utils import override_settings
from utils import roundTimeToMinute, _send_notification_email

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
        template = Template('my subject\nFirst {{ stuff }}.\nSecond {{ stuff }}.')
        _send_notification_email(template, 'from@test.com', ['to1@test.com', 'to2@test.com'], data = {'stuff': 'line'})

        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[test] my subject', email.subject)
        self.assertEqual('First line.\nSecond line.', email.body)
        self.assertEqual('from@test.com', email.from_email)
        self.assertEqual(['to1@test.com', 'to2@test.com'], email.to)
        self.assertEqual(['bcc@test.com'], email.bcc)

    def test_send_notification_email_without_from_or_to_or_subject_doesnt_send_any_message(self):
        template = Template('\nFirst line.\nSecond line.')
        _send_notification_email(template, 'from@test.com', ['to1@test.com', 'to2@test.com'])
        self.assertEqual(0, len(mail.outbox))

        template = Template('my subject\nFirst line.\nSecond line.')
        _send_notification_email(template, None, ['to1@test.com', 'to2@test.com'])
        self.assertEqual(0, len(mail.outbox))

        _send_notification_email(template, 'from@test.com', None)
        self.assertEqual(0, len(mail.outbox))

        _send_notification_email(template, 'from@test.com', [])
        self.assertEqual(0, len(mail.outbox))

    @override_settings(EMAIL_SUBJECT_PREFIX = '[test] ')
    def test_send_notification_email_a_template_with_only_a_subject_and_no_body_is_sent(self):
        template = Template('my subject')
        _send_notification_email(template, 'from@test.com', ['to1@test.com', 'to2@test.com'])
        self.assertEqual(1, len(mail.outbox))
        email = mail.outbox[0]
        self.assertEqual('[test] my subject', email.subject)
        self.assertEqual('', email.body)
        self.assertEqual('from@test.com', email.from_email)
        self.assertEqual(['to1@test.com', 'to2@test.com'], email.to)


