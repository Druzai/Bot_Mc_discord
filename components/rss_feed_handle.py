from asyncio import sleep as asleep
from datetime import datetime

from discord import Webhook, RequestsWebhookAdapter
from feedparser import parse

from config.init_config import Config, Bot_variables


async def check_on_rss_feed():
    while True:
        datetime_from = datetime.fromisoformat(Config.get_rss_last_date())
        send = False
        entries = parse(Config.get_rss_url()).entries
        entries.reverse()
        for entry in entries:
            if datetime.fromisoformat(entry.published) > datetime_from:
                send = True
                Bot_variables.webhook_rss.send(entry.link)
        if send:
            Config.set_rss_last_date(entries[-1].published)
            Config.save_config()
        await asleep(3600)


def create_feed_webhook():
    if Bot_variables.webhook_rss is None and Config.get_rss_url() and Config.get_webhook_rss():
        Bot_variables.webhook_rss = Webhook.from_url(url=Config.get_webhook_rss(), adapter=RequestsWebhookAdapter())
