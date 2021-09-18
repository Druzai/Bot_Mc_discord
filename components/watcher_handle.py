from os import SEEK_END, stat, linesep
from pathlib import Path
from re import search, split, findall
from sys import exc_info
from threading import Thread
from time import sleep
from traceback import print_exc

from discord import Webhook, RequestsWebhookAdapter

from components.localization import get_translation
from config.init_config import Config, BotVars


class Watcher:
    _running = True
    _thread = None

    # Constructor
    def __init__(self, watch_file: Path, call_func_on_change=None, *args, **kwargs):
        self._cached_stamp = None
        self._filename: Path = watch_file
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
                BotVars.watcher_last_line = self._call_func_on_change(file=self._filename,
                                                                      last_line=BotVars.watcher_last_line,
                                                                      *self._args, **self._kwargs)

    # Keep watching in a loop
    def watch(self):
        while self._running:
            try:
                # Look for changes
                sleep(self._refresh_delay_secs)
                self.look()
            except FileNotFoundError:
                print(get_translation("Watcher Error: File '{0}' wasn't found!").format(self._filename))
            except UnicodeDecodeError:
                print(get_translation("Watcher Error: Can't decode strings from file '{0}'"
                                      ", check that minecraft server saves it in utf-8 encoding!\n"
                                      "(Ensure you have '-Dfile.encoding=UTF-8' as one of the arguments "
                                      "to start the server in start script)").format(self._filename.as_posix()))
            except BaseException:
                print(get_translation("Watcher Unhandled Error: {0}").format(exc_info()[0]))
                print_exc()

    def start(self):
        self._thread = Thread(target=self.watch, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
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


def create_chat_webhook():
    if Config.get_cross_platform_chat_settings().webhook_url:
        BotVars.webhook_chat = Webhook.from_url(url=Config.get_cross_platform_chat_settings().webhook_url,
                                                adapter=RequestsWebhookAdapter())


def _check_log_file(file: Path, last_line: str = None):
    if Config.get_cross_platform_chat_settings().channel_id is None:
        return

    last_lines = _get_last_n_lines(file,
                                   Config.get_cross_platform_chat_settings().number_of_lines_to_check_in_console_log,
                                   last_line)
    if len(last_lines) == 0:
        return last_line

    if last_line is None:
        last_lines = last_lines[-1]

    for line in last_lines:
        if search(r"\[Server thread/INFO]", line) and search(r"<([^>]*)> (.*)", line) and ": <" in line:
            player_nick, player_message = search(r"<([^>]*)>", line)[0], \
                                          split(r"<([^>]*)>", line, maxsplit=1)[-1].strip()
            if search(r"@.+", player_message):
                split_arr = split(r"@[^\s]+", player_message)
                mentions = {i[1:].lower(): None for i in findall(r"@[^\s]+", player_message)}
                for guild in BotVars.bot_for_webhooks.guilds:
                    # Check mention on user mention
                    for member in guild.members:
                        if member.name.lower() in mentions.keys():
                            mentions[member.name.lower()] = member
                        elif member.display_name.lower() in mentions.keys():
                            mentions[member.display_name.lower()] = member
                    # Check mention on role mention
                    for role in guild.roles:
                        if role.name.lower() in mentions.keys():
                            mentions[role.name.lower()] = role
                i = 1
                for name, mention_obj in mentions.items():
                    split_arr.insert(i, mention_obj.mention if mention_obj is not None else f"@{name}")
                    i += 2
                player_message = "".join(split_arr)

            BotVars.webhook_chat.send(f"**{player_nick}** {player_message}")

    return last_lines[-1]


def _get_last_n_lines(file, number_of_lines, last_line):
    list_of_lines = []
    with open(file, 'rb') as read_obj:
        read_obj.seek(-len(linesep), SEEK_END)
        buffer = bytearray()
        pointer_location = read_obj.tell()
        while pointer_location >= 0:
            read_obj.seek(pointer_location)
            pointer_location = pointer_location - 1
            new_byte = read_obj.read(1)
            if new_byte == b'\n':
                decoded_line = buffer[::-1].decode().strip()
                if decoded_line == last_line:
                    return list(reversed(list_of_lines))
                list_of_lines.append(decoded_line)
                if len(list_of_lines) == number_of_lines:
                    return list(reversed(list_of_lines))
                buffer = bytearray()
            else:
                buffer.extend(new_byte)
        if len(buffer) > 0:
            list_of_lines.append(buffer[::-1].decode().strip())
    return list(reversed(list_of_lines))
