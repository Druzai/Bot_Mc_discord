import datetime as dt
import socket
from asyncio import run_coroutine_threadsafe, Queue, QueueEmpty, new_event_loop
from contextlib import suppress
from datetime import datetime
from os import SEEK_END, stat
from pathlib import Path
from re import search, split, findall, sub
from sys import exc_info
from threading import Thread
from time import sleep
from traceback import format_exc
from typing import TYPE_CHECKING

from colorama import Fore, Style
from discord import NoMoreItems
from discord import Webhook, RequestsWebhookAdapter, TextChannel, Role, ChannelType
from discord.iterators import _AsyncIterator, OLDEST_OBJECT
from discord.object import Object
from discord.utils import get as utils_get
from discord.utils import time_snowflake

from components.localization import get_translation
from config.init_config import Config, BotVars

if TYPE_CHECKING:
    from components.additional_funcs import ServerVersion


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
    if 7 <= server_version.minor:
        path_to_server_log = "logs/latest.log"
    elif 0 <= server_version.minor < 7:
        path_to_server_log = "server.log"
    else:
        return

    BotVars.watcher_of_log_file = Watcher(watch_file=Path(Config.get_selected_server_from_list().working_directory,
                                                          path_to_server_log),
                                          call_func_on_change=_check_log_file,
                                          server_version=server_version,
                                          poll=BotVars.bot_for_webhooks.get_cog("Poll"))


def create_chat_webhook():
    if Config.get_cross_platform_chat_settings().webhook_url:
        BotVars.webhook_chat = Webhook.from_url(url=Config.get_cross_platform_chat_settings().webhook_url,
                                                adapter=RequestsWebhookAdapter())


