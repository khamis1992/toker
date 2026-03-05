# TikTok Bot - How to Run Viewers

## ✅ Fixes Applied

1. **Fixed async database error** - Bot now properly creates viewer records
2. **Fixed undefined variable bug** - Viewers list now properly initialized  
3. **Added auto-refresh to session detail page** - Viewers update every 5 seconds
4. **Created API endpoint** - Real-time viewer status

## 🚀 How to Start a Session (3 Methods)

### Method 1: Command Line (RECOMMENDED - Most Reliable)

1. **Open a NEW Command Prompt window**
   - Press `Win + R`
   - Type `cmd`
   - Press Enter

2. **Navigate to project folder:**
   ```cmd
   cd C:\Users\khamis\Documents\tiktokbot
   ```

3. **Run the bot:**
   ```cmd
   python manage.py run_tiktok_bot
   ```

4. **You'll see output like:**
   ```
   ✓ Created new session: abc12345
   ✓ Loaded X active proxies.
   INFO: Viewer 1: Starting session
   INFO: Viewer 2: Starting session
   INFO: Viewer 3: Starting session
   INFO: Viewer 1: Loading page...
   INFO: Viewer 1: Page loaded (status: 200)
   INFO: Viewer 1: ✅ WATCHING
   ```

5. **KEEP THIS WINDOW OPEN** - The bot runs as long as this window is open!

6. **To view viewers:**
   - Open your browser
   - Go to Bot Control page
   - Click "Details" on the active session
   - You'll see 3 viewers with status "running"

7. **To stop:**
   - Press `Ctrl + C` in the command prompt window

---

### Method 2: Dashboard (Background Process)

1. Go to **Settings** page
   - Set **Number of Viewers** to 3-5 (not more!)
   - Click "Save Settings"

2. Go to **Bot Control** page

3. Click **"Start New Session"** button

4. The bot will start in the background

5. **Refresh the page** - you should see an active session card

6. Click **"Details"** (eye icon) to see viewers

**Note:** Background processes may be less reliable. Method 1 is preferred.

---

### Method 3: Batch File (Easiest)

1. **Double-click** `start_viewers.bat` in your project folder

2. The bot will start in a new window

3. Keep the window open while running

4. Close the window to stop the bot

---

## 📊 Viewing Your Viewers

### In the Dashboard:

1. **Bot Control Page:**
   - Shows active session cards
   - Each card displays: Session ID, Status, Viewer count, Success count

2. **Session Detail Page:**
   - Click "Details" (eye icon) on any session
   - Shows table with all viewers
   - Auto-refreshes every 5 seconds
   - Displays: Viewer ID, Status, Proxy, Comments, Reactions

### Check via Command Line:

```cmd
python manage.py shell -c "from bot_management.models import BotSession, Viewer; s = BotSession.objects.latest('start_time'); v = list(Viewer.objects.filter(session=s)); print(f'Session: {s.session_id} ({s.status})'); [print(f'  Viewer {x.viewer_id}: {x.status}') for x in v]"
```

---

## ⚠️ Important Notes

### Proxies:
- **Free proxies don't work** - They're unreliable and mostly dead
- **Running without proxies works** - But may get rate-limited by TikTok
- **Best option:** Purchase proxies from a reputable provider

### Viewer Count:
- **Start with 3 viewers** (default)
- **Maximum 5-10 viewers** per session
- **More viewers = more likely to get detected/banned**

### Session Duration:
- Default max: 30 minutes
- Adjust in Settings → "Max Duration"
- Longer sessions = higher detection risk

### Headless Mode:
- **Enabled by default** (no browser windows visible)
- Disable in Settings if you want to see the browsers

---

## 🔧 Troubleshooting

### Problem: "No viewers showing in dashboard"

**Solution:**
1. Make sure you ran `python manage.py run_tiktok_bot` in a terminal
2. Keep the terminal window OPEN
3. Refresh the dashboard page
4. Click "Details" on the active session

### Problem: "All viewers failed"

**Causes:**
- Bad proxies (most common)
- TikTok URL is not a live stream
- Network issues

**Solution:**
1. Disable all proxies: Go to Proxy Management → Deactivate all
2. Run again without proxies
3. Check if your TikTok URL is correct and the stream is LIVE

### Problem: "Session starts but immediately completes"

**Causes:**
- Stream is offline
- Bot configuration issues

**Solution:**
1. Check your live URL: `https://www.tiktok.com/@khamish92/live`
2. Make sure @khamish92 is currently LIVE on TikTok
3. Check logs in the terminal window

---

## 📝 Current Configuration

```
Live URL: https://www.tiktok.com/@khamish92/live
Viewers: 3
Max Duration: 30 minutes
Headless: True (no visible browsers)
```

To change settings: Go to Settings page in dashboard

---

## 🎯 Quick Start Guide

**For immediate testing:**

1. Open Command Prompt
2. Run: `cd C:\Users\khamis\Documents\tiktokbot`
3. Run: `python manage.py run_tiktok_bot`
4. Open browser → Bot Control → Click "Details"
5. You should see 3 viewers with status "running" or "starting"

**That's it!** The bot is now watching your TikTok live stream.
