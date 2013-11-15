from django.core.exceptions import PermissionDenied
from game.models import RuleInHand, CommodityInHand
from trade.models import Offer


def rules_in_hand(game, user, currently_in_hand = True):
    return RuleInHand.objects.filter(game = game, player = user, abandon_date__isnull = currently_in_hand).order_by('rulecard__ref_name')

def rules_formerly_in_hand(game, user):
    return rules_in_hand(game, user, currently_in_hand = False)

def known_rules(game, user):
    """ All the rules known by the user, whether in hand now or before. Duplicates are removed.
        It's actually the union of the two former methods. """
    return RuleInHand.objects.filter(game = game, player = user).distinct('rulecard__ref_name').order_by('rulecard__ref_name')

def commodities_in_hand(game, user):
    # alphabetical sort to obfuscate the value order of the commodities
    return CommodityInHand.objects.filter(game = game, player = user, nb_cards__gt = 0).order_by('commodity__name')

def free_informations_until_now(game, user):
    free_informations = []
    for offer in Offer.objects.filter(free_information__isnull = False, trade_responded__game = game,
                                      trade_responded__initiator = user, trade_responded__status = 'ACCEPTED'):
        free_informations.append({'offerer': offer.trade_responded.responder,
                                  'date': offer.trade_responded.closing_date,
                                  'free_information': offer.free_information})

    for offer in Offer.objects.filter(free_information__isnull = False, trade_initiated__game = game,
                                      trade_initiated__responder = user, trade_initiated__status = 'ACCEPTED'):
        free_informations.append({'offerer': offer.trade_initiated.initiator,
                                  'date': offer.trade_initiated.closing_date,
                                  'free_information': offer.free_information})

    return free_informations

def _check_game_access_or_PermissionDenied(game, user, players = None):
    """ Checks if a user has the rights to access a game.
         He/She must be a player in this game OR have super access, ie. be the game master or be an admin (staff) that is not a player in this game.
        Giving a list of the game players as input argument is optional: it may prevents a second fetching from the database if the caller already
         has the list.

        In case the user doesn't have access to the game, a PermissionDenied exception (HTTP status code 403) is raised.

        Otherwise, this function returns a boolean holding whether the user was granted permission thanks to having super access for this game or not.
    """
    if players is None:
        players = game.players.all()
    super_access = game.has_super_access(user)
    if user not in players and not super_access:
        raise PermissionDenied
    return super_access