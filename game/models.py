from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now
from scoring.models import Ruleset, RuleCard

class Game(models.Model):
    ruleset = models.ForeignKey(Ruleset)
    master = models.ForeignKey(User, related_name = 'mastering_games_set')

    rules = models.ManyToManyField(RuleCard)
    players = models.ManyToManyField(User, related_name = 'playing_games_set')

    # it's important to use django.utils.timezone.now() which is an aware date
    creation_date = models.DateTimeField(default = now())
    start_date = models.DateTimeField(default = now())
    end_date = models.DateTimeField()

    def __unicode__(self):
        return "{} by {} with {} players and {} rules [{} -> {}]".format(self.ruleset.name, self.master.get_profile().name,
                len(self.players.all()), len(self.rules.all()), self.start_date, self.end_date)