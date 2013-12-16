import pytz
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.query import QuerySet

class MystradeUserManager(BaseUserManager):
    def get_queryset(self):
        return MystradeUserQuerySet(self.model, using=self._db)

class MystradeUser(AbstractUser):
    send_notifications = models.BooleanField("Send game notifications", default = True, help_text = "Check to receive email alerts about your trades and games")

    timezone = models.CharField("Your timezone", max_length= 50, choices = [(tz, tz) for tz in pytz.common_timezones], help_text = "Required. For the display of dates.")

    bio = models.TextField(blank = True, help_text = "Your presentation text (optional)")
    contact = models.TextField(blank = True, help_text = "Your email address will never be publicly displayed. Specify here how other players can reach you (IM, email, etc.) (optional)")

    FUNKY_ORANGE = 'funky_orange'
    BLUISH_FIESTA = 'bluish_fiesta'
    ANTIQUE_BOUTIQUE = 'antique_boutique'
    # the first dict in this list will be the default
    PALETTES = [ {'key': FUNKY_ORANGE,   'name': 'Funky Orange',   'note': '(default palette)'},
                 {'key': BLUISH_FIESTA,  'name': 'Bluish Fiesta',  'note': 'by djey & vinu'},
                 {'key': ANTIQUE_BOUTIQUE, 'name': 'Antique Boutique', 'note': 'by manur & djey'}]
    PALETTE_CHOICES = [(dict['key'], dict['name']) for dict in PALETTES]
    DEFAULT_PALETTE = PALETTES[0]['key']
    palette = models.CharField(max_length = 50, choices = PALETTE_CHOICES, default = DEFAULT_PALETTE)

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

    objects = MystradeUserManager()

class MystradeUserQuerySet(QuerySet):
    """ There is no easy way a queryset can be sorted by a field not present in the database, such as the name @property above.
    The only (and inelegant) way seems to inject SQL code thanks to the extra() modifier, and "order by" the calculated SQL column.
    It violates the DRY principle as the algorithm is duplicated in the name @property above and in the SQL below, but again
    there seems not to be another way in Django 1.5.
    (see http://stackoverflow.com/questions/1652577/django-ordering-queryset-by-a-calculated-field)
    """
    def order_by_full_name(self):
        return self.extra(select = {'name_sort': "lower(CASE WHEN (first_name <> '' AND last_name <> '') THEN first_name || ' ' || last_name "
                                                 "           WHEN last_name <> '' THEN last_name "
                                                 "           WHEN first_name <> '' THEN first_name "
                                                 "           ELSE username"
                                                 "      END)"}).extra(order_by = ['name_sort'])

# def create_user_profile(sender, instance, created, **kwargs):
#     # "and not kwargs.get('raw', False)" added to let the test fixtures insert userprofiles without trying to recreate the users
#     # see http://stackoverflow.com/questions/3499791/how-do-i-prevent-fixtures-from-conflicting-with-django-post-save-signal-code
#     if created and not kwargs.get('raw', False):
#         UserProfile.objects.create(user=instance)
#
# post_save.connect(create_user_profile, sender=User)
