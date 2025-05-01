from django.urls import path
from .views import generate_key, get_info, redeem_key, authorize, refresh_token, receive_results, autobuy, get_order_info, delete_key

urlpatterns = [
    path("key/get_info", get_info, name="get_info"),
    path("key/redeem_key", redeem_key, name="redeem_key"),
    path("key/generate_key", generate_key, name="generate_key"),
    path("key/delete_key", delete_key, name="delete_key"),
#    path("key/all_keys", get_all_keys, name="get_all_keys"),
    path("result", receive_results, name="results"),
    path("authorize", authorize, name="authorize"),
    path("refresh", refresh_token, name="refresh_token"),
    path("webhook/autobuy", autobuy, name="AutoBuy"),
    path("get_order_info", get_order_info, name="get_order_info")
]