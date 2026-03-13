"""
URL configuration for shopproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path, reverse_lazy
from users import views
from django.contrib.auth import views as auth_views

app_name = 'users'
urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.user_login, name ='login'),
    path('logout/', auth_views.LogoutView.as_view(template_name='users/logout.html'), name='logout'),
    # PASSWORD RESET
    path(
        'password_reset/',
        auth_views.PasswordResetView.as_view(
            template_name='users/password_reset.html',
            email_template_name='users/password_reset_email.html',
            html_email_template_name="users/password_reset_email.html",
            success_url=reverse_lazy('users:password_reset_done')
        ),
        name='password_reset'
    ),

    path(
        "password_reset/done/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="users/password_reset_done.html"
        ),
        name="password_reset_done",
    ),

    path(
        "reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="users/password_reset_confirm.html",
            success_url=reverse_lazy("users:password_reset_complete")
        ),
        name="password_reset_confirm"
    ),

    path(
        "reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="users/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
    path(
        'password_change/',
        auth_views.PasswordChangeView.as_view(
            template_name='users/password_change.html',
            success_url=reverse_lazy('users:password_change_done')
        ),
        name='password_change'
    ),

    path(
        'password_change/done/',
        auth_views.PasswordChangeDoneView.as_view(
            template_name='users/password_change_done.html'
        ),
        name='password_change_done'
    ),
    path('register/', views.register, name='register'),
    path('edit/', views.edit, name='edit'),
]
