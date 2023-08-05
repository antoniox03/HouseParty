from django.contrib import admin
from django.urls import path
from .views import *

urlpatterns = [
    path('', view= RoomView.as_view()),
    path('create-room', view= CreateRoomView.as_view())
]

