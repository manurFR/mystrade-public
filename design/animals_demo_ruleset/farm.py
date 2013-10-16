import random


def FAR4(self, scoresheet):
    """Each cat cancels one mouse card, which then isn't worth any points."""
    nb_canceled_mice = min(scoresheet.nb_scored_cards("Cat"), scoresheet.nb_scored_cards("Mouse"))

    if nb_canceled_mice == 1:
        scoresheet.register_score_from_rule(self, 'Your cat has eaten a mouse, which will not bring you any points.', -1)
    elif nb_canceled_mice > 1:
        scoresheet.register_score_from_rule(self, 'Your {0} cats have eaten a mouse each, which will not bring you any points.', -nb_canceled_mice)

def FAR5(self, scoresheet):
    """"Each set of a dog card and a sheep card gives a bonus of three points."""
    nb_sets = min(scoresheet.nb_scored_cards("Dog"), scoresheet.nb_scored_cards("Sheep"))

    if nb_sets:
        scoresheet.register_score_from_rule(self,
                                            '{0} set(s) of a dog and a sheep bring you {0}x3 = {1} points.'.format(nb_sets, nb_sets * 3), nb_sets * 3)

def FAR6(self, scoresheet):
    """There's no accomodation for more than six animals in your farm. If you hand in more than six cards at the end of the game,
       some cards will be removed randomly until there are only six left."""
    total_scored_cards = 0
    present_animals = []
    for sfc in scoresheet.scores_from_commodity:
        if sfc.nb_scored_cards > 0:
            present_animals.append(sfc.name)
            total_scored_cards += sfc.nb_scored_cards
    if total_scored_cards > 6:
        detail = 'Your farm cannot accomodate more than 6 animals. Since you handed in {0} card(s), {1} have been discarded:'.format(total_scored_cards, total_scored_cards - 6)
        discarded = {}
        while total_scored_cards > 6:
            selected_animal = random.choice(present_animals)
            scoresheet.set_nb_scored_cards(selected_animal, nb_scored_cards = scoresheet.nb_scored_cards(selected_animal) - 1)
            if selected_animal not in discarded:
                discarded[selected_animal] = 1
            else:
                discarded[selected_animal] += 1
            if scoresheet.nb_scored_cards(selected_animal) == 0:
                present_animals.remove(selected_animal)
            total_scored_cards -= 1
        for index, color in enumerate(discarded.iterkeys()):
            detail += '{0} {1} card'.format(discarded[color], color) + ('s' if discarded[color] > 1 else '')
            detail += ', ' if index < (len(discarded) - 1) else '.'
        scoresheet.register_score_from_rule(self, detail, is_random = True)