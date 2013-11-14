# coding=utf-8
import hashlib
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth.models import UserManager
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from profile.forms import MystradeUserForm
from utils import utils


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

        if user_form.is_valid() and password_form.is_valid():
            email = UserManager.normalize_email(user_form.cleaned_data['email'])

            user = get_user_model()(username            = user_form.cleaned_data['username'],
                                    first_name          = user_form.cleaned_data['first_name'],
                                    last_name           = user_form.cleaned_data['last_name'],
                                    email               = email,
                                    send_notifications  = user_form.cleaned_data['send_notifications'],
                                    timezone            = user_form.cleaned_data['timezone'],
                                    bio                 = user_form.cleaned_data['bio'],
                                    contact             = user_form.cleaned_data['contact'],
                                    is_active           = False,
                                    is_staff            = False,
                                    is_superuser        = False,
                                    date_joined         = now())
            user.set_password(password_form.cleaned_data['new_password1'])
            user.save()

            # create an activation key and send it to the new user
            activation_key = _generate_activation_key(user_form.cleaned_data['username'])
            utils.send_notification_email("registration_activation", email,
                                          {'activation_url': request.build_absolute_uri(reverse('activation', args = [activation_key]))})

            return render(request, 'profile/registration_complete.html')
    else:
        user_form = MystradeUserForm()
        user_form['send_notifications'].field.initial = True
        password_form = SetPasswordForm(user = None)

    return render(request, 'profile/editprofile.html', {'user_form': user_form, 'password_form': password_form, 'sign_up': True})

def _generate_activation_key(username, salt = 'µy5Tr@d3'):
    crypted_salt = hashlib.sha1(salt).hexdigest()[:5]
    if isinstance(username, unicode):
        username = username.encode('utf-8')
    return hashlib.sha1(salt+username).hexdigest()

def activation(request):
    pass
