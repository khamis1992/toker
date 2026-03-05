import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiktok_dashboard.settings')
sys.path.insert(0, 'C:\\Users\\khamis\\Documents\\tiktokbot')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

# Test both passwords
username = 'admin'
passwords_to_test = ['password', 'pawssword']

print("Testing admin user login credentials...")
print("="*50)

for password in passwords_to_test:
    user = authenticate(username=username, password=password)
    if user is not None:
        print(f"[OK] SUCCESS: Password '{password}' works!")
        print(f"  User: {user.username}")
        print(f"  Superuser: {user.is_superuser}")
        print(f"  Staff: {user.is_staff}")
    else:
        print(f"[FAIL] Password '{password}' does not work")

print("="*50)

# Show current user info
try:
    admin_user = User.objects.get(username='admin')
    print(f"\nAdmin user exists:")
    print(f"  Username: {admin_user.username}")
    print(f"  Email: {admin_user.email}")
    print(f"  Is superuser: {admin_user.is_superuser}")
    print(f"  Is staff: {admin_user.is_staff}")
    print(f"  Is active: {admin_user.is_active}")
    print(f"  Date joined: {admin_user.date_joined}")
    print(f"  Last login: {admin_user.last_login}")
except User.DoesNotExist:
    print("Admin user does not exist!")
