from django.db import models
import importlib

class Ruleset(models.Model):
    name = models.CharField(max_length = 255)
    module = models.CharField("Internal scoring module name", max_length = 20)
    
    def __unicode__(self):
        return self.name

class RuleCard(models.Model):
    ruleset = models.ForeignKey(Ruleset)

    ref_name = models.CharField("Internal reference name", max_length = 20, unique = True)
    public_name = models.CharField("Public name shown to the players (can be blank)", max_length = 50, blank = True)
    
    mandatory = models.BooleanField("Activate for rules that must always be included in their ruleset")
    
    step = models.IntegerField("Rules will be applied in ascending step during the scoring (can be blank for rules that should not be individually applied)",
                               null = True)
    glob = models.BooleanField("Activate for rules that need to know the hands of all players to operate",
                               db_column = 'global')

    description = models.TextField()

    def __unicode__(self):
        return "{} - ({}) {}".format(self.ref_name, self.public_name, self.description)

    def perform(self, players):
        if self.ref_name:
            module = importlib.import_module('scoring.' + self.ruleset.module)
            func = getattr(module, self.ref_name)
            if self.glob:
                func(players)
            else:
                for scoresheet in players:
                    func(scoresheet)

class Commodity(models.Model):
    ruleset = models.ForeignKey(Ruleset)

    name = models.CharField(max_length = 50)
    value = models.IntegerField("Initial value of the commodity (optional)", null = True)

    def __unicode__(self):
        return self.name