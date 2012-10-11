from django.db import models

class Ruleset(models.Model):
    name = models.CharField(max_length = 255)

class RuleCard(models.Model):
    ruleset = models.ForeignKey(Ruleset)

    ref_name = models.CharField("Internal reference name", max_length = 20, unique = True)
    public_name = models.CharField("Public name shown to the players (can be blank)", max_length = 50, blank = True)

    description = models.TextField()