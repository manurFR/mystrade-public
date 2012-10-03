# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserChangeForm
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.shortcuts import render

@login_required
def editprofile(request, user_id):
    if int(user_id) != request.user.id:
        # TODO if user_id doesn't exist (get() raises exception)
        # TODO do not show email
        return render(request, 'userprofile/profile.html', {'is_other_user' : True, 'user' : User.objects.get(pk = user_id)})
    #form = UserChangeForm(instance = request.user)
    return HttpResponse("My profile to edit ({})".format(user_id))