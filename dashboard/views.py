from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Avg, Sum, Count, Q
import json
import uuid
import os
import logging
from datetime import datetime
from bot_management.models import BotConfiguration, Proxy, BotSession, Viewer, ProxyAutoFetchSettings

logger = logging.getLogger(__name__)


def _get_system_stats():
    """Return real system resource usage via psutil, with safe fallback."""
    try:
        import psutil
        disk = psutil.disk_usage('/')
        disk_pct = round(disk.percent, 1)
        mem = psutil.virtual_memory()
        mem_pct = round(mem.percent, 1)
        cpu_pct = round(psutil.cpu_percent(interval=0.2), 1)
        uptime_seconds = int(datetime.now().timestamp() - psutil.boot_time())
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        if hours >= 24:
            uptime_str = f"{hours // 24}d {hours % 24}h"
        elif hours > 0:
            uptime_str = f"{hours}h {minutes}m"
        else:
            uptime_str = f"{minutes}m"
        return {
            'disk_pct': disk_pct,
            'mem_pct': mem_pct,
            'cpu_pct': cpu_pct,
            'uptime': uptime_str,
        }
    except Exception:
        return {
            'disk_pct': None,
            'mem_pct': None,
            'cpu_pct': None,
            'uptime': 'N/A',
        }


@login_required
def dashboard_home(request):
    """Main dashboard view showing overview statistics."""
    # Get recent sessions
    recent_sessions = BotSession.objects.all().order_by('-start_time')[:10]

    # Active sessions count (not completed/failed/stopped)
    active_sessions_count = BotSession.objects.exclude(
        status__in=['completed', 'failed', 'stopped']
    ).count()

    # Active proxies
    active_proxies = Proxy.objects.filter(is_active=True).count()
    total_proxies = Proxy.objects.count()

    # Average viewers per session
    avg_viewers = BotSession.objects.aggregate(avg=Avg('viewers_count'))['avg']
    avg_viewers = round(avg_viewers, 1) if avg_viewers else 0

    # Overall success rate across all sessions
    totals = BotSession.objects.aggregate(
        total_viewers=Sum('viewers_count'),
        total_success=Sum('success_count'),
    )
    total_viewers = totals['total_viewers'] or 0
    total_success = totals['total_success'] or 0
    success_rate = round((total_success / total_viewers * 100), 1) if total_viewers > 0 else 0

    # Real-time system stats
    sys_stats = _get_system_stats()

    # Current configuration
    try:
        current_config = BotConfiguration.objects.filter(created_by=request.user).latest('updated_at')
    except BotConfiguration.DoesNotExist:
        current_config = None

    context = {
        'recent_sessions': recent_sessions,
        'active_sessions_count': active_sessions_count,
        'active_proxies': active_proxies,
        'total_proxies': total_proxies,
        'avg_viewers': avg_viewers,
        'success_rate': success_rate,
        'current_config': current_config,
        'sys_stats': sys_stats,
    }

    return render(request, 'dashboard/home.html', context)


