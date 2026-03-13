from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from .forms import LoginForm, UserRegistrationForm, UserEditForm, ProfileEditForm
from .models import Profile
# from posts.models import Post


# Create your views here.
def user_login(request):
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user = authenticate(request, username=data['username'], password=data['password'])
            if user is not None:
                login(request, user)
                if next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect('shops:index')
            else:
                return render(request, 'users/login.html', {
                    'form': form,
                    'next': next_url,
                })
    else:
        form = LoginForm()
    return render(request, 'users/login.html', {
        'form': form,
        'next': next_url,
    })

def register(request):
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = ProfileEditForm(request.POST, request.FILES)
        if user_form.is_valid() and profile_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()
            profile = new_user.profile
            profile.phone = profile_form.cleaned_data['phone']
            profile.photo = profile_form.cleaned_data['photo']
            profile.save()
            return redirect('users:register_done')
    else:
        user_form = UserRegistrationForm()
        profile_form = ProfileEditForm()

    return render(request, 'users/register.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

def register_done(request):
    return render(request, 'users/register_done.html')

@login_required
def index(request):
    user = request.user
    return redirect('shops:index')

def edit(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        user_form = UserEditForm(instance=request.user, data=request.POST)
        profile_form = ProfileEditForm(
            instance=profile,
            data=request.POST,
            files=request.FILES
        )
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            return render(request, 'users/index.html')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=profile)

    return render(
        request,
        'users/edit.html',
        {
            'user_form': user_form,
            'profile_form': profile_form
        }
    )
