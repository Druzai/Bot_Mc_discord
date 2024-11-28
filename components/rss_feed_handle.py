from contextlib import suppress
from datetime import datetime
from time import mktime
from typing import List, Optional

from discord import SyncWebhook, Webhook, TextChannel
from feedparser import parse

from components.localization import get_translation
from config.init_config import Config, BotVars, UserAgent


async def check_on_rss_feed():
    try:
        datetime_from = datetime.fromisoformat(Config.get_rss_feed_settings().rss_last_date)
    except (ValueError, TypeError):
        print(get_translation("RSS Warning: Date from bot config is invalid. Bot will use current date for checking..."))
        datetime_from = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if datetime_from.tzinfo is not None:
        datetime_from = datetime.fromtimestamp(datetime_from.timestamp())
    if Config.get_rss_feed_settings().rss_url is None:
        print(get_translation("RSS Warning: URL of RSS feed doesn't set!"))
        return

    send = False
    if Config.get_enable_rss_proxy():
        headers = BotVars.wh_session_rss.headers
        if Config.get_rss_feed_settings().rss_spoof_user_agent:
            headers["User-Agent"] = UserAgent.get_header()
        text = BotVars.wh_session_rss.get(
            Config.get_rss_feed_settings().rss_url,
            timeout=(10, None),
            headers=headers
        ).text
        parsed = parse(text)
    else:
        parsed = parse(
            Config.get_rss_feed_settings().rss_url,
            agent=UserAgent.get_header() if Config.get_rss_feed_settings().rss_spoof_user_agent else None
        )
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


async def get_feed_webhook(channel: Optional[TextChannel], webhooks: Optional[List[Webhook]]):
    if BotVars.wh_session_rss is None:
        BotVars.wh_session_rss = Config.get_webhook_proxy_session()
    if Config.get_rss_feed_settings().webhook_url:
        BotVars.webhook_rss = SyncWebhook.from_url(
            url=Config.get_rss_feed_settings().webhook_url,
            bot_token=Config.get_settings().bot_settings.token,
            session=BotVars.wh_session_rss
        ).fetch()
    elif (webhooks is not None and len(webhooks) > 0) or channel is not None:
        if webhooks is not None and len(webhooks) > 0:
            webhook = webhooks[0]
        else:
            webhook = await channel.create_webhook(name=get_translation("RSS webhook"))
        BotVars.webhook_rss = SyncWebhook.from_url(
            url=webhook.url,
            bot_token=Config.get_settings().bot_settings.token,
            session=BotVars.wh_session_rss
        ).fetch()
        Config.get_rss_feed_settings().webhook_url = webhook.url
        Config.save_config()
    else:
        raise ValueError("'channel' and 'webhooks' are not declared!")
