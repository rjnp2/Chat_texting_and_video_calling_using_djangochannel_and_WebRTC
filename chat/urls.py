# chat/urls.py

from django.urls import path
from . import views

app_name = 'chat'
urlpatterns = [
    path('', views.home,name = 'home'),
    path('<str:room_name>', views.home,name = 'home'),
    path('create_friend/<int:id>', views.create_friend, name ='create_friend'),
]