from pathlib import Path
from typing import Optional, List, TYPE_CHECKING
from queue import Queue
from discord import SyncWebhook, Webhook, TextChannel

from components.localization import get_translation
from components.logs.data import LogMessage
from components.logs.handler import HandlerThread
from components.logs.watcher import WatchThread
from config.init_config import Config, BotVars

from components.minecraft.connect import ServerVersion

if TYPE_CHECKING:
    from cogs.poll_cog import Poll


class Watcher:
    def __init__(self, watch_file: Path, server_version: ServerVersion,  poll: Optional['Poll']):
        self._running = False
        self._watcher_thread = None
        self._handler_thread = None
        self._filename: Path = watch_file
        self._queue: Queue[LogMessage] = Queue()
        self._server_version = server_version
        if poll is None:
            raise RuntimeError("Cog 'Poll' wasn't found!")
        self._poll = poll

    def start(self):
        if self._running:
            return

        self._running = True
        self._watcher_thread = WatchThread(self._filename, self._queue, self._server_version)
        self._watcher_thread.start()
        self._handler_thread = HandlerThread(self._queue, self._server_version, self._poll)
        self._handler_thread.start()

    def stop(self):
        self._running = False
        if self._watcher_thread is not None:
            self._watcher_thread.join()
            self._watcher_thread = None
        self._queue.join()
        if self._handler_thread is not None:
            self._handler_thread.join()
            self._handler_thread = None

    def is_running(self):
        return self._running


def create_watcher(watcher: Optional[Watcher], server_version: ServerVersion):
    if watcher is not None and watcher.is_running():
        watcher.stop()

    if 7 <= server_version.minor:
        path_to_server_log = "logs/latest.log"
    else:
        path_to_server_log = "server.log"

    return Watcher(
        watch_file=Path(Config.get_selected_server_from_list().working_directory, path_to_server_log),
        server_version=server_version,
        poll=BotVars.bot_for_webhooks.get_cog("Poll")
    )


async def get_chat_webhook(channel: Optional[TextChannel], webhooks: Optional[List[Webhook]]):
    need_to_save = False
    if Config.get_game_chat_settings().webhook_url:
        BotVars.webhook_chat = SyncWebhook.from_url(
            url=Config.get_game_chat_settings().webhook_url,
            bot_token=Config.get_settings().bot_settings.token
        ).fetch()
    elif (webhooks is not None and len(webhooks) > 0) or channel is not None:
        if webhooks is not None and len(webhooks) > 0:
            webhook = webhooks[0]
        else:
            webhook = await channel.create_webhook(name=get_translation("Game chat webhook"))
        BotVars.webhook_chat = SyncWebhook.from_url(
            url=webhook.url,
            bot_token=Config.get_settings().bot_settings.token
        ).fetch()
        Config.get_game_chat_settings().webhook_url = webhook.url
        need_to_save = True
    else:
        raise ValueError("'channel' and 'webhooks' are not declared!")

    if need_to_save:
        Config.save_config()
