from django.urls import path, include
from .views import index

urlpatterns = [
    path('', view = index),
    path('join', view = index),
    path('create', view = index)

]
