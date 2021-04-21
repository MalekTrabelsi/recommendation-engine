from django.urls import path
from . import views

app_name = "main"


urlpatterns = [
    path("", views.homepage, name="homepage"),
    path("allapps", views.allapps, name="allapps"),
    path("contact", views.contact, name="contact"),
    path("register", views.register, name="register"),
    path("login", views.login_request, name="login"),
    path("logout", views.logout_request, name="logout"),
    #path("user", views.userpage, name="userpage"),
]