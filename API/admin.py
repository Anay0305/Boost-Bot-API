from django.contrib import admin
from .models import RedeemCode, Order

class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_id', 'months', 'amount', 'server_invite', 'server_id')
    search_fields = ('order_id',)
    list_filter = ('amount', 'months')
    ordering = ('-ordered_at',)

admin.site.register(Order, OrderAdmin)

class RedeemAdmin(admin.ModelAdmin):
    list_display = ('key', 'redeemed', 'months', 'created_at', 'amount')
    search_fields = ('key',)
    list_filter = ('redeemed', 'months', 'amount')

    ordering = ('-created_at',)

admin.site.register(RedeemCode, RedeemAdmin)