"""django_peo URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from .views import *

app_name="risorse_umane"

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('aggiorna_carta_identita', upload_carta_identita, name='upload_carta_identita'),
    path('<str:nome_modello>/import_file', import_file, name='import_file'),    
]
