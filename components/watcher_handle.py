from os import SEEK_END, SEEK_CUR, stat
from pathlib import Path
from re import search, split, findall
from sys import exc_info
from threading import Thread
from time import sleep

from discord import Webhook, RequestsWebhookAdapter

from config.init_config import Config, BotVars


class Watcher:
    _running = True
    _thread = None

    # Constructor
    def __init__(self, watch_file, call_func_on_change=None, *args, **kwargs):
        self._cached_stamp = None
        self._filename = watch_file
        self._call_func_on_change = call_func_on_change
        self._refresh_delay_secs = Config.get_cross_platform_chat_settings().refresh_delay_of_console_log
        self._args = args
        self._kwargs = kwargs

    # Look for changes
    def look(self):
        stamp = stat(self._filename).st_mtime
        if stamp != self._cached_stamp:
            temp = self._cached_stamp
            self._cached_stamp = stamp
            if self._call_func_on_change is not None and temp is not None:
                self._call_func_on_change(file=self._filename, *self._args, **self._kwargs)

    # Keep watching in a loop
    def watch(self):
        while self._running:
            try:
                # Look for changes
                sleep(self._refresh_delay_secs)
                self.look()
            except FileNotFoundError:
                print(f"File {self._filename} wasn't found!")
            except BaseException:
                print('Unhandled error: %s' % exc_info()[0])

    def start(self):
        self._thread = Thread(target=self.watch)
        self._thread.daemon = True
        self._thread.start()

    def stop(self):
        self._running = False
        self._thread.join()
        self._thread = None

    def is_running(self):
        return self._running


def create_watcher():
    if BotVars.watcher_of_log_file is not None and BotVars.watcher_of_log_file.is_running():
        BotVars.watcher_of_log_file.stop()

    BotVars.watcher_of_log_file = Watcher(watch_file=Path(Config.get_selected_server_from_list().working_directory
                                                          + "/logs/latest.log"),
                                          call_func_on_change=_check_log_file)
    if BotVars.webhook_chat is None:
        BotVars.webhook_chat = \
            Webhook.from_url(url=Config.get_cross_platform_chat_settings().webhook_url,
                             adapter=RequestsWebhookAdapter())


def _check_log_file(file: Path):
    if Config.get_cross_platform_chat_settings().channel_id is None:
        return

    with open(file=file, mode="rb") as log_file:
        log_file.seek(-2, SEEK_END)
        while log_file.read(1) != b'\n':
            log_file.seek(-2, SEEK_CUR)
        last_line = log_file.readline().decode()

    if not last_line:
        return

    if search(r"\[Server thread/INFO]", last_line) and search(r"<([^>]*)> (.*)", last_line) and ": <" in last_line:
        player_nick, player_message = search(r"<([^>]*)>", last_line)[0], \
                                      split(r"<([^>]*)>", last_line, maxsplit=1)[-1].strip()
        if search(r"@.+", player_message):
            split_arr = split(r"@[^\s]+", player_message)
            members = {i[1:].lower(): None for i in findall(r"@[^\s]+", player_message)}
            for guild in BotVars.bot_for_webhooks.guilds:
                for member in guild.members:
                    if member.name.lower() in members.keys():
                        members[member.name.lower()] = member
                    elif member.display_name.lower() in members.keys():
                        members[member.display_name.lower()] = member
            i = 1
            for name, member in members.items():
                split_arr.insert(i, member.mention if member is not None else f"@{name}")
                i += 2
            player_message = "".join(split_arr)

        BotVars.webhook_chat.send(rf"**{player_nick}** {player_message}")
