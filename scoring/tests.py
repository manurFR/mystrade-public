from unittest.util import safe_repr
from django.contrib.auth.models import User
from django.test import TestCase
from model_mommy import mommy
from game.models import Game, GamePlayer, CommodityInHand
from ruleset.models import RuleCard, Commodity, Ruleset
from scoring.card_scoring import tally_scores, Scoresheet

class ScoringTest(TestCase):
    def setUp(self):
        self.game = mommy.make(Game, ruleset = Ruleset.objects.get(id = 1))

    def test_tally_scores_all_rules(self):
        for rule in RuleCard.objects.filter(ruleset__id = 1):
            self.game.rules.add(rule)
        _prepare_hand(self.game, player = "p1", yellow = 2, blue = 1, red = 3, orange = 3, white = 4)
        _prepare_hand(self.game, player = "p2", yellow = 3, blue = 5, red = 3,             white = 1)
        _prepare_hand(self.game, player = "p3", yellow = 3, blue = 1, red = 1, orange = 7, white = 1)
        _prepare_hand(self.game, player = "p4",             blue = 3, red = 4, orange = 2, white = 1)
        scoresheets = tally_scores(self.game)
        self.assertEqual(4, len(scoresheets))
        self.assertEqual(31, scoresheets[0].total_score)
        self.assertEqual(32, scoresheets[1].total_score)
        self.assertEqual(12, scoresheets[2].total_score)
        self.assertEqual(110, scoresheets[3].total_score)

    def test_tally_scores_rules_subset(self):
        for rule in RuleCard.objects.filter(ruleset__id = 1, public_name__in = ['4', '8', '10', '12', '13']):
            self.game.rules.add(rule)
        _prepare_hand(self.game, player = "p1", yellow = 4, blue = 2, red = 2, orange = 3, white = 2)
        _prepare_hand(self.game, player = "p2", yellow = 2, blue = 5, white = 5)
        _prepare_hand(self.game, player = "p3", yellow = 1, blue = 1, red = 1, orange = 7)
        _prepare_hand(self.game, player = "p4", blue = 3, red = 4, orange = 2, white = 1)
        scoresheets = tally_scores(self.game)
        self.assertEqual(82, scoresheets[0].total_score)
        self.assertEqual(12, scoresheets[1].total_score)
        self.assertEqual(34, scoresheets[2].total_score)
        self.assertEqual(43, scoresheets[3].total_score)
        self.assertEqual(4, len(scoresheets))
        self.assertEqual(4, scoresheets[0].score_for_commodity('Yellow').nb_submitted_cards)
        self.assertEqual(4, scoresheets[0].nb_scored_cards('Yellow'))
        self.assertEqual(1, scoresheets[0].actual_value('Yellow'))
        self.assertEqual(4, scoresheets[0].score_for_commodity('Yellow').score)
        self.assertEqual(2, scoresheets[0].score_for_commodity('Blue').nb_submitted_cards)
        self.assertEqual(2, scoresheets[0].nb_scored_cards('Blue'))
        self.assertEqual(2, scoresheets[0].actual_value('Blue'))
        self.assertEqual(4, scoresheets[0].score_for_commodity('Blue').score)
        self.assertEqual(2, scoresheets[0].score_for_commodity('Red').nb_submitted_cards)
        self.assertEqual(2, scoresheets[0].nb_scored_cards('Red'))
        self.assertEqual(3, scoresheets[0].actual_value('Red'))
        self.assertEqual(6, scoresheets[0].score_for_commodity('Red').score)
        self.assertEqual(3, scoresheets[0].score_for_commodity('Orange').nb_submitted_cards)
        self.assertEqual(3, scoresheets[0].nb_scored_cards('Orange'))
        self.assertEqual(4, scoresheets[0].actual_value('Orange'))
        self.assertEqual(12, scoresheets[0].score_for_commodity('Orange').score)
        self.assertEqual(2, scoresheets[0].score_for_commodity('White').nb_submitted_cards)
        self.assertEqual(2, scoresheets[0].nb_scored_cards('White'))
        self.assertEqual(5, scoresheets[0].actual_value('White'))
        self.assertEqual(10, scoresheets[0].score_for_commodity('White').score)
        self.assertListEqual(['HAG10', 'HAG10', 'HAG13', 'HAG13', 'HAG08'], [sfr.rulecard.ref_name for sfr in scoresheets[0].scores_from_rule])
        self.assertListEqual([10,      10,      5,       5,       16     ], [sfr.score for sfr in scoresheets[0].scores_from_rule])

    def test_calculate_commodity_scores(self):
        player = mommy.make(User, username = 'test')
        mommy.make(CommodityInHand, game = self.game, player = player, commodity__name = 'Blue', commodity__value = 2, nb_submitted_cards = 2)
        mommy.make(CommodityInHand, game = self.game, player = player, commodity__name = 'Red', commodity__value = 1, nb_submitted_cards = 3)

        gameplayer = mommy.make(GamePlayer, game = self.game, player = player, submit_date = self.game.end_date)

        scoresheet = Scoresheet(gameplayer)

        scoresheet._calculate_commodity_scores()

        self.assertEqual(4, scoresheet.score_for_commodity('Blue').score)
        self.assertEqual(3, scoresheet.score_for_commodity('Red').score)

    def test_Scoresheet_init(self):
        """Initial values : Yellow = 1 / Blue = 2 / Red = 3 / Orange = 4 / White = 5
           This is a test of the 3 mandatory rulecards for the initial values.
        """
        scoresheet = _prepare_scoresheet(self.game, "p1", yellow = 1, blue = 1, red = 1, orange = 1, white = 1)
        self.assertEqual(1, scoresheet.score_for_commodity('Yellow').nb_submitted_cards)
        self.assertEqual(1, scoresheet.nb_scored_cards('Yellow'))
        self.assertEqual(1, scoresheet.actual_value('Yellow'))
        self.assertEqual(1, scoresheet.score_for_commodity('Blue').nb_submitted_cards)
        self.assertEqual(1, scoresheet.nb_scored_cards('Blue'))
        self.assertEqual(2, scoresheet.actual_value('Blue'))
        self.assertEqual(1, scoresheet.score_for_commodity('Red').nb_submitted_cards)
        self.assertEqual(1, scoresheet.nb_scored_cards('Red'))
        self.assertEqual(3, scoresheet.actual_value('Red'))
        self.assertEqual(1, scoresheet.score_for_commodity('Orange').nb_submitted_cards)
        self.assertEqual(1, scoresheet.nb_scored_cards('Orange'))
        self.assertEqual(4, scoresheet.actual_value('Orange'))
        self.assertEqual(1, scoresheet.score_for_commodity('White').nb_submitted_cards)
        self.assertEqual(1, scoresheet.nb_scored_cards('White'))
        self.assertEqual(5, scoresheet.actual_value('White'))

        scoresheet = _prepare_scoresheet(self.game, "p2", blue = 1, red = 2, orange = 3)
        self.assertEqual(1, scoresheet.score_for_commodity('Blue').nb_submitted_cards)
        self.assertEqual(1, scoresheet.nb_scored_cards('Blue'))
        self.assertEqual(2, scoresheet.actual_value('Blue'))
        self.assertEqual(2, scoresheet.score_for_commodity('Red').nb_submitted_cards)
        self.assertEqual(2, scoresheet.nb_scored_cards('Red'))
        self.assertEqual(3, scoresheet.actual_value('Red'))
        self.assertEqual(3, scoresheet.score_for_commodity('Orange').nb_submitted_cards)
        self.assertEqual(3, scoresheet.nb_scored_cards('Orange'))
        self.assertEqual(4, scoresheet.actual_value('Orange'))

    def test_register_rule(self):
        rulecard = mommy.prepare_one(RuleCard)
        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 1)
        scoresheet.register_score_from_rule(rulecard, 'test', 10)
        self.assertEqual(rulecard, scoresheet.scores_from_rule[0].rulecard)
        self.assertEqual('test', scoresheet.scores_from_rule[0].detail)
        self.assertEqual(10, scoresheet.scores_from_rule[0].score)
        self.assertFalse(getattr(scoresheet.scores_from_rule[0], 'is_random', False))

    def test_register_rule_no_score(self):
        rulecard = mommy.prepare_one(RuleCard)
        scoresheet = _prepare_scoresheet(self.game, "p1", blue = 1)
        scoresheet.register_score_from_rule(rulecard, 'test', is_random = True)
        self.assertEqual(rulecard, scoresheet.scores_from_rule[0].rulecard)
        self.assertEqual('test', scoresheet.scores_from_rule[0].detail)
        self.assertIsNone(scoresheet.scores_from_rule[0].score)
        self.assertTrue(getattr(scoresheet.scores_from_rule[0], 'is_random', False))

