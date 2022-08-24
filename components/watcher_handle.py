import socket
from asyncio import run_coroutine_threadsafe
from contextlib import suppress
from datetime import datetime
from os import SEEK_END, stat
from pathlib import Path
from re import search, split, findall, sub
from sys import exc_info
from threading import Thread
from time import sleep
from traceback import format_exc
from typing import TYPE_CHECKING, Optional

from colorama import Fore, Style
from discord import SyncWebhook, TextChannel, Role, ChannelType
from discord.utils import get as utils_get, escape_markdown, find as utils_find

from components.localization import get_translation
from config.init_config import Config, BotVars

if TYPE_CHECKING:
    from components.additional_funcs import ServerVersion


class Watcher:
    def __init__(self, watch_file: Path, call_func_on_change, **kwargs):
        self._running = False
        self._thread = None
        self._filename: Path = watch_file
        self._call_func_on_change = call_func_on_change
        self._kwargs = kwargs

    def start(self):
        self._running = True
        self._thread = WatchThread(self._filename, self._call_func_on_change, **self._kwargs)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread is not None:
            self._thread.join()
            self._thread = None

    def is_running(self):
        return self._running


class WatchThread(Thread):
    def __init__(self, watch_file: Path, call_func_on_change, **kwargs):
        super().__init__()
        self.name = "WatchThread"
        self.daemon = True
        self._running = True
        self._cached_stamp = None
        self._last_line = None
        self._filename: Path = watch_file
        self._call_func_on_change = call_func_on_change
        self._refresh_delay_secs = Config.get_server_watcher().refresh_delay_of_console_log
        self._kwargs = kwargs

    # Look for changes
    def look(self):
        stamp = stat(self._filename).st_mtime
        if stamp != self._cached_stamp:
            self._cached_stamp = stamp
            if self._call_func_on_change is not None:
                self._last_line = self._call_func_on_change(file=self._filename,
                                                            last_line=self._last_line, **self._kwargs)

    # Keep watching in a loop
    def run(self):
        while self._running:
            try:
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

    def join(self, timeout=0.5):
        self._running = False
        sleep(max(timeout, 0.5))


def create_watcher(watcher: Optional[Watcher], server_version: 'ServerVersion'):
    if watcher is not None and watcher.is_running():
        watcher.stop()

    if 7 <= server_version.minor:
        path_to_server_log = "logs/latest.log"
    else:
        path_to_server_log = "server.log"

    return Watcher(
        watch_file=Path(Config.get_selected_server_from_list().working_directory, path_to_server_log),
        call_func_on_change=_check_log_file,
        server_version=server_version,
        poll=BotVars.bot_for_webhooks.get_cog("Poll")
    )


