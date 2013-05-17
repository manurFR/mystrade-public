from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.
class MystradeUser(AbstractUser):
    send_notifications = models.BooleanField("Send game notifications", help_text = "Check to receive email alerts about your trades and games")

    bio = models.TextField(blank = True, help_text = "Your presentation text")
    contact = models.TextField(blank = True, help_text = "Your email address will never be publicly displayed. Specify here how other players can reach you (IM, email, etc.)")

    @property
    def name(self):
        if self.first_name and self.last_name:
            return " ".join([self.first_name, self.last_name])
        elif self.last_name:
            return self.last_name
        elif self.first_name:
            return self.first_name
        else:
            return self.username

    def __unicode__(self):
        return self.name

# def create_user_profile(sender, instance, created, **kwargs):
#     # "and not kwargs.get('raw', False)" added to let the test fixtures insert userprofiles without trying to recreate the users
#     # see http://stackoverflow.com/questions/3499791/how-do-i-prevent-fixtures-from-conflicting-with-django-post-save-signal-code
#     if created and not kwargs.get('raw', False):
#         UserProfile.objects.create(user=instance)
#
# post_save.connect(create_user_profile, sender=User)