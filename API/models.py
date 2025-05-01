from django.db import models

class Order(models.Model):
    order_id = models.CharField(max_length=255, unique=True)
    status = models.BooleanField(default=False)
    months = models.IntegerField(default=1)
    amount = models.IntegerField(default=2)
    completed = models.IntegerField(default=0)
    tokens = models.JSONField(default=dict, null=True, blank=True)
    server_invite = models.CharField(max_length=255, default=None, null=True, blank=True)
    server_id = models.IntegerField(null=True, blank=True)
    ordered_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    service = models.CharField(max_length=255, null=True, blank=True, default="Manual Boost")
    message = models.TextField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Order {self.order_id} - Status: {'Completed' if self.status else 'Pending'}"

class RedeemCode(models.Model):
    key = models.CharField(max_length=255, unique=True)
    order_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.IntegerField(default=2)
    months = models.IntegerField(default=1)
    redeemed = models.BooleanField(default=False)
    server_id = models.IntegerField(null=True, blank=True)
    server_invite = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    tokens = models.JSONField(default=dict, null=True, blank=True)
    redeemed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.key