from django.core.management.base import BaseCommand
from django.conf import settings
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
        
        # Get configuration
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
        
        # Create or get session
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
        
        # Run the bot
        try:
            asyncio.run(self.run_bot_async(config, session))
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('Bot stopped by user.')
            )
        except Exception as e:
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
        # Update session status
        session.status = 'running'
        session.save()
        
        # Load proxies from database
        active_proxies = list(Proxy.objects.filter(is_active=True).values_list('proxy_url', flat=True))
        if active_proxies:
            # Update proxy_manager with our proxies
            proxy_manager.proxies = active_proxies
            self.stdout.write(
                self.style.SUCCESS(f'Loaded {len(active_proxies)} active proxies.')
            )
        
        # Create viewer tasks
        tasks = []
        viewers = []
        
        for i in range(config.num_viewers):
            proxy = proxy_manager.get_proxy() if active_proxies else None
            viewer = TikTokViewer(viewer_id=i+1, proxy=proxy)
            viewers.append(viewer)
            
            # Create viewer record in database
            viewer_record = Viewer.objects.create(
                session=session,
                viewer_id=i+1,
                proxy_used=Proxy.objects.filter(proxy_url=proxy).first() if proxy else None,
                status='starting'
            )
            
            # Add task (we'll modify the bot to accept callbacks for status updates)
            task = viewer.start(config.live_url)
            tasks.append(task)
            
            # Stagger viewer start times
            await asyncio.sleep(2)
        
        # Run all viewers
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Update session results
        success_count = sum(1 for result in results if result is True)
        error_count = len(results) - success_count
        
        session.success_count = success_count
        session.error_count = error_count
        session.status = 'completed'
        session.save()
        
        # Update viewer records
        for i, result in enumerate(results):
            viewer_record = Viewer.objects.get(session=session, viewer_id=i+1)
            if result is True:
                viewer_record.status = 'completed'
            else:
                viewer_record.status = 'failed'
            viewer_record.save()
        
        self.stdout.write(
            self.style.SUCCESS(f'Session completed. {success_count} successful, {error_count} failed.')
        )