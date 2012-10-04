# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404
from userprofile.forms import MysTradeUserChangeForm

@login_required
def editprofile(request, user_id):
    if int(user_id) != request.user.id:
        return render(request, 'userprofile/otherprofile.html', {'user' : get_object_or_404(User, pk = user_id)})
    form = MysTradeUserChangeForm(user = request.user)
    return render(request, 'userprofile/editprofile.html', {'form': form})