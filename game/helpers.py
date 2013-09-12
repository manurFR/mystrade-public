from game.models import RuleInHand, CommodityInHand

def rules_currently_in_hand(game, user):
    return RuleInHand.objects.filter(game = game, player = user, abandon_date__isnull = True).order_by('rulecard__ref_name')

def rules_formerly_in_hand(game, user, current_rulecards = []):
    """ Exclude former rulecard that are in the hand again now, and remove duplicates """
    return list(RuleInHand.objects.filter(game = game, player = user, abandon_date__isnull = False).
                                exclude(rulecard__in = current_rulecards).distinct('rulecard__ref_name').order_by('rulecard__ref_name'))

def known_rules(game, user):
    """ All the rules known by the user, whether in hand now or before. Duplicates are removed.
        It's actually the union of the two former methods. """
    return RuleInHand.objects.filter(game = game, player = user).distinct('rulecard__ref_name').order_by('rulecard__ref_name')

def commodities_in_hand(game, user):
    # alphabetical sort to obfuscate the value order of the commodities
    return CommodityInHand.objects.filter(game = game, player = user, nb_cards__gt = 0).order_by('commodity__name')