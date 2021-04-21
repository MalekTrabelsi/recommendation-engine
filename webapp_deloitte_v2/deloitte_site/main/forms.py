from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
#from .models import Profile


class NewUserForm(UserCreationForm):
    class Meta:
        model = User
        fields = ("username","password1", "password2",)

    def save(self, commit=True):
        user = super(NewUserForm, self).save(commit=False)
        if commit:
            user.save()
        return user

"""
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('id', 'cat_choice', 'app_choice')


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('apps',)
"""