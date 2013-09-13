from django.contrib.auth import get_user_model
from django.test import TestCase
from model_mommy import mommy
from game.models import Game, GamePlayer, CommodityInHand
from ruleset.models import RuleCard, Ruleset
from scoring.card_scoring import tally_scores, Scoresheet
from scoring.tests.commons import _prepare_hand, _prepare_scoresheet

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
        player = mommy.make(get_user_model(), username = 'test')
        mommy.make(CommodityInHand, game = self.game, player = player, commodity__name = 'Blue', commodity__value = 2,
                   nb_cards = 4, nb_submitted_cards = 2)
        mommy.make(CommodityInHand, game = self.game, player = player, commodity__name = 'Red', commodity__value = 1,
                   nb_cards = 3, nb_submitted_cards = 3)

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