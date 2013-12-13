import importlib
import types
from django.db import models
from django.db.models.signals import post_init

class Ruleset(models.Model):
    DEFAULT_RULECARDS_PER_PLAYER = 2
    DEFAULT_COMMODITY_CARDS_PER_PLAYER = 10

    name = models.CharField(max_length = 255)
    module = models.CharField("Internal scoring module name", max_length = 20)

    starting_rules = models.PositiveSmallIntegerField("Number of rule cards dealt to each player at the start of the game", default = DEFAULT_RULECARDS_PER_PLAYER)
    starting_commodities = models.PositiveSmallIntegerField("Number of commodity cards dealt to each player at the start of the game", default = DEFAULT_COMMODITY_CARDS_PER_PLAYER)

    description = models.CharField("Description shown to the game master creating a game", max_length = 600)
    intro = models.CharField("Public introduction to the game displayed to all players", max_length = 600, null = True)

    def __unicode__(self):
        return self.name

class RuleCard(models.Model):
    ruleset = models.ForeignKey(Ruleset)

    ref_name = models.CharField("Internal reference name", max_length = 20, unique = True)
    public_name = models.CharField("Public name shown to the players (can be blank)", max_length = 50, blank = True)

    mandatory = models.BooleanField("Activate for rules that must always be included in their ruleset", default = False)

    step = models.IntegerField("Rules will be applied in ascending step during the scoring (can be blank for rules that should not be individually applied)",
        null = True)
    glob = models.BooleanField("Activate for rules that need to know the hands of all players to operate", default = False,
        db_column = 'global') # 'global' is a python reserved word

    description = models.TextField()

    def __unicode__(self):
        return "{0} - ({1}) {2}".format(self.ref_name, self.public_name, self.description)

    def perform(self, scoresheet):
        """ Should be overriden dynamically at post_init (see below). """
        raise NotImplementedError

def bind_the_resolution_method_to_the_rulecard(**kwargs):
    """ The name of the module is found in the ruleset ; the name of the method in this module is the ref_name of the rule card """
    instance = kwargs.get('instance')
    if instance.ref_name:
        try:
            module = importlib.import_module('scoring.' + instance.ruleset.module)
            if hasattr(module, instance.ref_name):
                instance.perform = types.MethodType(getattr(module, instance.ref_name), instance)
        except (ImportError, ValueError):
            pass # so that our tests can feature a dummy or empty module name in Ruleset without failing

post_init.connect(bind_the_resolution_method_to_the_rulecard, RuleCard)

class Commodity(models.Model):
    ruleset = models.ForeignKey(Ruleset)

    name = models.CharField(max_length = 50)
    value = models.IntegerField("Initial value of the commodity (optional)", null = True)
    color = models.CharField("HTML background color to display the cards", max_length = 20, default = "white")
    symbol = models.CharField("Class of the identifying symbol", max_length = 255, null = True)
    category = models.CharField("Optional category to group commodities", max_length = 255, null = True)

    def __unicode__(self):
        return self.name

    def category_acronym(self):
        if self.category:
            return ''.join([word[0:1] for word in self.category.split()]).upper()
