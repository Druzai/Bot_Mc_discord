from asyncio import sleep as asleep
from datetime import datetime

from discord import Webhook, RequestsWebhookAdapter
from feedparser import parse

from config.init_config import Config, Bot_variables


async def check_on_rss_feed():
    while True:
        datetime_from = datetime.fromisoformat(Config.get_rss_feed_settings().rss_last_date)
        send = False
        entries = parse(Config.get_rss_feed_settings().rss_url).entries
        entries.reverse()
        for entry in entries:
            if datetime.fromisoformat(entry.published) > datetime_from:
                send = True
                Bot_variables.webhook_rss.send(entry.link)
        if send:
            Config.get_rss_feed_settings().rss_last_date = entries[-1].published
            Config.save_config()
        await asleep(Config.get_rss_feed_settings().rss_download_delay)


def create_feed_webhook():
    if Bot_variables.webhook_rss is None and Config.get_rss_feed_settings().rss_url and \
            Config.get_rss_feed_settings().webhook_url:
        Bot_variables.webhook_rss = Webhook.from_url(url=Config.get_rss_feed_settings().webhook_url,
                                                     adapter=RequestsWebhookAdapter())
