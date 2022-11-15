from re import search
from typing import List

from discord import (
    NotFound, Webhook, ChannelType
)
from discord.ext import commands
from discord.utils import get as utils_get

from components.rss_feed import get_feed_webhook
from components.logs.utils import get_chat_webhook
from config.init_config import Config, BotVars


def remove_owned_webhooks(webhooks: List[Webhook]):
    bot_webhooks = [
        int(search(r"https?://discord\.com/api/webhooks/(?P<id>\d+)?/.*", bot_w).group("id"))
        for bot_w in [
            Config.get_rss_feed_settings().webhook_url,
            Config.get_game_chat_settings().webhook_url
        ] if bot_w
    ]
    return sorted([w for w in webhooks if w.id not in bot_webhooks], key=lambda w: w.created_at)


async def create_webhooks(bot: commands.Bot):
    channel = bot.guilds[0].get_channel(Config.get_settings().bot_settings.commands_channel_id)
    if channel is None:
        channel = utils_get(bot.guilds[0].channels, type=ChannelType.text)
    webhooks = [w for w in await bot.guilds[0].webhooks() if w.user.id == bot.user.id]

    if Config.get_rss_feed_settings().enable_rss_feed and BotVars.webhook_rss is None:
        free_webhooks = remove_owned_webhooks(webhooks)
        try:
            await get_feed_webhook(channel, free_webhooks)
        except NotFound:
            Config.get_rss_feed_settings().webhook_url = None
            await get_feed_webhook(channel, free_webhooks)
    if Config.get_game_chat_settings().enable_game_chat and BotVars.webhook_chat is None:
        free_webhooks = remove_owned_webhooks(webhooks)
        try:
            await get_chat_webhook(channel, free_webhooks)
        except NotFound:
            Config.get_game_chat_settings().webhook_url = None
            await get_chat_webhook(channel, free_webhooks)
