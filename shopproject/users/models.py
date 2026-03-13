from django.db import models
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    photo = models.ImageField(upload_to='users/%Y/%m/%d', blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    user_code = models.CharField(max_length=20, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.user_code:
            last_profile = Profile.objects.order_by('-id').first()
            if last_profile and last_profile.user_code:
                last_id = int(last_profile.user_code.replace('USR', ''))
                new_id = last_id + 1
            else:
                new_id = 1
            self.user_code = f"USR{new_id:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)