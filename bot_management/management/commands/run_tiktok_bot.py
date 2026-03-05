from django.core.management.base import BaseCommand
from django.conf import settings
from asgiref.sync import sync_to_async
from bot_management.models import BotConfiguration, BotSession, Viewer, Proxy
import asyncio
import logging
import sys
import os

# Add the parent directory to Python path so we can import our bot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from bot_enhanced import TikTokViewer
    from proxy_manager import proxy_manager
    HAS_BOT_MODULES = True
except ImportError:
    HAS_BOT_MODULES = False
    print("Warning: Could not import bot modules. Using dummy implementation.")


class Command(BaseCommand):
    help = 'Run TikTok bot with Django integration'

    def add_arguments(self, parser):
        parser.add_argument('--session-id', type=str, help='Session ID for tracking')
        parser.add_argument('--config-id', type=int, help='Configuration ID to use')

    def handle(self, *args, **options):
        if not HAS_BOT_MODULES:
            self.stdout.write(
                self.style.ERROR('Bot modules not available. Please ensure bot_enhanced.py and related files are in the project directory.')
            )
            return
            
        session_id = options['session_id']
        config_id = options['config_id']
        
        # Get configuration (sync)
        if config_id:
            try:
                config = BotConfiguration.objects.get(id=config_id)
            except BotConfiguration.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Configuration with ID {config_id} not found.')
                )
                return
        else:
            # Use default configuration
            config = self.get_default_config()
        
        # Create or get session (sync)
        if session_id:
            session, created = BotSession.objects.get_or_create(
                session_id=session_id,
                defaults={
                    'configuration': config,
                    'status': 'started',
                    'viewers_count': config.num_viewers,
                }
            )
        else:
            from datetime import datetime
            import uuid
            session_id = str(uuid.uuid4())[:8]
            session = BotSession.objects.create(
                session_id=session_id,
                configuration=config,
                status='started',
                viewers_count=config.num_viewers,
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created new session: {session_id}')
            )
        
        # Run the bot in a new event loop
        try:
            # Create a new event loop and run in a separate thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.run_bot_async(config, session))
            loop.close()
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('Bot stopped by user.')
            )
        except Exception as e:
            # Sync version for error handling
            session.status = 'failed'
            session.save()
            self.stdout.write(
                self.style.ERROR(f'Bot failed with error: {str(e)}')
            )

    def get_default_config(self):
        """Create a default configuration if none exists."""
        from django.contrib.auth.models import User
        # Get or create a default user
        user, created = User.objects.get_or_create(username='default_bot_user')
        
        config, created = BotConfiguration.objects.get_or_create(
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

    async def run_bot_async(self, config, session):
        """Run the bot asynchronously with Django integration."""
        # Update session status (sync_to_async wrapper)
        await sync_to_async(self._update_session_status)(session, 'running')
        
        # Load proxies from database (sync_to_async wrapper)
        active_proxies = await sync_to_async(self._get_active_proxies)()
        if active_proxies:
            # Update proxy_manager with our proxies
            proxy_manager.proxies = active_proxies
            self.stdout.write(
                self.style.SUCCESS(f'Loaded {len(active_proxies)} active proxies.')
            )
        
        # Create viewer tasks
        tasks = []
        viewer_records = []
        viewers_list = []  # Fixed: define the list
        
        for i in range(config.num_viewers):
            proxy = proxy_manager.get_proxy() if active_proxies else None
            viewer = TikTokViewer(viewer_id=i+1, proxy=proxy)
            viewers_list.append(viewer)
            
            # Get or create viewer record in database (sync_to_async wrapper)
            # The view may have already created the record; update it rather than duplicate.
            viewer_record = await sync_to_async(self._get_or_create_viewer_record)(session, i+1, proxy)
            viewer_records.append(viewer_record)
            
            # Add task
            task = viewer.start(config.live_url)
            tasks.append(task)
            
            # Stagger viewer start times
            await asyncio.sleep(2)
        
        # Run all viewers
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update session results (sync_to_async wrapper)
        success_count = sum(1 for result in results if result is True)
        error_count = len(results) - success_count
        
        await sync_to_async(self._update_session_results)(session, success_count, error_count, 'completed')
        
        # Update viewer records (sync_to_async wrapper)
        for i, result in enumerate(results):
            status = 'completed' if result is True else 'failed'
            await sync_to_async(self._update_viewer_status)(viewer_records[i], status)
        
        self.stdout.write(
            self.style.SUCCESS(f'Session completed. {success_count} successful, {error_count} failed.')
        )
    
    def _update_session_status(self, session, status):
        """Helper to update session status (sync)."""
        session.status = status
        session.save()
    
    def _get_active_proxies(self):
        """Helper to get active proxies (sync)."""
        return list(Proxy.objects.filter(is_active=True).values_list('proxy_url', flat=True))
    
    def _create_viewer_record(self, session, viewer_id, proxy):
        """Helper to create viewer record (sync)."""
        proxy_obj = Proxy.objects.filter(proxy_url=proxy).first() if proxy else None
        return Viewer.objects.create(
            session=session,
            viewer_id=viewer_id,
            proxy_used=proxy_obj,
            status='starting'
        )

    def _get_or_create_viewer_record(self, session, viewer_id, proxy):
        """Get existing viewer record or create a new one (prevents duplicates)."""
        proxy_obj = Proxy.objects.filter(proxy_url=proxy).first() if proxy else None
        # Use the earliest record if duplicates exist (created by the view)
        existing = Viewer.objects.filter(session=session, viewer_id=viewer_id).order_by('id').first()
        if existing:
            # Update the proxy assignment if the bot picked a different one
            if proxy_obj and existing.proxy_used != proxy_obj:
                existing.proxy_used = proxy_obj
                existing.save(update_fields=['proxy_used'])
            return existing
        return Viewer.objects.create(
            session=session,
            viewer_id=viewer_id,
            proxy_used=proxy_obj,
            status='starting'
        )
    
    def _update_session_results(self, session, success_count, error_count, status):
        """Helper to update session results (sync)."""
        session.success_count = success_count
        session.error_count = error_count
        session.status = status
        session.save()
    
    def _update_viewer_status(self, viewer_record, status):
        """Helper to update viewer status (sync)."""
        viewer_record.status = status
        viewer_record.save()
