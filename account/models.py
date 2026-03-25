from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('GENERAL', 'General User'),
        ('ADMIN', 'Admin'),
        ('MANAGER', 'Manager'),
        ('DRIVER', 'Driver'),
        ('TECHNICIAN', 'Technician'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='GENERAL')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)

    def __str__(self):
        return self.username