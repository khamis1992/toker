from django.db import models
from django.contrib.auth.models import User


class BotConfiguration(models.Model):
    """Model to store bot configuration settings."""

    # Basic settings
    live_url = models.URLField(default="https://www.tiktok.com/@khamish92/live")
    num_viewers = models.IntegerField(default=3)
    headless = models.BooleanField(default=True)

    # Timing settings
    page_load_timeout = models.IntegerField(default=60000)
    element_wait_timeout = models.IntegerField(default=10000)
    session_max_duration = models.IntegerField(default=1800)
    keepalive_min_interval = models.IntegerField(default=30)
    keepalive_max_interval = models.IntegerField(default=60)

    # Retry settings
    max_retry_attempts = models.IntegerField(default=3)
    base_retry_delay = models.FloatField(default=2.0)

    # Browser settings
    window_width = models.IntegerField(default=1366)
    window_height = models.IntegerField(default=768)

    # Debug settings
    debug_screenshots = models.BooleanField(default=True)
    screenshot_dir = models.CharField(max_length=255, default="screenshots")
    log_level = models.CharField(
        max_length=10,
        default="INFO",
        choices=[
            ("DEBUG", "Debug"),
            ("INFO", "Info"),
            ("WARNING", "Warning"),
            ("ERROR", "Error"),
        ]
    )

    # User who created/modified this config
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"BotConfig-{self.id}"

    class Meta:
        verbose_name = "Bot Configuration"
        verbose_name_plural = "Bot Configurations"


class Proxy(models.Model):
    """Model to store proxy information."""

    PROXY_TYPE_CHOICES = [
        ('free', 'Free Proxy'),
        ('packetstream', 'PacketStream (Paid)'),
        ('custom', 'Custom / Other'),
    ]

    proxy_url = models.TextField()
    proxy_type = models.CharField(
        max_length=20,
        choices=PROXY_TYPE_CHOICES,
        default='free',
    )
    is_active = models.BooleanField(default=True)
    last_used = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.proxy_url

    class Meta:
        verbose_name = "Proxy"
        verbose_name_plural = "Proxies"


class PacketStreamSettings(models.Model):
    """Singleton model to store PacketStream paid proxy credentials."""

    username = models.CharField(max_length=100, blank=True, default='')
    cik = models.CharField(
        max_length=200, blank=True, default='',
        verbose_name='CIK / Password',
        help_text='Your PacketStream CIK (Customer Identification Key) from the dashboard.',
    )
    host = models.CharField(max_length=200, default='proxy.packetstream.io')
    port = models.IntegerField(default=31112)
    is_enabled = models.BooleanField(
        default=False,
        help_text='Enable PacketStream proxies as an option for bot sessions.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return 'PacketStream Settings'

    def save(self, *args, **kwargs):
        # Enforce singleton — only one row allowed
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'username': '',
                'cik': '',
                'host': 'proxy.packetstream.io',
                'port': 31112,
                'is_enabled': False,
            }
        )
        return obj

    def get_proxy_url(self):
        """Return the full proxy URL string."""
        if self.username and self.cik:
            return f'http://{self.username}:{self.cik}@{self.host}:{self.port}'
        return f'http://{self.host}:{self.port}'

    def test_connection(self):
        """Test if the PacketStream proxy is reachable and authenticated."""
        import requests as req
        proxy_url = self.get_proxy_url()
        proxies = {'http': proxy_url, 'https': proxy_url}
        try:
            r = req.get('http://ipinfo.io/json', proxies=proxies, timeout=10)
            if r.status_code == 200:
                return True, r.json().get('ip', 'unknown')
            return False, f'HTTP {r.status_code}'
        except Exception as e:
            return False, str(e)

    class Meta:
        verbose_name = 'PacketStream Settings'
        verbose_name_plural = 'PacketStream Settings'


class ProxyAutoFetchSettings(models.Model):
    """Singleton model to store auto-fetch scheduler settings."""

    INTERVAL_CHOICES = [
        (15,   'Every 15 minutes'),
        (30,   'Every 30 minutes'),
        (60,   'Every 1 hour'),
        (180,  'Every 3 hours'),
        (360,  'Every 6 hours'),
        (720,  'Every 12 hours'),
        (1440, 'Every 24 hours'),
    ]

    is_enabled = models.BooleanField(default=False)
    interval_minutes = models.IntegerField(default=60, choices=INTERVAL_CHOICES)

    # Which sources to fetch from
    use_proxyscrape   = models.BooleanField(default=True)
    use_geonode       = models.BooleanField(default=True)
    use_freeproxylist = models.BooleanField(default=False)

    activate_on_load  = models.BooleanField(default=True)
    last_run          = models.DateTimeField(null=True, blank=True)
    last_run_added    = models.IntegerField(default=0)
    last_run_skipped  = models.IntegerField(default=0)
    updated_at        = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Proxy Auto-Fetch Settings"

    def save(self, *args, **kwargs):
        # Enforce singleton — only one row allowed
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def get_settings(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    class Meta:
        verbose_name = "Proxy Auto-Fetch Settings"
        verbose_name_plural = "Proxy Auto-Fetch Settings"


class BotSession(models.Model):
    """Model to track bot sessions."""

    STATUS_CHOICES = [
        ('started', 'Started'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('stopped', 'Stopped'),
    ]

    PROXY_SOURCE_CHOICES = [
        ('free', 'Free Proxies'),
        ('packetstream', 'PacketStream (Paid)'),
        ('none', 'No Proxy (Direct)'),
    ]

    session_id = models.CharField(max_length=100, unique=True)
    configuration = models.ForeignKey(BotConfiguration, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='started')
    proxy_source = models.CharField(
        max_length=20,
        choices=PROXY_SOURCE_CHOICES,
        default='free',
    )
    viewers_count = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    logs = models.TextField(blank=True)

    def __str__(self):
        return f"Session-{self.session_id}"

    class Meta:
        verbose_name = "Bot Session"
        verbose_name_plural = "Bot Sessions"


class Viewer(models.Model):
    """Model to track individual viewers within a session."""

    session = models.ForeignKey(BotSession, on_delete=models.CASCADE, related_name='viewers')
    viewer_id = models.IntegerField()
    status = models.CharField(max_length=20, default='starting')
    proxy_used = models.ForeignKey(Proxy, on_delete=models.SET_NULL, null=True, blank=True)
    comments_sent = models.IntegerField(default=0)
    reactions_made = models.IntegerField(default=0)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Viewer-{self.viewer_id} (Session {self.session.session_id})"

    class Meta:
        verbose_name = "Viewer"
        verbose_name_plural = "Viewers"
