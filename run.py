import os
import django
from django.core.management import call_command
from django.contrib.auth import get_user_model
import uvicorn

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'WebApp.settings')
django.setup()

print("➡️ Making migrations...")
call_command('makemigrations', 'API', interactive=False)

print("➡️ Applying migrations...")
call_command('migrate', interactive=False)

print("➡️ Collecting static files...")
call_command('collectstatic', interactive=False, verbosity=0)

User = get_user_model()
username = 'Anay'
email = 'anaysumeet@gmail.com'
password = 'Anayg6@7'

if not User.objects.filter(username=username).exists():
    print(f"✅ Creating superuser: {username}")
    User.objects.create_superuser(username, email, password)
else:
    print(f"✅ Superuser '{username}' already exists.")

print("🚀 Starting Uvicorn server...")
print("Enter Port: ")
port = input()
uvicorn.run("WebApp.asgi:application", host="0.0.0.0", port=int(port))
