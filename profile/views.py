from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.shortcuts import render, redirect, get_object_or_404
from profile.forms import MystradeUserForm


@login_required
def profile(request, user_id = None):
    if user_id:
        if int(user_id) == request.user.id:
            return redirect('profile') # without our own's user_id
        else:
            return render(request, 'profile/otherprofile.html', {'user_displayed': get_object_or_404(get_user_model(), pk = user_id)})
    else:
        return render(request, 'profile/profile.html')

@login_required
def editprofile(request):
    if request.method == 'POST':
        user_form = MystradeUserForm(data = request.POST, instance = request.user)
        password_form = PasswordChangeForm(data = request.POST, user = request.user)

        if request.POST.get('new_password1'):
            if user_form.is_valid() and password_form.is_valid():
                user = user_form.save(commit = False)
                user.set_password(password_form.cleaned_data['new_password1'])
                user.save()
                return redirect('profile')
        elif user_form.is_valid():
            user_form.save()
            return redirect('profile')
    else:
        user_form = MystradeUserForm(instance = request.user)
        password_form = PasswordChangeForm(user = request.user)

    return render(request, 'profile/editprofile.html', {'user_form': user_form, 'password_form': password_form})

def sign_up(request):
    if request.method == 'POST':
        user_form = MystradeUserForm(data = request.POST)
        password_form = SetPasswordForm(data = request.POST, user = None)

        if user_form.is_valid():
            pass
    else:
        user_form = MystradeUserForm()
        user_form['send_notifications'].field.initial = True
        password_form = SetPasswordForm(user = None)

    return render(request, 'profile/editprofile.html', {'user_form': user_form, 'password_form': password_form, 'sign_up': True})
