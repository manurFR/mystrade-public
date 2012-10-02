# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

@login_required
def editprofile(request, user_id):
    return HttpResponse("My profile to edit ({})".format(user_id))