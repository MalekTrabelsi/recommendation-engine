from django.shortcuts import render, redirect
from .models import App
from .forms import NewUserForm #UserForm, ProfileForm
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
from django.contrib.auth.forms import AuthenticationForm
import random


# Create your views here.
def homepage(request):
    apps = App.objects.all()
    admin_apps = apps[:4]
    random_apps = []
    for i in range(4):
        random_index = random.randint(0,len(apps)-1)
        random_apps.append(apps[random_index])
    return render(request=request, template_name="main/home.html", context={'apps': apps, 'admin_apps': admin_apps, 'random_apps': random_apps})


def allapps(request):
    apps = App.objects.all()[:10]
    searches = None
    if 'q' in request.GET and request.GET['q']:
        q = request.GET['q']
        searches = App.objects.filter(app_name__icontains=q)[:10]
    return render(request=request, template_name="main/all-apps.html", context={'apps': apps, 'searches': searches})


def contact(request):
    return render(request=request, template_name="main/contact.html")


def register(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Inscription Réussite.")
            return redirect("main:homepage")
        messages.error(request, "Erruer inscription. Données invalides")
    form = NewUserForm
    return render(request=request, template_name="main/register.html", context={"form": form})


def login_request(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"Vous êtes connecté en tant que {username}.")
                return redirect("main:homepage")
            else:
                messages.error(request, "données invalides.")
        else:
            messages.error(request, "données invalides.")
    form = AuthenticationForm()
    return render(request=request, template_name="main/login.html", context={"form": form})


def logout_request(request):
    logout(request)
    messages.info(request, "Déconnexion Réussite.")
    return redirect("main:homepage")

"""
def userpage(request):
    user_form = UserForm(instance=request.user)
    profile_form = ProfileForm(instance=request.user.profile)
    return render(request=request, template_name="main/user.html",
                  context={"user": request.user, "user_form": user_form, "profile_form": profile_form})
"""