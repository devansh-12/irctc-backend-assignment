"""
URL configuration for trains app.
"""
from django.urls import path
from .views import TrainSearchView, TrainManageView

urlpatterns = [
    path('search/', TrainSearchView.as_view(), name='train_search'),
    path('', TrainManageView.as_view(), name='train_manage'),
]
