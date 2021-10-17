import socket
from contextlib import suppress
from os import SEEK_END, stat, linesep
from pathlib import Path
from re import search, split, findall
from sys import exc_info
from threading import Thread
from time import sleep
from traceback import format_exc

from colorama import Fore, Style
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
                print(get_translation("Watcher Error: File '{0}' wasn't found!").format(self._filename.as_posix()))
            except UnicodeDecodeError:
                print(get_translation("Watcher Error: Can't decode strings from file '{0}'"
                                      ", check that minecraft server saves it in utf-8 encoding!\n"
                                      "(Ensure you have '-Dfile.encoding=UTF-8' as one of the arguments "
                                      "to start the server in start script)").format(self._filename.as_posix()))
            except BaseException:
                exc = format_exc().rstrip("\n")
                print(get_translation("Watcher Unhandled Error: {0}").format(exc_info()[0]) +
                      f"\n{Style.DIM}{Fore.RED}{exc}{Style.RESET_ALL}")

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
        last_lines = last_lines[-1:]

    mention_max_words = 5
    mention_max_right_symbols = 5

    for line in last_lines:
        if search(r"\[Server thread/INFO]", line) and search(r"<([^>]*)> (.*)", line) and ": <" in line:
            player_nick, player_message = search(r"<([^>]*)>", line)[0], \
                                          split(r"<([^>]*)>", line, maxsplit=1)[-1].strip()
            if search(r"@[^\s]+", player_message):
                split_arr = split(r"@[^\s]+", player_message)
                mentions = [[i[1:]] for i in findall(r"@[^\s]+", player_message)]
                for i_mention in range(len(mentions)):
                    for words_number in range(mention_max_words + 1):
                        if len(split_arr[1 + i_mention]) < words_number:
                            break
                        found = False
                        add_string = " ".join(split_arr[1 + i_mention].lstrip(" ").split(" ")[:words_number]) \
                            if words_number > 0 else ""
                        for symbols_number in range(mention_max_right_symbols + 1):
                            mention = f"{mentions[i_mention][0]} {add_string}".lower() \
                                if len(add_string) > 0 else mentions[i_mention][0].lower()
                            cut_right_string = None
                            if symbols_number > 0:
                                cut_right_string = mention[-symbols_number:]
                                mention = mention[:-symbols_number]
                            found = False
                            # Check mention of everyone and here
                            for mention_pattern in ["a", "e", "everyone", "p", "here"]:
                                if mention_pattern == mention:
                                    mentions[i_mention] = [mention_pattern]
                                    if cut_right_string is not None:
                                        mentions[i_mention].extend([None, cut_right_string])
                                    found = True
                                    break
                            # Check mention on user mention
                            for member in BotVars.bot_for_webhooks.guilds[0].members:
                                if member.name.lower() == mention:
                                    mentions[i_mention] = [member.name if len(add_string) == 0
                                                           else [member.name, add_string], member]
                                    if cut_right_string is not None:
                                        mentions[i_mention].append(cut_right_string)
                                    found = True
                                    break
                                elif member.display_name.lower() == mention:
                                    mentions[i_mention] = [member.display_name if len(add_string) == 0
                                                           else [member.display_name, add_string], member]
                                    if cut_right_string is not None:
                                        mentions[i_mention].append(cut_right_string)
                                    found = True
                                    break
                            if found:
                                break
                            # Check mention on role mention
                            for role in BotVars.bot_for_webhooks.guilds[0].roles:
                                if role.name.lower() == mention:
                                    mentions[i_mention] = [role.name if len(add_string) == 0
                                                           else [role.name, add_string], role]
                                    if cut_right_string is not None:
                                        mentions[i_mention].append(cut_right_string)
                                    found = True
                                    break
                            if found:
                                break
                            # Check mention on minecraft nick mention
                            for user in Config.get_settings().known_users:
                                if user.user_minecraft_nick.lower() == mention:
                                    if len(mentions[i_mention]) == 1:
                                        mentions[i_mention] = [user.user_minecraft_nick if len(add_string) == 0
                                                               else [user.user_minecraft_nick, add_string], []]
                                        if cut_right_string is not None:
                                            mentions[i_mention].append(cut_right_string)
                                    if isinstance(mentions[i_mention][1], list):
                                        mentions[i_mention][1] += [m for m in BotVars.bot_for_webhooks.guilds[0].members
                                                                   if m.id == user.user_discord_id]
                                        found = True
                            if found:
                                break
                        if found:
                            break
                insert_numb = 1
                mention_nicks = []
                for mention in mentions:
                    if isinstance(mention[0], str):
                        is_list = False
                    elif isinstance(mention[0], list):
                        is_list = True
                    else:
                        raise ValueError("mention[0] is not string or list!")

                    if (mention[0] if not is_list else mention[0][0]) in ["a", "e", "everyone"]:
                        if len(mention) == 3:
                            split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"
                        split_arr.insert(insert_numb, f"@everyone")
                        if "@a" not in mention_nicks:
                            mention_nicks.append("@a")
                    elif (mention[0] if not is_list else mention[0][0]) in ["p", "here"]:
                        if len(mention) == 3:
                            split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"
                        split_arr.insert(insert_numb, f"@here")
                        if "@a" not in mention_nicks:
                            mention_nicks.append("@a")
                    elif len(mention) > 1 and isinstance(mention[1], list):
                        if not is_list:
                            if len(mention) == 3:
                                split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"
                            split_arr.insert(insert_numb,
                                             f"@{mention[0]} ({', '.join([mn.mention for mn in mention[1]])})")
                        else:
                            split_arr[insert_numb] = split_arr[insert_numb][1:].lstrip(mention[0][1])
                            if len(mention) == 3:
                                split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"
                            split_arr.insert(insert_numb,
                                             f"@{mention[0][0]} ({', '.join([mn.mention for mn in mention[1]])})")
                        if "@a" not in mention_nicks:
                            mention_nicks.append(mention[0] if not is_list else mention[0][0])
                    else:
                        if not is_list:
                            if len(mention) == 3:
                                split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"
                            split_arr.insert(insert_numb,
                                             mention[1].mention if len(mention) > 1 and
                                                                   mention[1] is not None else f"@{mention[0]}")
                        else:
                            split_arr[insert_numb] = split_arr[insert_numb][1:].lstrip(mention[0][1])
                            if len(mention) == 3:
                                split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"
                            split_arr.insert(insert_numb,
                                             mention[1].mention if len(mention) > 1 and
                                                                   mention[1] is not None else f"@{mention[0][0]}")
                    insert_numb += 2
                player_message = "".join(split_arr)

                if len(mention_nicks) > 0:
                    from components.additional_funcs import announce, connect_rcon, times

                    with suppress(ConnectionError, socket.error):
                        with connect_rcon() as cl_r:
                            with times(0, 60, 20, cl_r):
                                for nick in mention_nicks:
                                    announce(nick, f"@{player_nick[1:-1]} -> @{nick if nick != '@a' else 'everyone'}",
                                             cl_r)

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
