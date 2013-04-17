from game.models import RuleInHand

def rules_currently_in_hand(game, user):
    return RuleInHand.objects.filter(game = game, player = user, abandon_date__isnull = True).order_by('rulecard__ref_name')