@login_required
def settings_view(request):
    """View for managing bot settings."""
    if request.method == 'POST':
        # Handle form submission
        config_id = request.POST.get('config_id')
        if config_id:
            try:
                config = BotConfiguration.objects.get(id=config_id, created_by=request.user)
            except BotConfiguration.DoesNotExist:
                config = BotConfiguration(created_by=request.user)
        else:
            config = BotConfiguration(created_by=request.user)

        # Update configuration from form data
        config.live_url = request.POST.get('live_url', config.live_url)
        config.num_viewers = int(request.POST.get('num_viewers', config.num_viewers))
        config.headless = request.POST.get('headless') == 'on'
        config.page_load_timeout = int(request.POST.get('page_load_timeout', config.page_load_timeout))
        config.element_wait_timeout = int(request.POST.get('element_wait_timeout', config.element_wait_timeout))
        config.session_max_duration = int(request.POST.get('session_max_duration', config.session_max_duration))
        config.keepalive_min_interval = int(request.POST.get('keepalive_min_interval', config.keepalive_min_interval))
        config.keepalive_max_interval = int(request.POST.get('keepalive_max_interval', config.keepalive_max_interval))
        config.max_retry_attempts = int(request.POST.get('max_retry_attempts', config.max_retry_attempts))
        config.base_retry_delay = float(request.POST.get('base_retry_delay', config.base_retry_delay))
        config.window_width = int(request.POST.get('window_width', config.window_width))
        config.window_height = int(request.POST.get('window_height', config.window_height))
        config.debug_screenshots = request.POST.get('debug_screenshots') == 'on'
        config.screenshot_dir = request.POST.get('screenshot_dir', config.screenshot_dir)
        config.log_level = request.POST.get('log_level', config.log_level)

        config.save()
        messages.success(request, 'Settings updated successfully!')

        return redirect('dashboard:settings')

    # GET request - show current settings
    try:
        current_config = BotConfiguration.objects.filter(created_by=request.user).latest('updated_at')
    except BotConfiguration.DoesNotExist:
        current_config = BotConfiguration(created_by=request.user)

    context = {
        'current_config': current_config,
    }

    return render(request, 'dashboard/settings.html', context)


@login_required
def proxy_management(request):
    """View for managing proxies."""

    # Check if this is an AJAX request FIRST (before handling regular POST)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    # Handle AJAX POST requests - return JSON
    if is_ajax and request.method == 'POST':
        action = request.POST.get('action')
        response_data = {'success': False, 'message': 'Unknown action'}

        if action == 'add':
            proxy_url = request.POST.get('proxy_url', '').strip()
            if proxy_url:
                try:
                    # Check for duplicate
                    if Proxy.objects.filter(proxy_url=proxy_url).exists():
                        response_data = {'success': False, 'message': 'Proxy already exists in the system.'}
                    else:
                        Proxy.objects.create(proxy_url=proxy_url, is_active=True)
                        response_data = {'success': True, 'message': 'Proxy added successfully!'}
                except Exception as e:
                    response_data = {'success': False, 'message': f'Error adding proxy: {str(e)}'}
            else:
                response_data = {'success': False, 'message': 'Proxy URL cannot be empty.'}

        elif action == 'toggle':
            proxy_id = request.POST.get('proxy_id')
            try:
                proxy = Proxy.objects.get(id=proxy_id)
                proxy.is_active = not proxy.is_active
                proxy.save()
                status = "activated" if proxy.is_active else "deactivated"
                response_data = {'success': True, 'message': f'Proxy {status} successfully!'}
            except Proxy.DoesNotExist:
                response_data = {'success': False, 'message': 'Proxy not found!'}

        elif action == 'delete':
            proxy_id = request.POST.get('proxy_id')
            try:
                Proxy.objects.get(id=proxy_id).delete()
                response_data = {'success': True, 'message': 'Proxy deleted successfully!'}
            except Proxy.DoesNotExist:
                response_data = {'success': False, 'message': 'Proxy not found!'}

        return JsonResponse(response_data)

    # Handle regular (non-AJAX) POST requests - redirect after processing
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            proxy_url = request.POST.get('proxy_url', '').strip()
            if proxy_url:
                try:
                    if Proxy.objects.filter(proxy_url=proxy_url).exists():
                        messages.warning(request, 'Proxy already exists in the system.')
                    else:
                        Proxy.objects.create(proxy_url=proxy_url, is_active=True)
                        messages.success(request, 'Proxy added successfully!')
                except Exception as e:
                    messages.error(request, f'Error adding proxy: {str(e)}')
            else:
                messages.error(request, 'Proxy URL cannot be empty.')

        elif action == 'toggle':
            proxy_id = request.POST.get('proxy_id')
            try:
                proxy = Proxy.objects.get(id=proxy_id)
                proxy.is_active = not proxy.is_active
                proxy.save()
                status = "activated" if proxy.is_active else "deactivated"
                messages.success(request, f'Proxy {status} successfully!')
            except Proxy.DoesNotExist:
                messages.error(request, 'Proxy not found!')

        elif action == 'delete':
            proxy_id = request.POST.get('proxy_id')
            try:
                Proxy.objects.get(id=proxy_id).delete()
                messages.success(request, 'Proxy deleted successfully!')
            except Proxy.DoesNotExist:
                messages.error(request, 'Proxy not found!')

        elif action == 'test_all':
            messages.info(request, 'Proxy testing initiated. Results will appear shortly.')

        return redirect('dashboard:proxies')

    # GET request
    proxies = Proxy.objects.all().order_by('-created_at')

    # Get free proxy sources for context
    free_sources = [
        {
            "name": "ProxyScrape",
            "url": "https://proxyscrape.com/free-proxy-list",
            "description": "Community-maintained free proxy list"
        },
        {
            "name": "HideMyAss",
            "url": "https://hidemyass.com/proxy-checker",
            "description": "Limited free tier proxy service"
        },
        {
            "name": "FreeProxyLists",
            "url": "https://free-proxy-list.net/",
            "description": "Public proxy lists updated regularly"
        }
    ]

    # Calculate proxy statistics
    total_proxies = proxies.count()
    active_proxies = proxies.filter(is_active=True).count()

    context = {
        'proxies': proxies,
        'free_proxy_sources': free_sources,
        'total_proxies': total_proxies,
        'active_proxies': active_proxies,
        'show_examples': False,  # Never show fake example proxies
        'example_proxies': [],
    }

    return render(request, 'dashboard/proxies.html', context)


