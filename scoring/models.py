from django.db import models

class Ruleset(models.Model):
    name = models.CharField(max_length = 255)

class RuleCard(models.Model):
    ruleset = models.ForeignKey(Ruleset)

    ref_name = models.CharField("Internal reference name", max_length = 20, unique = True)
    public_name = models.CharField("Public name shown to the players (can be blank)", max_length = 50, blank = True)
    
    mandatory = models.BooleanField("Activate for rules that must always be included in their ruleset")

    description = models.TextField()

    def __unicode__(self):
        return "{} - ({}) {}".format(self.ref_name, self.public_name, self.description)

class Commodity(models.Model):
    ruleset = models.ForeignKey(Ruleset)

    name = models.CharField(max_length = 50)
    value = models.IntegerField("Initial value of the commodity (optional)", null = True)

    def __unicode__(self):
        return self.name