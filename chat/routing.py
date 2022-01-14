# chat/routing.py
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/chat/<str:room_name>/', consumers.ChatConsumer.as_asgi()),
    path('ws/personal_chat/<str:room_name>/', consumers.PersonalConsumer.as_asgi()),
]