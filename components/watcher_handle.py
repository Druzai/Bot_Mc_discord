from os import SEEK_END, SEEK_CUR, stat
from pathlib import Path
from re import search, split, findall
from sys import exc_info
from threading import Thread
from time import sleep

from discord import Webhook, RequestsWebhookAdapter

from config.init_config import Config, Bot_variables


class Watcher:
    running = True
    refresh_delay_secs = Config.get_watcher_refresh_delay()
    thread = None

    # Constructor
    def __init__(self, watch_file, call_func_on_change=None, *args, **kwargs):
        self._cached_stamp = None
        self.filename = watch_file
        self.call_func_on_change = call_func_on_change
        self.args = args
        self.kwargs = kwargs

    # Look for changes
    def look(self):
        stamp = stat(self.filename).st_mtime
        if stamp != self._cached_stamp:
            temp = self._cached_stamp
            self._cached_stamp = stamp
            if self.call_func_on_change is not None and temp is not None:
                self.call_func_on_change(*self.args, **self.kwargs)

    # Keep watching in a loop
    def watch(self):
        while self.running:
            try:
                # Look for changes
                sleep(self.refresh_delay_secs)
                self.look()
            except FileNotFoundError:
                print(f"File {self.filename} wasn't found!")
            except BaseException:
                print('Unhandled error: %s' % exc_info()[0])

    def start(self):
        self.thread = Thread(target=self.watch)
        self.thread.daemon = True
        self.thread.start()

    def stop(self):
        self.running = False
        self.thread.join()
        self.thread = None

    def isrunning(self):
        return self.running


def create_watcher():
    if Bot_variables.watcher_of_log_file is not None and Bot_variables.watcher_of_log_file.isrunning():
        Bot_variables.watcher_of_log_file.stop()

    Bot_variables.watcher_of_log_file = Watcher(Path(Config.get_selected_server_list()[0] + "/logs/latest.log"),
                                                _check_log_file)
    if Bot_variables.webhook_chat is None:
        Bot_variables.webhook_chat = Webhook.from_url(url=Config.get_webhook_chat(), adapter=RequestsWebhookAdapter())


def _check_log_file():
    if Config.get_discord_channel_id_for_crossplatform_chat() is None:
        return

    with open(file=Path(Config.get_selected_server_list()[0] + "/logs/latest.log"), mode="rb") as log_file:
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
            for guild in Bot_variables.bot_for_webhooks.guilds:
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

        Bot_variables.webhook_chat.send(rf"**{player_nick}** {player_message}")  # , username='WEBHOOK_BOT'
