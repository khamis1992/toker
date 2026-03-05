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
        proxy_pool = []  # list of proxy URL strings to rotate through

        if proxy_source == 'packetstream':
            ps = await sync_to_async(PacketStreamSettings.get_settings)()
            if ps.is_enabled and ps.username and ps.cik:
                ps_url = ps.get_proxy_url()
                # Every viewer gets the same PacketStream endpoint (it rotates IPs internally)
                proxy_pool = [ps_url] * config.num_viewers
                self.stdout.write(
                    self.style.SUCCESS(f'Using PacketStream proxy: {ps.host}:{ps.port} for {config.num_viewers} viewers.')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('PacketStream selected but credentials are not configured. Running direct.')
                )

        elif proxy_source == 'free':
            raw_proxies = await sync_to_async(self._get_free_proxies)()
            if raw_proxies:
                # Validate proxies against TikTok specifically — test up to 60 proxies
                # to find enough working ones (TikTok blocks many free proxies)
                test_count = min(len(raw_proxies), 60)
                self.stdout.write(self.style.WARNING(
                    f'Validating {test_count} proxies against TikTok...'
                ))
                validated = await self._validate_proxies(
                    raw_proxies[:test_count],
                    max_good=config.num_viewers * 5,
                    test_url='https://www.tiktok.com',
                )
                if validated:
                    proxy_pool = validated
                    self.stdout.write(self.style.SUCCESS(
                        f'Found {len(validated)} TikTok-compatible proxies out of {test_count} tested.'
                    ))
                else:
                    # Fall back: try a broader test (any connectivity)
                    self.stdout.write(self.style.WARNING(
                        'No TikTok-compatible proxies found. Trying general connectivity test...'
                    ))
                    validated = await self._validate_proxies(
                        raw_proxies[:test_count],
                        max_good=config.num_viewers * 5,
                        test_url='http://www.google.com',
                    )
                    if validated:
                        proxy_pool = validated
                        self.stdout.write(self.style.WARNING(
                            f'Using {len(validated)} general proxies (TikTok may block some).'
                        ))
                    else:
                        self.stdout.write(self.style.WARNING(
                            'No working free proxies found. Running direct.'
                        ))
            else:
                self.stdout.write(self.style.WARNING('No free proxies in DB. Running direct.'))

        else:  # proxy_source == 'none'
            self.stdout.write(self.style.WARNING('Running with no proxy (direct connection).'))

        # ---------------------------------------------------------------
        # Create viewer tasks — each viewer gets a proxy from the pool
        # ---------------------------------------------------------------
        tasks = []
        viewer_records = []

        for i in range(config.num_viewers):
            # Assign proxy round-robin from validated pool
            proxy = proxy_pool[i % len(proxy_pool)] if proxy_pool else None

            viewer = TikTokViewer(viewer_id=i + 1, proxy=proxy)

            # Get or create the viewer DB record (view may have pre-created it)
            viewer_record = await sync_to_async(self._get_or_create_viewer_record)(session, i + 1, proxy)
            viewer_records.append(viewer_record)

            # Mark viewer as "connecting" so the dashboard shows activity immediately
            await sync_to_async(self._update_viewer_status)(viewer_record, 'connecting', '')

            task = self._run_viewer_with_status(viewer, config.live_url, viewer_record, proxy_pool, i)
            tasks.append(task)

            # Stagger viewer start times slightly to avoid simultaneous browser launches
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

        self.stdout.write(
            self.style.SUCCESS(f'Session completed. {success_count} successful, {error_count} failed.')
        )

    async def _run_viewer_with_status(self, viewer, live_url, viewer_record, proxy_pool, viewer_index):
        """
        Run a single viewer, updating its DB status in real time.
        If the proxy fails, retry with the next proxy in the pool.
        """
        max_proxy_retries = min(3, len(proxy_pool)) if proxy_pool else 1
        tried_proxies = set()

        current_proxy = viewer.proxy
        if current_proxy:
            tried_proxies.add(current_proxy)

        for attempt in range(max_proxy_retries):
            result = await viewer.start(live_url)

            if result is True:
                # Viewer successfully connected — mark as active
                await sync_to_async(self._update_viewer_status)(viewer_record, 'active', '')
                return True
            else:
                # Failed — try a different proxy if available
                next_proxy = None
                for p in proxy_pool:
                    if p not in tried_proxies:
                        next_proxy = p
                        tried_proxies.add(p)
                        break

                if next_proxy and attempt < max_proxy_retries - 1:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Viewer {viewer.viewer_id}: Proxy failed, retrying with different proxy (attempt {attempt + 2}/{max_proxy_retries})'
                        )
                    )
                    viewer.proxy = next_proxy
                    # Update the proxy on the viewer record
                    await sync_to_async(self._update_viewer_proxy)(viewer_record, next_proxy)
                    await sync_to_async(self._update_viewer_status)(viewer_record, 'retrying', '')
                else:
                    break

        # All attempts failed
        await sync_to_async(self._update_viewer_status)(viewer_record, 'failed', 'All proxy attempts failed')
        return False

    async def _validate_proxies(self, proxy_list, max_good=10, timeout=10, test_url='https://www.tiktok.com'):
        """
        Quickly test proxies by making a GET request through each one.
        Returns a list of working proxy URLs (up to max_good).
        """
        import aiohttp

        async def test_one(proxy_url):
            try:
                connector = aiohttp.TCPConnector(ssl=False)
                async with aiohttp.ClientSession(connector=connector) as sess:
                    async with sess.get(
                        test_url,
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=timeout),
                        allow_redirects=True,
                        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
                    ) as resp:
                        # Accept any 2xx or 3xx response as working
                        if resp.status < 500:
                            return proxy_url
            except Exception:
                pass
            return None

        # Run all tests concurrently
        tasks = [test_one(p) for p in proxy_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        good = [r for r in results if isinstance(r, str)]
        return good[:max_good]

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
            viewer_record.proxy_used = proxy_obj
            viewer_record.save()
        return viewer_record

    def _update_viewer_proxy(self, viewer_record, proxy_url):
        """Update the proxy on a viewer record."""
        proxy_obj = Proxy.objects.filter(proxy_url=proxy_url).first()
        viewer_record.proxy_used = proxy_obj
        viewer_record.save()

    def _update_session_results(self, session, success_count, error_count, status, log_text=''):
        from django.utils import timezone
        session.success_count = success_count
        session.error_count = error_count
        session.status = status
        session.end_time = timezone.now()
        if log_text:
            existing = session.logs or ''
            session.logs = (existing + '\n' + log_text).strip()
        session.save()

    def _update_viewer_status(self, viewer_record, status, error_msg=''):
        from django.utils import timezone
        viewer_record.status = status
        if status in ('completed', 'failed'):
            viewer_record.end_time = timezone.now()
        viewer_record.save()
