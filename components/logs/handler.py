import socket
from asyncio import run_coroutine_threadsafe
from asyncio import sleep as asleep
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from queue import Queue
from re import search, findall, split
from sys import exc_info
from threading import Thread
from time import sleep
from traceback import format_exc
from typing import Optional, TYPE_CHECKING, List

from colorama import Fore, Style
from discord import TextChannel, Role, SyncWebhookMessage
from discord.utils import get as utils_get, escape_markdown, find as utils_find

from components.error_handlers import handle_rcon_error
from components.localization import get_translation
from components.logs.data import MessageType
from components.logs.watcher import LogMessage
from components.minecraft.connect import ServerVersion, get_server_players, connect_rcon
from components.minecraft.utils import times, announce
from components.utils import get_members_nicks_of_the_role, get_commands_channel, add_quotes
from config.init_config import BotVars, Config

if TYPE_CHECKING:
    from cogs.poll_cog import Poll


class HandlerThread(Thread):
    def __init__(self, queue: Queue, server_version: ServerVersion, poll: 'Poll'):
        super().__init__()
        self.name = "HandleThread"
        self.daemon = True
        self._running = True
        self._queue: Queue[LogMessage] = queue
        self._server_version = server_version
        self._poll = poll
        self._last_death_message: Optional[DeathMessage] = None

    def run(self):
        while self._running:
            if not self._queue.empty():
                message = self._queue.get(False)

                try:
                    if message.type == MessageType.PlayerMessage:
                        handle_game_chat_message(message.player_nick, message.player_message, self._server_version)
                    elif message.type == MessageType.PlayerLogin:
                        try:
                            data = get_server_players()
                            valid = message.player_nick in data["players"]
                        except (ConnectionError, socket.error):
                            valid = message.player_nick in [p.player_minecraft_nick
                                                            for p in Config.get_server_config().seen_players]
                        if valid:
                            handle_login_message(
                                message.player_nick,
                                message.player_ip,
                                self._server_version,
                                self._poll
                            )
                    elif message.type == MessageType.PlayerLogout:
                        BotVars.remove_player_login(message.player_nick)
                    elif message.type == MessageType.DeathMessage:
                        self._last_death_message = handle_death_message(
                            message.message_groups,
                            message.death_message_regex,
                            self._last_death_message
                        )
                    elif message.type == MessageType.MessageBlockEnd:
                        self._last_death_message = force_update_death_message(self._last_death_message)
                except BaseException:
                    exc = format_exc().rstrip("\n")
                    print(get_translation("Log Handler Unhandled Error: {0}").format(exc_info()[0]) +
                          f"\n{Style.DIM}{Fore.RED}{exc}{Style.RESET_ALL}")

                # Also if message wasn't processed add again in queue for 3 tries...
                self._queue.task_done()

    def join(self, timeout=0.5):
        self._running = False
        sleep(max(timeout, 0.5))


@dataclass
class DeathMessage:
    discord_message: Optional[SyncWebhookMessage]
    death_message: str
    count: int
    last_used_date: Optional[datetime]
    last_count: int = 0


