import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiktok_dashboard.settings')
sys.path.insert(0, 'C:\\Users\\khamis\\Documents\\tiktokbot')
django.setup()

from django.contrib.auth.models import User

# Create admin user if it doesn't exist
username = 'admin'
password = 'pawssword'
email = 'admin@example.com'

try:
    user = User.objects.get(username=username)
    print(f"User '{username}' already exists. Updating password...")
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"Password updated for user '{username}'")
except User.DoesNotExist:
    user = User.objects.create_superuser(username, email, password)
    print(f"Created superuser: {username}")

print("Done!")
