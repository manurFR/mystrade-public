from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404
from userprofile.forms import UserProfileForm, UserForm

@login_required
def profile(request, user_id = None):
    if user_id:
        if int(user_id) == request.user.id:
            return redirect('profile') # without our own's user_id
        else:
            return render(request, 'userprofile/otherprofile.html', {'user_displayed': get_object_or_404(User, pk=user_id)})
    else:
        return render(request, 'userprofile/profile.html')

@login_required
def editprofile(request):
    if request.method == 'POST':
        user_form = UserForm(data = request.POST, instance = request.user)
        userprofile_form = UserProfileForm(data = request.POST, instance = request.user.get_profile())
        if user_form.is_valid() and userprofile_form.is_valid():
            user = user_form.save(commit = False)
            if user_form.cleaned_data['new_password1']:
                user.set_password(user_form.cleaned_data['new_password1'])
            user.save()
            userprofile_form.save()
            return redirect('profile')
    else:
        user_form = UserForm(instance = request.user)
        userprofile_form = UserProfileForm(instance = request.user.get_profile())

    return render(request, 'userprofile/editprofile.html', {'user_form': user_form, 'userprofile_form': userprofile_form})