def handle_game_chat_message(player_nick: str, player_message: str, server_version: ServerVersion):
    if "> " in player_nick:
        splits = player_nick.split("> ")
        try:
            players = get_server_players()["players"]
            indexes = list(range(len(splits), 0, -1))
        except (ConnectionError, socket.error):
            players = []
            indexes = []

        for i in indexes:
            possible_nick = "> ".join(splits[:i])
            if possible_nick in players:
                player_nick = possible_nick
                message_part = "> ".join(splits[i:])
                if len(message_part) > 0:
                    message_part += "> "
                player_message = f"{message_part}{player_message}"
                break
        else:
            nick_part, message_part = player_nick.split("> ", maxsplit=1)
            player_nick = nick_part
            player_message = f"{message_part}> {player_message}"

    if search(r"@\S+", player_message):
        split_arr = split(r"@\S+", player_message)
        mentions = [[i[1:]] for i in findall(r"@\S+", player_message)]
        for i_mention in range(len(mentions)):
            for words_number in range(Config.get_game_chat_settings().max_words_in_mention + 1):
                if len(split_arr[1 + i_mention]) < words_number:
                    break
                found = False
                add_string = " ".join(split_arr[1 + i_mention].lstrip(" ").split(" ")[:words_number]) \
                    if words_number > 0 else ""
                for symbols_number in range(Config.get_game_chat_settings().
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
                        mention_nicks = get_members_nicks_of_the_role(possible_role, mention_nicks)
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
                    mention_nicks = get_members_nicks_of_the_role(mention[1], mention_nicks)
            insert_numb += 2
        player_message = "".join(split_arr)

        if len(mention_nicks) > 0 and server_version.minor > 7:
            mention_nicks = set(mention_nicks)
            nick_owner_id = None
            for u in Config.get_known_users_list():
                if u.user_minecraft_nick == player_nick:
                    nick_owner_id = u.user_discord_id
            for logged_in_nick in [u.user_minecraft_nick for u in Config.get_known_users_list()
                                   if u.user_discord_id == nick_owner_id]:
                with suppress(KeyError):
                    mention_nicks.remove(logged_in_nick)

            with suppress(ConnectionError, socket.error):
                with connect_rcon() as cl_r:
                    with times(0, 60, 20, cl_r):
                        for logged_in_nick in mention_nicks:
                            announce(
                                logged_in_nick,
                                f"@{player_nick} "
                                f"-> @{logged_in_nick if logged_in_nick != '@a' else 'everyone'}",
                                cl_r,
                                server_version
                            )

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
        chn = BotVars.bot_for_webhooks.get_channel(BotVars.webhook_chat.channel_id)
        if chn is None:
            print(get_translation("Bot Error: Couldn't find channel for game chat!"))
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


def handle_login_message(logged_in_nick: str, ip_address: str, server_version: ServerVersion, poll: 'Poll'):
    if Config.get_secure_auth().enable_secure_auth:
        save_auth_users = False
        if logged_in_nick not in [u.nick for u in Config.get_auth_users()]:
            Config.add_auth_user(logged_in_nick)
            save_auth_users = True
        nick_numb = [i for i in range(len(Config.get_auth_users()))
                     if Config.get_auth_users()[i].nick == logged_in_nick][0]
        nick_logged = BotVars.player_logged(Config.get_auth_users()[nick_numb].nick) is not None
        is_invasion_to_ban = nick_logged and ip_address not in Config.get_known_user_ips()
        is_invasion_to_kick = nick_logged and ip_address not in Config.get_known_user_ips(logged_in_nick)

        if not is_invasion_to_ban and not is_invasion_to_kick:
            if ip_address in [ip.ip_address for ip in Config.get_auth_users()[nick_numb].ip_addresses]:
                user_attempts, code = Config.update_ip_address(logged_in_nick, ip_address)
            else:
                user_attempts, code = Config.add_ip_address(logged_in_nick, ip_address, is_login_attempt=True)
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
                        Config.remove_ip_address(ip_address, [logged_in_nick])
                        save_auth_users = True
                        ban_reason = get_translation("Too many login attempts: User was banned!")
                    msg = f"{ban_reason}\n" + get_translation("Nick: {0}\nIP: {1}\nTime: {2}").format(
                        logged_in_nick,
                        ip_address,
                        datetime.now().strftime(get_translation("%H:%M:%S %d/%m/%Y"))
                    )
                    channel = get_commands_channel()
                    run_coroutine_threadsafe(channel.send(add_quotes(msg)), BotVars.bot_for_webhooks.loop)
            else:
                if is_invasion_to_kick:
                    kick_reason = get_translation("You don't own this logged in nick")
                else:
                    kick_reason = get_translation("Not authorized\nYour IP: {0}\nCode: {1}").format(ip_address,
                                                                                                    code)
                with suppress(ConnectionError, socket.error):
                    with connect_rcon() as cl_r:
                        response = cl_r.kick(
                            logged_in_nick if server_version.minor < 14 else f"'{logged_in_nick}'",
                            kick_reason
                        )
                        if not search(kick_reason, response):
                            secs = Config.get_secure_auth().mins_before_code_expires * 60
                            if server_version.minor > 2:
                                if server_version.minor < 7 or \
                                        (server_version.minor == 7 and server_version.patch < 6):
                                    kick_reason = kick_reason.replace("\n", " ")
                                else:
                                    kick_reason += "\n"
                                kick_reason += get_translation(
                                    "You will be unbanned in {0} sec or after authorization!"
                                ).format(secs)
                                cl_r.run(f"ban-ip {ip_address} {kick_reason}")
                            else:
                                cl_r.run(f"ban-ip {ip_address}")

                            async def run_delayed_command(ip_address, seconds):
                                await asleep(seconds)
                                with suppress(ConnectionError, socket.error):
                                    with connect_rcon() as cl_r:
                                        cl_r.run(f"pardon-ip {ip_address}")

                            run_coroutine_threadsafe(
                                run_delayed_command(ip_address, secs),
                                BotVars.bot_for_webhooks.loop
                            )
                if is_invasion_to_kick:
                    return
                member = None
                for user in Config.get_known_users_list():
                    if user.user_minecraft_nick == logged_in_nick:
                        member = BotVars.bot_for_webhooks.guilds[0].get_member(user.user_discord_id)

                user_nicks = Config.get_user_nicks(ip_address=ip_address, nick=logged_in_nick, authorized=True)
                status = get_translation("Status:") + f" {user_nicks[logged_in_nick][0][1]}\n"
                used_nicks = None
                if (len(user_nicks) != 1 and user_nicks.get(logged_in_nick, None) is not None) or \
                        len(user_nicks) > 1:
                    used_nicks = get_translation("Previously used nicknames:") + "\n"
                    for k, v in user_nicks.items():
                        if k != logged_in_nick:
                            used_nicks += f"- {k}: {v[0][1]}\n"
                if used_nicks is not None:
                    status += used_nicks

                msg = get_translation("Connection attempt detected!\nNick: {0}\n"
                                      "IP: {1}\n{2}Connection attempts: {3}\nTime: {4}") \
                    .format(logged_in_nick, ip_address, status,
                            f"{user_attempts}/{Config.get_secure_auth().max_login_attempts}",
                            datetime.now().strftime(get_translation("%H:%M:%S %d/%m/%Y")))
                msg = add_quotes(msg) + "\n"
                nick_for_command = logged_in_nick if " " not in logged_in_nick else f"\"{logged_in_nick}\""
                msg += get_translation("To proceed enter command `{0}` within {1} min") \
                           .format(f"{Config.get_settings().bot_settings.prefix}auth login "
                                   f"{nick_for_command} <code>",
                                   Config.get_secure_auth().mins_before_code_expires) + "\n"
                msg += get_translation("To ban this IP-address enter command `{0}`") \
                    .format(f"{Config.get_settings().bot_settings.prefix}auth ban {ip_address} [reason]")
                if member is not None:
                    for p in poll.get_polls().values():
                        if p.command == f"auth login {logged_in_nick} {ip_address}":
                            p.cancel()

                    async def send_message_and_poll(member, msg, poll, nick, ip_address, server_version):
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
                            banned_ips = Config.get_list_of_banned_ips_and_reasons(server_version)
                            if ip_address in [e["ip"] for e in banned_ips]:
                                async with handle_rcon_error(member):
                                    with connect_rcon() as cl_r:
                                        cl_r.run(f"pardon-ip {ip_address}")
                                    await member.send(add_quotes(
                                        get_translation("Unbanned IP-address {0}!").format(ip_address)
                                    ))

                    run_coroutine_threadsafe(
                        send_message_and_poll(member, msg, poll, logged_in_nick, ip_address, server_version),
                        BotVars.bot_for_webhooks.loop
                    )
                else:
                    channel = get_commands_channel()
                    run_coroutine_threadsafe(channel.send(msg), BotVars.bot_for_webhooks.loop)
        else:
            if logged_in_nick not in [i.player_minecraft_nick for i in Config.get_server_config().seen_players]:
                Config.add_to_seen_players_list(logged_in_nick)
                Config.save_server_config()
            BotVars.add_player_login(logged_in_nick)
        if save_auth_users:
            Config.save_auth_users()
    elif not Config.get_secure_auth().enable_secure_auth and BotVars.webhook_chat is not None:
        if logged_in_nick not in [i.player_minecraft_nick for i in Config.get_server_config().seen_players]:
            Config.add_to_seen_players_list(logged_in_nick)
            Config.save_server_config()
        BotVars.add_player_login(logged_in_nick)


def handle_death_message(
        message_groups: List[str],
        death_message_regex: str,
        last_death_message: Optional[DeathMessage]
):
    date = datetime.now()
    if len(message_groups) == 3 and death_message_regex.find("{1}") > death_message_regex.find("{2}"):
        message_groups = [message_groups[0], message_groups[2], message_groups[1]]
    if search(r"^\'.+\'$", death_message_regex.format(*message_groups)) or \
            (len(message_groups) == 1 and search(r"^\'.+", death_message_regex.format(*message_groups))):
        stripped_group = [message_groups[0][1:]]
        if len(message_groups) > 1:
            if death_message_regex.find("{1}") > death_message_regex.find("{2}"):
                stripped_group.append(message_groups[1][:-1])
                if len(message_groups) == 3:
                    stripped_group.append(message_groups[2])
            else:
                stripped_group.extend([message_groups[1], message_groups[2][:-1]])
        message_groups = stripped_group
    if len(message_groups) > 1:
        message_groups[1] = get_translation(message_groups[1])
    message_groups[0] = get_translation(message_groups[0])
    message_groups = [f"**{escape_markdown(g)}**" for g in message_groups]
    msg = get_translation(death_message_regex).format(*message_groups)

    if last_death_message is not None:
        if last_death_message.death_message == msg:
            if (date - last_death_message.last_used_date).seconds > 60:
                last_death_message = send_death_message(msg, 1, date)
            else:
                last_death_message.count += 1
                last_death_message.last_used_date = date
        else:
            if last_death_message.count > last_death_message.last_count:
                last_death_message.discord_message.edit(
                    content=f"{last_death_message.death_message} *(x{last_death_message.count})*"
                )
            last_death_message = send_death_message(msg, 1, date)
    else:
        last_death_message = send_death_message(msg, 1, date)

    return last_death_message


def send_death_message(death_message: str, count: int, date: datetime):
    avatar_url = Config.get_game_chat_settings().avatar_url_for_death_messages
    if avatar_url is None:
        avatar_url = BotVars.bot_for_webhooks.user.avatar.url

    return DeathMessage(
        death_message=death_message,
        discord_message=BotVars.webhook_chat.send(
            death_message + (f" *(x{count})*" if count > 1 else ""),
            username=get_translation("☠ Obituary ☠"),
            avatar_url=avatar_url,
            wait=True
        ),
        count=count,
        last_count=count,
        last_used_date=date
    )


def force_update_death_message(last_death_message: Optional[DeathMessage]):
    if last_death_message is not None and last_death_message.count > last_death_message.last_count:
        date = datetime.now()
        if (date - last_death_message.last_used_date).seconds > 60:
            last_death_message = send_death_message(
                last_death_message.death_message,
                last_death_message.last_count - last_death_message.count,
                date
            )
        else:
            last_death_message.discord_message.edit(
                content=f"{last_death_message.death_message} *(x{last_death_message.count})*"
            )
            last_death_message.last_count = last_death_message.count
            last_death_message.last_used_date = date
    return last_death_message
