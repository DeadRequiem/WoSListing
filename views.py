from django.shortcuts import render
from .models import Server

def server_list(request):
    servers = Server.objects.all()
    return render(request, 'server_list.html', {'servers': servers})
