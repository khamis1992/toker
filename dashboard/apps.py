from django.apps import AppConfig


class DashboardConfig(AppConfig):
    name = 'dashboard'

    def ready(self):
        """Start the background proxy auto-fetch scheduler when Django boots."""
        import os
        # Only start in the main process (not in the reloader child process)
        if os.environ.get('RUN_MAIN') != 'true' and os.environ.get('DJANGO_SETTINGS_MODULE'):
            return
        try:
            from dashboard.scheduler import start_scheduler
            start_scheduler()
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning(
                "Could not start proxy auto-fetch scheduler: %s", exc
            )
