from django.test import TestCase
from model_mommy import mommy
from game.models import Game
from ruleset.models import Ruleset, RuleCard
from scoring.tests.commons import _prepare_scoresheet, assertRuleNotApplied, assertRuleApplied


class PizzazTest(TestCase):
    def setUp(self):
        self.game = mommy.make(Game, ruleset = Ruleset.objects.get(id = 3))

    def test_PIZ04(self):
        """If your pizza contains no Cheese, Don Peppino will curse you but his wife will arrange so that
            you get a bonus of 6 points (damn doctors!)."""
        rulecard = RuleCard.objects.get(ref_name = 'PIZ04')
        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 1, mushrooms = 3, parmesan = 1) # ham: 3 pts, mushrooms: 2 pts, parmesan: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(12, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 1, mushrooms = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(15, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A pizza with no cheese gives you a bonus of 6 points.', score = 6)

    def test_PIZ06(self):
        """Don Peppino likes his pizza with no more than 10 toppings (cards). Each added topping removes 5 points."""
        rulecard = RuleCard.objects.get(ref_name = 'PIZ06')
        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 6, mushrooms = 5) # ham: 3 pts, mushrooms: 2 pts
        rulecard.perform(scoresheet)
        self.assertEqual(6*3 + 5*2 - 5, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Since your pizza had 11 toppings (more than 10), you lose 5 points.', score = -5)

    def test_PIZ07(self):
        """ If your pizza has more Vegetable [V] cards than Meat [M], Fish & Seafood [F&S] and Cheese [C] cards combined,
            there is a bonus of 12 points for you."""
        rulecard = RuleCard.objects.get(ref_name = 'PIZ07')
        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 2, mushrooms = 5, parmesan = 2) # ham: 3 pts, mushrooms: 2 pts, parmesan: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(2*3 + 5*2 + 2*3 + 12, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'There is more Vegetable cards in your pizza than Meat, Fish & Seafood and Cheese cards combined. You earn a bonus of 12 points.',
                          score = 12)

        scoresheet = _prepare_scoresheet(self.game, "p1", ham = 2, mushrooms = 3, parmesan = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(2*3 + 3*2 + 3, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

    def test_PIZ08(self):
        """ Don Peppino dislikes the following toppings, unless paired with the appropriate ingredient:
            peppers, pineapple and ham. Absolutely no points can be earned from those. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ08')
        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, parmesan = 2, ham = 1, pineapple = 1, peppers = 1) # mushrooms: 2 pts, parmesan: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(3*2 + 2*3 + 0 + 0 + 0, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Don Peppino absolutely dislikes ham, pineapple and peppers. Those cards give you no points.')

        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, parmesan = 2) # mushrooms: 2 pts, parmesan: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(3*2 + 2*3, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

    def test_PIZ09(self):
        """ One garlic card makes Don Peppino tolerate all the toppings he usually dislikes. But beware!
            More than one garlic and he'll revert to his usual distastes. """
        rulecardPIZ08 = RuleCard.objects.get(ref_name = 'PIZ08')
        rulecardPIZ09 = RuleCard.objects.get(ref_name = 'PIZ09')
        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, pineapple = 1, garlic = 1) # mushrooms: 2 pts, pineapple: 2 pts, garlic: 0 pts
        rulecardPIZ08.perform(scoresheet)
        rulecardPIZ09.perform(scoresheet)
        self.assertEqual(3*2 + 2, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecardPIZ08, 'Don Peppino absolutely dislikes ham, pineapple and peppers. Those cards should give you no points...')
        assertRuleApplied(scoresheet, rulecardPIZ09, '...but since your pizza contains one garlic, he tolerates them. Phew!')

        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, pineapple = 1, garlic = 2) # mushrooms: 2 pts, pineapple: 2 pts, garlic: 0 pts
        rulecardPIZ08.perform(scoresheet)
        rulecardPIZ09.perform(scoresheet)
        self.assertEqual(3*2 + 0, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecardPIZ08, 'Don Peppino absolutely dislikes ham, pineapple and peppers. Those cards give you no points.')
        assertRuleNotApplied(scoresheet, rulecardPIZ09)

    def test_PIZ10(self):
        """ Each topping with at least a double ration (two cards or more) is worth 4 points more. """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ10')
        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 2, ham = 1) # mushrooms: 2 pts, ham: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(2*2 + 3 + 4, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A double ration of Mushrooms gives you a bonus of 4 points.', score = 4)
        for sfr in scoresheet.scores_from_rule:
            if sfr.rulecard == rulecard and 'Ham' in sfr.detail:
                self.fail("The PIZ10 bonus should not have been given for only one Ham.")

        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 4, ham = 2) # mushrooms: 2 pts, ham: 3 pts
        rulecard.perform(scoresheet)
        self.assertEqual(4*2 + 2*3 + 4 + 4, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A double ration of Mushrooms gives you a bonus of 4 points.', score = 4)
        assertRuleApplied(scoresheet, rulecard, 'A double ration of Ham gives you a bonus of 4 points.', score = 4)
        number_of_bonus_for_mushrooms = 0
        for sfr in scoresheet.scores_from_rule:
            if sfr.rulecard == rulecard and 'Mushrooms' in sfr.detail:
                number_of_bonus_for_mushrooms += 1
        self.assertEqual(1, number_of_bonus_for_mushrooms, "The PIZ10 bonus for a double ration of mushrooms should have been given only once (actual: {0}x).".format(number_of_bonus_for_mushrooms))

    def test_PIZ11(self):
        """ A pizza with at least three different toppings whose name begins with the same letter brings
            a bonus of 8 points. (Different letters will add up.) """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ11')
        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 1, mussels = 1, mozzarella = 1,
                                                          parmesan = 1, pineapple = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(2 + 3 + 3 + 3 + 2 + 8, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '3 different toppings starting by the letter M (Mozzarella, Mushrooms, Mussels) give you a bonus of 8 points.', score = 8)

        scoresheet = _prepare_scoresheet(self.game, "p1", mushrooms = 3, mussels = 1, mozzarella = 1, # mushrooms: 2 pts, mussels: 3 pts, mozza: 3 pts
                                                          parmesan = 1, pepperoni = 2, pineapple = 1, prosciutto = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(3*2 + 3 + 3 + 3 + 2*3 + 2 + 3 + 8 + 8, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '3 different toppings starting by the letter M (Mozzarella, Mushrooms, Mussels) give you a bonus of 8 points.', score = 8)
        assertRuleApplied(scoresheet, rulecard, '4 different toppings starting by the letter P (Parmesan, Pepperoni, Pineapple, Prosciutto) give you a bonus of 8 points.', score = 8)

    def test_PIZ12(self):
        """ The cook whose pizza has the smallest number of different toppings will earn a bonus of 12 points.
            In case of a tie, each player will earn the bonus. (Multiple copies of the same topping count for one.) """
        rulecard = RuleCard.objects.get(ref_name = 'PIZ12')
        player1 = _prepare_scoresheet(self.game, "p1", mushrooms = 5, ham = 1)
        player2 = _prepare_scoresheet(self.game, "p2", mushrooms = 1, mussels = 1, mozzarella = 2)
        player3 = _prepare_scoresheet(self.game, "p3", parmesan = 1, pepperoni = 2, pineapple = 1, prosciutto = 1)
        rulecard.perform([player1, player2, player3])
        self.assertEqual(5*2 + 3 + 12, player1.total_score)
        assertRuleApplied(player1, rulecard, 'You have the smallest number of different toppings (2 toppings) of all the players. You earn a bonus of 12 points.', 12)
        self.assertEqual(2 + 3 + 2*3, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(3 + 2*3 + 2 + 3, player3.total_score)
        assertRuleNotApplied(player3, rulecard)

    def test_PIZ12_tie(self):
        rulecard = RuleCard.objects.get(ref_name = 'PIZ12')
        player1 = _prepare_scoresheet(self.game, "p1", mushrooms = 5, ham = 1)
        player2 = _prepare_scoresheet(self.game, "p2", mushrooms = 1, mussels = 1, mozzarella = 2)
        player3 = _prepare_scoresheet(self.game, "p3", pepperoni = 2, pineapple = 1)
        rulecard.perform([player1, player2, player3])
        self.assertEqual(5*2 + 3 + 12, player1.total_score)
        assertRuleApplied(player1, rulecard, 'You have the smallest number of different toppings (2 toppings) of all the players. You earn a bonus of 12 points.', 12)
        self.assertEqual(2 + 3 + 2*3, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(2*3 + 2 + 12, player3.total_score)
        assertRuleApplied(player3, rulecard, 'You have the smallest number of different toppings (2 toppings) of all the players. You earn a bonus of 12 points.', 12)
