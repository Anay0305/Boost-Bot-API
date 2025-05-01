import json
import secrets
from datetime import timedelta
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from functools import wraps
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import RedeemCode, Order
from .results import RESULTS
from datetime import datetime
from django.utils.timezone import make_aware
import uuid
import time

ACCESS_TOKENS = {}
REFRESH_TOKENS = {}
autobuy = {}
TOKEN_EXPIRY_SECONDS = 3600
MAX_WAIT_SECONDS = 120
WAIT_INTERVAL = 5

def censor_key_parts(key):
    parts = key.split('-')
    masked = [p[:2] + '*' * (len(p) - 3) + p[-1:] for p in parts]
    return '-'.join(masked)

def generate_token():
    return secrets.token_urlsafe(32)

def token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        token = auth_header.split("Bearer ")[1]
        expiry = ACCESS_TOKENS.get(token)
        if not expiry or expiry < timezone.now():
            return JsonResponse({"error": "Invalid or expired token"}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper

@csrf_exempt
def authorize(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    key = request.POST.get("key")
    autobuy = request.POST.get("autobuy")

    if not key:
        return JsonResponse({"error": "Missing API key"}, status=400)

    if key != "secrettoken123":
        return JsonResponse({"error": "Invalid API key"}, status=401)

    access_token = generate_token()
    refresh_token = generate_token()
    now = timezone.now()

    ACCESS_TOKENS[access_token] = now + timedelta(seconds=TOKEN_EXPIRY_SECONDS)
    REFRESH_TOKENS[refresh_token] = access_token

    return JsonResponse({
        "access_token": access_token,
        "refresh_token": refresh_token
    })

@csrf_exempt
def refresh_token(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    refresh_token = request.POST.get("refresh_token")
    if not refresh_token:
        return JsonResponse({"error": "Missing refresh token"}, status=400)

    old_access = REFRESH_TOKENS.get(refresh_token)
    if not old_access:
        return JsonResponse({"error": "Invalid refresh token"}, status=401)

    new_access_token = generate_token()
    ACCESS_TOKENS[new_access_token] = timezone.now() + timedelta(seconds=TOKEN_EXPIRY_SECONDS)
    REFRESH_TOKENS[refresh_token] = new_access_token

    return JsonResponse({"access_token": new_access_token})

from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils.timezone import now
import uuid, json

@csrf_exempt
def autobuy(request):
    if request.method == "POST":
        channel_layer = get_channel_layer()
        id = str(uuid.uuid4())[:8]

        try:
            data = json.loads(request.body)
            invoice_id = data.get("invoice_id")
            email = data.get("email")
            product_id = data.get("product_id")
            shop_id = data.get("shop_id")
            custom_fields = data.get("custom_fields", [])

            fields = {
                field["name"]: field["value"]
                for field in custom_fields
                if "name" in field and "value" in field
            }

            invite = fields.get("Invite Link")
            nickname = fields.get("Nickname")
            bio = fields.get("Bio")
            avatar = fields.get("Avatar")
            banner = fields.get("Banner")

            if shop_id not in autobuy:
                return JsonResponse({"error": "Shop ID not found in autobuy"}, status=400)
            if product_id not in autobuy[shop_id]:
                return JsonResponse({"error": "Product ID not found in autobuy"}, status=400)

            amount = autobuy[shop_id][product_id].get("amount")
            months = autobuy[shop_id][product_id].get("months")

            print(f"New SellAuth Order | Invoice: {invoice_id} | Email: {email} | Fields: {fields}")

            async_to_sync(channel_layer.group_send)(
                "boost",
                {
                    "type": "send_data",
                    "data": {
                        "id": id,
                        "action": "boost_order",
                        "data": {
                            "order_id": id,
                            "service": f"SellAuth Order {invoice_id}",
                            "amount": amount,
                            "months": months,
                            "invite_code": invite,
                            "nickname": nickname,
                            "bio": bio,
                            "avatar": avatar,
                            "banner": banner,
                        },
                        "invoice_id": invoice_id,
                    },
                },
            )

            Order.objects.create(
                order_id=id,
                months=months,
                amount=amount,
                server_invite=invite,
                status=False,
                ordered_at=now(),
                completed=0,
                service=f"SellAuth Order {invoice_id}",
                message="Processing your order",
            )

            base_url = request.get_host()
            return JsonResponse({
                "message": f"Order received. Your boosts will be processed shortly.\n\nYou can check the live status of your order on `https://{base_url}/order?order_id={id}`",
                "status": "success",
                "invoice_id": invoice_id
            })

        except Exception as e:
            print(f"SellAuth Webhook Error: {str(e)}")
            return JsonResponse({"error": "Invalid request or internal error."}, status=400)

    return JsonResponse({"error": "Invalid method"}, status=405)

def live_stock(request):
    channel_layer = get_channel_layer()
    id = str(uuid.uuid4())[:8]
    async_to_sync(channel_layer.group_send)(
        "boost",
        {
            "type": "send_data",
            "data": {
                "id": id,
                "action": "get_stock"
            }
        }
    )
    start_time = time.time()
    while True:
        if id in RESULTS:
            result = RESULTS.pop(id)
            data = result.get('data').get('stock')
            return render(request, 'stock.html', {
                '1m_ava': data['1_month']['available'],
                '1m_inuse': data['1_month']['in_use'],
                '1m_total': data['1_month']['total'],
                '3m_ava': data['3_month']['available'],
                '3m_inuse': data['3_month']['in_use'],
                '3m_total': data['3_month']['total'],
            })
        if time.time() - start_time > MAX_WAIT_SECONDS:
            return JsonResponse({"error": "Timeout waiting for result"}, status=504)
        time.sleep(WAIT_INTERVAL)

@csrf_exempt
@token_required
def generate_key(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            key = data.get('key')
            amount = data.get('amount')
            month = data.get('months')
            RedeemCode.objects.create(key=key, amount=amount, months=month)
            return JsonResponse({"status": "success", "message": "Key generated successfully"})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

    return JsonResponse({"error": "Invalid method"}, status=405)

def redeem(request):
    return render(request, 'Key/redeem.html')

def show_info(request):
    key = request.GET.get('key')
    if key:
        try:
            redeem_code = RedeemCode.objects.get(key=key)
            status = "Redeemed" if redeem_code.redeemed else "Not Redeemed"
            if not redeem_code.redeemed:
                return render(request, 'Key/info_not_redeemed.html', {
                    'key': redeem_code.key,
                    'amount': redeem_code.amount,
                    'months': redeem_code.months,
                    'redeemed': redeem_code.redeemed,
                    'status': status,
                    'created_at': redeem_code.created_at
                })
            else:
                return render(request, 'Key/info_redeemed.html', {
                    'key': redeem_code.key,
                    'amount': redeem_code.amount,
                    'months': redeem_code.months,
                    'redeemed': redeem_code.redeemed,
                    'status': status,
                    'created_at': redeem_code.created_at,
                    'redeemed_at': redeem_code.redeemed_at,
                    'order_id': redeem_code.order_id,
                    'server_id': redeem_code.server_id,
                    'server_invite': redeem_code.server_invite
                })
        except RedeemCode.DoesNotExist:
            return render(request, 'Key/nokey.html')
    else:
        return render(request, 'Key/nokey.html')

@csrf_exempt
def get_info(request):
    if request.method == "POST":
        data = json.loads(request.body)
        key = data.get('key')
        if key:
            try:
                redeem_code = RedeemCode.objects.get(key=key)
                status = "Redeemed" if redeem_code.redeemed else "Not Redeemed"
                if redeem_code.redeemed_at:
                    redeemed_at = redeem_code.redeemed_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    redeemed_at = None
                return JsonResponse({
                    'key': redeem_code.key,
                    'order_id': redeem_code.order_id,
                    'server_id': redeem_code.server_id,
                    'server_invite': redeem_code.server_invite,
                    'amount': redeem_code.amount,
                    'months': redeem_code.months,
                    'redeemed': redeem_code.redeemed,
                    'status': status,
                    'created_at': redeem_code.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    'redeemed_at': redeemed_at
                })
            except RedeemCode.DoesNotExist:
                return JsonResponse({"error": "Key not found"}, status=200)
        else:
            return JsonResponse({"error": "Key parameter is required"}, status=400)

@csrf_exempt
def redeem_key(request):
    if request.method == "POST":
        data = json.loads(request.body)
        key = data.get('key')
        invite = data.get('invite')
        if key:
            try:
                redeem_code = RedeemCode.objects.get(key=key)
                channel_layer = get_channel_layer()
                id = str(uuid.uuid4())[:8]
                order_id = str(uuid.uuid4())[:8]
                async_to_sync(channel_layer.group_send)(
                    "boost",
                    {
                        "type": "send_data",
                        "data": {
                            "id": id,
                            "action": "boost_order",
                            "data" : {
                                "order_id": order_id,
                                "service": f"Redeem Code {censor_key_parts(key)}",
                                "amount": redeem_code.amount,
                                "months": redeem_code.months,
                                "invite_code": invite
                            }
                        }
                    }
                )
                start_time = time.time()
                while True:
                    if id in RESULTS:
                        res = RESULTS.pop(id)
                        break
                    if time.time() - start_time > MAX_WAIT_SECONDS:
                        return JsonResponse({"error": "Timeout waiting for result"}, status=504)
                    time.sleep(WAIT_INTERVAL)
                if res['success'] == True:
                    redeem_code.redeemed = True
                    redeem_code.redeemed_at = timezone.now()
                    redeem_code.tokens = res['tokens']
                    redeem_code.order_id = res['order_id']
                    redeem_code.server_id = res['server_id']
                    redeem_code.server_invite = res['request']['invite']
                    redeem_code.save()
                return JsonResponse({"status": res['success'], "message": res['message']})
            except RedeemCode.DoesNotExist:
                return JsonResponse({"error": "Key not found"}, status=200)
        else:
            return JsonResponse({"error": "Key parameter is required"}, status=400)

@csrf_exempt
@token_required
def receive_results(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            result = data.get('result')
            id = data.get('id')
            RESULTS[id] = result
            print(RESULTS)

            service = result.get('service')
            success = result.get('success')
            message = result.get('message')
            error = result.get('error')
            order_id = result.get('order_id')
            requested = result.get('request', {})
            tokens = result.get('tokens')
            server_id = result.get('server_id')
            amount = requested.get('amount')
            month = requested.get('months')
            invite = requested.get('invite')
            ordered_at = result.get('ordered_at')
            finished_at = result.get('time')
            completed = result.get('total_boosts')

            if ordered_at:
                ordered_at = make_aware(datetime.fromtimestamp(ordered_at))
            else:
                ordered_at = make_aware(datetime.now())

            if not finished_at:
                finished_at = make_aware(datetime.now())
            else:
                finished_at = make_aware(datetime.fromtimestamp(finished_at))

            if completed is None:
                completed = 0

            if service and service.startswith("SellAuth Order"):
                try:
                    order_obj = Order.objects.get(order_id=id)
                    order_obj.status = success
                    order_obj.tokens = tokens
                    order_obj.server_invite = invite
                    order_obj.server_id = server_id
                    order_obj.finished_at = finished_at
                    order_obj.completed = completed
                    order_obj.error = error
                    order_obj.message = message
                    order_obj.save()
                except Order.DoesNotExist:
                    Order.objects.create(
                        order_id=order_id,
                        months=month,
                        amount=amount,
                        tokens=tokens,
                        server_invite=invite,
                        server_id=server_id,
                        status=success,
                        ordered_at=ordered_at,
                        finished_at=finished_at,
                        completed=completed,
                        service=service,
                        error=error,
                        message=message
                    )
            else:
                Order.objects.create(
                    order_id=order_id,
                    months=month,
                    amount=amount,
                    tokens=tokens,
                    server_invite=invite,
                    server_id=server_id,
                    status=success,
                    ordered_at=ordered_at,
                    finished_at=finished_at,
                    completed=completed,
                    service=service,
                    error=error,
                    message=message
                )

            return JsonResponse({"status": "success", "message": "Result received successfully"})
        
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            return JsonResponse({"error": f"Internal server error: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid method"}, status=405)

@csrf_exempt
def show_order_info(request):
    order_id = request.GET.get('order_id')
    if order_id:
        try:
            Order_ = Order.objects.get(order_id=order_id)
            if not Order_.finished_at:
                status = "Pending"
                status_class = "status-pending"
                status_message_class = "status-message-pending"
            else:
                if Order_.completed == 0:
                    status = "Incompleted"
                    status_class = "status-incomplete"
                    status_message_class = "status-message-incomplete"
                elif Order_.completed == Order_.amount:
                    status = "Completed"
                    status_class = "status-complete"
                    status_message_class = "status-message-complete"
                else:
                    percent = round((Order_.completed / Order_.amount) * 100)
                    status = f"Completed {percent}%"
                    status_class = "status-partial"
                    status_message_class = "status-message-partial"
            return render(request, 'order_info.html', {
                    'status': status,
                    'amount': Order_.amount,
                    'completed': Order_.completed,
                    'months': Order_.months,
                    'ordered_at': Order_.ordered_at,
                    'finished_at': Order_.finished_at,
                    'order_id': order_id,
                    'server_id': Order_.server_id,
                    'server_invite': Order_.server_invite,
                    'service': Order_.service,
                    'message': Order_.message,
                    'status_class': status_class,
                    'status_message_class': status_message_class,
                })
        except Order.DoesNotExist:
            return render(request, 'no_order.html')
    else:
        return render(request, 'no_order.html')