from django.urls import path
from .views import generate_key, get_info, redeem_key, authorize, refresh_token, receive_results

urlpatterns = [
    path("key/get_info", get_info, name="get_info"),
    path("key/redeem_key", redeem_key, name="redeem_key"),
    path("key/generate_key", generate_key, name="generate_key"),
    path("result", receive_results, name="results"),
    path("authorize", authorize, name="authorize"),
    path("refresh", refresh_token, name="refresh_token"),
]