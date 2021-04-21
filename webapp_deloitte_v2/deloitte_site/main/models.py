from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save

# Create your models here.
class App(models.Model):
    app_name = models.CharField(max_length=150)
    app_type = models.CharField(max_length=25)
    app_description = models.TextField()
    affiliate_url = models.SlugField(blank=True, null=True)
    app_image = models.ImageField(upload_to='images/')

    def __str__(self):
        return self.app_name
"""
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    apps = models.ManyToManyField(App)

    @receiver(post_save, sender=User)  # add this
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)

    @receiver(post_save, sender=User)  # add this
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()
"""