def create_chat_webhook():
    if Config.get_cross_platform_chat_settings().webhook_url:
        BotVars.webhook_chat = SyncWebhook.from_url(url=Config.get_cross_platform_chat_settings().webhook_url)


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
        last_lines = last_lines[-min(50, Config.get_server_watcher().number_of_lines_to_check_in_console_log):]
    last_lines = [sub(r"§[\dabcdefklmnor]", "", line) for line in last_lines]
    death_message = ""

    for line in last_lines:
        if not search(rf"{date_line} {INFO_line}", line) or search(rf"{date_line} {INFO_line} \* ", line):
            continue

        if Config.get_cross_platform_chat_settings().channel_id is not None:
            match = search(rf"{date_line} {INFO_line}( \[Not Secure])? <(?P<nick>[^>]*)> (?P<message>.*)", line)
            if match is not None:
                player_nick = match.group("nick")
                player_message = match.group("message")
                if search(r"@\S+", player_message):
                    split_arr = split(r"@\S+", player_message)
                    mentions = [[i[1:]] for i in findall(r"@\S+", player_message)]
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
                                            mentions[i_mention][1] += [utils_get(
                                                BotVars.bot_for_webhooks.guilds[0].members,
                                                id=user.user_discord_id
                                            )]
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
                                possible_role = utils_get(
                                    BotVars.bot_for_webhooks.guilds[0].roles,
                                    id=Config.get_settings().bot_settings.managing_commands_role_id
                                )
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
                                                 mention[1].mention if len(mention) > 1 and mention[1] is not None
                                                 else f"@{mention[0]}")
                            else:
                                split_arr[insert_numb] = split_arr[insert_numb][1:].lstrip(mention[0][1])
                                if len(mention) == 3:
                                    split_arr[insert_numb] = f"{mention[2]}{split_arr[insert_numb]}"
                                split_arr.insert(insert_numb,
                                                 mention[1].mention if len(mention) > 1 and mention[1] is not None
                                                 else f"@{mention[0][0]}")
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

                if search(r":\w+:", player_message):
                    split_arr = split(r":\w+:", player_message)
                    emojis = findall(r":(\w+):", player_message)
                    i = 1
                    for emoji_name in emojis:
                        emoji = utils_get(BotVars.bot_for_webhooks.emojis, name=emoji_name)
                        if emoji is None:
                            emoji = utils_find(lambda e: e.name.lower() == emoji_name.lower(),
                                               BotVars.bot_for_webhooks.emojis)
                        if emoji is None:
                            emoji = f":{emoji_name}:"
                        else:
                            emoji = str(emoji)
                        split_arr.insert(i, emoji)
                        i += 2
                    player_message = "".join(split_arr)

                edited_message = False
                if search(r"^\*[^*].*", player_message):
                    chn = BotVars.bot_for_webhooks.get_channel(Config.get_cross_platform_chat_settings().channel_id)
                    if chn is None:
                        print(get_translation("Bot Error: Couldn't find channel for cross-platform chat!"))
                    else:
                        async def get_last_message(channel: TextChannel):
                            last_msg = None
                            async for message in channel.history(limit=100):
                                if message.author.discriminator == "0000" and message.author.name == player_nick:
                                    last_msg = message
                                    break
                            return last_msg

                        last_message = run_coroutine_threadsafe(get_last_message(chn),
                                                                BotVars.bot_for_webhooks.loop).result()
                        if last_message is not None:
                            last_message_timestamp = int((last_message.edited_at or
                                                          last_message.created_at).timestamp())
                            server_timestamp = Config.get_server_config().states.started_info.date_stamp
                            # Check if edited message not older 5 hours and
                            # server was started earlier then message editing
                            if int(datetime.now().timestamp()) < last_message_timestamp + 18000 and \
                                    (server_timestamp is None or server_timestamp < last_message_timestamp):
                                edited_message = True
                                BotVars.webhook_chat.edit_message(message_id=last_message.id,
                                                                  content=player_message[1:].strip())

                if not edited_message:
                    player_url_pic = None
                    for user in Config.get_settings().known_users:
                        if user.user_minecraft_nick.lower() == player_nick.lower():
                            possible_user = BotVars.bot_for_webhooks.guilds[0].get_member(user.user_discord_id)
                            if possible_user is not None and possible_user.avatar is not None:
                                player_url_pic = possible_user.avatar.url
                                break

                    BotVars.webhook_chat.send(player_message, username=player_nick, avatar_url=player_url_pic)
                continue

        if Config.get_secure_auth().enable_secure_auth or \
                Config.get_cross_platform_chat_settings().channel_id is not None:
            player_logout = check_if_player_logged_out(line, INFO_line)

            if player_logout[0] is not None and player_logout[1] is not None:
                BotVars.remove_player_login(player_logout[0])
                continue

            player_login = check_if_player_logged_in(line, INFO_line)

            if player_login[0] is not None and player_login[1] is not None and \
                    Config.get_secure_auth().enable_secure_auth:
                from components.additional_funcs import connect_rcon, add_quotes

                nick = player_login[0]
                ip_address = player_login[1]
                save_auth_users = False
                if nick not in [u.nick for u in Config.get_auth_users()]:
                    Config.add_auth_user(nick)
                    save_auth_users = True
                nick_numb = [i for i in range(len(Config.get_auth_users()))
                             if Config.get_auth_users()[i].nick == nick][0]
                nick_logged = BotVars.player_logged(Config.get_auth_users()[nick_numb].nick) is not None
                is_invasion_to_ban = nick_logged and ip_address not in Config.get_known_user_ips()
                is_invasion_to_kick = nick_logged and ip_address not in Config.get_known_user_ips(nick)

                if not is_invasion_to_ban and not is_invasion_to_kick:
                    if ip_address in [ip.ip_address for ip in Config.get_auth_users()[nick_numb].ip_addresses]:
                        user_attempts, code = Config.update_ip_address(nick, ip_address)
                    else:
                        user_attempts, code = Config.add_ip_address(nick, ip_address, is_login_attempt=True)
                    save_auth_users = True
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
                                if server_version.minor > 2:
                                    if server_version.minor < 7 or \
                                            (server_version.minor == 7 and server_version.patch < 6):
                                        ban_reason = ban_reason.replace("\n", " ")
                                    cl_r.run(f"ban-ip {ip_address} {ban_reason}")
                                else:
                                    cl_r.run(f"ban-ip {ip_address}")
                            if is_invasion_to_ban:
                                ban_reason = get_translation("Intrusion prevented: User was banned!")
                            else:
                                Config.remove_ip_address(ip_address, [nick])
                                save_auth_users = True
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
                        nick_for_command = nick if " " not in nick else f"\"{nick}\""
                        msg += get_translation("To proceed enter command `{0}` within {1} min") \
                                   .format(f"{Config.get_settings().bot_settings.prefix}auth login "
                                           f"{nick_for_command} <code>",
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
                                                  embed_message=get_translation("Login without code?\n(Less safe)"),
                                                  command=f"auth login {nick} {ip_address}",
                                                  need_for_voting=1,
                                                  timeout=Config.get_secure_auth().mins_before_code_expires * 60,
                                                  remove_logs_after=5,
                                                  add_mention=False,
                                                  add_votes_count=False):
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
                    BotVars.add_player_login(nick)
                if save_auth_users:
                    Config.save_auth_users()
                continue
            elif player_login[0] is not None and player_login[1] is not None and \
                    not Config.get_secure_auth().enable_secure_auth and \
                    Config.get_cross_platform_chat_settings().channel_id is not None:
                BotVars.add_player_login(player_login[0])
                continue

        if Config.get_cross_platform_chat_settings().channel_id is not None:
            from components.additional_funcs import DEATH_MESSAGES, REGEX_DEATH_MESSAGES, MASS_REGEX_DEATH_MESSAGES

            if search(f"{INFO_line} {MASS_REGEX_DEATH_MESSAGES}", line):
                for regex in range(len(REGEX_DEATH_MESSAGES)):
                    message_match = search(f"{INFO_line} {REGEX_DEATH_MESSAGES[regex]}", line)
                    if message_match:
                        groups = [g.strip() for g in message_match.groups()]
                        if len(groups) == 3 and DEATH_MESSAGES[regex].find("{1}") > DEATH_MESSAGES[regex].find("{2}"):
                            groups = [groups[0], groups[2], groups[1]]
                        if search(r"^\'.+\'$", DEATH_MESSAGES[regex].format(*groups)) or \
                                (len(groups) == 1 and search(r"^\'.+", DEATH_MESSAGES[regex].format(*groups))):
                            stripped_group = [groups[0][1:]]
                            if len(groups) > 1:
                                if DEATH_MESSAGES[regex].find("{1}") > DEATH_MESSAGES[regex].find("{2}"):
                                    stripped_group.append(groups[1][:-1])
                                    if len(groups) == 3:
                                        stripped_group.append(groups[2])
                                else:
                                    stripped_group.extend([groups[1], groups[2][:-1]])
                            groups = stripped_group
                        if len(groups) > 1:
                            groups[1] = get_translation(groups[1])
                        groups[0] = get_translation(groups[0])
                        groups = [f"**{escape_markdown(g)}**" for g in groups]
                        msg = get_translation(DEATH_MESSAGES[regex]).format(*groups)
                        if death_message != msg:
                            avatar_url = Config.get_cross_platform_chat_settings().avatar_url_for_death_messages
                            if avatar_url is None:
                                avatar_url = BotVars.bot_for_webhooks.user.avatar.url
                            BotVars.webhook_chat.send(msg,
                                                      username=get_translation("☠ Obituary ☠"),
                                                      avatar_url=avatar_url)
                            death_message = msg
                        break
                continue

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


def check_if_player_logged_out(line: str, INFO_line: str):
    match = search(rf"{INFO_line} (?P<nick>[^\[\]<>]+) lost connection:", line)
    if match:
        nick = match.group("nick").strip()
        reason = split(r"lost connection:", line, maxsplit=1)[-1].strip()
    else:
        nick = None
        reason = None
    return nick, reason


def check_if_player_logged_in(line: str, INFO_line: str):
    match = search(
        rf"{INFO_line} (?P<nick>[^\[\]<>]+)\[/(?P<ip>\d+\.\d+\.\d+\.\d+):\d+] logged in with entity id \d+ at",
        line
    )
    if match:
        nick = match.group("nick").strip()
        ip_address = match.group("ip").strip()
    else:
        nick = None
        ip_address = None
    return nick, ip_address


def _get_last_n_lines(file: Path, number_of_lines: int, last_line: Optional[str]):
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