def _check_log_file(file: Path, server_version: 'ServerVersion', last_line: str = None, poll=None):
    if Config.get_cross_platform_chat_settings().channel_id is None and \
            not Config.get_secure_auth().enable_secure_auth:
        return

    last_lines = _get_last_n_lines(file, Config.get_server_watcher().number_of_lines_to_check_in_console_log, last_line)
    if len(last_lines) == 0:
        return last_line

    date_line = r"^\[(\d{2}\w{3}\d{4} )?\d+:\d+:\d+(\.\d+)?]" if server_version.minor > 6 \
        else r"^\d+-\d+-\d+ \d+:\d+:\d+"
    INFO_line = r"\[Server thread/INFO][^\*<>]*:" if server_version.minor > 6 else r"\[INFO]"

    if last_line is None:
        if Config.get_secure_auth().enable_secure_auth:
            last_lines = last_lines[-5:]
        else:
            last_lines = last_lines[-2:]
    last_lines = [sub(r"§[0-9abcdefklmnor]", "", line) for line in last_lines]

    for line in last_lines:
        if Config.get_cross_platform_chat_settings().channel_id is not None:
            if search(rf"{date_line} {INFO_line} <([^>]*)> (.*)", line):
                player_nick, player_message = search(r"<([^>]*)>", line)[0][1:-1], \
                                              split(r"<([^>]*)>", line, maxsplit=1)[-1].strip()
                if search(r"@[^\s]+", player_message):
                    split_arr = split(r"@[^\s]+", player_message)
                    mentions = [[i[1:]] for i in findall(r"@[^\s]+", player_message)]
                    for i_mention in range(len(mentions)):
                        for words_number in range(Config.get_cross_platform_chat_settings().max_words_in_mention + 1):
                            if len(split_arr[1 + i_mention]) < words_number:
                                break
                            found = False
                            add_string = " ".join(split_arr[1 + i_mention].lstrip(" ").split(" ")[:words_number]) \
                                if words_number > 0 else ""
                            for symbols_number in range(Config.get_cross_platform_chat_settings().
                                                                max_wrong_symbols_in_mention_from_right + 1):
                                mention = f"{mentions[i_mention][0]} {add_string}".lower() \
                                    if len(add_string) > 0 else mentions[i_mention][0].lower()
                                cut_right_string = None
                                if symbols_number > 0:
                                    if symbols_number == len(mention):
                                        break
                                    cut_right_string = mention[-symbols_number:]
                                    mention = mention[:-symbols_number]
                                found = False
                                # Check mention of everyone and here
                                for mention_pattern in ["a", "all", "e", "everyone", "p", "here"]:
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
                                            mentions[i_mention][1] += [utils_get(BotVars.bot_for_webhooks
                                                                                 .guilds[0].members,
                                                                                 id=user.user_discord_id)]
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

                        if (mention[0] if not is_list else mention[0][0]) in ["e", "everyone"]:
                            if len(mention) == 3:
                                split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"
                            split_arr.insert(insert_numb, "@everyone")
                            if "@a" not in mention_nicks:
                                mention_nicks.append("@a")
                        elif (mention[0] if not is_list else mention[0][0]) in ["p", "here"]:
                            if len(mention) == 3:
                                split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"
                            split_arr.insert(insert_numb, "@here")
                            if "@a" not in mention_nicks:
                                mention_nicks.append("@a")
                        elif (mention[0] if not is_list else mention[0][0]) in ["a", "all"]:
                            if len(mention) == 3:
                                split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"

                            if Config.get_settings().bot_settings.managing_commands_role_id is None:
                                possible_role = None
                            else:
                                possible_role = utils_get(BotVars.bot_for_webhooks.guilds[0].roles,
                                                          id=Config.get_settings()
                                                          .bot_settings.managing_commands_role_id)
                            if possible_role is not None:
                                split_arr.insert(insert_numb, possible_role.mention)
                                if "@a" not in mention_nicks:
                                    mention_nicks = _get_members_nicks_of_the_role(possible_role, mention_nicks)
                            else:
                                split_arr.insert(insert_numb, "@everyone")
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
                            if "@a" not in mention_nicks and len(mention) > 1 and isinstance(mention[1], Role):
                                mention_nicks = _get_members_nicks_of_the_role(mention[1], mention_nicks)
                        insert_numb += 2
                    player_message = "".join(split_arr)

                    if len(mention_nicks) > 0 and server_version.minor > 7:
                        mention_nicks = set(mention_nicks)
                        nick_owner_id = None
                        for u in Config.get_known_users_list():
                            if u.user_minecraft_nick == player_nick:
                                nick_owner_id = u.user_discord_id
                        for nick in [u.user_minecraft_nick for u in Config.get_known_users_list()
                                     if u.user_discord_id == nick_owner_id]:
                            with suppress(KeyError):
                                mention_nicks.remove(nick)
                        from components.additional_funcs import announce, connect_rcon, times

                        with suppress(ConnectionError, socket.error):
                            with connect_rcon() as cl_r:
                                with times(0, 60, 20, cl_r):
                                    for nick in mention_nicks:
                                        announce(nick, f"@{player_nick} -> @{nick if nick != '@a' else 'everyone'}",
                                                 cl_r)

                if search(r":[^:]+:", player_message):
                    split_arr = split(r":[^:]+:", player_message)
                    emojis = [i[1:-1] for i in findall(r":[^:]+:", player_message)]
                    i = 1
                    for emoji_name in emojis:
                        emoji = utils_get(BotVars.bot_for_webhooks.emojis, name=emoji_name)
                        if emoji is None:
                            emoji = utils_get(BotVars.bot_for_webhooks.guilds[0].emojis, name=emoji_name)
                        if emoji is None:
                            emoji = emoji_name
                        else:
                            emoji = f"<:{emoji.name}:{emoji.id}>"
                        split_arr.insert(i, emoji)
                        i += 2
                    player_message = "".join(split_arr)

                edited_message = False
                if search(r"^\*[^*].*", player_message):
                    chn = BotVars.bot_for_webhooks.get_channel(Config.get_cross_platform_chat_settings().channel_id)
                    if chn is None:
                        print(get_translation("Bot Error: Couldn't find channel for cross-platform chat!"))
                    else:
                        # TODO: Change to 'channel.history' and 'async for' when discord.py 2.0 is out!
                        async def get_last_message(channel: TextChannel):
                            last_msg = None
                            async for message in HistoryIterator(channel, limit=100):
                                if message.author.discriminator == "0000" and message.author.name == player_nick:
                                    last_msg = message
                                    break
                            return last_msg

                        last_message = run_coroutine_threadsafe(get_last_message(chn),
                                                                BotVars.bot_for_webhooks.loop).result()
                        if last_message is not None:
                            last_message_timestamp = int((last_message.edited_at or last_message.created_at)
                                                         .replace(tzinfo=dt.timezone.utc).timestamp())
                            server_timestamp = Config.get_server_config().states.started_info.date_stamp
                            if int(datetime.now().timestamp()) < last_message_timestamp + 18000 and \
                                    (server_timestamp is None or server_timestamp < last_message_timestamp):
                                edited_message = True
                                BotVars.webhook_chat.edit_message(message_id=last_message.id,
                                                                  content=player_message[1:])

                if not edited_message:
                    player_url_pic = None
                    for user in Config.get_settings().known_users:
                        if user.user_minecraft_nick.lower() == player_nick.lower():
                            possible_user = BotVars.bot_for_webhooks.guilds[0].get_member(user.user_discord_id)
                            if possible_user is not None:
                                player_url_pic = possible_user.avatar_url
                                break

                    BotVars.webhook_chat.send(player_message, username=player_nick, avatar_url=player_url_pic)

        if Config.get_secure_auth().enable_secure_auth:
            from components.additional_funcs import connect_rcon, add_quotes
            if not search(rf"{date_line} {INFO_line}", line) or search(rf"{date_line} {INFO_line} \*", line):
                continue
            if search(r"[^\[\]<>]+ lost connection:", line) and \
                    "You logged in from another location" not in split(r"[^\[\]<>]+ lost connection:",
                                                                       line, maxsplit=1)[1]:
                nick = split(r"lost connection:", search(r"[^\[\]<>]+ lost connection:", line)[0])[0].strip()
                Config.set_user_logged(nick, False)
                Config.save_auth_users()

            if search(rf"{INFO_line} [^\[\]<>]+\[/\d+\.\d+\.\d+\.\d+:\d+] logged in with entity id \d+ at", line):
                nick = split(INFO_line, search(rf"{INFO_line} [^\[\]<>]+\[", line)[0], maxsplit=1)[-1][1:-1].strip()
                ip_address = search(r"\[/\d+\.\d+\.\d+\.\d+:\d+]", line)[0].split(":")[0][2:]
                if nick not in [u.nick for u in Config.get_auth_users()]:
                    Config.add_auth_user(nick)
                nick_numb = [i for i in range(len(Config.get_auth_users()))
                             if Config.get_auth_users()[i].nick == nick][0]
                is_invasion_to_ban = Config.get_auth_users()[nick_numb].logged and \
                                     ip_address not in Config.get_known_user_ips()
                is_invasion_to_kick = Config.get_auth_users()[nick_numb].logged and \
                                      ip_address not in Config.get_known_user_ips(nick)

                if not is_invasion_to_ban and not is_invasion_to_kick:
                    if ip_address in [ip.ip_address for ip in Config.get_auth_users()[nick_numb].ip_addresses]:
                        user_attempts, code = Config.update_ip_address(nick, ip_address)
                    else:
                        user_attempts, code = Config.add_ip_address(nick, ip_address, is_login_attempt=True)
                else:
                    user_attempts, code = 0, 0
                if is_invasion_to_ban or is_invasion_to_kick or (code is not None and user_attempts is not None):
                    if is_invasion_to_ban or user_attempts >= Config.get_secure_auth().max_login_attempts + 1:
                        if is_invasion_to_ban:
                            ban_reason = get_translation("Intrusion attempt on already logged in nick\nYour IP: {0}") \
                                .format(ip_address)
                        else:
                            ban_reason = get_translation("Too many login attempts\nYour IP: {0}").format(ip_address)
                        with suppress(ConnectionError, socket.error):
                            with connect_rcon() as cl_r:
                                cl_r.run(f"ban-ip {ip_address} " + ban_reason)
                            if is_invasion_to_ban:
                                ban_reason = get_translation("Intrusion prevented: User was banned!")
                            else:
                                Config.remove_ip_address(ip_address, [nick])
                                ban_reason = get_translation("Too many login attempts: User was banned!")
                            msg = f"{ban_reason}\n" + get_translation("Nick: {0}\nIP: {1}\nTime: {2}") \
                                .format(nick, ip_address, datetime.now().strftime(get_translation("%H:%M:%S %d/%m/%Y")))
                            channel = _get_commands_channel()
                            run_coroutine_threadsafe(channel.send(add_quotes(msg)), BotVars.bot_for_webhooks.loop)
                    else:
                        if is_invasion_to_kick:
                            kick_reason = get_translation("You don't own this logged in nick")
                        else:
                            kick_reason = get_translation("Not authorized\nYour IP: {0}\nCode: {1}").format(ip_address,
                                                                                                            code)
                        with suppress(ConnectionError, socket.error):
                            with connect_rcon() as cl_r:
                                cl_r.kick(nick, kick_reason)
                        if is_invasion_to_kick:
                            continue
                        member = None
                        for user in Config.get_known_users_list():
                            if user.user_minecraft_nick == nick:
                                member = BotVars.bot_for_webhooks.guilds[0].get_member(user.user_discord_id)

                        user_nicks = Config.get_user_nicks(ip_address=ip_address, nick=nick, authorized=True)
                        status = get_translation("Status:") + f" {user_nicks[nick][0][1]}\n"
                        used_nicks = None
                        if (len(user_nicks) != 1 and user_nicks.get(nick, None) is not None) or len(user_nicks) > 1:
                            used_nicks = get_translation("Previously used nicknames:") + "\n"
                            for k, v in user_nicks.items():
                                if k != nick:
                                    used_nicks += f"- {k}: {v[0][1]}\n"
                        if used_nicks is not None:
                            status += used_nicks

                        msg = get_translation("Connection attempt detected!\nNick: {0}\n"
                                              "IP: {1}\n{2}Connection attempts: {3}\nTime: {4}") \
                            .format(nick, ip_address, status,
                                    f"{user_attempts}/{Config.get_secure_auth().max_login_attempts}",
                                    datetime.now().strftime(get_translation("%H:%M:%S %d/%m/%Y")))
                        msg = add_quotes(msg) + "\n"
                        msg += get_translation("To proceed enter command `{0}` within {1} min") \
                                   .format(f"{Config.get_settings().bot_settings.prefix}auth login {nick} <code>",
                                           Config.get_secure_auth().mins_before_code_expires) + "\n"
                        msg += get_translation("To ban this IP-address enter command `{0}`") \
                            .format(f"{Config.get_settings().bot_settings.prefix}auth ban {ip_address} [reason]")
                        if member is not None:
                            for p in poll.get_polls().values():
                                if p.command == f"auth login {nick} {ip_address}":
                                    p.cancel()

                            async def send_message_and_poll(member, msg, poll, nick, ip_address):
                                await member.send(msg)
                                if await poll.run(channel=member,
                                                  embeded_message=get_translation("Login without code?\n(Less safe)"),
                                                  command=f"auth login {nick} {ip_address}",
                                                  need_for_voting=1,
                                                  timeout=Config.get_secure_auth().mins_before_code_expires * 60,
                                                  remove_logs_after=5,
                                                  add_mention=False,
                                                  add_str_count=False):
                                    Config.update_ip_address(nick, ip_address, whitelist=True)
                                    Config.save_auth_users()
                                    await member.send(get_translation("{0}, bot gave access to the nick "
                                                                      "`{1}` with IP-address `{2}`!")
                                                      .format(member.mention, nick, ip_address))

                            run_coroutine_threadsafe(send_message_and_poll(member, msg, poll, nick, ip_address),
                                                     BotVars.bot_for_webhooks.loop)
                        else:
                            channel = _get_commands_channel()
                            run_coroutine_threadsafe(channel.send(msg), BotVars.bot_for_webhooks.loop)
                else:
                    Config.set_user_logged(nick, True)
                Config.save_auth_users()

    for line in reversed(last_lines):
        if search(date_line, line):
            return line


