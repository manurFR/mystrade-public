"""
    Rule card scoring resolution for ruleset "Pizzaz!"
"""

def PIZ04(self, scoresheet):
    """ If your pizza contains no Cheese, Don Peppino will curse you but his wife will arrange so
        that you get a bonus of 6 points (damn doctors!).  """
    nb_cheeses = 0
    for sfc in scoresheet.scores_from_commodity:
        if sfc.commodity.category.lower() == 'cheese':
            nb_cheeses += 1
    if nb_cheeses == 0:
        scoresheet.register_score_from_rule(self, 'A pizza with no cheese gives you a bonus of 6 points.', score = 6)