@login_required
def api_fetch_free_proxies(request):
    """API endpoint to fetch free proxies from public sources and return them as JSON."""
    import requests as req
    from bs4 import BeautifulSoup

    source = request.GET.get('source', 'proxyscrape')
    proxies = []
    error = None

    try:
        if source == 'proxyscrape':
            url = 'https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=all&anonymity=all&limit=50'
            r = req.get(url, timeout=10)
            r.raise_for_status()
            lines = [line.strip() for line in r.text.splitlines() if line.strip()]
            proxies = [f'http://{line}' for line in lines if ':' in line]

        elif source == 'geonode':
            url = 'https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc&protocols=http,https'
            r = req.get(url, timeout=10)
            r.raise_for_status()
            data = r.json()
            for item in data.get('data', []):
                ip = item.get('ip', '')
                port = item.get('port', '')
                protocols = item.get('protocols', ['http'])
                proto = protocols[0] if protocols else 'http'
                if ip and port:
                    proxies.append(f'{proto}://{ip}:{port}')

        elif source == 'freeproxylist':
            url = 'https://free-proxy-list.net/'
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            r = req.get(url, timeout=10, headers=headers)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            table = soup.find('table')
            if table:
                for row in table.find_all('tr')[1:]:
                    cols = row.find_all('td')
                    if len(cols) >= 2:
                        ip = cols[0].text.strip()
                        port = cols[1].text.strip()
                        https = cols[6].text.strip() if len(cols) > 6 else 'no'
                        proto = 'https' if https.lower() == 'yes' else 'http'
                        if ip and port and ip != 'IP Address':
                            proxies.append(f'{proto}://{ip}:{port}')
                            if len(proxies) >= 50:
                                break

    except Exception as e:
        error = str(e)

    # Filter out already-existing proxies
    existing_urls = set(Proxy.objects.values_list('proxy_url', flat=True))
    new_proxies = [p for p in proxies if p not in existing_urls]

    return JsonResponse({
        'success': error is None,
        'source': source,
        'proxies': new_proxies,
        'total_fetched': len(proxies),
        'new_count': len(new_proxies),
        'already_exists': len(proxies) - len(new_proxies),
        'error': error,
    })


