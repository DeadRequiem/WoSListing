from django.urls import path
from . import views

urlpatterns = [
    path('', views.server_list, name='server_list'),
    path('refresh_server_data/', views.refresh_server_data, name='refresh_server_data'),
]
