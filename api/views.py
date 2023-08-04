from django.shortcuts import render
from django.http import HttpResponse
from .models import *
from rest_framework import generics

# Create your views here.
def main(request):
    return HttpResponse("Hello")

class RoomView()