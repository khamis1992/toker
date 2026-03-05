"""
Proxy Auto-Fetch Scheduler
--------------------------
Uses APScheduler to run a background job that periodically fetches free proxies
from configured sources and loads them into the database automatically.

The scheduler is started once when Django boots (via AppConfig.ready()).
The job interval is controlled by the ProxyAutoFetchSettings singleton model.
"""

import logging
import threading
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone

logger = logging.getLogger(__name__)

# Module-level scheduler instance (singleton)
_scheduler = None
_scheduler_lock = threading.Lock()

JOB_ID = "auto_fetch_proxies"


# ---------------------------------------------------------------------------
# Core fetch logic (reused from views.py, kept standalone to avoid circular
# imports at scheduler startup)
# ---------------------------------------------------------------------------

def _fetch_from_proxyscrape(limit=100):
    """Fetch HTTP proxies from the ProxyScrape public API."""
    import requests
    url = (
        f"https://api.proxyscrape.com/v2/"
        f"?request=getproxies&protocol=http&timeout=10000&country=all&limit={limit}"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    proxies = []
    for line in resp.text.strip().splitlines():
        line = line.strip()
        if line and ":" in line:
            proxies.append(f"http://{line}")
    return proxies


def _fetch_from_geonode(limit=100):
    """Fetch proxies from the GeoNode JSON API."""
    import requests
    url = (
        f"https://proxylist.geonode.com/api/proxy-list"
        f"?limit={limit}&page=1&sort_by=lastChecked&sort_type=desc"
    )
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    proxies = []
    for item in data.get("data", []):
        ip   = item.get("ip", "")
        port = item.get("port", "")
        if ip and port:
            proxies.append(f"http://{ip}:{port}")
    return proxies


def _fetch_from_freeproxylist(limit=100):
    """Scrape proxies from free-proxy-list.net."""
    import requests
    from bs4 import BeautifulSoup
    resp = requests.get("https://free-proxy-list.net/", timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    proxies = []
    table = soup.find("table")
    if table:
        for row in table.find_all("tr")[1:limit + 1]:
            cols = row.find_all("td")
            if len(cols) >= 2:
                ip   = cols[0].text.strip()
                port = cols[1].text.strip()
                if ip and port:
                    proxies.append(f"http://{ip}:{port}")
    return proxies


def _save_proxies(proxy_urls, activate=True):
    """
    Save a list of proxy URL strings to the database.
    Returns (added, skipped) counts.
    """
    from bot_management.models import Proxy
    added = skipped = 0
    existing = set(Proxy.objects.values_list("proxy_url", flat=True))
    new_proxies = []
    for url in proxy_urls:
        if url not in existing:
            new_proxies.append(Proxy(proxy_url=url, is_active=activate))
            existing.add(url)
            added += 1
        else:
            skipped += 1
    if new_proxies:
        Proxy.objects.bulk_create(new_proxies)
    return added, skipped


# ---------------------------------------------------------------------------
# The scheduled job
# ---------------------------------------------------------------------------

def auto_fetch_proxies_job():
    """
    Background job: fetch proxies from enabled sources and save to DB.
    Reads settings from ProxyAutoFetchSettings each time it runs so that
    changes take effect without restarting the server.
    """
    try:
        from bot_management.models import ProxyAutoFetchSettings
        settings = ProxyAutoFetchSettings.get_settings()

        if not settings.is_enabled:
            logger.debug("Auto-fetch is disabled — skipping run.")
            return

        logger.info("Auto-fetch job started.")
        all_proxies = []

        if settings.use_proxyscrape:
            try:
                proxies = _fetch_from_proxyscrape(limit=100)
                all_proxies.extend(proxies)
                logger.info("ProxyScrape: fetched %d proxies", len(proxies))
            except Exception as exc:
                logger.warning("ProxyScrape fetch failed: %s", exc)

        if settings.use_geonode:
            try:
                proxies = _fetch_from_geonode(limit=100)
                all_proxies.extend(proxies)
                logger.info("GeoNode: fetched %d proxies", len(proxies))
            except Exception as exc:
                logger.warning("GeoNode fetch failed: %s", exc)

        if settings.use_freeproxylist:
            try:
                proxies = _fetch_from_freeproxylist(limit=100)
                all_proxies.extend(proxies)
                logger.info("FreeProxyList: fetched %d proxies", len(proxies))
            except Exception as exc:
                logger.warning("FreeProxyList fetch failed: %s", exc)

        # Deduplicate within this batch
        all_proxies = list(dict.fromkeys(all_proxies))

        added, skipped = _save_proxies(all_proxies, activate=settings.activate_on_load)

        # Update last-run stats
        settings.last_run         = timezone.now()
        settings.last_run_added   = added
        settings.last_run_skipped = skipped
        settings.save()

        logger.info(
            "Auto-fetch job complete: %d added, %d skipped (duplicates).",
            added, skipped
        )

    except Exception as exc:
        logger.error("Auto-fetch job error: %s", exc, exc_info=True)


# ---------------------------------------------------------------------------
# Scheduler lifecycle
# ---------------------------------------------------------------------------

def get_scheduler():
    global _scheduler
    if _scheduler is None:
        with _scheduler_lock:
            if _scheduler is None:
                _scheduler = BackgroundScheduler(timezone="UTC")
    return _scheduler


def start_scheduler():
    """
    Start the background scheduler and register the auto-fetch job.
    Called once from DashboardConfig.ready().
    """
    scheduler = get_scheduler()
    if scheduler.running:
        return

    try:
        from bot_management.models import ProxyAutoFetchSettings
        settings = ProxyAutoFetchSettings.get_settings()
        interval = settings.interval_minutes
    except Exception:
        interval = 60  # fallback default

    scheduler.add_job(
        auto_fetch_proxies_job,
        trigger=IntervalTrigger(minutes=interval),
        id=JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Proxy auto-fetch scheduler started (interval: %d min).", interval)


def reschedule_job(interval_minutes):
    """
    Reschedule the job with a new interval without restarting the scheduler.
    Called when the user saves new settings.
    """
    scheduler = get_scheduler()
    if not scheduler.running:
        return
    scheduler.reschedule_job(
        JOB_ID,
        trigger=IntervalTrigger(minutes=interval_minutes),
    )
    logger.info("Auto-fetch job rescheduled to every %d minutes.", interval_minutes)


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Proxy auto-fetch scheduler stopped.")
