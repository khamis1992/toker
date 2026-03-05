# TikTok Bot Dashboard

A web-based interface for controlling and monitoring your TikTok bot.

## Quick Start

1. **Double-click** on `launch_dashboard.bat` to start the dashboard
2. Your web browser will automatically open to http://localhost:8000
3. **Login** with:
   - Username: `admin`
   - Password: `password`

## Features

### Dashboard Home
Overview of bot status and quick actions.

### Bot Control
- Start new bot sessions with one click
- Monitor active sessions in real-time
- View detailed statistics for each session
- Stop sessions when needed

### Settings Management
Change all bot configuration parameters through web forms:
- Live stream URL
- Number of viewers
- Timing settings
- Browser settings
- Advanced configuration options

### Proxy Management
- Add new proxies
- Activate/deactivate proxies
- Delete proxies
- View proxy status and usage history

### Logs
- View system logs in real-time
- Filter logs by severity level
- Monitor bot activity and errors

## Usage

### Starting the Dashboard
Double-click on `launch_dashboard.bat` or run:
```bash
python start_dashboard.py
```

### Stopping the Dashboard
Close the command window or press **Ctrl+C**

## Login Credentials
- **Username**: admin
- **Password**: password

## Security Notes
- Change the default password immediately after first login
- This is for development use only
- Not suitable for production without additional security measures

## Troubleshooting

### Port Already in Use
If you get an error about port 8000 being in use:
1. Close any other running instances
2. Run: `python manage.py runserver 8001` to use port 8001 instead

### Missing Packages
Install required packages:
```bash
pip install django celery redis
```

## File Structure
```
tiktokbot/
├── launch_dashboard.bat      # Double-click launcher
├── start_dashboard.py        # Python launcher script
├── manage.py                 # Django management
├── tiktok_dashboard/         # Main Django project
├── dashboard/                # Dashboard app
├── bot_management/           # Bot management app
└── templates/                # HTML templates
```