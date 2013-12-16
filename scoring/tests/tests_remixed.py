from django.test import TestCase
from model_mommy import mommy
from game.models import Game
from ruleset.models import Ruleset, RuleCard
from scoring.card_scoring import tally_scores
from scoring.tests.commons import _prepare_scoresheet, assertRuleNotApplied, assertRuleApplied, _prepare_hand

class RemixedHaggleTest(TestCase):
    fixtures = ['initial_data.json']

    def setUp(self):
        self.game = mommy.make(Game, ruleset = Ruleset.objects.get(id = 2))

    def test_RMX04(self):
        """If a player has a combined number of yellow and green cards strictly higher than five cards,
            all of his/her green cards lose their value."""
        rulecard = RuleCard.objects.get(ref_name = 'RMX04')
        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 2, green = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(23, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 3, green = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(12, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Since the combined number of yellow cards (3) and green cards (3) is 6 (higher than five), the value of green cards is set to zero.')

    def test_RMX05(self):
        """"A player can score only as many yellow cards as he/she has pink cards."""
        rulecard = RuleCard.objects.get(ref_name = 'RMX05')
        scoresheet = _prepare_scoresheet(self.game, "p1", pink = 3, yellow = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(21, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", pink = 2, yellow = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(14, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Since there are 2 pink card(s), only 2 yellow card(s) score.')

    def test_RMX06(self):
        """If a player has five or more blue cards, 10 points are deducted from every other player's score."""
        rulecard = RuleCard.objects.get(ref_name = 'RMX06')
        player1 = _prepare_scoresheet(self.game, "p1", blue = 5, green = 1)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 6, yellow = 2)
        player3 = _prepare_scoresheet(self.game, "p3", blue = 2, white = 4, pink = 3, green = 1)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(10-10, scoresheets[0].total_score)
        assertRuleApplied(scoresheets[0], rulecard, 'Since p2 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(14-10, scoresheets[1].total_score)
        assertRuleApplied(scoresheets[1], rulecard, 'Since p1 has 5 blue cards, 10 points are deducted.', -10)
        self.assertEqual(24-20, scoresheets[2].total_score)
        assertRuleApplied(scoresheets[2], rulecard, 'Since p1 has 5 blue cards, 10 points are deducted.', -10)
        assertRuleApplied(scoresheets[2], rulecard, 'Since p2 has 6 blue cards, 10 points are deducted.', -10)

    def test_RMX07(self):
        """A set of three yellow cards protects you from one set of five blue cards."""
        rulecardRMX06 = RuleCard.objects.get(ref_name = 'RMX06')
        rulecardRMX07 = RuleCard.objects.get(ref_name = 'RMX07')
        player1 = _prepare_scoresheet(self.game, "p1", blue = 5, green = 1)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 6, yellow = 3)
        player3 = _prepare_scoresheet(self.game, "p3", blue = 2, yellow = 6)
        rulecardRMX06.perform([player1, player2, player3])
        rulecardRMX07.perform(player1)
        rulecardRMX07.perform(player2)
        rulecardRMX07.perform(player3)
        self.assertEqual(10-10, player1.total_score)
        assertRuleApplied(player1, rulecardRMX06, 'Since p2 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(18, player2.total_score)
        assertRuleApplied(player2, rulecardRMX06, 'Since p1 has 5 blue cards, 10 points should have been deducted...')
        assertRuleApplied(player2, rulecardRMX07, '...but a set of three yellow cards cancels that penalty.')
        self.assertEqual(26, player3.total_score)
        assertRuleApplied(player3, rulecardRMX06, 'Since p1 has 5 blue cards, 10 points should have been deducted...')
        assertRuleApplied(player3, rulecardRMX06, 'Since p2 has 6 blue cards, 10 points should have been deducted...')
        assertRuleApplied(player3, rulecardRMX07, '...but a set of three yellow cards cancels that penalty.', times = 2)

    def test_RMX08(self):
        """Each set of five different colors gives a bonus of 8 points."""
        rulecard = RuleCard.objects.get(ref_name = 'RMX08')
        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 4, white = 3, pink = 2, yellow = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(20, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 4, white = 3, pink = 2, yellow = 1, green = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(33, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A set of five different colors gives a bonus of 8 points.', 8)

        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 4, white = 3, pink = 2, yellow = 3, green = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(59, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A set of five different colors gives a bonus of 8 points.', 8, times = 2)

    def test_RMX09(self):
        """The player with the most white cards triples their value.
            In case of a tie, no player collects the extra value.
        """
        rulecard = RuleCard.objects.get(ref_name = 'RMX09')
        player1 = _prepare_scoresheet(self.game, "p1", blue = 3, white = 4)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 1, white = 3)
        player3 = _prepare_scoresheet(self.game, "p3", yellow = 2, green = 1)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(11+16, player1.total_score)
        assertRuleApplied(player1, rulecard, 'Having the most white cards (4 cards) triples their value.', 16)
        self.assertEqual(7, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(13, player3.total_score)
        assertRuleNotApplied(player3, rulecard)

    def test_RMX09_tie(self):
        rulecard = RuleCard.objects.get(ref_name = 'RMX09')
        player1 = _prepare_scoresheet(self.game, "p1", blue = 3, white = 3)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 1, white = 3)
        player3 = _prepare_scoresheet(self.game, "p3", yellow = 2, green = 2)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(9, player1.total_score)
        assertRuleNotApplied(player1, rulecard)
        self.assertEqual(7, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(18, player3.total_score)
        assertRuleNotApplied(player3, rulecard)

    def test_RMX10(self):
        """If the total of the basic values of all the cards handed in by a player is higher than 35 points,
            cards are removed at random until the total becomes less or equal than 35 points.
            Only the basic values of the cards are considered, before any other rule is applied.
        """
        rulecard = RuleCard.objects.get(ref_name = 'RMX10')
        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 4, white = 4, pink = 4, yellow = 4, green = 4)
        self.assertEqual(4+8+12+16+20, scoresheet.total_score)
        rulecard.perform(scoresheet)
        self.assertLess(scoresheet.total_score, 36)
        self.assertEqual(1, len(scoresheet.scores_from_rule))
        sfr = scoresheet.scores_from_rule[0]
        self.assertEqual('RMX10', sfr.rulecard.ref_name)
        self.assertTrue(sfr.detail.startswith('Since the total of the basic values of your cards was 60 points (more than 35)'))

    def test_RMX11(self):
        """If a player hands in seven or more cards of the same color,
            10 points are deducted from his/her score for each of these colors.
        """
        rulecard = RuleCard.objects.get(ref_name = 'RMX11')
        scoresheet = _prepare_scoresheet(self.game, "p1", white = 6, pink = 3, green = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(26, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", white = 7, pink = 3, green = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(28-10, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Since 7 white cards where submitted (seven or more), 10 points are deducted.', -10)

        scoresheet = _prepare_scoresheet(self.game, "p1", white = 7, pink = 8, green = 1)
        rulecard.perform(scoresheet)
        self.assertEqual(43-20, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'Since 7 white cards where submitted (seven or more), 10 points are deducted.', -10)
        assertRuleApplied(scoresheet, rulecard, 'Since 8 pink cards where submitted (seven or more), 10 points are deducted.', -10)

    def test_RMX12(self):
        """The player with the most blue cards doubles the value of his/her pink cards.
            In case of a tie, no player collects the extra value.
        """
        rulecard = RuleCard.objects.get(ref_name = 'RMX12')
        player1 = _prepare_scoresheet(self.game, "p1", blue = 3, pink = 4)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 1, pink = 3)
        player3 = _prepare_scoresheet(self.game, "p3", yellow = 2, green = 2)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(15+12, player1.total_score)
        assertRuleApplied(player1, rulecard, 'Having the most blue cards (3 cards) doubles the value of pink cards.', 12)
        self.assertEqual(10, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(18, player3.total_score)
        assertRuleNotApplied(player3, rulecard)

    def test_RMX12_tie(self):
        rulecard = RuleCard.objects.get(ref_name = 'RMX12')
        player1 = _prepare_scoresheet(self.game, "p1", blue = 3, pink = 4)
        player2 = _prepare_scoresheet(self.game, "p2", blue = 3, pink = 3)
        player3 = _prepare_scoresheet(self.game, "p3", yellow = 2, green = 2)
        scoresheets = [player1, player2, player3]
        rulecard.perform(scoresheets)
        self.assertEqual(3, len(scoresheets))
        self.assertEqual(15, player1.total_score)
        assertRuleNotApplied(player1, rulecard)
        self.assertEqual(12, player2.total_score)
        assertRuleNotApplied(player2, rulecard)
        self.assertEqual(18, player3.total_score)
        assertRuleNotApplied(player3, rulecard)

    def test_RMX13(self):
        """If four colors are handed in with the same number of cards for each,
            and no cards are handed in from the fifth color, the value of the hand is doubled.
        """
        rulecard = RuleCard.objects.get(ref_name = 'RMX13')
        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 3, white = 3, yellow = 3, green = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(36*2, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A set of the same number of cards for 4 colors (blue, green, white, yellow) and no other cards doubles the score.', 36)

        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 2, white = 2, pink = 2, yellow = 2, green = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(30, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 4, white = 2, pink = 4, yellow = 4, green = 4)
        rulecard.perform(scoresheet)
        self.assertEqual(56, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

    def test_RMX14(self):
        """Each set of two pink cards doubles the value of one yellow card."""
        rulecard = RuleCard.objects.get(ref_name = 'RMX14')
        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(12, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", pink = 1, yellow = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(15, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", pink = 2, yellow = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(18+4, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A pair of pink cards doubles the value of one yellow card.', 4)

        scoresheet = _prepare_scoresheet(self.game, "p1", pink = 6, yellow = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(30+3*4, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A pair of pink cards doubles the value of one yellow card.', 4, times = 3)

        scoresheet = _prepare_scoresheet(self.game, "p1", pink = 8, yellow = 3)
        rulecard.perform(scoresheet)
        self.assertEqual(36+3*4, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A pair of pink cards doubles the value of one yellow card.', 4, times = 3)

    def test_RMX15(self):
        """Each set of three white cards triples the value of one green card."""
        rulecard = RuleCard.objects.get(ref_name = 'RMX15')
        scoresheet = _prepare_scoresheet(self.game, "p1", green = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(10, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", white = 2, green = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(14, scoresheet.total_score)
        assertRuleNotApplied(scoresheet, rulecard)

        scoresheet = _prepare_scoresheet(self.game, "p1", white = 3, green = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(16+10, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A set of three white cards triples the value of one green card.', 10)

        scoresheet = _prepare_scoresheet(self.game, "p1", white = 6, green = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(22+20, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A set of three white cards triples the value of one green card.', 10, times = 2)

        scoresheet = _prepare_scoresheet(self.game, "p1", white = 9, green = 2)
        rulecard.perform(scoresheet)
        self.assertEqual(28+20, scoresheet.total_score)
        assertRuleApplied(scoresheet, rulecard, 'A set of three white cards triples the value of one green card.', 10, times = 2)

    def test_all_rules_remixed_haggle_together(self):
        for rule in RuleCard.objects.filter(ruleset__id = 2):
            self.game.rules.add(rule)
        _prepare_hand(self.game, player = "p1", blue = 2, white = 1, pink = 3, yellow = 3, green = 2) # -6+7 8 14
        _prepare_hand(self.game, player = "p2", blue = 7, white = 5, pink = 3,             green = 1) # 9 11 12 15
        _prepare_hand(self.game, player = "p3", blue = 3, white = 1, pink = 1, yellow = 4, green = 2) # 4 5 -6+7 8
        _prepare_hand(self.game, player = "p4",           white = 2, pink = 2, yellow = 2, green = 2) # -6 13 14
        scoresheets = tally_scores(self.game)
        self.assertEqual(4, len(scoresheets))
        self.assertEqual(35+8+4, scoresheets[0].total_score)
        self.assertEqual(31+20-10+9+10, scoresheets[1].total_score)
        self.assertEqual(12+8, scoresheets[2].total_score)
        self.assertEqual((28-10+4)*2, scoresheets[3].total_score)