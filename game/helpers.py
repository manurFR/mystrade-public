from game.models import RuleInHand, CommodityInHand

def rules_currently_in_hand(game, user):
    return RuleInHand.objects.filter(game = game, player = user, abandon_date__isnull = True).order_by('rulecard__ref_name')

def rules_formerly_in_hand(game, user):
    return RuleInHand.objects.filter(game = game, player = user, abandon_date__isnull = False).order_by('rulecard__ref_name')

def commodities_in_hand(game, user):
    # alphabetical sort to obfuscate the value order of the commodities
    return CommodityInHand.objects.filter(game = game, player = user, nb_cards__gt = 0).order_by('commodity__name')