def _get_commands_channel():
    channel = BotVars.bot_for_webhooks.guilds[0] \
        .get_channel(Config.get_settings().bot_settings.commands_channel_id)
    if channel is None:
        channel = utils_get(BotVars.bot_for_webhooks.guilds[0].channels, type=ChannelType.text)
    return channel


def _get_members_nicks_of_the_role(role: Role, mention_nicks: list):
    for member in role.members:
        possible_user = [u.user_minecraft_nick for u in Config.get_settings().known_users
                         if member.id == u.user_discord_id]
        if len(possible_user) != 0:
            mention_nicks.extend(possible_user)
    return mention_nicks


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


# Workaround for getting 'channel.history' from other sync thread
class HistoryIterator(_AsyncIterator):
    def __init__(self, messageable, limit,
                 before=None, after=None, around=None, oldest_first=None):

        if isinstance(before, datetime):
            before = Object(id=time_snowflake(before, high=False))
        if isinstance(after, datetime):
            after = Object(id=time_snowflake(after, high=True))
        if isinstance(around, datetime):
            around = Object(id=time_snowflake(around))

        if oldest_first is None:
            self.reverse = after is not None
        else:
            self.reverse = oldest_first

        self.messageable = messageable
        self.limit = limit
        self.before = before
        self.after = after or OLDEST_OBJECT
        self.around = around

        self._filter = None  # message dict -> bool

        self.state = self.messageable._state
        self.logs_from = self.state.http.logs_from
        try:
            self.messages = Queue()
        except RuntimeError:
            self.messages = Queue(loop=new_event_loop())

        if self.around:
            if self.limit is None:
                raise ValueError('history does not support around with limit=None')
            if self.limit > 101:
                raise ValueError("history max limit 101 when specifying around parameter")
            elif self.limit == 101:
                self.limit = 100  # Thanks discord

            self._retrieve_messages = self._retrieve_messages_around_strategy
            if self.before and self.after:
                self._filter = lambda m: self.after.id < int(m['id']) < self.before.id
            elif self.before:
                self._filter = lambda m: int(m['id']) < self.before.id
            elif self.after:
                self._filter = lambda m: self.after.id < int(m['id'])
        else:
            if self.reverse:
                self._retrieve_messages = self._retrieve_messages_after_strategy
                if (self.before):
                    self._filter = lambda m: int(m['id']) < self.before.id
            else:
                self._retrieve_messages = self._retrieve_messages_before_strategy
                if (self.after and self.after != OLDEST_OBJECT):
                    self._filter = lambda m: int(m['id']) > self.after.id

    async def next(self):
        if self.messages.empty():
            await self.fill_messages()

        try:
            return self.messages.get_nowait()
        except QueueEmpty:
            raise NoMoreItems()

    def _get_retrieve(self):
        l = self.limit
        if l is None or l > 100:
            r = 100
        else:
            r = l
        self.retrieve = r
        return r > 0

    async def flatten(self):
        # this is similar to fill_messages except it uses a list instead
        # of a queue to place the messages in.
        result = []
        channel = await self.messageable._get_channel()
        self.channel = channel
        while self._get_retrieve():
            data = await self._retrieve_messages(self.retrieve)
            if len(data) < 100:
                self.limit = 0  # terminate the infinite loop

            if self.reverse:
                data = reversed(data)
            if self._filter:
                data = filter(self._filter, data)

            for element in data:
                result.append(self.state.create_message(channel=channel, data=element))
        return result

    async def fill_messages(self):
        if not hasattr(self, 'channel'):
            # do the required set up
            channel = await self.messageable._get_channel()
            self.channel = channel

        if self._get_retrieve():
            data = await self._retrieve_messages(self.retrieve)
            if len(data) < 100:
                self.limit = 0  # terminate the infinite loop

            if self.reverse:
                data = reversed(data)
            if self._filter:
                data = filter(self._filter, data)

            channel = self.channel
            for element in data:
                await self.messages.put(self.state.create_message(channel=channel, data=element))

    async def _retrieve_messages(self, retrieve):
        pass

    async def _retrieve_messages_before_strategy(self, retrieve):
        before = self.before.id if self.before else None
        data = await self.logs_from(self.channel.id, retrieve, before=before)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.before = Object(id=int(data[-1]['id']))
        return data

    async def _retrieve_messages_after_strategy(self, retrieve):
        after = self.after.id if self.after else None
        data = await self.logs_from(self.channel.id, retrieve, after=after)
        if len(data):
            if self.limit is not None:
                self.limit -= retrieve
            self.after = Object(id=int(data[0]['id']))
        return data

    async def _retrieve_messages_around_strategy(self, retrieve):
        if self.around:
            around = self.around.id if self.around else None
            data = await self.logs_from(self.channel.id, retrieve, around=around)
            self.around = None
            return data
        return []
