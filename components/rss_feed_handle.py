from contextlib import suppress
from datetime import datetime
from time import mktime

from discord import SyncWebhook
from feedparser import parse

from components.localization import get_translation
from config.init_config import Config, BotVars


async def check_on_rss_feed():
    try:
        datetime_from = datetime.fromisoformat(Config.get_rss_feed_settings().rss_last_date)
    except (ValueError, TypeError):
        print(get_translation("Date from bot config is invalid. Bot will use current date for checking..."))
        datetime_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if datetime_from.tzinfo is not None:
        datetime_from = datetime.fromtimestamp(datetime_from.timestamp())
    send = False
    parsed = parse(Config.get_rss_feed_settings().rss_url)
    with suppress(KeyError, AttributeError):
        new_date = datetime_from
        entries = parsed.entries
        entries.reverse()
        for entry in entries:
            entry_date = datetime.fromtimestamp(mktime(entry.published_parsed))
            if entry_date > datetime_from:
                send = True
                BotVars.webhook_rss.send(entry.link)
                if entry_date > new_date:
                    new_date = entry_date
        if send:
            Config.get_rss_feed_settings().rss_last_date = new_date.isoformat()
            Config.save_config()


def create_feed_webhook():
    if Config.get_rss_feed_settings().rss_url and Config.get_rss_feed_settings().webhook_url:
        BotVars.webhook_rss = SyncWebhook.from_url(url=Config.get_rss_feed_settings().webhook_url)
