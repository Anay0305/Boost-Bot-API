import os
import django
from django.core.management import call_command
from django.contrib.auth import get_user_model
import uvicorn
import yaml

with open('config.yaml', 'r') as file:
    config = yaml.safe_load(file)
superuser = config.get('SUPERUSER', {})

if superuser:
    username = superuser.get('USERNAME')
    password = superuser.get('PASSWORD')
    email = superuser.get('EMAIL')
else:
    username = None
    password = None
    email = None

port = config.get('PORT', 8080)
try:
    port = int(port)
except ValueError:
    print(f"❌ Invalid port number: {port}. Using default port 8000.")
    port = 8080

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WebApp.settings')
django.setup()

print("➡️ Making migrations...")
call_command('makemigrations', 'API', interactive=False)

print("➡️ Applying migrations...")
call_command('migrate', interactive=False)

print("➡️ Collecting static files...")
call_command('collectstatic', interactive=False, verbosity=0)

if username is not None:
    User = get_user_model()
    if not User.objects.filter(username=username).exists():
        print(f"✅ Creating superuser: {username}")
        User.objects.create_superuser(username, email, password)
    else:
        print(f"✅ Superuser '{username}' already exists.")

print("🚀 Starting Uvicorn server...")
uvicorn.run("WebApp.asgi:application", host="0.0.0.0", port=int(port))