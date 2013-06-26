from django.test import TestCase
from model_mommy import mommy
from game.models import Game
from ruleset.models import Ruleset, RuleCard
from scoring.tests.commons import _prepare_scoresheet, assertRuleNotApplied, assertRuleApplied

class HaggleTest(TestCase):
    def setUp(self):
        self.game = mommy.make(Game, ruleset = Ruleset.objects.get(id = 1))

    def test_haggle_HAG04(self):
        """If a player has more than three white cards, all of his/her white cards lose their value."""
        rulecard = RuleCard.objects.get(ref_name = 'HAG04')
        scoresheet = _prepare_scoresheet(self.game, "p1", white = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(15, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", white = 4)
        rulecard.perform(scoresheet)
        self.assertEqual(0, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(4) Since there are 4 white cards (more than three), their value is set to zero.')

    def test_haggle_HAG05(self):
        """"A player can score only as many as orange cards as he/she has blue cards."""
        rulecard = RuleCard.objects.get(ref_name = 'HAG05')
        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 3, orange = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(18, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 2, orange = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(12, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(5) Since there are 2 blue card(s), only 2 orange card(s) score.')

    def test_haggle_HAG06(self):
        """If a player has five or more blue cards, 10 points are deducted from every other player's score."""
        rulecard = RuleCard.objects.get(ref_name = 'HAG06')
        player1 = _prepare_scoresheet(self.game, "p1", blue = 5)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 6, orange = 1)
        player3 = _prepare_scoresheet(self.game, "p3", yellow = 4, blue = 2, white = 4)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(10-10, scoresheets[0].total_score)
        assertRuleApplied(scoresheets[0], rulecard, '(6) Since p2 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(16-10, scoresheets[1].total_score)
        assertRuleApplied(scoresheets[1], rulecard, '(6) Since p1 has 5 blue cards, 10 points are deducted.', -10)
        self.assertEqual(28-20, scoresheets[2].total_score)
        assertRuleApplied(scoresheets[2], rulecard, '(6) Since p1 has 5 blue cards, 10 points are deducted.', -10)
        assertRuleApplied(scoresheets[2], rulecard, '(6) Since p2 has 6 blue cards, 10 points are deducted.', -10)

    def test_haggle_HAG07(self):
        """A set of three red cards protects you from one set of five blue cards."""
        rulecardHAG06 = RuleCard.objects.get(ref_name = 'HAG06')
        rulecardHAG07 = RuleCard.objects.get(ref_name = 'HAG07')
        player1 = _prepare_scoresheet(self.game, "p1", blue = 5)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 6, red = 3)
        player3 = _prepare_scoresheet(self.game, "p3", yellow = 2, blue = 2, red = 6)
        rulecardHAG06.perform([player1, player2, player3])
        rulecardHAG07.perform(player1)
        rulecardHAG07.perform(player2)
        rulecardHAG07.perform(player3)
        self.assertEqual(10-10, player1.total_score)
        assertRuleApplied(player1, rulecardHAG06, '(6) Since p2 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(21, player2.total_score)
        assertRuleApplied(player2, rulecardHAG06, '(6) Since p1 has 5 blue cards, 10 points should have been deducted...')
        assertRuleApplied(player2, rulecardHAG07, '(7) ...but a set of three red cards cancels that penalty.')
        self.assertEqual(24, player3.total_score)
        assertRuleApplied(player3, rulecardHAG06, '(6) Since p1 has 5 blue cards, 10 points should have been deducted...')
        assertRuleApplied(player3, rulecardHAG06, '(6) Since p2 has 6 blue cards, 10 points should have been deducted...')
        assertRuleApplied(player3, rulecardHAG07, '(7) ...but a set of three red cards cancels that penalty.', times = 2)

    def test_haggle_HAG08(self):
        """The player with the most yellow cards gets a bonus of the number of those cards squared. 
           If two or more players tie for most yellow, the bonus is calculated instead for the player 
           with the next highest number of yellows.
        """
        rulecard = RuleCard.objects.get(ref_name = 'HAG08')
        player1 = _prepare_scoresheet(self.game, "p1", yellow = 5)
        player2 = _prepare_scoresheet(self.game, "p2", yellow = 3, red = 3)
        player3 = _prepare_scoresheet(self.game, "p3", orange = 2)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(5+(5**2), scoresheets[0].total_score)
        assertRuleApplied(scoresheets[0], rulecard, '(8) Having the most yellow cards (5 cards) gives a bonus of 5x5 points.', 5**2)
        self.assertEqual(12, scoresheets[1].total_score)
        self.assertEqual(8, scoresheets[2].total_score)

    def test_haggle_HAG08_tie(self):
        rulecard = RuleCard.objects.get(ref_name = 'HAG08')
        player1 = _prepare_scoresheet(self.game, "p1", yellow = 3, blue = 1)
        player2 = _prepare_scoresheet(self.game, "p2", yellow = 3, red = 3)
        player3 = _prepare_scoresheet(self.game, "p3", yellow = 2, orange = 2)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(5, scoresheets[0].total_score)
        assertRuleNotApplied(scoresheets[0], rulecard)
        self.assertEqual(12, scoresheets[1].total_score)
        assertRuleNotApplied(scoresheets[1], rulecard)
        self.assertEqual(10+(2**2), scoresheets[2].total_score)
        assertRuleApplied(scoresheets[2], rulecard, '(8) Having the most yellow cards (2 cards) gives a bonus of 2x2 points.', 2**2)

    def test_haggle_HAG09(self):
        """If a player hands in seven or more cards of the same color, 
           for each of these colors 10 points are deducted from his/her score.
        """
        rulecard = RuleCard.objects.get(ref_name = 'HAG09')
        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 6, blue = 3, white = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(17, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 7, blue = 3, white = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(8, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(9) Since 7 yellow cards where submitted (seven or more), 10 points are deducted.', -10)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 7, blue = 8, white = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(8, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(9) Since 7 yellow cards where submitted (seven or more), 10 points are deducted.', -10)
        assertRuleApplied(scoresheet, rulecard, '(9) Since 8 blue cards where submitted (seven or more), 10 points are deducted.', -10)

    def test_haggle_HAG10(self):
        """Each set of five different colors gives a bonus of 10 points."""
        rulecard = RuleCard.objects.get(ref_name = 'HAG10')
        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 4, blue = 3, red = 2, orange = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(20, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 4, blue = 3, red = 2, orange = 1, white = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(35, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(10) A set of five different colors gives a bonus of 10 points.', 10)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 4, blue = 3, red = 2, orange = 3, white = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(63, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(10) A set of five different colors gives a bonus of 10 points.', 10, times = 2)

    def test_haggle_HAG11(self):
        """If a \"pyramid\" is handed in with no other cards, the value of the hand is doubled. 
           A pyramid consists of four cards of one color, three cards of a second color, 
           two cards of a third, and one card of a fourth color.
        """
        rulecard = RuleCard.objects.get(ref_name = 'HAG11')
        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 4, blue = 3, red = 2, orange = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(20*2, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(11) A pyramid of 4 yellow cards, 3 blue cards, 2 red cards, 1 orange card and no other card doubles the score.', 20)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 1, blue = 2, orange = 3, white = 4)
        rulecard.perform(scoresheet)
        self.assertEqual(37*2, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(11) A pyramid of 4 white cards, 3 orange cards, 2 blue cards, 1 yellow card and no other card doubles the score.', 37)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 1, blue = 2, red = 1, orange = 3, white = 4)
        rulecard.perform(scoresheet)
        self.assertEqual(40, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

    def test_haggle_HAG12(self):
        """The player with the most red cards double their value.
           In case of a tie, no player collects the extra value.
        """
        rulecard = RuleCard.objects.get(ref_name = 'HAG12')
        player1 = _prepare_scoresheet(self.game, "p1", yellow = 3, red = 4)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 1, red = 3)
        player3 = _prepare_scoresheet(self.game, "p3", yellow = 2, orange = 2)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(15+12, player1.total_score)
        assertRuleApplied(player1, rulecard, '(12) Having the most red cards (4 cards) doubles their value.', 12)
        self.assertEqual(11, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(10, player3.total_score)
        assertRuleNotApplied(player3, rulecard)

    def test_haggle_HAG12_tie(self):
        rulecard = RuleCard.objects.get(ref_name = 'HAG12')
        player1 = _prepare_scoresheet(self.game, "p1", yellow = 3, red = 3)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 1, red = 3)
        player3 = _prepare_scoresheet(self.game, "p3", yellow = 2, orange = 2)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(12, player1.total_score)
        assertRuleNotApplied(player1, rulecard)
        self.assertEqual(11, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(10, player3.total_score)
        assertRuleNotApplied(player3, rulecard)

    def test_haggle_HAG13(self):
        """Each set of two yellow cards doubles the value of one white card."""
        rulecard = RuleCard.objects.get(ref_name = 'HAG13')
        scoresheet = _prepare_scoresheet(self.game, "p1", white = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(15, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 1, white = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(16, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 2, white = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(17+5, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(13) A pair of yellow cards doubles the value of one white card.', 5)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 6, white = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(21+3*5, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(13) A pair of yellow cards doubles the value of one white card.', 5, times = 3)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 8, white = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(23+3*5, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(13) A pair of yellow cards doubles the value of one white card.', 5, times = 3)

    def test_haggle_HAG14(self):
        """Each set of three blue cards quadruples the value of one orange card."""
        rulecard = RuleCard.objects.get(ref_name = 'HAG14')
        scoresheet = _prepare_scoresheet(self.game, "p1", orange = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(8, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 2, orange = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(12, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 3, orange = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(14+12, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(14) A set of three blue cards quadruples the value of one orange card.', 12)

        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 6, orange = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(20+24, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(14) A set of three blue cards quadruples the value of one orange card.', 12, times = 2)

        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 9, orange = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(26+24, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, '(14) A set of three blue cards quadruples the value of one orange card.', 12, times = 2)

    def test_haggle_HAG15(self):
        """No more than thirteen cards in a hand can be scored. 
           If more are handed in, the excess will be removed at random.
        """
        rulecard = RuleCard.objects.get(ref_name = 'HAG15')
        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 5, blue = 5, red = 5, orange = 5, white = 15)
        rulecard.perform(scoresheet)
        total_scored_cards = sum(sfc.nb_scored_cards for sfc in scoresheet._scores_from_commodity)
        self.assertEqual(13, total_scored_cards)
        self.assertEqual(1, len(scoresheet.scores_from_rule))
        sfr = scoresheet.scores_from_rule[0]
        self.assertEqual('HAG15', sfr.rulecard.ref_name)
        self.assertTrue(sfr.detail.startswith('(15) Since 35 cards had to be scored, 22 have been discarded'))