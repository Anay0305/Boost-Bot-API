"""
URL configuration for WebApp project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.contrib import admin
from django.urls import path, include
from django.conf.urls import handler404
from API.views import show_info, redeem, live_stock, show_order_info, custom_404

urlpatterns = [
    path('admin/', admin.site.urls),
    path("key/info/", show_info, name="info"),
    path("key/redeem/", redeem, name="redeem"),
    path('stock/', live_stock, name='live_stock'),
    path('order/', show_order_info, name='show_order_info'),
    path('api/', include('API.urls')),
]


handler404 = 'API.views.custom_404'