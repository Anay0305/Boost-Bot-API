import json
import secrets
from datetime import timedelta
from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.utils import timezone
from functools import wraps
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import RedeemCode, Order, Token
from .results import RESULTS
from datetime import datetime
from django.utils.timezone import make_aware
from django.utils.timezone import now
from django.http import HttpResponse
import uuid
import time
import re
import requests

autobuy_data = {}
TOKEN_EXPIRY_SECONDS = 3600
MAX_WAIT_SECONDS = 120
WAIT_INTERVAL = 5

def custom_404(request, exception):
    return redirect('/stock')

def censor_key_parts(key):
    parts = key.split('-')
    masked = [p[:2] + '*' * (len(p) - 3) + p[-1:] for p in parts]
    return '-'.join(masked)

def check_invite(invite):
    if not invite:
        return None
    if invite.startswith("https://"):
        return invite
    else:
        if invite.startswith("discord"):
            return f"https://{invite}"
        try:
            r = requests.get(
                f"https://discord.com/api/v9/invites/{invite}?inputValue={invite}&with_counts=true&with_expiration=true"
            )
            if r.status_code == 200:
                return f"https://discord.gg/{invite}"
            return invite
        except Exception as e:
            return invite

def extract_amount_and_months(name):
    match = re.search(r"(\d+)x.*\[(\d+)\s*Month", name)
    if match:
        amount = int(match.group(1))
        months = int(match.group(2))
        return amount, months
    return None, None

def generate_token():
    return secrets.token_urlsafe(32)

def token_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JsonResponse({"error": "Unauthorized"}, status=401)

        access_token = auth_header.split("Bearer ")[1]
        try:
            token = Token.objects.get(access_token=access_token)
            #if token.is_expired():
            #    return JsonResponse({"error": "Token expired"}, status=401)
        except Token.DoesNotExist:
            return JsonResponse({"error": "Invalid token"}, status=401)

        return view_func(request, *args, **kwargs)
    return wrapper

@csrf_exempt
def authorize(request):
    global autobuy_data
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    key = request.POST.get("key")
    if not key or key != "2272ae95d39833092b48de480cdd0c3244f20098859d6a44b69ddf641b5bd4be":
        return JsonResponse({"error": "Invalid API key"}, status=401)

    try:
        autobuy_data_raw = request.POST.get("autobuy")
        autobuy_data = json.loads(autobuy_data_raw)
    except:
        autobuy_data = {}

    access_token = generate_token()
    refresh_token = generate_token()
    expires_at = timezone.now() + timedelta(seconds=TOKEN_EXPIRY_SECONDS)

    Token.objects.create(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_at=expires_at,
        ip_address=request.META.get("REMOTE_ADDR"),
        user_agent=request.META.get("HTTP_USER_AGENT", "")
    )

    return JsonResponse({
        "access_token": access_token,
        "refresh_token": refresh_token
    })