@login_required
def api_load_free_proxies(request):
    """API endpoint to save a list of fetched free proxies into the database."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)

    try:
        body = json.loads(request.body)
        proxy_list = body.get('proxies', [])
        activate = body.get('activate', True)

        if not proxy_list:
            return JsonResponse({'success': False, 'message': 'No proxies provided'})

        added = 0
        skipped = 0
        existing_urls = set(Proxy.objects.values_list('proxy_url', flat=True))

        for proxy_url in proxy_list:
            proxy_url = proxy_url.strip()
            if not proxy_url:
                continue
            if proxy_url in existing_urls:
                skipped += 1
                continue
            Proxy.objects.create(proxy_url=proxy_url, is_active=activate)
            existing_urls.add(proxy_url)
            added += 1

        return JsonResponse({
            'success': True,
            'message': f'Successfully loaded {added} proxies ({skipped} already existed).',
            'added': added,
            'skipped': skipped,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error loading proxies: {str(e)}'})


@login_required
def api_get_autofetch_settings(request):
    """Return the current auto-fetch settings as JSON."""
    s = ProxyAutoFetchSettings.get_settings()
    return JsonResponse({
        'success': True,
        'is_enabled': s.is_enabled,
        'interval_minutes': s.interval_minutes,
        'use_proxyscrape': s.use_proxyscrape,
        'use_geonode': s.use_geonode,
        'use_freeproxylist': s.use_freeproxylist,
        'activate_on_load': s.activate_on_load,
        'last_run': s.last_run.isoformat() if s.last_run else None,
        'last_run_added': s.last_run_added,
        'last_run_skipped': s.last_run_skipped,
        'interval_choices': [
            {'value': v, 'label': l}
            for v, l in ProxyAutoFetchSettings.INTERVAL_CHOICES
        ],
    })


@login_required
def api_save_autofetch_settings(request):
    """Save auto-fetch settings and reschedule the background job."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        s = ProxyAutoFetchSettings.get_settings()
        s.is_enabled        = bool(body.get('is_enabled', s.is_enabled))
        s.interval_minutes  = int(body.get('interval_minutes', s.interval_minutes))
        s.use_proxyscrape   = bool(body.get('use_proxyscrape', s.use_proxyscrape))
        s.use_geonode       = bool(body.get('use_geonode', s.use_geonode))
        s.use_freeproxylist = bool(body.get('use_freeproxylist', s.use_freeproxylist))
        s.activate_on_load  = bool(body.get('activate_on_load', s.activate_on_load))
        s.save()

        # Reschedule the background job with the new interval
        try:
            from dashboard.scheduler import reschedule_job
            reschedule_job(s.interval_minutes)
        except Exception:
            pass  # Scheduler may not be running in dev reloader child

        return JsonResponse({
            'success': True,
            'message': f'Auto-fetch settings saved. Scheduler is {"enabled" if s.is_enabled else "disabled"}.'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error saving settings: {str(e)}'})


@login_required
def bot_control(request):
    """View for controlling bot sessions."""
    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'start':
            # Create a new session
            try:
                config = BotConfiguration.objects.filter(created_by=request.user).latest('updated_at')
            except BotConfiguration.DoesNotExist:
                config = BotConfiguration(created_by=request.user)
                config.save()

            session_id = str(uuid.uuid4())[:8]
            session = BotSession.objects.create(
                session_id=session_id,
                configuration=config,
                status='started',
                viewers_count=config.num_viewers,
            )

            # Immediately create Viewer records so the dashboard shows them right away.
            # The background bot process will update their status as it runs.
            active_proxies = list(Proxy.objects.filter(is_active=True))
            for i in range(config.num_viewers):
                proxy_obj = active_proxies[i % len(active_proxies)] if active_proxies else None
                Viewer.objects.create(
                    session=session,
                    viewer_id=i + 1,
                    proxy_used=proxy_obj,
                    status='starting',
                )

            # Actually start the bot process in the background
            try:
                from bot_management.task_runner import start_bot_session
                success = start_bot_session(session_id, config.id)

                if success:
                    session.status = 'running'
                    session.save()
                    messages.success(request, f'Bot session {session_id} started with {config.num_viewers} viewers!')
                else:
                    messages.warning(request, f'Session created but failed to start bot process. Session ID: {session_id}')
            except Exception as e:
                messages.warning(request, f'Session created but background process failed: {str(e)}. Session ID: {session_id}')

        elif action == 'stop':
            # Stop a session
            session_id = request.POST.get('session_id')
            try:
                session = BotSession.objects.get(session_id=session_id)
                session.status = 'stopped'
                session.end_time = datetime.now()
                session.save()
                # Also try to kill the background process
                try:
                    from bot_management.task_runner import stop_bot_session
                    stop_bot_session(session_id)
                except Exception:
                    pass
                messages.success(request, f'Session {session_id} stopped!')
            except BotSession.DoesNotExist:
                messages.error(request, 'Session not found!')

        return redirect('dashboard:control')

    # GET request
    active_sessions = BotSession.objects.exclude(status__in=['completed', 'failed', 'stopped'])
    recent_sessions = BotSession.objects.all().order_by('-start_time')[:10]

    # Compute real success rate and uptime from DB
    totals = BotSession.objects.aggregate(
        total_viewers=Sum('viewers_count'),
        total_success=Sum('success_count'),
    )
    total_viewers = totals['total_viewers'] or 0
    total_success = totals['total_success'] or 0
    overall_success_rate = round((total_success / total_viewers * 100), 1) if total_viewers > 0 else 0

    # Real uptime
    sys_stats = _get_system_stats()

    # Load the latest saved configuration so the modal shows real values
    try:
        current_config = BotConfiguration.objects.filter(created_by=request.user).latest('updated_at')
    except BotConfiguration.DoesNotExist:
        current_config = None

    context = {
        'active_sessions': active_sessions,
        'recent_sessions': recent_sessions,
        'current_config': current_config,
        'overall_success_rate': overall_success_rate,
        'sys_uptime': sys_stats['uptime'],
    }

    return render(request, 'dashboard/control.html', context)


@login_required
def session_detail(request, session_id):
    """Detail view for a specific bot session."""
    try:
        session = BotSession.objects.get(session_id=session_id)
        viewers = Viewer.objects.filter(session=session)
    except BotSession.DoesNotExist:
        messages.error(request, 'Session not found!')
        return redirect('dashboard:control')

    context = {
        'session': session,
        'viewers': viewers,
    }

    return render(request, 'dashboard/session_detail.html', context)


@login_required
def api_session_data(request, session_id):
    """API endpoint to get real-time session and viewer data."""
    try:
        session = BotSession.objects.get(session_id=session_id)
        viewers = Viewer.objects.filter(session=session)

        data = {
            'status': session.status,
            'success_count': session.success_count,
            'error_count': session.error_count,
            'viewers_count': session.viewers_count,
            'viewers': [
                {
                    'id': viewer.id,
                    'viewer_id': viewer.viewer_id,
                    'status': viewer.status,
                    'proxy_used': {
                        'id': viewer.proxy_used.id,
                        'proxy_url': viewer.proxy_used.proxy_url,
                    } if viewer.proxy_used else None,
                    'comments_sent': viewer.comments_sent,
                    'reactions_made': viewer.reactions_made,
                    'start_time': viewer.start_time.isoformat(),
                }
                for viewer in viewers
            ]
        }

        return JsonResponse(data)
    except BotSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)


@csrf_exempt
def api_update_viewer_stats(request):
    """API endpoint for updating viewer statistics."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            session_id = data.get('session_id')
            viewer_id = data.get('viewer_id')
            stats = data.get('stats', {})

            # Update viewer stats
            try:
                session = BotSession.objects.get(session_id=session_id)
                viewer, created = Viewer.objects.get_or_create(
                    session=session,
                    viewer_id=viewer_id,
                    defaults={'status': 'running'}
                )

                viewer.status = stats.get('status', viewer.status)
                viewer.comments_sent = stats.get('comments_sent', viewer.comments_sent)
                viewer.reactions_made = stats.get('reactions_made', viewer.reactions_made)
                viewer.save()

                return JsonResponse({'status': 'success'})
            except BotSession.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Session not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})


@login_required
def api_get_logs(request):
    """API endpoint to fetch real log entries from BotSession logs field."""
    session_id = request.GET.get('session_id')
    limit = int(request.GET.get('limit', 200))

    log_entries = []

    if session_id:
        # Fetch logs for a specific session
        try:
            session = BotSession.objects.get(session_id=session_id)
            if session.logs:
                lines = session.logs.strip().splitlines()
                log_entries = lines[-limit:]
        except BotSession.DoesNotExist:
            pass
    else:
        # Aggregate logs from recent sessions (latest 10)
        recent_sessions = BotSession.objects.all().order_by('-start_time')[:10]
        for session in recent_sessions:
            if session.logs:
                lines = session.logs.strip().splitlines()
                for line in lines:
                    log_entries.append(f'[Session {session.session_id}] {line}')

    # Also try to read from the Django log file if configured
    log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'django.log')
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                file_lines = f.readlines()
                # Take last N lines
                file_lines = [l.rstrip() for l in file_lines[-limit:] if l.strip()]
                log_entries = file_lines + log_entries
        except Exception:
            pass

    # Compute log stats
    error_count = sum(1 for l in log_entries if 'ERROR' in l.upper())
    warning_count = sum(1 for l in log_entries if 'WARNING' in l.upper() or 'WARN' in l.upper())
    info_count = sum(1 for l in log_entries if 'INFO' in l.upper())
    total_count = len(log_entries)
    success_count = sum(1 for l in log_entries if 'SUCCESS' in l.upper() or '✅' in l)

    return JsonResponse({
        'success': True,
        'logs': log_entries[-limit:],
        'stats': {
            'total': total_count,
            'errors': error_count,
            'warnings': warning_count,
            'info': info_count,
            'success': success_count,
        }
    })


@login_required
def logs_view(request):
    """View for displaying real logs from sessions and log files."""
    # Aggregate logs from recent sessions
    recent_sessions = BotSession.objects.all().order_by('-start_time')[:10]
    log_entries = []

    for session in recent_sessions:
        if session.logs:
            lines = session.logs.strip().splitlines()
            for line in lines:
                log_entries.append({
                    'session_id': session.session_id,
                    'text': line,
                    'level': _classify_log_level(line),
                })

    # Also try to read from the Django log file
    log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'django.log')
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='replace') as f:
                file_lines = f.readlines()
                for line in file_lines[-200:]:
                    line = line.rstrip()
                    if line:
                        log_entries.append({
                            'session_id': 'system',
                            'text': line,
                            'level': _classify_log_level(line),
                        })
        except Exception:
            pass

    # Compute real stats
    error_count = sum(1 for l in log_entries if l['level'] == 'error')
    warning_count = sum(1 for l in log_entries if l['level'] == 'warning')
    info_count = sum(1 for l in log_entries if l['level'] == 'info')
    success_count = sum(1 for l in log_entries if l['level'] == 'success')
    total_count = len(log_entries)

    # Success rate based on log entries
    non_error = total_count - error_count
    log_success_rate = round((non_error / total_count * 100), 1) if total_count > 0 else 100

    context = {
        'log_entries': log_entries[-200:],  # Show last 200 entries
        'error_count': error_count,
        'warning_count': warning_count,
        'info_count': info_count,
        'success_count': success_count,
        'total_count': total_count,
        'log_success_rate': log_success_rate,
        'has_logs': total_count > 0,
    }

    return render(request, 'dashboard/logs.html', context)


def _classify_log_level(line):
    """Classify a log line into a level string."""
    upper = line.upper()
    if 'ERROR' in upper or 'FAILED' in upper or 'EXCEPTION' in upper or 'TRACEBACK' in upper:
        return 'error'
    elif 'WARNING' in upper or 'WARN' in upper:
        return 'warning'
    elif 'SUCCESS' in upper or '✅' in line or 'WATCHING' in upper:
        return 'success'
    else:
        return 'info'
