from unittest.util import safe_repr
from django.contrib.auth import get_user_model
from model_mommy import mommy
from game.models import GamePlayer, CommodityInHand
from ruleset.models import Commodity
from scoring.card_scoring import Scoresheet

#############################################################################
##                           Common Utils                                  ##
#############################################################################

def _prepare_hand(game, player, **commodities):
    try:
        p = get_user_model().objects.get(username = player)
        gameplayer = GamePlayer.objects.get(game = game, player = p)
        CommodityInHand.objects.filter(game = game, player = p).delete()
    except get_user_model().DoesNotExist:
        p = mommy.make(get_user_model(), username = player)
        gameplayer = mommy.make(GamePlayer, game = game, player = p)

    for name, nb_submitted_cards in commodities.iteritems():
        commodity = Commodity.objects.get(ruleset = game.ruleset, name__istartswith = name)
        mommy.make(CommodityInHand, game = game, player = p, commodity = commodity,
                   nb_cards = nb_submitted_cards, nb_submitted_cards = nb_submitted_cards)
    return gameplayer

def _prepare_scoresheet(game, player, **commodities):
    return Scoresheet(_prepare_hand(game, player, **commodities))

def assertRuleApplied(scoresheet, rulecard, detail = '', score = None, times = 1):
    rulecards = ['{0} ({1}) - {2}{3}'.format(sfr.rulecard.public_name, sfr.rulecard.ref_name, sfr.detail, " / score= " + str(sfr.score) if sfr.score else '')
                 for sfr in scoresheet.scores_from_rule]
    for _i in range(times):
        for sfr in scoresheet.scores_from_rule:
            if sfr.rulecard == rulecard and sfr.detail == detail and sfr.score == score:
                break
        else:
            rulecards.insert(0, 'Actual scores from rules:')
            raise AssertionError(rulecards)

def assertRuleNotApplied(scoresheet, rulecard):
    applied_rules = [sfr.rulecard for sfr in scoresheet.scores_from_rule]
    if rulecard in applied_rules:
        raise AssertionError('{0} unexpectedly found in {1}'.format(safe_repr(rulecard), safe_repr(applied_rules)))

