from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User)

    send_notifications = models.BooleanField("Send game notifications", help_text = "Check to receive email alerts about your trades and games")
    
    bio = models.TextField(blank = True, help_text = "Your presentation text")
    contact = models.TextField(blank = True, help_text = "Your email address will never be publicly displayed. Specify here how other players can reach you (IM, email, etc.)")
    
    @property
    def name(self):
        if self.user.first_name and self.user.last_name:
            return " ".join([self.user.first_name, self.user.last_name])
        elif self.user.last_name:
            return self.user.last_name
        elif self.user.first_name:
            return self.user.first_name
        else:
            return self.user.username
        
    def __unicode__(self):
        return self.name

def create_user_profile(sender, instance, created, **kwargs):
    # "and not kwargs.get('raw', False)" added to let the test fixtures insert userprofiles without trying to recreate the users
    # see http://stackoverflow.com/questions/3499791/how-do-i-prevent-fixtures-from-conflicting-with-django-post-save-signal-code
    if created and not kwargs.get('raw', False):
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)