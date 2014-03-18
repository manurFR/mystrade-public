#MysTrade

MysTrade is a multiplayer, asynchronous, party game for large groups. It is inspired by [Haggle](http://en.wikipedia.org/wiki/Haggle_(game)), a game from Sid Sackson's 1969 book *A Gamut of Game*. A minimum of ten players is required, but twelve to fifteen is a better count.

Players try to earn the most points by performing trades of "commodity" and "rule cards". Commodity cards are the one that give points, alone or in specific combinations. The rule cards detail how many points each kind of commodity cards is worth, and how they can be combined to give more (or less) points to their owner.

At the start of a game session, each player only owns a small subset of all existing rule cards, and thus knows only a small part of the scoring rules. Since all scoring rules will be applied to all players, they will have to balance their trading strategy between getting to know more rule cards and optimizing their hand of commodity cards, two processes that will frequently be antagonistic.

Three different "rulesets" of cards are included: the original Haggle ruleset from *A Gamut of Game*; a "remixed" ruleset following the same ideas but with different commodities and rules; and a Pizzaz! ruleset for slightly larger groups, intended for dedicated pizza chefs.


### Technology notes

MysTrade has been implemented in Python 2.7 with the [Django](https://www.djangoproject.com/) framework (v. 1.6.1 at the time of writing). The use of the following libraries and tools is notable : [pip](http://www.pip-installer.org/en/latest/), [PostgreSQL](http://www.postgresql.org/), [South](http://south.aeracode.org/), [SASS](http://sass-lang.com/), [Django Debug Toolbar](https://github.com/django-debug-toolbar/django-debug-toolbar), [Django Extensions](https://github.com/django-extensions/django-extensions), [Model Mommy](https://github.com/vandersonmota/model_mommy), [Bleach](https://github.com/jsocol/bleach), [jQuery](http://jquery.com/) and [jQueryUI](http://jqueryui.com/).

* Thanks to git hooks, the deployment of new versions on the production server is made with a one-command "git push production" on the development box, à la Heroku. Look at the scripts in the [production/](production/) folder.

* The functions called for scoring calculation are dynamically linked to the rule cards used for scoring, depending on the ruleset and card names fetched from the database. Django signals and importlib are used for this feature. See [ruleset/models.py](ruleset/models.py), lines 44-55.

* Players can choose between three "palettes" of color for the look of the website, with live-switching between palettes on the profile editing page.

* The main game page is AJAX-powered. It features an easy graphical management of trades; a display of which other players are connected right now on the same game page (a Django middleware is recording requests to enable this functionality); and an auto-refresh of the trades' offers and life cycle, of public messages and of the online status of other players.

* Sign up pages allow users to register a player profile through a two-step validation process with sending of a confirmation email. Lost password can also be reinitialized this way.

* Players can specify their timezone in their profile, making all dates display in this timezone.

* Development was made in TDD; there are ~280 unit tests securing the code, which can be run with "./runtests.sh" (a PostgreSQL instance is required, see [mystrade/settings.py](mystrade/settings.py)).

The game was made through more than 600 git commits, with ~6000 lines of Python code, ~2300 lines of HTML, ~1300 lines of SASS and 200+ quite complex lines of JavaScript/jQuery for the main game page (10.000 LOC total).
