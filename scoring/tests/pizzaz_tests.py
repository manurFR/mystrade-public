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
