import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tiktok_dashboard.settings')
sys.path.insert(0, 'C:\\Users\\khamis\\Documents\\tiktokbot')
django.setup()

from django.contrib.auth.models import User

# Set password to 'password'
username = 'admin'
password = 'password'

try:
    user = User.objects.get(username=username)
    print(f"User '{username}' exists. Setting password to '{password}'...")
    user.set_password(password)
    user.is_staff = True
    user.is_superuser = True
    user.save()
    print(f"Password updated successfully!")
    
    # Verify it works
    from django.contrib.auth import authenticate
    auth_user = authenticate(username=username, password=password)
    if auth_user is not None:
        print(f"Verification: Login works with password '{password}'")
    else:
        print(f"Verification FAILED")
except User.DoesNotExist:
    print(f"User '{username}' does not exist!")

print("Done!")
