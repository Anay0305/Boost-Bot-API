# 🎯 WebApp – License & Order Management System

A **full-stack Django application** for managing license/boost keys, live order tracking, stock monitoring, and Discord/autobuy integration.
Designed for **digital product automation**, providing both real-time updates and easy management.

---

## ✨ Why This App Exists

Imagine buying a **digital ticket or license**:

* You redeem it online.
* The system connects to Discord and processes your order automatically.
* You can **track progress live** like a shipment on Amazon.
* Admins can **create keys, monitor stock, and manage orders** effortlessly.

This app automates the complete workflow.

---

## 🛠 Core Features

### Key Management

* Generate new keys (licenses/boost tickets)
* Redeem keys and link them to Discord servers
* Delete or view key details
* Check key redemption status

### Order Tracking

* Live progress: Pending → Completed
* See percentage of completed tasks
* Check order messages, errors, and token status

### Stock Monitoring

* Live stock page shows availability
* Real-time updates for multiple durations (e.g., 1 month, 3 months)

### Secure API & Tokens

* Token-based authentication (access + refresh)
* Admins can update autobuy settings securely

### Autobuy Integration

* Receive webhooks from platforms like SellAuth
* Automatically create and process orders

### WebSockets

* Real-time worker-to-server communication
* Instant updates on order status

### Frontend Pages

* Stock Page
* Order Info Page
* Redeem Key Page
* Admin Panel

---

## 🖥 User Pages

| Page           | Purpose             |
| -------------- | ------------------- |
| `/key/info/`   | Check key status    |
| `/key/redeem/` | Redeem a key        |
| `/stock/`      | Live stock page     |
| `/order/`      | Order tracking page |
| `/admin/`      | Admin dashboard     |

---

## 🚀 How It Works

1. Admin generates keys (licenses/tickets).
2. User redeems a key via the website.
3. Server sends the task to workers.
4. Workers complete boosts/orders and send results back.
5. User sees **live order updates**.

---

## ⚙️ Tech Stack

* **Backend:** Django 5, Django Channels
* **Server:** Uvicorn (ASGI)
* **Static Files:** WhiteNoise
* **Database:** SQLite (default) / PostgreSQL recommended
* **Config:** YAML (`config.yaml`)
* **Auth:** Token-based (access + refresh)
* **Frontend:** HTML + CSS + JS templates

---

## 📡 API Endpoints

All APIs under `/api/`. Protected routes require:
`Authorization: Bearer <access_token>`

### 🔑 Auth

* `POST /api/authorize` → Get access & refresh tokens

```json
{
  "key": "YOUR_INTERNAL_KEY"
}
```

* `POST /api/refresh` → Refresh expired access token

```json
{
  "refresh_token": "ey...xyz"
}
```

### 🔑 Key Management

* `POST /api/key/generate_key` → Generate a key

```json
{
  "key": "ABC-123",
  "amount": 2,
  "months": 1
}
```

* `POST /api/key/delete_key` → Delete a key

```json
{
  "key": "ABC-123"
}
```

* `POST /api/key/get_info` → Get key status

```json
{
  "key": "ABC-123"
}
```

* `POST /api/key/redeem_key` → Redeem a key

```json
{
  "key": "ABC-123",
  "invite": "discord.gg/server"
}
```

### 📦 Orders

* `POST /api/get_order_info` → Fetch order progress

```json
{
  "order_id": "abcd1234"
}
```

Example Response:

```json
{
  "status": "Completed 50%",
  "amount": 4,
  "completed": 2,
  "months": 1,
  "order_id": "abcd1234",
  "server_invite": "https://discord.gg/xyz"
}
```

### 🔔 Webhooks

* `POST /api/webhook/autobuy` → Receive autobuy orders

```json
{
  "invoice_id": "inv_123",
  "email": "user@example.com",
  "item": {
    "product": { "name": "2x Nitro [3 Month]" },
    "custom_fields": { "Invite": "abc", "Nickname": "user1" }
  }
}
```

### 🛠 Worker → Server

* `POST /api/result` → Worker sends boost result

```json
{
  "id": "worker1",
  "result": {
    "success": true,
    "order_id": "abcd1234",
    "tokens": ["token1", "token2"]
  }
}
```

### 📡 WebSocket

Connect for real-time updates:

```
ws://<host>:<port>/ws/boost/?token=<access_token>
```

---

## 📂 Project Structure (Simplified)

```
API/         → Core app (views, models, consumers, routing)
WebApp/      → Project settings (settings, urls, asgi/wsgi)
templates/   → HTML pages (stock, order, key info, redeem)
static/      → CSS + JS assets
config.yaml  → Port, superuser, links
```

---

## 🧭 Quick Start

```bash
# Clone & enter project
git clone <repo-url>
cd <project>

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Migrate database
python manage.py migrate

# Run dev server
python manage.py runserver
# Or use runner.py (auto-superuser, migrations, Uvicorn)
```

---

## 📬 Contact

**Anay Gupta**
📧 [anaysumeet@gmail.com](mailto:anaysumeet@gmail.com)

---

## 📝 License

MIT License – free to use and adapt.
