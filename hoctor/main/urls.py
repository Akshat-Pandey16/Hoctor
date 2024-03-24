
from django.urls import path
from .views import index,home,track,track2

app_name = 'main'

urlpatterns = [
    path('',index,name="index"),
    path('home',home,name="home"),
    path('track',track,name="track"),
    path("track2", track2, name="track2")
]