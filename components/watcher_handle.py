import socket
from contextlib import suppress
from datetime import datetime
from os import SEEK_END, stat
from pathlib import Path
from re import search, split, findall
from sys import exc_info
from threading import Thread
from time import sleep
from traceback import format_exc

from colorama import Fore, Style
from discord import Webhook, RequestsWebhookAdapter, TextChannel

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
        self._refresh_delay_secs = Config.get_server_watcher().refresh_delay_of_console_log
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
                                      ", check that Minecraft server saves it in utf-8 encoding!\n"
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

    from components.additional_funcs import get_server_version
    server_version = get_server_version()
    if 7 <= server_version:
        path_to_server_log = "logs/latest.log"
    elif 0 <= server_version < 7:
        path_to_server_log = "server.log"
    else:
        return

    BotVars.watcher_of_log_file = Watcher(watch_file=Path(Config.get_selected_server_from_list().working_directory,
                                                          path_to_server_log),
                                          call_func_on_change=_check_log_file)


def create_chat_webhook():
    if Config.get_cross_platform_chat_settings().webhook_url:
        BotVars.webhook_chat = Webhook.from_url(url=Config.get_cross_platform_chat_settings().webhook_url,
                                                adapter=RequestsWebhookAdapter())


def _check_log_file(file: Path, last_line: str = None):
    if Config.get_cross_platform_chat_settings().channel_id is None and \
            not Config.get_auth_security().enable_auth_security:
        return

    last_lines = _get_last_n_lines(file, Config.get_server_watcher().number_of_lines_to_check_in_console_log, last_line)
    if len(last_lines) == 0:
        return last_line

    if last_line is None:
        if Config.get_auth_security().enable_auth_security:
            last_lines = last_lines[-5:]
        else:
            last_lines = last_lines[-2:]

    mention_max_words = 5
    mention_max_right_symbols = 5

    for line in last_lines:
        if Config.get_cross_platform_chat_settings().channel_id is not None:
            if search(r"INFO", line) and "*" not in split(r"<([^>]*)>", line, maxsplit=1)[0] and \
                    search(r"<([^>]*)> (.*)", line):
                player_nick, player_message = search(r"<([^>]*)>", line)[0][1:-1], \
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
                                # Check mention on Minecraft nick mention
                                for user in Config.get_settings().known_users:
                                    if user.user_minecraft_nick.lower() == mention:
                                        if len(mentions[i_mention]) == 1:
                                            mentions[i_mention] = [user.user_minecraft_nick if len(add_string) == 0
                                                                   else [user.user_minecraft_nick, add_string], []]
                                            if cut_right_string is not None:
                                                mentions[i_mention].append(cut_right_string)
                                        if isinstance(mentions[i_mention][1], list):
                                            mentions[i_mention][1] += [m for m in
                                                                       BotVars.bot_for_webhooks.guilds[0].members
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
                                        announce(nick, f"@{player_nick} -> @{nick if nick != '@a' else 'everyone'}",
                                                 cl_r)

                player_url_pic = None
                for user in Config.get_settings().known_users:
                    if user.user_minecraft_nick.lower() == player_nick.lower():
                        possible_users = [m for m in BotVars.bot_for_webhooks.guilds[0].members
                                          if m.id == user.user_discord_id]
                        if len(possible_users) > 0:
                            player_url_pic = possible_users[0].avatar_url
                            break

                BotVars.webhook_chat.send(player_message, username=player_nick, avatar_url=player_url_pic)

        if Config.get_auth_security().enable_auth_security:
            from components.additional_funcs import connect_rcon, add_quotes
            if search(r"INFO", line) and "*" not in split(r"[\w ]+\[/\d+\.\d+\.\d+\.\d+:\d+]", line)[0] and \
                    search(r": [\w ]+\[/\d+\.\d+\.\d+\.\d+:\d+] logged in with entity id \d+ at", line):
                nick = search(r": [\w ]+\[", line)[0][2:-1]
                ip_address = search(r"\[/\d+\.\d+\.\d+\.\d+:\d+]", line)[0].split(":")[0][2:]
                if nick not in [u.nick for u in Config.get_auth_users()]:
                    Config.add_auth_user(nick)
                nick_numb = [i for i in range(len(Config.get_auth_users()))
                             if Config.get_auth_users()[i].nick == nick][0]
                if ip_address in [ip.ip_address for ip in Config.get_auth_users()[nick_numb].ip_addresses]:
                    user_attempts, code = Config.update_ip_address(nick, ip_address)
                else:
                    user_attempts, code = Config.add_ip_address(nick, ip_address, is_login_attempt=True)
                if code is not None and user_attempts is not None:
                    if user_attempts >= Config.get_auth_security().max_login_attempts + 1:
                        with suppress(ConnectionError, socket.error):
                            with connect_rcon() as cl_r:
                                cl_r.run(f"ban-ip {ip_address} " +
                                         get_translation("Too many login attempts\nYour IP: {0}").format(ip_address))
                            Config.remove_ip_address([nick], ip_address)
                            msg = get_translation("Too many login attempts: User was banned!\n"
                                                  "Nick: {0}\nIP: {1}\nTime: {2}") \
                                .format(nick, ip_address, datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
                            channel = _get_commands_channel()
                            BotVars.bot_for_webhooks.loop.create_task(channel.send(add_quotes(msg)))
                    else:
                        with suppress(ConnectionError, socket.error):
                            with connect_rcon() as cl_r:
                                cl_r.kick(nick, get_translation("Not authorized\nYour IP: {0}\nCode: {1}")
                                          .format(ip_address, code))
                        member = None
                        for user in Config.get_known_users_list():
                            if user.user_minecraft_nick == nick:
                                member = [m for m in BotVars.bot_for_webhooks.guilds[0].members
                                          if m.id == user.user_discord_id][0]
                        msg = get_translation("Connection attempt detected!\nNick: {0}\n"
                                              "IP: {1}\nConnection attempts: {2}\nTime: {3}") \
                            .format(nick, ip_address,
                                    f"{user_attempts}/{Config.get_auth_security().max_login_attempts}",
                                    datetime.now().strftime('%d/%m/%Y %H:%M:%S'))
                        msg = add_quotes(msg) + "\n"
                        msg += get_translation("To proceed enter command `{0}` within {1} min") \
                            .format(f"{Config.get_settings().bot_settings.prefix}auth login <nick> <code>",
                                    Config.get_auth_security().mins_before_code_expires)
                        if member is not None:
                            BotVars.bot_for_webhooks.loop.create_task(member.send(msg))
                        else:
                            channel = _get_commands_channel()
                            BotVars.bot_for_webhooks.loop.create_task(channel.send(msg))
                Config.save_auth_users()

    for line in reversed(last_lines):
        if search(r"^\[\d+:\d+:\d+]", line):
            return line


def _get_commands_channel():
    channel = BotVars.bot_for_webhooks.guilds[0] \
        .get_channel(Config.get_settings().bot_settings.commands_channel_id)
    if channel is None:
        channel = [ch for ch in BotVars.bot_for_webhooks.guilds[0].channels
                   if isinstance(ch, TextChannel)][0]
    return channel


def _get_last_n_lines(file, number_of_lines, last_line):
    list_of_lines = []
    with open(file, 'rb') as read_obj:
        read_obj.seek(-2, SEEK_END)
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
