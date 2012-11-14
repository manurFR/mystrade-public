from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save

# Create your models here.
class UserProfile(models.Model):
    user = models.OneToOneField(User)
    
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
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)