class RemixedHaggleTest(TestCase):
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
        assertRuleApplied(scoresheet, rulecard, '(4) Since the combined number of yellow cards (3) and green cards (3) is 6 (higher than five), the value of green cards is set to zero.')

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
        assertRuleApplied(scoresheets[0], rulecard, '(6) Since player #2 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(16-10, scoresheets[1].total_score)
        assertRuleApplied(scoresheets[1], rulecard, '(6) Since player #1 has 5 blue cards, 10 points are deducted.', -10)
        self.assertEqual(28-20, scoresheets[2].total_score)
        assertRuleApplied(scoresheets[2], rulecard, '(6) Since player #1 has 5 blue cards, 10 points are deducted.', -10)
        assertRuleApplied(scoresheets[2], rulecard, '(6) Since player #2 has 6 blue cards, 10 points are deducted.', -10)

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
        assertRuleApplied(player1, rulecardHAG06, '(6) Since player #2 has 6 blue cards, 10 points are deducted.', -10)
        self.assertEqual(21, player2.total_score)
        assertRuleApplied(player2, rulecardHAG06, '(6) Since player #1 has 5 blue cards, 10 points should have been deducted...')
        assertRuleApplied(player2, rulecardHAG07, '(7) ...but a set of three red cards cancels that penalty.')
        self.assertEqual(24, player3.total_score)
        assertRuleApplied(player3, rulecardHAG06, '(6) Since player #1 has 5 blue cards, 10 points should have been deducted...')
        assertRuleApplied(player3, rulecardHAG06, '(6) Since player #2 has 6 blue cards, 10 points should have been deducted...')
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

#############################################################################
##                           Common Utils                                  ##
#############################################################################

def _prepare_hand(game, player, **commodities):
    try:
        p = User.objects.get(username = player)
        gameplayer = GamePlayer.objects.get(game = game, player = p)
        CommodityInHand.objects.filter(game = game, player = p).delete()
    except User.DoesNotExist:
        p = mommy.make(User, username = player)
        gameplayer = mommy.make(GamePlayer, game = game, player = p)

    for name, nb_submitted_cards in commodities.iteritems():
        commodity = Commodity.objects.get(ruleset = game.ruleset, name__iexact = name)
        mommy.make(CommodityInHand, game = game, player = p, commodity = commodity,
                       nb_cards = nb_submitted_cards, nb_submitted_cards = nb_submitted_cards)
    return gameplayer

def _prepare_scoresheet(game, player, **commodities):
    return Scoresheet(_prepare_hand(game, player, **commodities))

def assertRuleApplied(scoresheet, rulecard, detail = '', score = None, times = 1):
    for _i in range(times):
        for sfr in scoresheet.scores_from_rule:
            if sfr.rulecard == rulecard and sfr.detail == detail and sfr.score == score:
                break
        else:
            raise AssertionError

def assertRuleNotApplied(scoresheet, rulecard):
    applied_rules = [sfr.rulecard for sfr in scoresheet.scores_from_rule]
    if rulecard in applied_rules:
        raise AssertionError('{} unexpectedly found in {}'.format(safe_repr(rulecard), safe_repr(applied_rules)))
