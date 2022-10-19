from django import template
from django.contrib.auth.models import User

register = template.Library()

@property
def is_place_client(self):
    return self.groups.filter(name='Client').exists()

@property
def is_place_staff(self):  
    return self.groups.filter(name='Staff').exists()


setattr(User, 'is_place_client', is_place_client)
setattr(User, 'is_place_staff', is_place_staff)


