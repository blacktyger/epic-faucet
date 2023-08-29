from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('stats/', views.stats, name='stats'),
    path('stats_data/', views.stats_stream, name='stats_stream'),


    ]