@csrf_exempt
def refresh_token(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    refresh_token_value = request.POST.get("refresh_token")
    if not refresh_token_value:
        return JsonResponse({"error": "Missing refresh token"}, status=400)

    try:
        token = Token.objects.get(refresh_token=refresh_token_value)
    except Token.DoesNotExist:
        return JsonResponse({"error": "Invalid refresh token"}, status=401)

    new_access_token = generate_token()
    new_expiry = timezone.now() + timedelta(seconds=TOKEN_EXPIRY_SECONDS)

    token.access_token = new_access_token
    token.expires_at = new_expiry
    token.save(update_fields=["access_token", "expires_at"])

    return JsonResponse({
        "access_token": new_access_token
    })

@csrf_exempt
@token_required
def update_autobuy(request):
    global autobuy_data
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    autobuy_data_raw = request.POST.get("autobuy")
    if not autobuy_data_raw:
        return JsonResponse({"error": "Missing Autobuy Data"}, status=400)
    else:
        try:
            autobuy_data = json.loads(autobuy_data_raw)
            print("Autobuy Data Updated.")
            return JsonResponse({'success': True}, status=200)
        except Exception:
            return JsonResponse({'success': False}, status=201)

@csrf_exempt
def autobuy(request):
    if request.method == "POST":
        channel_layer = get_channel_layer()
        id = str(uuid.uuid4())[:8]

        try:
            data = json.loads(request.body)
            invoice_id = data.get("invoice_id")
            email = data.get("email")
            product_id = data.get("item").get("product_id")
            shop_id = data.get("shop_id")
            item_custom_fields = data.get("item", {}).get("custom_fields", {})
            if not item_custom_fields:
                return JsonResponse({"error": "Custom fields are missing or empty."}, status=400)

            fields = {
                field: item_custom_fields[field]
                for field in item_custom_fields if field in ["Invite", "Nickname", "Bio", "Avatar", "Banner"]
            }

            invite = fields.get("Invite")
            nickname = fields.get("Nickname")
            bio = fields.get("Bio")
            avatar = fields.get("Avatar")
            banner = fields.get("Banner")

            if str(shop_id) not in autobuy_data:
                return HttpResponse(
                    f"Shop ID not found in autobuy."
                )
            if product_id not in autobuy_data[str(shop_id)]['product_ids']:
                return HttpResponse(
                    f"Product ID not found in autobuy."
                )

            amount, months = extract_amount_and_months(data.get("item").get("product").get("name"))

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
            return HttpResponse(
                    f"Order received. Your boosts will be processed shortly.\n\nYou can check the live status of your order on https://{base_url}/order?order_id={id}"
                )

        except Exception as e:
            print(f"SellAuth Webhook Error: {str(e)}")
            return HttpResponse(
                f"Internal Server Error."
            )

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
                '1m_ava': data['1_month']['available'] * 2,
                '1m_inuse': data['1_month']['in_use'] * 2,
                '1m_total': data['1_month']['total'] * 2,
                '3m_ava': data['3_month']['available'] * 2,
                '3m_inuse': data['3_month']['in_use'] * 2,
                '3m_total': data['3_month']['total'] * 2,
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

@csrf_exempt
@token_required
def delete_key(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            key = data.get('key')
            try:
                code = RedeemCode.objects.get(key=key)
            except RedeemCode.DoesNotExist:
                return JsonResponse({"status": "failed"}, status=404)
            data = {
                'status': "Redeemed" if code.redeemed else "Not Redeemed",
                'key': code.key,
                'amount': code.amount,
                'month': code.months,
                'created_at': code.created_at,
                'redeemed_at': code.redeemed_at
            }
            code.delete()
            return JsonResponse({"success": True, "key_info": data})

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
                    'server_invite': check_invite(redeem_code.server_invite)
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
                order_status = "Pending"
                message = None
                completed = 0
                if redeem_code.order_id:
                    try:
                        Order_ = Order.objects.get(order_id=redeem_code.order_id)
                        if not Order_.finished_at:
                            order_status = "Pending"
                        else:
                            if Order_.completed == 0:
                                order_status = "Incompleted"
                            elif Order_.completed == Order_.amount:
                                order_status = "Completed"
                            else:
                                percent = round((Order_.completed / Order_.amount) * 100)
                                order_status = f"Completed {percent}%"
                            completed = Order_.completed
                            message = Order_.message
                    except:
                        pass
                data = {
                    'status': status,
                    'key': redeem_code.key,
                    'order_id': redeem_code.order_id,
                    'server_id': redeem_code.server_id,
                    'server_invite': check_invite(redeem_code.server_invite),
                    'amount': redeem_code.amount,
                    'months': redeem_code.months,
                    'order_status': order_status,
                    'created_at': redeem_code.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    'redeemed_at': redeemed_at,
                    'message': message,
                    'completed': completed,
                }
                return JsonResponse(data)
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
                    redeem_code.server_invite = check_invite(res['request']['invite'])
                    redeem_code.save()
                if 'message' in res:
                    msg = res['message']
                elif 'error' in res:
                    msg = res['error']
                else:
                    msg = None
                return JsonResponse({"status": res['success'], "message": msg})
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
                    order_obj.server_invite = check_invite(invite)
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
                        server_invite=check_invite(invite),
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
                    server_invite=check_invite(invite),
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
                    'server_invite': check_invite(Order_.server_invite),
                    'service': Order_.service,
                    'message': Order_.message,
                    'status_class': status_class,
                    'status_message_class': status_message_class,
                })
        except Order.DoesNotExist:
            return render(request, 'no_order.html')
    else:
        return render(request, 'no_order.html')
    
@csrf_exempt
@token_required
def get_order_info(request):
    if request.method == "POST":
        data = json.loads(request.body)
        order_id = data.get('order_id')
        if order_id is None:
            return JsonResponse({"error": "No Order Found"}, status=404)
        else:
            try:
                Order_ = Order.objects.get(order_id=order_id)
                if not Order_.finished_at:
                    status = "Pending"
                else:
                    if Order_.completed == 0:
                        status = "Incompleted"
                    elif Order_.completed == Order_.amount:
                        status = "Completed"
                    else:
                        percent = round((Order_.completed / Order_.amount) * 100)
                        status = f"Completed {percent}%"
                return JsonResponse({
                        'status': status,
                        'amount': Order_.amount,
                        'completed': Order_.completed,
                        'months': Order_.months,
                        'ordered_at': Order_.ordered_at,
                        'finished_at': Order_.finished_at,
                        'order_id': order_id,
                        'server_id': Order_.server_id,
                        'server_invite': check_invite(Order_.server_invite),
                        'service': Order_.service,
                        'message': Order_.message,
                    }, status=200)
            except Order.DoesNotExist:
                return JsonResponse({"error": "No Order Found"}, status=404)
    else:
        return JsonResponse({"error": "Invalid Method"}, status=405)