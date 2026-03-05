#!/usr/bin/env python3
"""
Script to start the TikTok Bot Dashboard server and open the web page.
"""

import subprocess
import webbrowser
import time
import sys
import os

def start_dashboard():
    """Start the Django server and open the web page."""
    print("=" * 50)
    print("           TIKTOK BOT DASHBOARD")
    print("=" * 50)
    print("Login Information:")
    print("  Username: admin")
    print("  Password: password")
    print("-" * 50)
    
    try:
        # Start the Django server in the background
        print("Starting Django development server...")
        server_process = subprocess.Popen([
            sys.executable, "manage.py", "runserver"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Give the server time to start
        print("Waiting for server to start...")
        time.sleep(5)
        
        # Check if server started successfully
        if server_process.poll() is None:
            print("✓ Server started successfully!")
            
            # Open the web browser
            print("Opening dashboard in your web browser...")
            webbrowser.open("http://localhost:8000")
            
            print("\n✨ Dashboard is now running!")
            print("➡️  Browser opened to: http://localhost:8000")
            print("🔐 Use the credentials above to log in")
            print("\n🛑 TO STOP THE SERVER:")
            print("   Close this window or press Ctrl+C")
            print("=" * 50)
            
            # Keep the script running
            try:
                server_process.communicate()
            except KeyboardInterrupt:
                print("\n🛑 Shutting down server...")
                server_process.terminate()
                server_process.wait()
                print("✅ Server stopped.")
        else:
            print("❌ Failed to start server:")
            print("   Please check that port 8000 is not in use")
            print("   and that all required packages are installed.")
            
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    start_dashboard()