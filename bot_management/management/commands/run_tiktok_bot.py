from django.core.management.base import BaseCommand
from django.conf import settings
from asgiref.sync import sync_to_async
from bot_management.models import BotConfiguration, BotSession, Viewer, Proxy, PacketStreamSettings
import asyncio
import logging
import sys
import os

# Add the project root to Python path so we can import bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from bot_enhanced import TikTokViewer
    from proxy_manager import proxy_manager
    HAS_BOT_MODULES = True
except ImportError:
    HAS_BOT_MODULES = False
    print("Warning: Could not import bot modules. Ensure bot_enhanced.py is in the project root.")


class Command(BaseCommand):
    help = 'Run TikTok bot with Django integration'

    def add_arguments(self, parser):
        parser.add_argument('--session-id', type=str, help='Session ID for tracking')
        parser.add_argument('--config-id', type=int, help='Configuration ID to use')
        parser.add_argument(
            '--proxy-source',
            type=str,
            default='free',
            choices=['free', 'packetstream', 'none'],
            help='Proxy pool to use: free, packetstream, or none (direct connection)',
        )

    def handle(self, *args, **options):
        if not HAS_BOT_MODULES:
            self.stdout.write(
                self.style.ERROR(
                    'Bot modules not available. Ensure bot_enhanced.py and related files are in the project directory.'
                )
            )
            return

        session_id = options['session_id']
        config_id = options['config_id']
        proxy_source = options.get('proxy_source', 'free')

        # Get configuration (sync)
        if config_id:
            try:
                config = BotConfiguration.objects.get(id=config_id)
            except BotConfiguration.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Configuration with ID {config_id} not found.'))
                return
        else:
            config = self.get_default_config()

        # Create or get session (sync)
        if session_id:
            session, created = BotSession.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'configuration': config,
                    'status': 'started',
                    'proxy_source': proxy_source,
                    'viewers_count': config.num_viewers,
                }
            )
        else:
            import uuid
            session_id = str(uuid.uuid4())[:8]
            session = BotSession.objects.create(
                session_id=session_id,
                configuration=config,
                status='started',
                proxy_source=proxy_source,
                viewers_count=config.num_viewers,
            )
            self.stdout.write(self.style.SUCCESS(f'Created new session: {session_id}'))

        # Run the bot in a new event loop
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_bot_async(config, session, proxy_source))
            loop.close()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Bot stopped by user.'))
        except Exception as e:
            session.status = 'failed'
            session.save()
            self.stdout.write(self.style.ERROR(f'Bot failed with error: {str(e)}'))

    def get_default_config(self):
        """Create a default configuration if none exists."""
        from django.contrib.auth.models import User
        user, _ = User.objects.get_or_create(username='default_bot_user')
        config, _ = BotConfiguration.objects.get_or_create(
            created_by=user,
            defaults={
                'live_url': 'https://www.tiktok.com/@khamish92/live',
                'num_viewers': 3,
                'headless': True,
                'page_load_timeout': 60000,
                'element_wait_timeout': 10000,
                'session_max_duration': 1800,
                'keepalive_min_interval': 30,
                'keepalive_max_interval': 60,
                'max_retry_attempts': 3,
                'base_retry_delay': 2.0,
                'window_width': 1366,
                'window_height': 768,
                'debug_screenshots': True,
                'screenshot_dir': 'screenshots',
                'log_level': 'INFO',
            }
        )
        return config

    async def run_bot_async(self, config, session, proxy_source='free'):
        """Run the bot asynchronously with Django integration."""
        await sync_to_async(self._update_session_status)(session, 'running')

        # Apply DB configuration values to the global config object used by TikTokViewer
        from config import config as bot_config
        bot_config.live_url = config.live_url
        bot_config.num_viewers = config.num_viewers
        bot_config.headless = config.headless
        bot_config.page_load_timeout = config.page_load_timeout
        bot_config.element_wait_timeout = config.element_wait_timeout
        bot_config.session_max_duration = config.session_max_duration
        bot_config.keepalive_min_interval = config.keepalive_min_interval
        bot_config.keepalive_max_interval = config.keepalive_max_interval
        bot_config.max_retry_attempts = config.max_retry_attempts
        bot_config.base_retry_delay = config.base_retry_delay
        bot_config.window_width = config.window_width
        bot_config.window_height = config.window_height
        bot_config.debug_screenshots = config.debug_screenshots
        bot_config.screenshot_dir = config.screenshot_dir
        bot_config.log_level = config.log_level

        # ---------------------------------------------------------------
        # Resolve proxy list based on the user-selected proxy_source
        # ---------------------------------------------------------------
        active_proxies = []

        if proxy_source == 'packetstream':
            # Use the PacketStream paid proxy (single rotating endpoint)
            ps = await sync_to_async(PacketStreamSettings.get_settings)()
            if ps.is_enabled and ps.username and ps.cik:
                ps_url = ps.get_proxy_url()
                # Every viewer gets the same PacketStream endpoint (it rotates IPs internally)
                active_proxies = [ps_url] * config.num_viewers
                self.stdout.write(
                    self.style.SUCCESS(f'Using PacketStream proxy: {ps.host}:{ps.port} for {config.num_viewers} viewers.')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('PacketStream selected but credentials are not configured. Falling back to direct connection.')
                )

        elif proxy_source == 'free':
            # Load free proxies from the database
            active_proxies = await sync_to_async(self._get_free_proxies)()
            if active_proxies:
                proxy_manager.proxies = active_proxies
                self.stdout.write(
                    self.style.SUCCESS(f'Loaded {len(active_proxies)} free proxies from database.')
                )
            else:
                # Fall back to proxies.txt (only for free-type entries)
                proxy_manager._load_proxies()
                if proxy_manager.proxies:
                    active_proxies = proxy_manager.proxies
                    self.stdout.write(
                        self.style.WARNING(
                            f'No free DB proxies found. Loaded {len(active_proxies)} proxies from proxies.txt.'
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            'No free proxies available. Running without proxies (direct connection).'
                        )
                    )

        else:  # proxy_source == 'none'
            self.stdout.write(
                self.style.WARNING('Running with no proxy (direct connection). May be detected by TikTok.')
            )

        # ---------------------------------------------------------------
        # Create viewer tasks
        # ---------------------------------------------------------------
        tasks = []
        viewer_records = []

        for i in range(config.num_viewers):
            # Assign a proxy from the pool (round-robin)
            if proxy_source == 'packetstream' and active_proxies:
                # All viewers share the same PacketStream endpoint
                proxy = active_proxies[0]
            elif proxy_source == 'free' and active_proxies:
                proxy = proxy_manager.get_proxy()
            else:
                proxy = None

            viewer = TikTokViewer(viewer_id=i + 1, proxy=proxy)

            # Use get_or_create to avoid duplicates (view already pre-created the records)
            viewer_record = await sync_to_async(self._get_or_create_viewer_record)(session, i + 1, proxy)
            viewer_records.append(viewer_record)

            task = viewer.start(config.live_url)
            tasks.append(task)

            # Stagger viewer start times slightly
            await asyncio.sleep(2)

        # ---------------------------------------------------------------
        # Run all viewers concurrently
        # ---------------------------------------------------------------
        results = await asyncio.gather(*tasks, return_exceptions=True)

        success_count = sum(1 for r in results if r is True)
        error_count = len(results) - success_count

        from datetime import datetime
        log_lines = [
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Session completed: {success_count} successful, {error_count} failed. "
            f"Proxy source: {proxy_source}."
        ]
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                log_lines.append(f"  Viewer {i + 1}: FAILED — {result}")
            elif result is True:
                log_lines.append(f"  Viewer {i + 1}: SUCCESS")
            else:
                log_lines.append(f"  Viewer {i + 1}: FAILED — unknown error")
        log_text = "\n".join(log_lines)

        await sync_to_async(self._update_session_results)(session, success_count, error_count, 'completed', log_text)

        for i, result in enumerate(results):
            status = 'completed' if result is True else 'failed'
            error_msg = str(result) if isinstance(result, Exception) else ''
            await sync_to_async(self._update_viewer_status)(viewer_records[i], status, error_msg)

        self.stdout.write(
            self.style.SUCCESS(f'Session completed. {success_count} successful, {error_count} failed.')
        )

    # ------------------------------------------------------------------
    # Sync helper methods (called via sync_to_async)
    # ------------------------------------------------------------------

    def _update_session_status(self, session, status):
        session.status = status
        session.save()

    def _get_free_proxies(self):
        """Return active free proxies from the database."""
        return list(
            Proxy.objects.filter(proxy_type='free', is_active=True).values_list('proxy_url', flat=True)
        )

    def _get_or_create_viewer_record(self, session, viewer_id, proxy):
        """Get or create a viewer record (avoids duplicates when view pre-creates them)."""
        proxy_obj = Proxy.objects.filter(proxy_url=proxy).first() if proxy else None
        viewer_record, created = Viewer.objects.get_or_create(
            session=session,
            viewer_id=viewer_id,
            defaults={'status': 'starting', 'proxy_used': proxy_obj},
        )
        if not created and proxy_obj and viewer_record.proxy_used is None:
            # Update the proxy on the existing record
            viewer_record.proxy_used = proxy_obj
            viewer_record.save()
        return viewer_record

    def _update_session_results(self, session, success_count, error_count, status, log_text=''):
        from datetime import datetime
        session.success_count = success_count
        session.error_count = error_count
        session.status = status
        session.end_time = datetime.now()
        if log_text:
            existing = session.logs or ''
            session.logs = (existing + '\n' + log_text).strip()
        session.save()

    def _update_viewer_status(self, viewer_record, status, error_msg=''):
        from datetime import datetime
        viewer_record.status = status
        viewer_record.end_time = datetime.now()
        viewer_record.save()
