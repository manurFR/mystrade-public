import re
from django.utils import timezone
from django.utils.timezone import now
from game.models import GamePlayer


class TimezoneMiddleware(object):
    def process_request(self, request):
        try:
            tz = request.user.timezone
            if tz:
                timezone.activate(tz)
            else:
                timezone.deactivate()
        except AttributeError:
            timezone.deactivate()


class OnlineStatusMiddleware(object):
    def process_request(self, request):
        """ This relies on the fact that all urls starting with /game/(\d+)/... or /trade/(\d+)/... will have the game_id as this first argument """
        if request.user.is_authenticated():
            match = re.match(r'/(?:game|trade)/(\d+)/', request.path)
            if match:
                game_id = match.group(1)
                # nothing will be updated if there's no GamePlayer instance (e.g. for the game master or the admins)
                GamePlayer.objects.filter(game__id = game_id, player = request.user).update(last_seen = now())
            return