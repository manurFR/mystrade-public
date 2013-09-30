from django.utils import timezone


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

