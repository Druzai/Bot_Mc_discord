import inspect
import socket
import sys
import typing
from asyncio import sleep as asleep, Task, CancelledError
from contextlib import contextmanager, suppress, asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum, auto
from io import BytesIO
from itertools import chain
from json import dumps
from os import chdir, system, walk, mkdir, remove
from os.path import join as p_join, getsize, isfile
from pathlib import Path
from random import randint, choice
from re import search, split, findall, sub, compile
from shutil import rmtree
from sys import argv
from textwrap import wrap
from threading import Thread, Event
from time import sleep
from traceback import format_exception
from typing import Tuple, List, Dict, Optional, Union, TYPE_CHECKING, AsyncIterator, Callable, Awaitable, Any
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED, ZIP_BZIP2, ZIP_LZMA

from PIL import Image, UnidentifiedImageError
from aiohttp import ClientSession
from colorama import Style, Fore
from discord import (
    Activity, ActivityType, Message, Status, Member, Role, MessageType, NotFound, HTTPException, Forbidden, Emoji,
    ChannelType, TextChannel, VoiceChannel, Thread as ChannelThread, GroupChannel, Webhook, InvalidData, SelectOption,
    Interaction, Client, ButtonStyle
)
from discord.abc import Messageable
from discord.ext import commands
from discord.ui import View, Select, Item, Button, button
from discord.utils import get as utils_get, _get_mime_type_for_image, MISSING
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r, WrongPassword
from psutil import process_iter, NoSuchProcess, disk_usage, Process, AccessDenied
from requests import post as req_post, get as req_get, head as req_head, Timeout

from components.decorators import MissingAdminPermissions, is_admin, is_minecrafter
from components.localization import get_translation, get_locales, get_current_locale, set_locale
from components.rss_feed_handle import get_feed_webhook
from components.watcher_handle import create_watcher, get_chat_webhook
from config.init_config import Config, BotVars, ServerProperties, OS, URL_REGEX

if TYPE_CHECKING:
    from commands.poll import Poll
    from commands.minecraft_commands import MinecraftCommands
    from commands.chat_commands import ChatCommands

if Config.get_os() == OS.Windows:
    from os import startfile

UNITS = ("B", "KB", "MB", "GB", "TB", "PB")
DISCORD_SYMBOLS_IN_MESSAGE_LIMIT = 2000
MAX_RCON_COMMAND_STR_LENGTH = 1446
MAX_RCON_COMMAND_RUN_STR_LENGTH = 1370
MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH = MAX_RCON_COMMAND_STR_LENGTH - 9 - 2
DISCORD_SELECT_FIELD_MAX_LENGTH = 100
DISCORD_SELECT_OPTIONS_MAX_LENGTH = 25
DISCORD_MAX_SELECT_OPTIONS_IN_MESSAGE = DISCORD_SELECT_OPTIONS_MAX_LENGTH * 5
ANSI_ESCAPE = compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

# Messages taken from https://minecraft.fandom.com/wiki/Death_messages
DEATH_MESSAGES = [
    '{0} fell off a ladder', '{0} fell off some vines', '{0} fell off some weeping vines',
    '{0} fell off some twisting vines', '{0} fell off scaffolding', '{0} fell while climbing',
    '{0} fell from a high place', '{0} was doomed to fall', '{0} was doomed to fall by {1}',
    '{0} was doomed to fall by {1} using {2}', '{0} fell too far and was finished by {1}',
    '{0} fell too far and was finished by {1} using {2}', '{0} was struck by lightning',
    '{0} was struck by lightning whilst fighting {1}', '{0} went up in flames',
    '{0} walked into fire whilst fighting {1}', '{0} burned to death',
    '{0} was burnt to a crisp whilst fighting {1} wielding {2}', '{0} was burnt to a crisp whilst fighting {1}',
    '{0} tried to swim in lava', '{0} tried to swim in lava to escape {1}', '{0} discovered the floor was lava',
    '{0} walked into danger zone due to {1}', '{0} suffocated in a wall',
    '{0} suffocated in a wall whilst fighting {1}', '{0} was squished too much', '{0} was squashed by {1}',
    '{0} drowned', '{0} drowned whilst trying to escape {1}', '{0} died from dehydration',
    '{0} died from dehydration whilst trying to escape {1}', '{0} starved to death',
    '{0} starved to death whilst fighting {1}', '{0} was pricked to death',
    '{0} walked into a cactus whilst trying to escape {1}', '{0} died', '{0} died because of {1}', '{0} blew up',
    '{0} was blown up by {1}', '{0} was blown up by {1} using {2}', '{0} was killed by magic',
    '{0} was killed by magic whilst trying to escape {1}', '{0} was killed by even more magic', '{0} withered away',
    '{0} withered away whilst fighting {1}', '{0} was shot by a skull from {1}',
    '{0} was shot by a skull from {1} using {2}', '{0} was squashed by a falling anvil',
    '{0} was squashed by a falling anvil whilst fighting {1}', '{0} was squashed by a falling block',
    '{0} was squashed by a falling block whilst fighting {1}', '{0} was impaled on a stalagmite',
    '{0} was impaled on a stalagmite whilst fighting {1}', '{0} was skewered by a falling stalactite',
    '{0} was skewered by a falling stalactite whilst fighting {1}', '{0} was obliterated by a sonically-charged shriek',
    '{0} was obliterated by a sonically-charged shriek whilst trying to escape {1} wielding {2}',
    '{0} was obliterated by a sonically-charged shriek whilst trying to escape {1}', '{0} was slain by {1}',
    '{0} was slain by {1} using {2}', '{0} was shot by {1}', '{0} was shot by {1} using {2}',
    '{0} was fireballed by {1}', '{0} was fireballed by {1} using {2}', '{0} was pummeled by {1}',
    '{0} was pummeled by {1} using {2}', '{0} was killed by {1} using magic', '{0} was killed by {1} using {2}',
    '{0} was killed trying to hurt {1}', '{0} was killed by {2} trying to hurt {1}', '{0} was impaled by {1}',
    '{0} was impaled by {1} with {2}', '{0} hit the ground too hard',
    '{0} hit the ground too hard whilst trying to escape {1}', '{0} fell out of the world',
    "{0} didn't want to live in the same world as {1}", '{0} was roasted in dragon breath',
    '{0} was roasted in dragon breath by {1}', '{0} experienced kinetic energy',
    '{0} experienced kinetic energy whilst trying to escape {1}', '{0} went off with a bang',
    '{0} went off with a bang whilst fighting {1}', '{0} went off with a bang due to a firework fired from {2} by {1}',
    '{0} was killed by {1}', '{0} was poked to death by a sweet berry bush',
    '{0} was poked to death by a sweet berry bush whilst trying to escape {1}', '{0} was stung to death',
    '{0} was stung to death by {1} using {2}', '{0} was stung to death by {1}', '{0} froze to death',
    '{0} was frozen to death by {1}', '{0} fell out of the water', "{0} was shot by a {1}'s skull",
    '{0} was fell too far and was finished by {1}', '{0} was fell too far and was finished by {1} using {2}'
]
DEATH_MESSAGES = sorted(DEATH_MESSAGES, key=lambda s: len(s), reverse=True)
REGEX_DEATH_MESSAGES = [sub(r"\{\d}", r"(.+)", m) for m in DEATH_MESSAGES]
MASS_REGEX_DEATH_MESSAGES = "|".join(REGEX_DEATH_MESSAGES)


async def send_msg(ctx: Union[Messageable, Interaction], msg: str, is_reaction=False):
    if isinstance(ctx, Interaction):
        await send_interaction(ctx, msg, is_reaction=is_reaction)
    else:
        await ctx.send(
            content=msg,
            delete_after=(Config.get_timeouts_settings().await_seconds_before_message_deletion
                          if is_reaction else None)
        )


async def send_interaction(
        interaction: Optional[Interaction],
        msg: str,
        ctx: Messageable = None,
        ephemeral=False,
        is_reaction=False
):
    try:
        if interaction is None or interaction.is_expired():
            raise ValueError()

        if interaction.response.is_done():
            msg = await interaction.followup.send(msg, ephemeral=ephemeral, wait=True)
        else:
            await interaction.response.send_message(msg, ephemeral=ephemeral)
            msg = await interaction.original_response()

        if is_reaction:
            await msg.delete(delay=Config.get_timeouts_settings().await_seconds_before_message_deletion)
    except (NotFound, HTTPException, ValueError):
        if ctx is None and interaction is not None:
            ctx = interaction.channel()
        if ctx is not None:
            await ctx.send(
                content=msg,
                delete_after=(Config.get_timeouts_settings().await_seconds_before_message_deletion
                              if is_reaction else None)
            )


async def edit_interaction(interaction: Optional[Interaction], view: View, message_id: int):
    if interaction.is_expired():
        return

    if interaction.response.is_done():
        await interaction.followup.edit_message(message_id, view=view)
    else:
        await interaction.response.edit_message(view=view)


def add_quotes(msg: str) -> str:
    return f"```{msg}```"


async def delete_after_by_msg(message: Union[Message, int], ctx: commands.Context = None, without_delay=False):
    if isinstance(message, Message):
        await message.delete(
            delay=Config.get_timeouts_settings().await_seconds_before_message_deletion if not without_delay else None
        )
    elif isinstance(message, int):
        await (await ctx.channel.fetch_message(message)).delete(
            delay=Config.get_timeouts_settings().await_seconds_before_message_deletion if not without_delay else None
        )


def get_author_and_mention(
        ctx: Union[commands.Context, Message, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        is_reaction=False
):
    if is_reaction:
        author_mention = BotVars.react_auth.mention
        author = BotVars.react_auth
    else:
        if hasattr(ctx, "author"):
            author_mention = ctx.author.mention
            author = ctx.author
        elif hasattr(ctx, "user"):
            author_mention = ctx.user.mention
            author = ctx.user
        else:
            author_mention = bot.user.mention
            author = bot.user
    return author, author_mention


async def send_status(ctx: Union[commands.Context, Interaction], is_reaction=False):
    if BotVars.is_server_on:
        if BotVars.is_backing_up:
            await send_msg(ctx, add_quotes(get_translation("Bot is backing up server!")), is_reaction)
        else:
            await send_msg(ctx, add_quotes(get_translation("server have already started!").capitalize()), is_reaction)
    else:
        if BotVars.is_backing_up:
            await send_msg(ctx, add_quotes(get_translation("Bot is backing up server!")), is_reaction)
        elif BotVars.is_restoring:
            await send_msg(ctx, add_quotes(get_translation("Bot is restoring server from backup!")), is_reaction)
        elif BotVars.is_loading:
            await send_msg(ctx, add_quotes(get_translation("server is loading!").capitalize()), is_reaction)
        elif BotVars.is_stopping:
            await send_msg(ctx, add_quotes(get_translation("server is stopping!").capitalize()), is_reaction)
        else:
            await send_msg(ctx, add_quotes(get_translation("server have already been stopped!").capitalize()),
                           is_reaction)


def _ignore_some_tasks_errors(task: Task):
    with suppress(CancelledError, ConnectionResetError):
        task.result()


async def start_server(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        backups_thread=None,
        shut_up=False,
        is_reaction=False
):
    BotVars.is_loading = True
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
    print(get_translation("Loading server by request of {0}").format(author))
    if ctx and not shut_up:
        await send_msg(ctx, add_quotes(get_translation("Loading server.......\nPlease wait)")), is_reaction)
    chdir(Config.get_selected_server_from_list().working_directory)
    try:
        if not isfile(Config.get_selected_server_from_list().start_file_name):
            raise FileNotFoundError()
        if Config.get_os() in [OS.Linux, OS.MacOS]:
            exts = [".sh"]
            if Config.get_os() == OS.MacOS:
                exts.append(".command")
            if not any(ext in Config.get_selected_server_from_list().start_file_name for ext in exts):
                raise NameError()
            code = system(f"screen -dmS {Config.get_selected_server_from_list().server_name.replace(' ', '_')} "
                          f"./{Config.get_selected_server_from_list().start_file_name}")
            if code != 0:
                raise ReferenceError()
        elif Config.get_os() == OS.Windows:
            is_file_exists = False
            for ext in [".bat", ".cmd", ".lnk"]:
                if ext in Config.get_selected_server_from_list().start_file_name:
                    if ext == ".lnk":
                        start_file_target = Config.read_link_target(
                            Path(f"./{Config.get_selected_server_from_list().start_file_name}"))
                        if not Path(start_file_target).is_file():
                            raise FileNotFoundError(".lnk")
                        elif len(start_file_target.split(".")) == 1 or \
                                start_file_target.split(".")[-1] not in ["bat", "cmd"]:
                            raise ReferenceError(".lnk")
                    is_file_exists = True
                    break
            if not is_file_exists:
                raise NameError()
            startfile(Config.get_selected_server_from_list().start_file_name)
    except (NameError, ValueError, FileNotFoundError, ReferenceError) as ex:
        chdir(Config.get_bot_config_path())
        if ex.__class__ is FileNotFoundError:
            if len(ex.args) == 0:
                print(get_translation("Script '{0}' doesn't exist.")
                      .format(Config.get_selected_server_from_list().start_file_name))
                await send_msg(ctx, add_quotes(get_translation("Couldn't open script because it "
                                                               "doesn't exists! Retreating...")),
                               is_reaction)
            else:
                print(get_translation("Target script of this shortcut '{0}' doesn't exists.")
                      .format(Config.get_selected_server_from_list().start_file_name))
                await send_msg(ctx, add_quotes(get_translation("Couldn't open shortcut because target script "
                                                               "doesn't exists! Retreating...")),
                               is_reaction)
        elif ex.__class__ is not ReferenceError:
            print(get_translation("Couldn't open script! Check naming and extension of the script!"))
            await send_msg(ctx, add_quotes(get_translation("Couldn't open script because of naming! Retreating...")),
                           is_reaction)
        else:
            if len(ex.args) == 0:
                print(get_translation("Couldn't open script because there is no command 'screen'! "
                                      "Install it via packet manager!"))
                await send_msg(ctx, add_quotes(get_translation("Couldn't open script because command 'screen' "
                                                               "wasn't installed! Retreating...")), is_reaction)
            else:
                print(get_translation("Target of this shortcut '{0}' isn't '*.bat' file or '*.cmd' file.")
                      .format(Config.get_selected_server_from_list().start_file_name))
                await send_msg(ctx, add_quotes(get_translation("Couldn't open shortcut because target file "
                                                               "isn't a script! Retreating...")),
                               is_reaction)
        BotVars.is_loading = False
        if BotVars.is_restarting:
            BotVars.is_restarting = False
        return
    chdir(Config.get_bot_config_path())
    check_time = datetime.now()
    last_presence_change = datetime.now() - timedelta(seconds=4)
    while True:
        timedelta_secs = (datetime.now() - check_time).seconds
        if len(get_list_of_processes()) == 0 and timedelta_secs > 5:
            print(get_translation("Error while loading server! Retreating..."))
            await send_msg(ctx, add_quotes(get_translation("Error while loading server! Retreating...")),
                           is_reaction)
            task = bot.loop.create_task(
                bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                      name=Config.get_settings().bot_settings.idle_status)))
            task.add_done_callback(_ignore_some_tasks_errors)
            BotVars.is_loading = False
            if BotVars.is_restarting:
                BotVars.is_restarting = False
            return
        if (datetime.now() - last_presence_change).seconds >= 4:
            if Config.get_selected_server_from_list().server_loading_time:
                percentage = round((timedelta_secs / Config.get_selected_server_from_list().server_loading_time) * 100)
                output_bot = get_translation("Loading: ") + ((str(percentage) + "%") if percentage < 101 else "100%...")
            else:
                output_bot = get_translation("{0}, elapsed time: ") \
                                 .format(Config.get_settings().bot_settings.idle_status) \
                             + get_time_string(timedelta_secs, True)
            await bot.change_presence(activity=Activity(type=ActivityType.listening, name=output_bot))
            last_presence_change = datetime.now()
        await asleep(Config.get_timeouts_settings().await_seconds_when_connecting_via_rcon)
        with suppress(ConnectionError, socket.error):
            with connect_query() as cl_q:
                _ = cl_q.basic_stats
            break
    if Config.get_game_chat_settings().enable_game_chat or \
            Config.get_secure_auth().enable_secure_auth:
        BotVars.watcher_of_log_file = create_watcher(BotVars.watcher_of_log_file, get_server_version())
        BotVars.watcher_of_log_file.start()
    to_save = False
    if Config.get_selected_server_from_list().server_loading_time:
        average_server_loading_time = (Config.get_selected_server_from_list().server_loading_time +
                                       (datetime.now() - check_time).seconds) // 2
        if average_server_loading_time != Config.get_selected_server_from_list().server_loading_time:
            Config.get_selected_server_from_list().server_loading_time = average_server_loading_time
            to_save = True
    else:
        Config.get_selected_server_from_list().server_loading_time = (datetime.now() - check_time).seconds
        to_save = True
    if to_save:
        Config.save_config()
    print(get_translation("Server on!"))
    if ctx and not shut_up:
        await send_msg(ctx, author_mention + "\n" + add_quotes(get_translation("Server's on now")), is_reaction)
        if randint(0, 8) == 0:
            await send_msg(ctx, get_translation("Kept you waiting, huh?"), is_reaction)
    if backups_thread is not None:
        backups_thread.skip()
    BotVars.players_login_dict.clear()
    BotVars.auto_shutdown_start_date = None
    BotVars.is_loading = False
    BotVars.is_server_on = True
    if BotVars.is_restarting:
        BotVars.is_restarting = False
    Config.get_server_config().states.started_info.set_state_info(author.id, datetime.now(), bot=author == bot.user)
    Config.save_server_config()
    task = bot.loop.create_task(
        bot.change_presence(activity=Activity(type=ActivityType.playing,
                                              name=Config.get_settings().bot_settings.gaming_status)))
    task.add_done_callback(_ignore_some_tasks_errors)


async def stop_server(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        poll: 'Poll',
        how_many_sec=10,
        is_restart=False,
        shut_up=False,
        is_reaction=False
):
    no_connection = False
    players_info = None
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)

    if "stop" in [p.command for p in poll.get_polls().values()]:
        if not is_reaction:
            await delete_after_by_msg(ctx.message)
        if not shut_up:
            await ctx.send(get_translation("{0}, bot already has poll on `stop`/`restart` command!")
                           .format(author_mention),
                           delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
        return

    try:
        players_info = get_server_players()
    except (ConnectionError, socket.error):
        if len(get_list_of_processes()) == 0:
            print(get_translation("Bot Exception: Couldn't connect to server, because it's stopped"))
            if not shut_up:
                await send_msg(ctx, add_quotes(get_translation("Couldn't connect to server to shut it down! "
                                                               "Server stopped...")), is_reaction)
            BotVars.is_stopping = False
            BotVars.is_server_on = False
            return
        no_connection = True

    if not no_connection:
        if players_info["current"] > 0:
            logged_only_author_accounts = None
            author_id = ctx.author.id if not is_reaction else BotVars.react_auth.id
            if len(Config.get_known_users_list()) > 0:
                for player in players_info["players"]:
                    possible_player = [u.user_discord_id for u in Config.get_known_users_list()
                                       if u.user_minecraft_nick == player]
                    if len(possible_player) > 0 and author_id == possible_player[0]:
                        logged_only_author_accounts = True
                    else:
                        logged_only_author_accounts = False
                        break

            if not logged_only_author_accounts and await poll.timer(ctx, 5, "stop"):
                if not await poll.run(channel=ctx.channel if hasattr(ctx, 'channel') else ctx,
                                      message=get_translation("this man {0} trying to stop the server with {1} "
                                                              "player(s) on it. Will you let that happen?")
                                              .format(author_mention, players_info["current"]),
                                      command="stop",
                                      needed_role=Config.get_settings().bot_settings.managing_commands_role_id,
                                      remove_logs_after=5):
                    return
            elif not logged_only_author_accounts and not is_reaction:
                await delete_after_by_msg(ctx.message)
        elif players_info["current"] == 0 and is_reaction:
            how_many_sec = 0

        BotVars.is_stopping = True
        print(get_translation("Stopping server by request of {0}").format(author))
        if not shut_up:
            await send_msg(ctx, add_quotes(get_translation("Stopping server") + "......." +
                                           ("\n" + get_translation("Please wait {0} sec.").format(str(how_many_sec))
                                            if how_many_sec > 0 else "")), is_reaction)

        with suppress(ConnectionError, socket.error):
            server_version = get_server_version()
            with connect_rcon() as cl_r:
                if how_many_sec != 0:
                    w = 1
                    if how_many_sec > 5:
                        while True:
                            w += 1
                            if how_many_sec % w == 0 and w <= 10:
                                break
                            elif how_many_sec % w == 0 and w > 10:
                                how_many_sec += 1
                                w = 1
                    if not is_restart:
                        bot_message = get_translation("Server\'s shutting down in {0} seconds") \
                            .format(str(how_many_sec))
                    else:
                        bot_message = get_translation("Server\'s restarting in {0} seconds").format(str(how_many_sec))

                    if server_version.minor < 7:
                        cl_r.say(bot_message)
                    else:
                        tellraw_init = build_nickname_tellraw_for_bot(server_version, get_bot_display_name(bot))
                        cl_r.tellraw("@a", tellraw_init + [{"text": bot_message}])
                    for i in range(how_many_sec, 0, -w):
                        if server_version.minor < 7:
                            cl_r.say(get_translation("{0} sec to go").format(str(i)))
                        else:
                            cl_r.tellraw("@a",
                                         tellraw_init + [{"text": get_translation("{0} sec to go").format(str(i))}])
                        await asleep(w)
                cl_r.run("stop")

        if BotVars.watcher_of_log_file is not None and BotVars.watcher_of_log_file.is_running():
            BotVars.watcher_of_log_file.stop()
        stop_datetime = datetime.now()
        while True:
            await asleep(Config.get_timeouts_settings().await_seconds_when_connecting_via_rcon)
            try:
                with connect_query() as cl_q:
                    _ = cl_q.basic_stats
            except (ConnectionError, socket.error):
                break
            if (datetime.now() - stop_datetime).seconds > 60:
                break
    else:
        print(get_translation("Bot Exception: Couldn't connect to server, so killing it now..."))
        if not shut_up:
            await send_msg(ctx,
                           add_quotes(get_translation("Couldn't connect to server to shut it down! Killing it now...")),
                           is_reaction)
    kill_server()
    BotVars.players_login_dict.clear()
    BotVars.auto_shutdown_start_date = None
    BotVars.is_stopping = False
    BotVars.is_server_on = False
    print(get_translation("Server's off now"))
    if not shut_up:
        await send_msg(ctx, author_mention + "\n" + add_quotes(get_translation("Server's off now")), is_reaction)
    Config.get_server_config().states.stopped_info.set_state_info(author.id, datetime.now(), bot=author == bot.user)
    Config.save_server_config()
    task = bot.loop.create_task(
        bot.change_presence(activity=Activity(type=ActivityType.listening,
                                              name=Config.get_settings().bot_settings.idle_status)))
    task.add_done_callback(_ignore_some_tasks_errors)


def get_list_of_processes() -> List[Process]:
    renew_list = False
    if len(BotVars.java_processes) > 0:
        for p in BotVars.java_processes:
            if not p.is_running():
                renew_list = True
                break
    else:
        renew_list = True
    if not renew_list:
        return BotVars.java_processes

    list_proc = []
    for proc in process_iter():
        with proc.oneshot():
            with suppress(NoSuchProcess, AccessDenied):
                if "java" in proc.name() and Config.get_selected_server_from_list().working_directory == proc.cwd():
                    list_proc.append(proc)
    BotVars.java_processes = list_proc
    return list_proc


def kill_server():
    list_proc = get_list_of_processes()
    if len(list_proc) != 0:
        for p in list_proc:
            with suppress(NoSuchProcess, AccessDenied):
                p.kill()


def get_bot_display_name(bot: commands.Bot):
    for member in bot.guilds[0].members:
        if member.id == bot.user.id:
            return member.display_name
    return bot.user.display_name


async def get_member_string(bot: commands.Bot, id: int, mention: bool = False):
    try:
        member = bot.guilds[0].get_member(id)
        if member is None:
            member = await bot.guilds[0].fetch_member(id)
        if not mention:
            member = f"{member.display_name}#{member.discriminator}"
        else:
            member = member.mention
    except (HTTPException, Forbidden, NotFound):
        try:
            user = await bot.fetch_user(id)
            if not mention:
                member = f"{user.name}#{user.discriminator}"
            else:
                member = user.mention
        except (HTTPException, NotFound):
            member = f"{'@' if mention else ''}invalid-user"
    return member


async def get_channel_string(bot: commands.Bot, id: int, mention: bool = False):
    try:
        channel = bot.get_channel(id)
        if channel is None:
            channel = await bot.fetch_channel(id)
        if not mention:
            channel = channel.name
        else:
            channel = channel.mention
    except (InvalidData, HTTPException, NotFound, Forbidden):
        channel = f"{'#' if mention else ''}deleted-channel"
    return channel


async def get_role_string(bot: Union[commands.Bot, Client], id: int, mention: bool = False):
    try:
        role = bot.guilds[0].get_role(id)
        if role is None:
            role = utils_get(await bot.guilds[0].fetch_roles(), id=id)
            if role is None:
                raise ValueError()
        if not mention:
            role = role.name
        else:
            role = role.mention
    except (HTTPException, ValueError):
        role = f"{'@' if mention else ''}deleted-role"
    return role


async def get_message_and_channel(bot: Union[commands.Bot, Client], message_id: int, channel_id: Optional[int] = None):
    if channel_id is None:
        for ch in bot.guilds[0].channels:
            sub_chs = [ch]
            if hasattr(ch, "threads"):
                sub_chs.extend(ch.threads)
            for sub_ch in sub_chs:
                if isinstance(sub_ch, (TextChannel, VoiceChannel, Thread)):
                    with suppress(NotFound, Forbidden, HTTPException):
                        message = await sub_ch.fetch_message(message_id)
                        return message, sub_ch
        return None, None
    else:
        with suppress(NotFound, Forbidden, HTTPException, InvalidData):
            channel = await bot.fetch_channel(channel_id)
            message = await channel.fetch_message(message_id)
            return message, channel
        return None, None


class BackupsThread(Thread):
    def __init__(self, bot):
        super().__init__()
        self.name = "BackupsThread"
        self.daemon = True
        self._skip = Event()
        self._bot = bot
        self._terminate = False
        self._backing_up = False

    def run(self):
        while True:
            is_skipped = self._skip.wait(Config.get_backups_settings().period_of_automatic_backups * 60)
            if self._terminate:
                break
            if is_skipped:
                self._skip.clear()
                continue

            if not BotVars.is_backing_up and not BotVars.is_restoring and Config.get_backups_settings().automatic_backup:
                self._backing_up = True
                if BotVars.is_loading or BotVars.is_stopping or BotVars.is_restarting:
                    while True:
                        sleep(Config.get_timeouts_settings().await_seconds_when_connecting_via_rcon)
                        if (not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting) or \
                                self._terminate:
                            break

                players_count = 0
                if BotVars.is_server_on:
                    with suppress(ConnectionError, socket.error):
                        players_count = get_server_players().get("current")
                    if players_count != 0:
                        BotVars.is_auto_backup_disable = False
                elif len(Config.get_server_config().backups) > 0 and \
                        Config.get_server_config().states.started_info.date > \
                        max([b.file_creation_date for b in Config.get_server_config().backups]):
                    BotVars.is_auto_backup_disable = False

                if not BotVars.is_auto_backup_disable:
                    print(get_translation("Starting auto backup"))
                    handle_backups_limit_and_size(self._bot, auto_backups=True)
                    # Creating auto backup
                    file_name = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
                    level_name_path = Path(Config.get_selected_server_from_list().working_directory,
                                           ServerProperties().level_name).as_posix()
                    try:
                        obj = next(create_zip_archive(
                            self._bot,
                            file_name,
                            Path(Config.get_selected_server_from_list().working_directory,
                                 Config.get_backups_settings().name_of_the_backups_folder).as_posix(),
                            level_name_path,
                            Config.get_backups_settings().compression_method
                        ), None)
                        Config.add_backup_info(file_name=file_name)
                        Config.save_server_config()
                        print(get_translation("Backup completed!"))
                        if isinstance(obj, list) and len(obj) > 0:
                            print(get_translation("Bot couldn't archive some files "
                                                  "to this backup, they located in path '{0}'")
                                  .format(Path(Config.get_selected_server_from_list().working_directory,
                                               ServerProperties().level_name).as_posix()))
                            print(get_translation("List of these files:"))
                            print(", ".join(obj))
                    except FileNotFoundError:
                        print(get_translation("The world folder in path '{0}' doesn't exist or is empty!")
                              .format(level_name_path))
                        print(get_translation("Backup cancelled!"))

                if BotVars.is_server_on and players_count == 0:
                    BotVars.is_auto_backup_disable = True
                elif not BotVars.is_server_on:
                    BotVars.is_auto_backup_disable = True
                self._backing_up = False

    def skip(self):
        self._skip.set()

    def join(self, timeout=0.5):
        while self._backing_up:
            sleep(1.0)
        self._terminate = True
        self.skip()
        sleep(max(timeout, 0.5))


def create_zip_archive(
        bot: commands.Bot,
        zip_name: str,
        zip_path: str,
        dir_path: str,
        compression: str,
        forced=False,
        user: Member = None
):
    """recursively .zip a directory"""
    BotVars.is_backing_up = True
    if compression == "STORED":
        comp = ZIP_STORED
    elif compression == "DEFLATED":
        comp = ZIP_DEFLATED
    elif compression == "BZIP2":
        comp = ZIP_BZIP2
    elif compression == "LZMA":
        comp = ZIP_LZMA
    else:
        comp = ZIP_DEFLATED
    list_of_unarchived_files = []
    total = 0
    dt = datetime.now()
    last_message_change = datetime.now() - timedelta(seconds=4)

    # Check if world folder doesn't exist or is empty
    dir_obj = Path(dir_path)
    if not dir_obj.exists() or not dir_obj.is_dir() or next(dir_obj.rglob('*'), None) is None:
        BotVars.is_backing_up = False
        raise FileNotFoundError()

    # Count size of all files in directory
    for root, _, files in walk(dir_path):
        for fname in files:
            total += getsize(p_join(root, fname))

    current = 0
    use_rcon = False
    if BotVars.is_server_on:
        with suppress(ConnectionError, socket.error):
            server_version = get_server_version()
            use_rcon = True

    if use_rcon:
        if server_version.minor > 6:
            tellraw_init = build_nickname_tellraw_for_bot(server_version, get_bot_display_name(bot))
            tellraw_msg = tellraw_init.copy()
            if forced:
                tellraw_msg.append({"text": get_translation("Starting backup triggered by {0} in 3 seconds...")
                                   .format(f"{user.display_name}#{user.discriminator}"), "color": "yellow"})
            else:
                tellraw_msg.append({"text": get_translation("Starting automatic backup in 3 seconds..."),
                                    "color": "dark_aqua"})
        with suppress(ConnectionError, socket.error):
            with connect_rcon() as cl_r:
                if server_version.minor < 7:
                    if forced:
                        cl_r.say(get_translation("Starting backup triggered by {0} in 3 seconds...")
                                 .format(f"{user.display_name}#{user.discriminator}"))
                    else:
                        cl_r.say(get_translation("Starting automatic backup in 3 seconds..."))
                else:
                    cl_r.tellraw("@a", tellraw_msg)
        sleep(3.0)
        with suppress(ConnectionError, socket.error):
            with connect_rcon(timeout=60) as cl_r:
                if server_version.minor < 7:
                    cl_r.say(get_translation("Saving chunks..."))
                else:
                    cl_r.tellraw("@a", tellraw_init +
                                 [{"text": get_translation("Saving chunks..."), "color": "light_purple"}])
                if server_version.minor > 2 or (server_version.minor == 2 and server_version.patch >= 4):
                    cl_r.run("save-off")
                _ = cl_r.run("save-all flush")
        with suppress(ConnectionError, socket.error):
            with connect_rcon() as cl_r:
                if server_version.minor < 2 or (server_version.minor == 2 and server_version.patch < 4):
                    cl_r.run("save-off")
                if server_version.minor < 7:
                    cl_r.say(get_translation("Chunks saved!"))
                    cl_r.say(get_translation("Creating zip-archive for backup!"))
                else:
                    cl_r.tellraw("@a", tellraw_init + [{"text": get_translation("Chunks saved!"),
                                                        "color": "dark_green"}])
                    cl_r.tellraw("@a", tellraw_init + [{"text": get_translation("Creating zip-archive for backup!"),
                                                        "color": "light_purple"}])
    # Create zip file with output of percents
    with ZipFile(Path(f"{zip_path}/{zip_name}.zip"), mode="w", compression=comp) as z:
        for root, _, files in walk(dir_path):
            for file in files:
                if file == "session.lock":
                    continue

                fn = Path(root, file)
                afn = fn.relative_to(dir_path)
                if forced:
                    if (datetime.now() - last_message_change).seconds >= 4:
                        timedelta_secs = (datetime.now() - dt).seconds
                        percent = round(100 * current / total)
                        yield add_quotes(f"diff\n{percent}% {get_time_string(timedelta_secs, False)} '{afn}'\n"
                                         f"- |{'█' * (percent // 5)}{' ' * (20 - percent // 5)}|")
                        last_message_change = datetime.now()
                tries = 0
                while tries < 3:
                    with suppress(PermissionError):
                        with open(fn, mode="rb") as f:
                            f.read(1)
                        z.write(fn, arcname=afn)
                        break
                    tries += 1
                    sleep(1)
                if tries >= 3:
                    list_of_unarchived_files.append(f"'{afn.as_posix()}'")
                current += getsize(fn)

    if forced:
        date_t = get_time_string((datetime.now() - dt).seconds, True)
        backup_size = get_file_size(f"{zip_path}/{zip_name}.zip")
        backup_size_str = get_human_readable_size(backup_size, round=True)
        world_folder_size = get_folder_size(Config.get_selected_server_from_list().working_directory,
                                            ServerProperties().level_name)
        world_folder_size_str = get_human_readable_size(world_folder_size, stop_unit=backup_size_str.split(" ")[-1],
                                                        round=True)
        yield add_quotes(get_translation("Done in {0}\nCompression method: {1}").format(date_t, compression) +
                         f"\n{world_folder_size_str} -> {backup_size_str} " +
                         (f"(x{world_folder_size // backup_size})"
                          if round(world_folder_size / backup_size, 1).is_integer()
                          else f"(x{world_folder_size / backup_size:.1f})"))
    if use_rcon:
        with suppress(ConnectionError, socket.error):
            with connect_rcon() as cl_r:
                cl_r.run("save-on")
                if server_version.minor < 7:
                    cl_r.say(get_translation("Backup completed!"))
                else:
                    cl_r.tellraw("@a", tellraw_init + [{"text": get_translation("Backup completed!"),
                                                        "color": "dark_green"}])
                if len(list_of_unarchived_files) > 0:
                    if server_version.minor < 7:
                        cl_r.say(get_translation("Bot couldn't archive some files into this backup!"))
                    else:
                        cl_r.tellraw("@a", tellraw_init +
                                     [{"text": get_translation("Bot couldn't archive some files to this backup!"),
                                       "color": "dark_red"}])
    BotVars.is_backing_up = False
    if len(list_of_unarchived_files) > 0:
        yield list_of_unarchived_files


def restore_from_zip_archive(zip_name: str, zip_path: str, dir_path: str):
    BotVars.is_restoring = True
    rmtree(dir_path, ignore_errors=True)
    mkdir(dir_path)

    with ZipFile(Path(f"{zip_path}/{zip_name}.zip"), mode="r") as z:
        z.extractall(dir_path)
    BotVars.is_restoring = False


def calculate_space_for_current_server():
    """Get sizes
    Return
    ----------
    free_space: int
        free space of drive
    used_space: int
        used space by backups
    """
    disk_bytes_free = disk_usage(Config.get_selected_server_from_list().working_directory).free
    bc_folder_bytes = get_folder_size(Config.get_selected_server_from_list().working_directory,
                                      Config.get_backups_settings().name_of_the_backups_folder)
    limit = Config.get_backups_settings().size_limit
    if limit is not None and limit - bc_folder_bytes < disk_bytes_free:
        return limit - bc_folder_bytes, bc_folder_bytes
    else:
        return disk_bytes_free, bc_folder_bytes


def delete_oldest_auto_backup_if_exists(reason: str, bot: commands.Bot):
    backup = None
    for bc in Config.get_server_config().backups:
        if bc.initiator is None:
            backup = bc
            break
    if backup is None:
        backup = Config.get_server_config().backups[0]
    remove(Path(Config.get_selected_server_from_list().working_directory,
                Config.get_backups_settings().name_of_the_backups_folder, f"{backup.file_name}.zip"))
    send_message_of_deleted_backup(bot, reason, backup)
    Config.get_server_config().backups.remove(backup)


def send_message_of_deleted_backup(bot: commands.Bot, reason: str, backup=None, member_name: str = None):
    if backup is not None:
        if backup.initiator is None:
            msg = get_translation("Deleted auto backup '{0}.zip' because of {1}").format(backup.file_name, reason)
        else:
            if member_name is not None:
                member = member_name
            else:
                member = get_member_string(bot, backup.initiator)
            msg = get_translation("Deleted backup '{0}.zip' made by {1} because of {2}").format(backup.file_name,
                                                                                                member, reason)
    else:
        msg = get_translation("Deleted all backups because of {0}").format(reason)
    with suppress(ConnectionError, socket.error):
        server_version = get_server_version()
        with connect_rcon() as cl_r:
            if server_version.minor < 7:
                cl_r.say(msg)
            else:
                cl_r.tellraw("@a",
                             build_nickname_tellraw_for_bot(server_version, get_bot_display_name(bot)) +
                             [{"text": msg, "color": "red"}])
    print(msg)


def handle_backups_limit_and_size(bot: commands.Bot, auto_backups=False):
    # If limit is exceeded
    is_rewritten = False
    while True:
        if Config.get_backups_settings().max_backups_limit_for_server is not None and \
                Config.get_backups_settings().max_backups_limit_for_server <= \
                len(Config.get_server_config().backups):
            if not auto_backups:
                return get_translation("backups' count limit")
            delete_oldest_auto_backup_if_exists(get_translation("backups' count limit"), bot)
            is_rewritten = True
            continue
        break
    if is_rewritten:
        Config.save_server_config()

    is_rewritten = False
    average_backup_size = get_average_backup_size()
    # If not enough free space
    while True:
        free, used = calculate_space_for_current_server()
        if Config.get_backups_settings().size_limit is not None and average_backup_size < free and \
                Config.get_backups_settings().size_limit > used + average_backup_size:
            break
        if not auto_backups:
            return get_translation("lack of space")
        delete_oldest_auto_backup_if_exists(get_translation("lack of space"), bot)
        is_rewritten = True
    if is_rewritten:
        Config.save_server_config()


def get_average_backup_size():
    average_backup_size = 0
    for backup in Config.get_server_config().backups[:-3:-1]:
        backup_size = get_file_size(Config.get_selected_server_from_list().working_directory,
                                    Config.get_backups_settings().name_of_the_backups_folder,
                                    f"{backup.file_name}.zip")
        average_backup_size += backup_size
    if len(Config.get_server_config().backups) != 0:
        average_backup_size //= len(Config.get_server_config().backups[:-3:-1])
    return average_backup_size


def get_folder_size(*path: str) -> int:
    return sum(p.stat().st_size for p in Path(*path).rglob('*'))


def get_file_size(*path: str) -> int:
    return Path(*path).stat().st_size


def get_archive_uncompressed_size(*path: str):
    total_uncompressed = 0
    with ZipFile(Path(*path)) as z:
        for info in z.infolist():
            total_uncompressed += info.file_size
    return total_uncompressed


def get_human_readable_size(size: Union[int, float], stop_unit=None, round=False):
    human_radix = 1024.
    for u in UNITS[:-1]:
        if size < human_radix or stop_unit == get_translation(u):
            if round:
                return f"{int(size)} {get_translation(u)}"
            else:
                return f"{size:.2f} {get_translation(u)}"
        size /= human_radix

    if round:
        return f"{int(size)} {get_translation(UNITS[-1])}"
    else:
        return f"{size:.2f} {get_translation(UNITS[-1])}"


async def warn_about_auto_backups(ctx: Union[commands.Context, Interaction], bot: commands.Bot, is_reaction=False):
    if Config.get_backups_settings().automatic_backup:
        if len(Config.get_server_config().backups) > 0 \
                and handle_backups_limit_and_size(bot) is not None \
                and all([b.initiator for b in Config.get_server_config().backups]):
            await send_msg(
                ctx,
                get_translation("Bot has backups only from members for '{0}' server, "
                                "so keep in mind, that bot will delete oldest backup "
                                "on next auto backup!").format(Config.get_selected_server_from_list().server_name),
                is_reaction=is_reaction
            )


def get_half_members_count_with_role(channel: TextChannel, role: int):
    count = 0
    for m in channel.members:
        if not m.bot and m.status != Status.offline:
            if role:
                if role in (e.id for e in m.roles):
                    count += 1
            else:
                count += 1
    if count < 2:
        return count
    return count // 2


def get_time_string(seconds: int, use_colon=False):
    sec_str = get_translation(" sec")
    if seconds == 0:
        return f"{seconds}{sec_str}"
    elif use_colon:
        if seconds // 60 != 0:
            return f"{seconds // 60}:{(seconds % 60):02d}"
        else:
            return f"{seconds}{sec_str}"
    else:
        min_str = get_translation(" min")
        return ("" if seconds // 60 == 0 else f"{str(seconds // 60)}{min_str}") + \
               (" " if seconds > 59 and seconds % 60 != 0 else "") + \
               ("" if seconds % 60 == 0 else f"{str(seconds % 60)}{sec_str}")


async def server_checkups(bot: commands.Bot, backups_thread: BackupsThread, poll: 'Poll'):
    try:
        info = get_server_players()
        if info.get("current") != 0:
            to_save = False
            BotVars.players_login_dict = {k: v for k, v in BotVars.players_login_dict.items()
                                          if k in info.get("players")}
            for player in info.get("players"):
                if player not in [i.player_minecraft_nick for i in Config.get_server_config().seen_players]:
                    Config.add_to_seen_players_list(player)
                    to_save = True
                BotVars.add_player_login(player)
            if to_save:
                Config.save_server_config()
            if BotVars.is_auto_backup_disable:
                BotVars.is_auto_backup_disable = False
        if not BotVars.is_server_on:
            BotVars.is_server_on = True
        if Config.get_game_chat_settings().enable_game_chat or \
                Config.get_secure_auth().enable_secure_auth:
            if BotVars.watcher_of_log_file is None:
                BotVars.watcher_of_log_file = create_watcher(BotVars.watcher_of_log_file, get_server_version())
            BotVars.watcher_of_log_file.start()
        if not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting:
            task = bot.loop.create_task(bot.change_presence(
                activity=Activity(type=ActivityType.playing,
                                  name=Config.get_settings().bot_settings.gaming_status +
                                       ", " + str(info.get("current")) + get_translation(" player(s) online"))
            ))
            task.add_done_callback(_ignore_some_tasks_errors)
            if Config.get_settings().bot_settings.auto_shutdown:
                if info.get("current") == 0 and BotVars.auto_shutdown_start_date is None:
                    BotVars.auto_shutdown_start_date = \
                        datetime.now() + timedelta(seconds=Config.get_timeouts_settings().calc_before_shutdown)
                elif info.get("current") != 0 and BotVars.auto_shutdown_start_date is not None:
                    BotVars.auto_shutdown_start_date = None
                elif info.get("current") == 0 and BotVars.auto_shutdown_start_date <= datetime.now():
                    channel = bot.guilds[0].get_channel(Config.get_settings().bot_settings.commands_channel_id)
                    if channel is None:
                        channel = utils_get(bot.guilds[0].channels, type=ChannelType.text)
                    print(get_translation("Bot detected: Server is idle for {0} "
                                          "without players! Stopping server now!")
                          .format(get_time_string(Config.get_timeouts_settings().calc_before_shutdown)))
                    await send_msg(ctx=channel,
                                   msg=add_quotes(get_translation(
                                       "Bot detected: Server is idle for "
                                       "{0} without players!\n"
                                       "Time: {1}\n"
                                       "Shutting down server now!"
                                   ).format(get_time_string(Config.get_timeouts_settings().calc_before_shutdown),
                                            datetime.now().strftime(get_translation("%H:%M:%S %d/%m/%Y")))),
                                   is_reaction=True)
                    await stop_server(ctx=channel, bot=bot, poll=poll, shut_up=True)
    except (ConnectionError, socket.error):
        java_processes = get_list_of_processes()
        if len(java_processes) == 0:
            if BotVars.is_server_on:
                BotVars.is_server_on = False
                print(get_translation("Server unexpectedly stopped!"))
                Config.get_server_config().states.stopped_info.set_state_info(None, datetime.now())
                Config.save_server_config()
            if BotVars.watcher_of_log_file is not None and BotVars.watcher_of_log_file.is_running():
                BotVars.watcher_of_log_file.stop()
        if not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting:
            task = bot.loop.create_task(
                bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                      name=Config.get_settings().bot_settings.idle_status +
                                                           (" 🤔" if len(java_processes) != 0 else ""))))
            task.add_done_callback(_ignore_some_tasks_errors)
        if Config.get_settings().bot_settings.forceload and not BotVars.is_stopping \
                and not BotVars.is_loading and not BotVars.is_restarting:
            channel = bot.guilds[0].get_channel(Config.get_settings().bot_settings.commands_channel_id)
            if channel is None:
                channel = utils_get(bot.guilds[0].channels, type=ChannelType.text)
            print(get_translation("Bot detected: Server's offline! Starting up server again!"))
            await send_msg(ctx=channel,
                           msg=add_quotes(get_translation(
                               "Bot detected: Server's offline!\n"
                               "Time: {0}\n"
                               "Starting up server again!"
                           ).format(datetime.now().strftime(get_translation("%H:%M:%S %d/%m/%Y")))),
                           is_reaction=True)
            await start_server(ctx=channel, bot=bot, backups_thread=backups_thread, shut_up=True)
    if Config.get_secure_auth().enable_secure_auth:
        check_if_ips_expired()


async def bot_status(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        is_reaction=False
):
    states = ""
    bot_message = ""
    states_info = Config.get_server_config().states
    if states_info.started_info.date is not None and states_info.started_info.user is not None:
        if not states_info.started_info.bot:
            states += get_translation("Server has been started at {0} by member {1}") \
                          .format(states_info.started_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y")),
                                  await get_member_string(bot, states_info.started_info.user)) + "\n"
        else:
            states += get_translation("Server has started at {0}") \
                          .format(states_info.started_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))) + "\n"
    if states_info.stopped_info.date is not None and states_info.stopped_info.user is not None:
        if not states_info.stopped_info.bot:
            states += get_translation("Server has been stopped at {0} by member {1}") \
                          .format(states_info.stopped_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y")),
                                  await get_member_string(bot, states_info.stopped_info.user)) + "\n"
        else:
            states += get_translation("Server has stopped at {0}") \
                          .format(states_info.stopped_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))) + "\n"
    elif states_info.stopped_info.date is not None and states_info.stopped_info.user is None:
        states += get_translation("Server has crashed at {0}") \
                      .format(states_info.stopped_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))) + "\n"
    states = states.strip("\n")
    bot_message += get_translation("Server address: ") + Config.get_settings().bot_settings.ip_address + "\n"
    if BotVars.is_backing_up:
        bot_message += get_translation("Server is backing up") + "\n"
    if BotVars.is_restoring:
        bot_message += get_translation("Server is restoring from backup") + "\n"
    server_info = get_translation("Selected server: {0}") \
                      .format(Config.get_selected_server_from_list().server_name) + "\n"
    if Config.get_selected_server_from_list().server_loading_time is not None:
        server_info += get_translation("Average server loading time: {0}") \
                           .format(get_time_string(Config.get_selected_server_from_list().server_loading_time)) + "\n"
    if BotVars.is_server_on and not BotVars.is_stopping:
        try:
            server_version = get_server_version()
            bot_message = get_translation("server online").capitalize() + "\n" + bot_message
            if server_version.minor > 7:
                # Rcon check daytime cycle
                with connect_rcon() as cl_r:
                    time_ticks = int(cl_r.run("time query daytime").split(" ")[-1])
                message = get_translation("Time in Minecraft: ")
                if 450 <= time_ticks <= 11616:
                    message += get_translation("Day")
                elif 11617 <= time_ticks <= 13800:
                    message += get_translation("Sunset")
                elif 13801 <= time_ticks <= 22550:
                    message += get_translation("Night")
                else:
                    message += get_translation("Sunrise")
                message += f", {(6 + time_ticks // 1000) % 24}:{((time_ticks % 1000) * 60 // 1000):02d}\n"
                bot_message += message
            server_info_splits = server_info.split("\n", maxsplit=1)
            server_version_str = get_translation("Server version: {0}").format(server_version.version_string)
            server_info = f"{server_info_splits[0]}\n{server_version_str}\n{server_info_splits[-1]}"
            bot_message += server_info + states
            await send_msg(ctx, add_quotes(bot_message), is_reaction)
        except (ConnectionError, socket.error):
            bot_message += get_translation("Server thinking...") + "\n" + server_info + states
            await send_msg(ctx, add_quotes(bot_message), is_reaction)
            print(get_translation("Server's down via rcon"))
    else:
        if BotVars.is_loading:
            bot_message = get_translation("server is loading!").capitalize()[:-1] + "\n" + bot_message
        elif BotVars.is_stopping:
            bot_message = get_translation("server is stopping!").capitalize()[:-1] + "\n" + bot_message
        else:
            bot_message = get_translation("server offline").capitalize() + "\n" + bot_message
        bot_message += server_info + states
        await send_msg(ctx, add_quotes(bot_message), is_reaction)


async def bot_list(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        is_reaction=False
):
    try:
        info = get_server_players()
        if info.get("current") == 0:
            await send_msg(ctx, add_quotes(get_translation("There are no players on the server")), is_reaction)
        else:
            players_dict = {p: None for p in info.get("players")}
            if Config.get_secure_auth().enable_secure_auth:
                for player in Config.get_auth_users():
                    if player.nick in players_dict.keys() and BotVars.player_logged(player.nick) is not None:
                        non_expired_ips = [ip.expires_on_date for ip in player.ip_addresses
                                           if ip.expires_on_date is not None and datetime.now() < ip.expires_on_date]
                        if len(non_expired_ips) > 0:
                            players_dict[player.nick] = max(non_expired_ips) - \
                                                        timedelta(days=Config.get_secure_auth().days_before_ip_expires)
            else:
                for logged_player, date in BotVars.players_login_dict.items():
                    if logged_player in players_dict.keys():
                        players_dict[logged_player] = date
            players_list = []
            w_from = get_translation("from")
            time_f = get_translation("%H:%M %d/%m/%y")
            for k, v in players_dict.items():
                if v is not None:
                    if v.day == datetime.now().day:
                        players_list.append(f"{k} ({w_from} {v.strftime('%H:%M')})")
                    else:
                        players_list.append(f"{k} ({w_from} {v.strftime(time_f)})")
                else:
                    players_list.append(k)
            await send_msg(ctx, add_quotes(get_translation("Players online: {0} / {1}").format(info.get("current"),
                                                                                               info.get("max")) +
                                           "\n- " + "\n- ".join(players_list)),
                           is_reaction)
    except (ConnectionError, socket.error):
        author_mention = get_author_and_mention(ctx, bot, is_reaction)[1]
        await send_msg(ctx, f"{author_mention}, " + get_translation("server offline"), is_reaction)


async def bot_start(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        backups_thread,
        is_reaction=False
):
    if not BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and \
            not BotVars.is_backing_up and not BotVars.is_restoring:
        await start_server(ctx, bot=bot, backups_thread=backups_thread, is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_stop(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        command,
        bot: Union[commands.Bot, Client],
        poll: 'Poll',
        is_reaction=False
):
    if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and \
            not BotVars.is_backing_up and not BotVars.is_restoring:
        if BotVars.is_doing_op:
            await send_msg(ctx, add_quotes(get_translation("Some player(s) still have an operator, waiting for them")),
                           is_reaction)
            return
        if Config.get_settings().bot_settings.forceload:
            Config.get_settings().bot_settings.forceload = False
            Config.save_config()
        await stop_server(ctx, bot, poll, command, is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_restart(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        command,
        bot: Union[commands.Bot, Client],
        poll: 'Poll',
        backups_thread: BackupsThread,
        is_reaction=False
):
    if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and \
            not BotVars.is_backing_up and not BotVars.is_restoring:
        if BotVars.is_doing_op:
            await send_msg(ctx, add_quotes(get_translation("Some player(s) still have an operator, waiting for them")),
                           is_reaction)
            return
        BotVars.is_restarting = True
        print(get_translation("Restarting server"))
        await stop_server(ctx, bot, poll, command, True, is_reaction=is_reaction)
        await start_server(ctx, bot, backups_thread, is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_clear(
        ctx: commands.Context,
        poll: 'Poll',
        subcommand: str = None,
        count: int = None,
        discord_mentions=None
):
    message_created = None
    mentions = set()
    if discord_mentions is not None:
        for mention in discord_mentions:
            if isinstance(mention, Member):
                mentions.add(mention)
            elif isinstance(mention, Role):
                mentions.update(mention.members)
    if len(mentions):
        check_condition = lambda m: m.author in mentions and m.id not in poll.get_polls().keys()
    elif len(mentions) == 0 and not len(ctx.message.channel_mentions):
        check_condition = lambda m: m.id not in poll.get_polls().keys()
    else:
        await ctx.send(get_translation("You should mention ONLY members or roles of this server!"))
        return
    delete_limit = Config.get_settings().bot_settings.deletion_messages_limit_without_poll + 1

    if subcommand is None:
        if count > 0:
            lim = count if count < delete_limit else delete_limit + 1
            if delete_limit == 0 or len([m async for m in ctx.channel.history(limit=lim)]) <= delete_limit:
                await ctx.message.delete()
                await clear_with_big_limit(ctx, count=count, check_condition=check_condition)
                return
        elif count < 0:
            message_created = await get_last_element_of_async_iterator(
                ctx.channel.history(limit=-count, oldest_first=True)
            )
            if delete_limit == 0 or len([m async for m in ctx.channel.history(limit=delete_limit + 1,
                                                                              after=message_created,
                                                                              oldest_first=True)]) <= delete_limit:
                await ctx.message.delete()
                await clear_with_none_limit(ctx, check_condition=check_condition, after_message=message_created)
                return
        else:
            await send_msg(ctx, get_translation("Nothing's done!"), True)
            return
    elif subcommand == "all":
        if delete_limit == 0 or len([m async for m in ctx.channel.history(limit=delete_limit + 1)]) <= delete_limit:
            await ctx.message.delete()
            await clear_with_none_limit(ctx, check_condition=check_condition)
            return
    elif subcommand == "reply":
        message_created = ctx.message.reference.resolved
        if delete_limit == 0 or len([m async for m in ctx.channel.history(limit=delete_limit + 1,
                                                                          after=message_created,
                                                                          oldest_first=True)]) <= delete_limit:
            await ctx.message.delete()
            await clear_with_none_limit(ctx, check_condition=check_condition, after_message=message_created)
            return
    if await poll.timer(ctx, 5, "clear"):
        if ctx.channel in [p.channel for p in poll.get_polls().values() if p.command == "clear"]:
            await delete_after_by_msg(ctx.message)
            await ctx.send(get_translation("{0}, bot already has poll on `clear` command for this channel!")
                           .format(ctx.author.mention),
                           delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
            return
        if await poll.run(channel=ctx.channel,
                          message=get_translation(
                              "this man {0} trying to delete some history of this channel. Will you let that happen?"
                          ).format(ctx.author.mention),
                          command="clear",
                          remove_logs_after=5):
            if subcommand == "all" or subcommand == "reply" or count < 0:
                await ctx.message.delete()
                await clear_with_none_limit(ctx, check_condition=check_condition, after_message=message_created)
            else:
                await ctx.message.delete()
                await clear_with_big_limit(ctx, count=count, check_condition=check_condition)
    else:
        await delete_after_by_msg(ctx.message)


async def get_last_element_of_async_iterator(async_iterator: AsyncIterator):
    last_element = None
    while True:
        try:
            last_element = await async_iterator.__anext__()
        except StopAsyncIteration:
            return last_element


async def clear_with_big_limit(ctx: commands.Context, count: int, check_condition):
    last_undeleted_message = None
    ranges_to_delete = [100 for _ in range(count // 100)] + [count % 100]
    ranges_to_delete_length = len(ranges_to_delete)
    for i in range(ranges_to_delete_length):
        if ranges_to_delete_length > i + 1:
            last_undeleted_message = await get_last_element_of_async_iterator(
                ctx.channel.history(limit=ranges_to_delete[i], before=last_undeleted_message)
            )
        await ctx.channel.purge(limit=ranges_to_delete[i], check=check_condition, before=last_undeleted_message)


async def clear_with_none_limit(ctx: commands.Context, check_condition, after_message: Message = None):
    last_undeleted_message = None
    while True:
        limited_messages = [m async for m in ctx.channel.history(before=last_undeleted_message)]
        await ctx.channel.purge(check=check_condition, before=last_undeleted_message, after=after_message)
        if (after_message is not None and after_message in limited_messages) or len(limited_messages) == 0:
            return
        last_undeleted_message = limited_messages[-1]


async def bot_dm_clear(ctx: commands.Context, bot: commands.Bot, subcommand: str = None, count: int = None):
    message_created = None
    if count is not None:
        count += 1
    if subcommand is None:
        if count < 0:
            message_created = await get_last_element_of_async_iterator(
                ctx.channel.history(limit=-count, oldest_first=True)
            )
        elif count == 0:
            await send_msg(ctx, get_translation("Nothing's done!"), True)
            return
    elif subcommand == "reply":
        message_created = ctx.message.reference.resolved

    async for msg in ctx.channel.history(limit=count, after=message_created):
        if msg.author == bot.user and msg.type == MessageType.default:
            await msg.delete()


async def bot_backup(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        is_reaction=False
):
    bot_message = (get_translation("Automatic backups enabled") if Config.get_backups_settings()
                   .automatic_backup else get_translation("Automatic backups disabled")) + "\n"
    bot_message += get_translation("Automatic backups period set to {0} min").format(Config.get_backups_settings()
                                                                                     .period_of_automatic_backups)
    if Config.get_backups_settings().max_backups_limit_for_server is not None:
        bot_message += "\n" + get_translation("Max backups' count limit for server - {0}") \
            .format(Config.get_backups_settings().max_backups_limit_for_server)
    if Config.get_backups_settings().size_limit is not None:
        bot_message += "\n" + get_translation("Max backups' size limit for server - {0}") \
            .format(get_human_readable_size(Config.get_backups_settings().size_limit))
    bot_message += "\n" + get_translation("Current compression method - {0}").format(Config.get_backups_settings()
                                                                                     .compression_method) + "\n\n"

    bc_free_bytes, bc_used_bytes = calculate_space_for_current_server()
    bot_message += get_translation("Backups folder info for '{0}' server:") \
                       .format(Config.get_selected_server_from_list().server_name) + "\n" + \
                   get_translation("Used - {0}").format(get_human_readable_size(bc_used_bytes)) + "\n" + \
                   get_translation("Free - {0}").format(get_human_readable_size(bc_free_bytes))
    average_backup_size = get_average_backup_size()
    max_backups = None
    if average_backup_size != 0:
        max_backups = bc_free_bytes // average_backup_size
    if Config.get_backups_settings().max_backups_limit_for_server is not None:
        if max_backups is None or (max_backups + len(Config.get_server_config().backups)) > Config \
                .get_backups_settings().max_backups_limit_for_server:
            max_backups = Config.get_backups_settings().max_backups_limit_for_server - \
                          len(Config.get_server_config().backups)
    bot_message += "\n" + get_translation("Stored backups count - {0}").format(len(Config.get_server_config().backups))
    bot_message += "\n" + get_translation("Approximate remaining backups count - {0}") \
        .format(max_backups if max_backups is not None else "∞")

    if len(Config.get_server_config().backups) > 0:
        backup = Config.get_server_config().backups[-1]
        bot_message += "\n\n" + get_translation("Last backup: ") + \
                       backup.file_creation_date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))
        bot_message += "\n" + get_translation("Backup size: ") + \
                       get_human_readable_size(get_file_size(Config.get_selected_server_from_list().working_directory,
                                                             Config.get_backups_settings().name_of_the_backups_folder,
                                                             f"{backup.file_name}.zip"))
        if backup.reason is None and backup.initiator is None:
            bot_message += "\n" + get_translation("Reason: ") + get_translation("Automatic backup")
        else:
            bot_message += "\n" + get_translation("Reason: ") + \
                           (backup.reason if backup.reason else get_translation("Not stated"))
            bot_message += "\n" + get_translation("Initiator: ") + await get_member_string(bot, backup.initiator)
        if backup.restored_from:
            bot_message += "\n" + get_translation("The world of the server was restored from this backup")
    await send_msg(ctx, add_quotes(bot_message), is_reaction)


async def on_backups_select_option(i: int, bot: commands.Bot):
    backup = Config.get_server_config().backups[i]

    if backup.reason is None and backup.initiator is None:
        description_str = shorten_string(get_translation("Reason: ") + get_translation("Automatic backup"),
                                         DISCORD_SELECT_FIELD_MAX_LENGTH)
    else:
        if backup.reason:
            description_str = shorten_string(await get_member_string(bot, backup.initiator) + f" ({backup.reason}",
                                             DISCORD_SELECT_FIELD_MAX_LENGTH - 1) + ")"
        else:
            description_str = shorten_string(await get_member_string(bot, backup.initiator),
                                             DISCORD_SELECT_FIELD_MAX_LENGTH)

    return SelectOption(
        label=shorten_string(
            get_translation("Backup from") + " " +
            backup.file_creation_date.strftime(
                get_translation("%H:%M:%S %d/%m/%Y")
            ),
            DISCORD_SELECT_FIELD_MAX_LENGTH
        ),
        value=str(i),
        description=description_str
    )


def check_if_string_in_all_translations(translate_text: str, match_text: str):
    current_locale = get_current_locale()
    list_of_locales = get_locales()
    list_of_locales.remove(current_locale)
    list_of_locales.append(current_locale)
    if match_text == get_translation(translate_text):
        return True

    for locale in list_of_locales:
        set_locale(locale)
        if locale != current_locale and match_text == get_translation(translate_text):
            return True
    return False


async def bot_associate(
        ctx: commands.Context,
        bot: commands.Bot,
        discord_mention: Member,
        assoc_command: str,
        minecraft_nick: str
):
    need_to_save = False

    if "☠ " in minecraft_nick and \
            check_if_string_in_all_translations(translate_text="☠ Obituary ☠", match_text=minecraft_nick):
        await ctx.send(get_translation("{0}, you don't have permission to control fates! "
                                       "Not in this life at least...").format(discord_mention.mention))
        return

    if assoc_command == "add":
        if minecraft_nick in [u.user_minecraft_nick for u in Config.get_known_users_list()]:
            associated_member = [u.user_discord_id for u in Config.get_known_users_list()
                                 if u.user_minecraft_nick == minecraft_nick][0]
            associated_member = await bot.guilds[0].fetch_member(associated_member)
            await ctx.send(get_translation("This nick is already associated with member {0}.")
                           .format(associated_member.mention))
        else:
            need_to_save = True
            Config.add_to_known_users_list(minecraft_nick, discord_mention.id)
            await ctx.send(get_translation("Now {0} associates with nick `{1}` in Minecraft.")
                           .format(discord_mention.mention, minecraft_nick))
    elif assoc_command == "remove":
        if minecraft_nick in [u.user_minecraft_nick for u in Config.get_known_users_list()] and \
                discord_mention.id in [u.user_discord_id for u in Config.get_known_users_list()]:
            need_to_save = True
            Config.remove_from_known_users_list(minecraft_nick, discord_mention.id)
            await ctx.send(get_translation("Now link {0} -> `{1}` do not exist!")
                           .format(discord_mention.mention, minecraft_nick))
        else:
            await ctx.send(get_translation("Bot don't have `mention to nick` link already!"))
    if need_to_save:
        Config.save_config()


async def bot_associate_info(ctx: commands.Context, for_me: bool, show: str = None):
    if show is not None:
        message = get_translation("{0}, bot has this data on nicks and number of remaining uses:") \
                      .format(ctx.author.mention) + "\n```"
    else:
        message = get_translation("{0}, bot has this data on nicks:").format(ctx.author.mention) + "\n```"

    if for_me:
        if ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()]:
            return get_translation("{0}, you have no bound nicks").format(ctx.author.mention)

        user_nicks = [u.user_minecraft_nick for u in Config.get_known_users_list()
                      if u.user_discord_id == ctx.author.id]
        user_players_data = {}

        if show is not None:
            for m_nick in user_nicks:
                for p in Config.get_seen_players_list():
                    if p.player_minecraft_nick == m_nick:
                        user_players_data.update({p.player_minecraft_nick: p.number_of_times_to_op})
                        user_nicks.remove(m_nick)
        if show is None or show == "all":
            user_players_data.update({n: -1 for n in user_nicks})

        for k, v in user_players_data.items():
            if show is not None:
                message += f"- {k}: {str(v) if v >= 0 else get_translation('not seen on server')}\n"
            else:
                message += f"- {k}\n"
    else:
        users_to_nicks = {}
        for user in Config.get_known_users_list():
            if users_to_nicks.get(user.user_discord_id, None) is None:
                users_to_nicks.update({user.user_discord_id: []})
            users_to_nicks[user.user_discord_id].append(user.user_minecraft_nick)

        if show is not None:
            for user_id in users_to_nicks.keys():
                for p in Config.get_seen_players_list():
                    if p.player_minecraft_nick in users_to_nicks[user_id]:
                        users_to_nicks[user_id].remove(p.player_minecraft_nick)
                        users_to_nicks[user_id].append({p.player_minecraft_nick: p.number_of_times_to_op})

        for k, v in users_to_nicks.items():
            if not len(v) or (show is not None and show == "seen" and all([isinstance(i, str) for i in v])):
                continue
            member = await ctx.guild.fetch_member(k)
            message += f"{member.display_name}#{member.discriminator}:\n"
            for item in v:
                if show is None:
                    message += f"- {item}\n"
                elif show == "all" and isinstance(item, str):
                    message += f"- {item}: " + get_translation("not seen on server") + "\n"
                elif isinstance(item, dict):
                    message += f"- {list(item.items())[0][0]}: {str(list(item.items())[0][1])}\n"

    if message[-3:] == "```":
        message += "-----"
    message += "```"
    return message


def bot_shutdown_info(with_timeout=False, only_timeout=False):
    msg = get_translation("Task: ") + "\"" + get_translation("Shutdown of Minecraft server when idle") + "\""
    if not only_timeout:
        msg += "\n" + get_translation("State: ")
        if Config.get_settings().bot_settings.auto_shutdown:
            msg += get_translation("Active")
        else:
            msg += get_translation("Disabled")
    if with_timeout:
        msg += "\n" + get_translation("Timeout: {0} sec") \
            .format(Config.get_timeouts_settings().await_seconds_before_shutdown)
        if Config.get_timeouts_settings().calc_before_shutdown > 59 or \
                Config.get_timeouts_settings().await_seconds_before_shutdown % \
                Config.get_timeouts_settings().await_seconds_in_check_ups != 0:
            msg += " (" + (f"~ " if Config.get_timeouts_settings().await_seconds_before_shutdown %
                                    Config.get_timeouts_settings().await_seconds_in_check_ups != 0 else "") + \
                   f"{get_time_string(Config.get_timeouts_settings().calc_before_shutdown)})"
        if Config.get_timeouts_settings().calc_before_shutdown == 0:
            msg += "\n" + get_translation("Server will be stopped immediately.").strip(".")
    return msg


def bot_forceload_info():
    msg = get_translation("Task: ") + "\"" + get_translation("Autoload if server crashes") + \
          "\"\n" + get_translation("State: ")
    if Config.get_settings().bot_settings.forceload:
        msg += get_translation("Active")
    else:
        msg += get_translation("Disabled")
    return msg


def get_param_type(arg_data):
    if arg_data.annotation != inspect._empty:
        if hasattr(arg_data.annotation, '__origin__') and arg_data.annotation.__origin__._name == "Union":
            param_type = " | ".join([a.__name__ for a in arg_data.annotation.__args__ if a != type(None)])
        elif hasattr(arg_data.annotation, '__origin__') and arg_data.annotation.__origin__._name == "Literal":
            param_type = " | ".join([str(a) for a in arg_data.annotation.__args__])
        elif getattr(arg_data.annotation, '__name__', None) is not None:
            param_type = getattr(arg_data.annotation, '__name__', None)
        elif hasattr(arg_data.annotation, 'converter'):
            param_type = sub(r"\w*?\.", "", str(arg_data.annotation.converter))
            if not isinstance(arg_data.annotation.converter, typing._GenericAlias):
                param_type = param_type.strip("<>").lstrip("class").strip("' ")
        else:
            param_type = sub(r"\w*?\.", "", str(arg_data.annotation))
    elif arg_data.annotation == inspect._empty and arg_data.default != inspect._empty:
        param_type = type(arg_data.default).__name__
    else:
        param_type = "Any"
    return param_type


def parse_params_for_help(command_params: dict, string_to_add: str, create_params_dict=False) -> Tuple[str, dict]:
    params = {}
    converter = False
    for arg_name, arg_data in command_params.items():
        if arg_data.annotation != inspect._empty and hasattr(arg_data.annotation, 'converter') \
                and isinstance(arg_data.annotation.converter, typing._GenericAlias):
            converter = True
        if create_params_dict:
            params[arg_name] = get_param_type(arg_data)
        is_optional = hasattr(arg_data.annotation, '__origin__') \
                      and arg_data.annotation.__origin__._name == "Union" \
                      and type(None) in arg_data.annotation.__args__
        if arg_data.default != inspect._empty or arg_data.kind == arg_data.VAR_POSITIONAL or is_optional:
            add_data = ""
            if arg_data.default != inspect._empty and bool(arg_data.default) \
                    and arg_data.kind != arg_data.VAR_POSITIONAL:
                add_data = f"'{arg_data.default}'" if isinstance(arg_data.default, str) else str(arg_data.default)
            string_to_add += f" [{arg_name}" + (f" = {add_data}" if add_data else "") + \
                             ("..." if arg_data.kind == arg_data.VAR_POSITIONAL or converter else "") + "]"
        else:
            string_to_add += f" <{arg_name}>"
    return string_to_add, params


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


async def get_avatar_info(ctx: commands.Context, url: Optional[str]):
    avatar_blob = None
    avatar_url = None
    if url is not None:
        avatar_url = url
        async with ClientSession(timeout=30) as session:
            async with session.get(url=url) as response:
                avatar_blob = await response.read()
                try:
                    _get_mime_type_for_image(avatar_blob)
                except ValueError:
                    avatar_blob = None
    if avatar_blob is None:
        for attachment in ctx.message.attachments:
            avatar_file = await attachment.to_file()
            avatar_url = attachment.url
            avatar_blob = avatar_file.fp.read()
            try:
                _get_mime_type_for_image(avatar_blob)
                break
            except ValueError:
                avatar_blob = None
    return avatar_blob, avatar_url


def check_if_ips_expired():
    removed = False
    remove_empty_nicks = []
    remove_old_ips = {}
    for user in Config.get_auth_users():
        if len(user.ip_addresses) == 0:
            remove_empty_nicks.append(user)
            continue
        for ip in user.ip_addresses:
            if ip.expires_on_date is not None and (datetime.now() - ip.expires_on_date).days >= \
                    Config.get_secure_auth().days_before_ip_will_be_deleted:
                if remove_old_ips.get(user.nick, None) is None:
                    remove_old_ips[user.nick] = []
                remove_old_ips[user.nick].append(ip)
    if len(remove_empty_nicks) > 0:
        for user in remove_empty_nicks:
            Config.get_auth_users().remove(user)
        removed = True
    if len(remove_old_ips.keys()) > 0:
        for i in range(len(Config.get_auth_users())):
            if remove_old_ips.get(Config.get_auth_users()[i].nick, None) is None:
                continue
            for address in remove_old_ips[Config.get_auth_users()[i].nick]:
                Config.get_auth_users()[i].ip_addresses.remove(address)
        removed = True
    if removed:
        Config.save_auth_users()


def parse_subcommands_for_help(
        command: Union[commands.Command, commands.Group],
        all_params=False
) -> Tuple[List[str], List[str]]:
    if not hasattr(command, "commands") or len(command.commands) == 0:
        return [], []
    command_commands = sorted(command.commands, key=lambda c: c.name)

    if not all_params:
        return [c.name for c in command_commands], []

    subcommands = []
    for subcommand in command_commands:
        sub_sub_commands_line = parse_subcommands_for_help(subcommand)[0]
        sub_commands_aliases_line = ("/" if len(subcommand.aliases) > 0 else "") + "/".join(subcommand.aliases)
        if sub_sub_commands_line:
            sub_sub_commands_line = " " + " | ".join(sub_sub_commands_line) if len(sub_sub_commands_line) else ""
            sub_command, *sub_command_params = parse_params_for_help(subcommand.clean_params,
                                                                     subcommand.name)[0].split()
            subcommands.append(sub_command + sub_commands_aliases_line + sub_sub_commands_line +
                               (" | " if len(sub_command_params) > 0 else "") + " ".join(sub_command_params))
        else:
            subcommands.append(parse_params_for_help(subcommand.clean_params,
                                                     subcommand.name + sub_commands_aliases_line)[0])
    return [c.name for c in command_commands], subcommands


async def send_help_of_command(ctx: commands.Context, command: Union[commands.Command, commands.Group]):
    subcommands_names, subcommands = parse_subcommands_for_help(command, True)
    str_help = f"{Config.get_settings().bot_settings.prefix}{command}"
    str_help += " " + " | ".join(subcommands_names) if len(subcommands_names) else ""
    str_params, params = parse_params_for_help(command.clean_params, "", True)
    if len(str_params):
        str_help += " |" + str_params if len(subcommands_names) else str_params

    str_help += "\n\n" + get_translation("Description") + ":\n"
    str_help += get_translation(f'help_{str(command).replace(" ", "_")}').format(
        prefix=Config.get_settings().bot_settings.prefix
    ) + "\n\n"
    if len(command.aliases):
        str_help += get_translation("Aliases") + ": " + ", ".join(command.aliases) + "\n\n"

    if len(subcommands):
        str_help += get_translation("Subcommands") + ":\n" + "\n".join(subcommands) + "\n\n"

    if len(params.keys()):
        str_help += get_translation("Parameters") + ":\n"
        for arg_name, arg_type in params.items():
            str_help += f"{arg_name}: {arg_type}\n" + \
                        get_translation(f'help_{str(command).replace(" ", "_")}_{arg_name}').format(
                            prefix=Config.get_settings().bot_settings.prefix,
                            code_length=Config.get_secure_auth().code_length
                        ) + "\n\n"
    await ctx.send(add_quotes(f"\n{str_help}"))


def find_subcommand(
        subcommands: List[str],
        command: Union[commands.Command, commands.Group],
        pos: int
) -> Optional[Union[commands.Command, commands.Group]]:
    if hasattr(command, "all_commands") and len(command.all_commands) != 0:
        pos += 1
        for subcomm_name, subcomm in command.all_commands.items():
            if subcomm_name == subcommands[pos]:
                if len(subcommands) == pos + 1:
                    return subcomm
                else:
                    return find_subcommand(subcommands, subcomm, pos)


def make_underscored_line(line: Union[int, float, str]):
    """This func underscores int, float or strings without spaces!"""
    underscore = "\u0332"
    if isinstance(line, int) or isinstance(line, float):
        return underscore + underscore.join(str(line))
    elif isinstance(line, str):
        return underscore.join(line) + underscore


class TemplateSelectView(View):
    def __init__(
            self,
            options_raw: List,
            namespace: str = "template_select_view",
            name: str = "TemplateSelectView",
            ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, None] = None,
            raw_content: Optional[str] = None,
            message_id: Optional[int] = None,
            channel_id: Optional[int] = None,
            message: Optional[Message] = None,
            min_values: int = 1,
            max_values: int = 1,
            start_row: int = 0,
            is_reaction: bool = False,
            timeout: Optional[float] = None
    ):
        super().__init__(timeout=timeout)
        self.namespace = namespace
        self.name = name
        self.ctx = ctx
        self.message_id = message_id
        self.channel_id = channel_id
        self.message = message
        self.raw_content = raw_content
        self.select_page: int = -1
        self.options_list_raw = options_raw
        self.options_list_length = len(options_raw)
        if start_row > 3:
            raise RuntimeError("'start_row' more than 3!")
        self.is_reaction = is_reaction
        self.controls_removed = False

        # Creating Select and buttons

        self.v_select = Select(
            custom_id=f"{namespace}:select",
            min_values=min_values,
            max_values=max_values,
            row=start_row
        )
        self.v_select.callback = self.v_select_callback
        self.add_item(self.v_select)

        self.v_start = Button(
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_start",
            emoji="⏮",
            row=start_row + 1
        )
        self.v_start.callback = self.v_start_callback
        self.add_item(self.v_start)

        self.v_left = Button(
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_left",
            emoji="◀",
            row=start_row + 1
        )
        self.v_left.callback = self.v_left_callback
        self.add_item(self.v_left)

        self.v_page = Button(
            label="N / N",
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_page",
            disabled=True,
            row=start_row + 1
        )
        self.add_item(self.v_page)

        self.v_right = Button(
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_right",
            emoji="▶",
            row=start_row + 1
        )
        self.v_right.callback = self.v_right_callback
        self.add_item(self.v_right)

        self.v_end = Button(
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_end",
            emoji="⏭",
            row=start_row + 1
        )
        self.v_end.callback = self.v_end_callback
        self.add_item(self.v_end)

    async def update_view(
            self,
            send: bool = True,
            update_content: bool = False,
            check_if_content_is_different: bool = False
    ):
        await self.update_view_components()
        await self.update_select_options()
        if self.options_list_length > DISCORD_SELECT_OPTIONS_MAX_LENGTH:
            last_page = self.get_last_page()
            if self.select_page == 0:
                self.v_left.disabled = True
                self.v_start.disabled = True
                self.v_right.disabled = False
                self.v_end.disabled = False
            elif self.select_page == last_page:
                self.v_left.disabled = False
                self.v_start.disabled = False
                self.v_right.disabled = True
                self.v_end.disabled = True
            else:
                self.v_left.disabled = False
                self.v_start.disabled = False
                self.v_right.disabled = False
                self.v_end.disabled = False
            self.v_page.label = f"{self.select_page + 1} / {last_page + 1}"
            if last_page == 1:
                self.v_start.disabled = True
                self.v_end.disabled = True
        else:
            if not self.controls_removed:
                for c in [self.v_left, self.v_start, self.v_page, self.v_right, self.v_end]:
                    self.remove_item(c)
                self.controls_removed = True
        if not send:
            return

        if self.message is None and self.message_id is not None:
            self.message, channel = await get_message_and_channel(
                BotVars.bot_for_webhooks,
                self.message_id,
                self.channel_id
            )
            if channel is not None:
                self.channel_id = channel.id
        if self.message is not None:
            if check_if_content_is_different and self.message.clean_content == get_translation(self.raw_content):
                update_content = False
            self.message = await self.message.edit(
                view=self,
                content=(get_translation(self.raw_content)
                         if self.raw_content is not None and update_content else MISSING)
            )
        await self.do_after_sending_message()

    async def update_select_options(self, page: Optional[int] = None):
        if page is None:
            self.v_select.options = [SelectOption(label="Not implemented!")]
        else:
            self.v_select.options = [SelectOption(label="Not implemented!")]

    async def update_view_components(self):
        pass

    async def do_after_sending_message(self):
        pass

    def get_indexes(self, current_pos: int):
        start_index = current_pos // DISCORD_SELECT_OPTIONS_MAX_LENGTH
        if start_index > 0 and start_index > self.get_last_page():
            start_index -= 1
        self.select_page = start_index
        stop_index = start_index * DISCORD_SELECT_OPTIONS_MAX_LENGTH + 25
        if stop_index > self.options_list_length:
            stop_index = self.options_list_length
        start_index *= DISCORD_SELECT_OPTIONS_MAX_LENGTH

        return start_index, stop_index

    def set_by_page(self, page: int):
        last_page = self.get_last_page()
        if page <= 0:
            self.select_page = 0
        elif page >= last_page:
            self.select_page = last_page
        else:
            self.select_page = page
        stop_index = self.select_page * DISCORD_SELECT_OPTIONS_MAX_LENGTH + 25
        if stop_index > self.options_list_length:
            stop_index = self.options_list_length
        start_index = self.select_page * DISCORD_SELECT_OPTIONS_MAX_LENGTH

        return start_index, stop_index

    def get_last_page(self):
        if self.options_list_length % DISCORD_SELECT_OPTIONS_MAX_LENGTH == 0:
            return (self.options_list_length // DISCORD_SELECT_OPTIONS_MAX_LENGTH) - 1
        return self.options_list_length // DISCORD_SELECT_OPTIONS_MAX_LENGTH

    async def interaction_check_select(self, interaction: Interaction, /) -> bool:
        return True

    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any], /) -> None:
        await send_error_on_interaction(self.name, interaction, self.ctx, error, self.is_reaction)

    async def v_select_callback(self, interaction: Interaction):
        pass

    async def v_start_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await self.update_select_options(0)
            self.v_start.disabled = True
            self.v_left.disabled = True
            self.v_right.disabled = False
            self.v_end.disabled = False
            self.v_page.label = f"{1} / {self.get_last_page() + 1}"
            await edit_interaction(interaction, self, self.message_id)

    async def v_left_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await self.update_select_options(self.select_page - 1)
            last_page = self.get_last_page()
            self.v_start.disabled = self.select_page == 0 if last_page > 1 else True
            self.v_left.disabled = self.select_page == 0
            self.v_right.disabled = False
            self.v_end.disabled = last_page == 1
            self.v_page.label = f"{self.select_page + 1} / {last_page + 1}"
            await edit_interaction(interaction, self, self.message_id)

    async def v_right_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await self.update_select_options(self.select_page + 1)
            last_page = self.get_last_page()
            self.v_start.disabled = last_page == 1
            self.v_left.disabled = False
            self.v_right.disabled = self.select_page == last_page
            self.v_end.disabled = self.select_page == last_page if last_page > 1 else True
            self.v_page.label = f"{self.select_page + 1} / {last_page + 1}"
            await edit_interaction(interaction, self, self.message_id)

    async def v_end_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await self.update_select_options(self.get_last_page())
            self.v_start.disabled = False
            self.v_left.disabled = False
            self.v_right.disabled = True
            self.v_end.disabled = True
            self.v_page.label = "{0} / {0}".format(self.get_last_page() + 1)
            await edit_interaction(interaction, self, self.message_id)


class SelectView(TemplateSelectView):
    def __init__(
            self,
            options_raw: List,
            pivot_index: Optional[int],
            make_select_option: Callable[[int, Optional[commands.Bot]], Awaitable[SelectOption]],
            ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, None] = None,
            bot: Optional[commands.Bot] = None,
            namespace: str = "select_view",
            name: str = "SelectView",
            min_values: int = 1,
            max_values: int = 1,
            timeout: Optional[float] = 180.0
    ):
        super().__init__(
            options_raw=options_raw,
            ctx=ctx,
            namespace=namespace,
            name=name,
            min_values=min_values,
            max_values=max_values,
            timeout=timeout
        )
        self.pivot_index = pivot_index if pivot_index is not None else 0  # Starts from 0 to len(options_raw) - 1
        self.make_select_option = make_select_option
        self.bot = bot

    async def update_select_options(self, page: Optional[int] = None):
        if page is None:
            indexes = self.get_indexes(self.pivot_index)
        else:
            indexes = self.set_by_page(page)
        self.v_select.options = [
            await self.make_select_option(i, self.bot) for i in range(*indexes)
        ]


class SelectChoice(Enum):
    DO_NOTHING = auto()
    STOP_VIEW = auto()
    DELETE_SELECT = auto()


async def send_select_view(
        ctx: commands.Context,
        raw_options: List,
        pivot_index: Optional[int],
        make_select_option: Callable[[int, Optional[commands.Bot]], Awaitable[SelectOption]],
        on_callback: Callable[[Optional[Interaction]], Awaitable[SelectChoice]],
        on_interaction_check: Optional[Callable[[Interaction], bool]] = None,
        message: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        bot: Optional[commands.Bot] = None,
        timeout: Optional[int] = 180.0
):
    view = SelectView(
        raw_options,
        pivot_index,
        make_select_option,
        ctx=ctx,
        min_values=min_values,
        max_values=max_values,
        bot=bot,
        timeout=timeout
    )
    await view.update_view(send=False)

    if on_interaction_check is not None:
        async def interaction_check(interaction: Interaction):
            return on_interaction_check(interaction)

        view.interaction_check = interaction_check

    msg = await ctx.send(content=message, view=view)

    async def on_timeout():
        view.stop()
        await msg.delete()

    view.on_timeout = on_timeout

    async def callback(interaction: Interaction):
        choice = await on_callback(interaction)
        if choice == SelectChoice.STOP_VIEW:
            view.stop()
            view.on_timeout = lambda: None
        elif choice == SelectChoice.DELETE_SELECT:
            view.stop()
            await msg.delete()

    view.v_select.callback = callback


async def on_server_select_callback(
        interaction: Interaction,
        ctx: Optional[commands.Context] = None,
        is_reaction: bool = False
):
    selected_server = int(interaction.data.get("values", [None])[0])

    if BotVars.is_server_on or BotVars.is_loading or BotVars.is_stopping or BotVars.is_restarting:
        await send_interaction(
            interaction,
            add_quotes(get_translation("You can't change server, while some instance is still running\n"
                                       "Please stop it, before trying again")),
            ctx=ctx,
            is_reaction=True
        )
        return SelectChoice.DO_NOTHING

    if BotVars.watcher_of_log_file is not None:
        BotVars.watcher_of_log_file.stop()
        BotVars.watcher_of_log_file = None
    Config.get_settings().selected_server_number = selected_server + 1
    Config.save_config()
    await send_interaction(
        interaction,
        add_quotes(get_translation("Selected server") + ": " +
                   Config.get_selected_server_from_list().server_name +
                   f" [{str(Config.get_settings().selected_server_number)}]"),
        ctx=ctx,
        is_reaction=is_reaction
    )
    print(get_translation("Selected server") + f" - '{Config.get_selected_server_from_list().server_name}'")
    Config.read_server_info()
    await send_interaction(
        interaction,
        add_quotes(get_translation("Server properties read!")),
        ctx=ctx,
        is_reaction=is_reaction
    )
    print(get_translation("Server info read!"))
    return SelectChoice.STOP_VIEW


class MenuServerView(TemplateSelectView):
    def __init__(self, commands_cog: 'MinecraftCommands'):
        super().__init__(
            options_raw=Config.get_settings().servers_list,
            raw_content="List of commands for interacting with Minecraft server via buttons"
                        " and dropdown for selecting server",
            namespace="menu_server_view",
            name="MenuServerView",
            message_id=Config.get_menu_settings().server_menu_message_id,
            channel_id=Config.get_menu_settings().server_menu_channel_id,
            start_row=2,
            is_reaction=True
        )
        self.commands_cog = commands_cog

    async def update_select_options(self, page: Optional[int] = None):
        if page is None:
            indexes = self.get_indexes(Config.get_settings().selected_server_number)
        else:
            indexes = self.set_by_page(page)
        self.v_select.options = [
            SelectOption(
                label=shorten_string(Config.get_settings().servers_list[i].server_name,
                                     DISCORD_SELECT_FIELD_MAX_LENGTH),
                value=str(i),
                default=i + 1 == Config.get_settings().selected_server_number
            ) for i in range(*indexes)
        ]

    async def do_after_sending_message(self):
        if self.channel_id is not None and Config.get_menu_settings().server_menu_channel_id is None:
            Config.get_menu_settings().server_menu_channel_id = self.channel_id
            Config.save_config()

    async def interaction_check_select(self, interaction: Interaction, /) -> bool:
        return is_minecrafter(interaction)

    @button(label="status", style=ButtonStyle.secondary, custom_id="menu_server_view:status", emoji="⚠", row=0)
    async def c_status(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        await bot_status(interaction, interaction.client, is_reaction=True)

    @button(label="list", style=ButtonStyle.secondary, custom_id="menu_server_view:list", emoji="📋", row=0)
    async def c_list(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        await bot_list(interaction, interaction.client, is_reaction=True)

    @button(label="backup", style=ButtonStyle.secondary, custom_id="menu_server_view:backup", emoji="💾", row=0)
    async def c_backup(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        await bot_backup(interaction, interaction.client, is_reaction=True)

    @button(label="update", style=ButtonStyle.secondary, custom_id="menu_server_view:update", emoji="📶", row=0)
    async def c_update(self, interaction: Interaction, button: Button):
        self.commands_cog.checkups_task.restart()
        await send_interaction(interaction, get_translation("Updated bot status!"), is_reaction=True)

    @button(label="start", style=ButtonStyle.secondary, custom_id="menu_server_view:start", emoji="⏯", row=1)
    async def c_start(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        if await self.interaction_check_select(interaction):
            await bot_start(
                interaction,
                interaction.client,
                self.commands_cog.backups_thread,
                is_reaction=True
            )

    @button(label="stop 10", style=ButtonStyle.secondary, custom_id="menu_server_view:stop_10", emoji="⏹", row=1)
    async def c_stop(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        if await self.interaction_check_select(interaction):
            await bot_stop(
                interaction,
                command=10,
                bot=interaction.client,
                poll=self.commands_cog._IndPoll,
                is_reaction=True
            )

    @button(label="restart 10", style=ButtonStyle.secondary, custom_id="menu_server_view:restart_10", emoji="🔄", row=1)
    async def c_restart(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        if await self.interaction_check_select(interaction):
            await bot_restart(
                interaction,
                command=10,
                bot=interaction.client,
                poll=self.commands_cog._IndPoll,
                backups_thread=self.commands_cog.backups_thread,
                is_reaction=True
            )

    async def v_select_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await on_server_select_callback(interaction, is_reaction=True)
            await self.update_view()


async def on_language_select_callback(
        interaction: Optional[Interaction],
        set_language: Optional[str],
        ctx: Optional[commands.Context] = None,
        is_reaction: bool = False
):
    new_language = interaction.data.get("values", [None])[0] if interaction is not None else set_language

    if not set_locale(new_language):
        msg = add_quotes(get_translation("Bot doesn't have this language!\n"
                                         "Check list of available languages via {0}language")
                         .format(Config.get_settings().bot_settings.prefix))
        await send_interaction(interaction, msg, ctx=ctx, is_reaction=is_reaction)
        return SelectChoice.DO_NOTHING
    else:
        Config.get_settings().bot_settings.language = new_language.lower()
        Config.save_config()
        await send_interaction(
            interaction,
            add_quotes(get_translation("Language switched successfully!")),
            ctx=ctx,
            is_reaction=is_reaction
        )
        return SelectChoice.STOP_VIEW


class MenuBotView(TemplateSelectView):
    def __init__(self, bot: commands.Bot, commands_cog: 'MinecraftCommands'):
        super().__init__(
            options_raw=get_locales(),
            raw_content="List of bot features for interaction via buttons"
                        " and dropdown for selecting bot language",
            namespace="menu_bot_view",
            name="MenuBotView",
            message_id=Config.get_menu_settings().bot_menu_message_id,
            channel_id=Config.get_menu_settings().bot_menu_channel_id,
            start_row=3,
            is_reaction=True
        )
        self.bot = bot
        self.commands_cog = commands_cog
        self.chat_cog: Optional['ChatCommands'] = None

    async def update_select_options(self, page: Optional[int] = None):
        pivot = [i for i in range(self.options_list_length) if get_current_locale() == self.options_list_raw[i]][0]
        if page is None:
            indexes = self.get_indexes(pivot)
        else:
            indexes = self.set_by_page(page)
        self.v_select.options = [
            SelectOption(
                label=shorten_string(self.options_list_raw[i].capitalize(), DISCORD_SELECT_FIELD_MAX_LENGTH),
                value=shorten_string(self.options_list_raw[i], DISCORD_SELECT_FIELD_MAX_LENGTH),
                description=shorten_string(get_translation(self.options_list_raw[i]),
                                           DISCORD_SELECT_FIELD_MAX_LENGTH),
                default=pivot == i,
                emoji="🌐" if pivot == i else None
            ) for i in range(*indexes)
        ]

    async def update_view_components(self):
        if self.chat_cog is None:
            self.chat_cog = self.bot.get_cog("ChatCommands")
            if self.chat_cog is None:
                raise RuntimeError("Cog 'ChatCommands' not found!")

        self.b_auth.style = ButtonStyle.green if Config.get_secure_auth().enable_secure_auth else ButtonStyle.red
        self.b_auth.emoji = "🔒" if Config.get_secure_auth().enable_secure_auth else "🔑"
        self.b_auth.label = get_translation("Authorization")

        self.b_a_backup.style = ButtonStyle.green if Config.get_backups_settings().automatic_backup else ButtonStyle.red
        self.b_a_backup.label = get_translation("Auto backup")

        self.b_whitelist.style = ButtonStyle.green if ServerProperties().white_list else ButtonStyle.red
        self.b_whitelist.label = get_translation("White list")

        self.b_forceload.style = ButtonStyle.green if Config.get_settings().bot_settings.forceload else ButtonStyle.red
        self.b_forceload.emoji = "♾" if Config.get_settings().bot_settings.forceload else "🇽"
        self.b_forceload.label = get_translation("Forceload")

        self.b_a_shutdown.style = ButtonStyle.green \
            if Config.get_settings().bot_settings.auto_shutdown else ButtonStyle.red
        self.b_a_shutdown.emoji = "🌜" if Config.get_settings().bot_settings.auto_shutdown else "🌕"
        self.b_a_shutdown.label = get_translation("Auto shutdown")

        self.b_chat.style = ButtonStyle.green \
            if Config.get_game_chat_settings().enable_game_chat else ButtonStyle.red
        self.b_chat.label = get_translation("Game chat")

        self.b_c_p_images.style = ButtonStyle.green \
            if Config.get_game_chat_settings().image_preview.enable_images_preview else ButtonStyle.red
        self.b_c_p_images.label = get_translation("Image preview")

        self.b_rss_news.style = ButtonStyle.green if Config.get_rss_feed_settings().enable_rss_feed else ButtonStyle.red
        self.b_rss_news.emoji = "🔔" if Config.get_rss_feed_settings().enable_rss_feed else "🔕"
        self.b_rss_news.label = get_translation("RSS feed")

    async def do_after_sending_message(self):
        if self.channel_id is not None and Config.get_menu_settings().bot_menu_channel_id is None:
            Config.get_menu_settings().bot_menu_channel_id = self.channel_id
            Config.save_config()

    @button(custom_id="menu_bot_view:authorize", row=0)
    async def b_auth(self, interaction: Interaction, button: Button):
        if is_admin(interaction):
            Config.get_secure_auth().enable_secure_auth = not Config.get_secure_auth().enable_secure_auth
            Config.save_config()
            button.emoji = "🔑" if button.style == ButtonStyle.green else "🔒"
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_secure_auth().enable_secure_auth:
                with suppress(ConnectionError, socket.error):
                    if BotVars.watcher_of_log_file is None:
                        BotVars.watcher_of_log_file = create_watcher(BotVars.watcher_of_log_file, get_server_version())
                    BotVars.watcher_of_log_file.start()
                msg = add_quotes(get_translation("Secure authorization on"))
            else:
                if not Config.get_game_chat_settings().enable_game_chat and \
                        BotVars.watcher_of_log_file is not None:
                    BotVars.watcher_of_log_file.stop()
                msg = add_quotes(get_translation("Secure authorization off"))
            await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:auto_backup", emoji="💾", row=0)
    async def b_a_backup(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            Config.get_backups_settings().automatic_backup = not Config.get_backups_settings().automatic_backup
            Config.save_config()
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_backups_settings().automatic_backup:
                await warn_about_auto_backups(interaction, self.bot, is_reaction=True)
                msg = add_quotes(get_translation("Automatic backups enabled"))
            else:
                msg = add_quotes(get_translation("Automatic backups disabled"))
            await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:whitelist", emoji="🗒️", row=0)
    async def b_whitelist(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            async with handle_rcon_error(None, interaction, is_reaction=True):
                msg = None
                with connect_rcon() as cl_r:
                    if ServerProperties().white_list:
                        cl_r.run("whitelist off")
                        msg = add_quotes(get_translation("The server is allowed to let any players regardless "
                                                         "of the list of allowed nicknames"))
                    else:
                        cl_r.run("whitelist on")
                        msg = add_quotes(get_translation("The server is forbidden to let players not "
                                                         "from the list of allowed nicknames"))

                button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
                await edit_interaction(interaction, self, self.message_id)
                if msg is not None:
                    await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:forceload", row=1)
    async def b_forceload(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            Config.get_settings().bot_settings.forceload = not Config.get_settings().bot_settings.forceload
            Config.save_config()
            button.emoji = "🇽" if button.style == ButtonStyle.green else "♾"
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            await send_interaction(interaction, add_quotes(bot_forceload_info()), is_reaction=True)

    @button(custom_id="menu_bot_view:auto_shutdown", row=1)
    async def b_a_shutdown(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            Config.get_settings().bot_settings.auto_shutdown = not Config.get_settings().bot_settings.auto_shutdown
            Config.save_config()
            button.emoji = "🌕" if button.style == ButtonStyle.green else "🌜"
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            await send_interaction(
                interaction,
                add_quotes(bot_shutdown_info(with_timeout=Config.get_settings().bot_settings.auto_shutdown)),
                is_reaction=True
            )

    @button(custom_id="menu_bot_view:chat", emoji="💬", row=2)
    async def b_chat(self, interaction: Interaction, button: Button):
        if is_admin(interaction):
            Config.get_game_chat_settings().enable_game_chat = \
                not Config.get_game_chat_settings().enable_game_chat
            Config.save_config()
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_game_chat_settings().enable_game_chat:
                BotVars.webhook_chat = None
                await create_webhooks(self.bot)
                with suppress(ConnectionError, socket.error):
                    if BotVars.watcher_of_log_file is None:
                        BotVars.watcher_of_log_file = create_watcher(BotVars.watcher_of_log_file, get_server_version())
                    BotVars.watcher_of_log_file.start()
                msg = get_translation("Game chat enabled") + "!"
            else:
                if not Config.get_secure_auth().enable_secure_auth and BotVars.watcher_of_log_file is not None:
                    BotVars.watcher_of_log_file.stop()
                msg = get_translation("Game chat disabled") + "!"
            await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:chat_preview_images", emoji="🖼", row=2)
    async def b_c_p_images(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            Config.get_game_chat_settings().image_preview.enable_images_preview = \
                not Config.get_game_chat_settings().image_preview.enable_images_preview
            Config.save_config()
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_game_chat_settings().image_preview.enable_images_preview:
                msg = get_translation("Image preview enabled") + "!"
            else:
                msg = get_translation("Image preview disabled") + "!"
            await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:rss_news", row=2)
    async def b_rss_news(self, interaction: Interaction, button: Button):
        if is_admin(interaction):
            Config.get_rss_feed_settings().enable_rss_feed = not Config.get_rss_feed_settings().enable_rss_feed
            Config.save_config()
            button.emoji = "🔕" if button.style == ButtonStyle.green else "🔔"
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_rss_feed_settings().enable_rss_feed:
                BotVars.webhook_rss = None
                await create_webhooks(self.bot)
                if self.chat_cog.rss_feed_task.is_running():
                    self.chat_cog.rss_feed_task.restart()
                else:
                    self.chat_cog.rss_feed_task.start()
                msg = get_translation("RSS enabled") + "!"
            else:
                if self.chat_cog.rss_feed_task.is_running():
                    self.chat_cog.rss_feed_task.stop()
                msg = get_translation("RSS disabled") + "!"
            await send_interaction(interaction, msg, is_reaction=True)

    async def v_select_callback(self, interaction: Interaction):
        await on_language_select_callback(interaction, None, is_reaction=True)
        await self.update_view(update_content=True)
        if self.commands_cog.menu_server_view is not None:
            await self.commands_cog.menu_server_view.update_view(update_content=True)


@contextmanager
def connect_rcon(timeout=1):
    try:
        with Client_r(Config.get_settings().bot_settings.local_address, Config.get_server_config().rcon_port,
                      passwd=Config.get_server_config().rcon_password, timeout=timeout) as cl_r:
            yield cl_r
    except WrongPassword:
        print(get_translation("Bot Error: {0}")
              .format(get_translation("Rcon password '{0}' doesn't match with its value in '{1}'!")
                      .format(Config.get_server_config().rcon_password,
                              Path(Config.get_selected_server_from_list().working_directory + "/server.properties")
                              .as_posix())))
        raise ConnectionError()


@contextmanager
def connect_query():
    with Client_q(Config.get_settings().bot_settings.local_address,
                  Config.get_server_config().query_port, timeout=1) as cl_q:
        yield cl_q


@asynccontextmanager
async def handle_rcon_error(ctx: Optional[commands.Context], interaction: Interaction = None, is_reaction=False):
    try:
        yield
    except (ConnectionError, socket.error):
        if BotVars.is_server_on:
            await send_interaction(
                interaction,
                add_quotes(get_translation("Couldn't connect to server, try again(")),
                ctx=ctx,
                is_reaction=is_reaction
            )
        else:
            await send_interaction(
                interaction,
                add_quotes(get_translation("server offline").capitalize()),
                ctx=ctx,
                is_reaction=is_reaction
            )


class HelpCommandArgument(commands.CheckFailure):
    pass


class BadIPv4Address(commands.BadArgument):
    def __init__(self, ip_address: str):
        self.argument = ip_address
        super().__init__(f"\"{ip_address}\" is not a recognised IPv4 address.")


class IPv4Address(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if search(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)(\.(?!$)|$)){4}$", argument):
            return argument
        raise BadIPv4Address(argument)


class BadURLAddress(commands.BadArgument):
    def __init__(self, url: str):
        self.argument = url
        super().__init__(f"\"{url}\" is not a recognised URL address.")


class URLAddress(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if search(URL_REGEX, argument):
            return argument
        raise BadURLAddress(argument)


# Handling errors
async def send_error(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel],
        bot: commands.Bot,
        error: Union[commands.CommandError, commands.CommandInvokeError],
        is_reaction=False
):
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
    parsed_input = None
    if hasattr(error, "param"):
        error_param_type = get_param_type(error.param)
        error_param_name = error.param.name
    else:
        error_param_type = ""
        error_param_name = ""
    if hasattr(error, "argument") and isinstance(error.argument, str):
        parsed_input = await commands.clean_content(fix_channel_mentions=True).convert(ctx, error.argument)
    if parsed_input is None:
        parsed_input = await commands.clean_content(fix_channel_mentions=True) \
            .convert(ctx, ctx.message.content[ctx.view.previous:ctx.view.index])

    if isinstance(error, commands.MissingRequiredArgument):
        print(get_translation("{0} didn't input the argument '{1}' of type '{2}' in command '{3}'")
              .format(author, error_param_name, error_param_type,
                      f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Required argument '{0}' of type '{1}' is missing!")
                                  .format(error_param_name, error_param_type)),
                       is_reaction)
    elif isinstance(error, commands.TooManyArguments):
        print(get_translation("{0} passed too many arguments to command '{1}'")
              .format(author, f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("You passed too many arguments to this command!")),
                       is_reaction)
    elif isinstance(error, commands.MemberNotFound):
        print(get_translation("{0} passed member mention '{1}' that can't be found").format(author, parsed_input))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Member '{0}' not found!").format(parsed_input)), is_reaction)
    elif isinstance(error, commands.UserNotFound):
        print(get_translation("{0} passed user mention '{1}' that can't be found").format(author, parsed_input))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("User '{0}' not found!").format(parsed_input)), is_reaction)
    elif isinstance(error, commands.RoleNotFound):
        print(get_translation("{0} passed role mention '{1}' that can't be found"))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Role '{0}' not found!").format(parsed_input)), is_reaction)
    elif isinstance(error, commands.ChannelNotReadable):
        print(get_translation("Bot can't read messages in channel '{0}'").format(error.argument))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Bot can't read messages in channel '{0}'")
                                  .format(error.argument) + "!"),
                       is_reaction)
    elif isinstance(error, commands.ChannelNotFound):
        print(get_translation("{0} passed channel mention '{1}' that can't be found").format(author, parsed_input))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Channel '{0}' not found!").format(parsed_input)), is_reaction)
    elif isinstance(error, commands.ThreadNotFound):
        print(get_translation("{0} passed thread mention '{1}' that can't be found").format(author, parsed_input))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Thread '{0}' not found!").format(parsed_input)), is_reaction)
    elif isinstance(error, commands.BadBoolArgument):
        print(get_translation("{0} passed bad bool argument '{1}'").format(author, parsed_input))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Bot couldn't convert bool argument '{0}'!").format(parsed_input)),
                       is_reaction)
    elif isinstance(error, commands.BadLiteralArgument):
        print(get_translation("{0} passed bad literal '{1}'").format(author, parsed_input))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation(
                           "Bot couldn't find argument '{0}' in any of these values: {1}!"
                       ).format(parsed_input, str(error.literals).strip("()"))),
                       is_reaction)
    elif isinstance(error, BadIPv4Address):
        print(get_translation("{0} passed an invalid IPv4 address as argument '{1}'").format(author, parsed_input))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Bot couldn't convert argument '{0}' "
                                                  "to an IPv4 address!").format(parsed_input)),
                       is_reaction)
    elif isinstance(error, BadURLAddress):
        print(get_translation("{0} passed an invalid URL as argument '{1}'").format(author, parsed_input))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Bot couldn't convert argument '{0}' "
                                                  "to a URL!").format(parsed_input)),
                       is_reaction)
    elif isinstance(error, (commands.BadArgument, commands.ArgumentParsingError)):
        conv_args = findall(r"Converting to \".+\" failed for parameter \".+\"\.", "".join(error.args))
        if len(conv_args) > 0:
            conv_args = findall(r"\"([^\"]+)\"", conv_args[0])
        if len(conv_args) > 0:
            print(get_translation("{0} passed parameter '{2}' in string \"{3}\" that bot couldn't "
                                  "convert to type '{1}' in command '{4}'")
                  .format(author, *conv_args, parsed_input,
                          f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
            await send_msg(ctx, f"{author_mention}\n" +
                           add_quotes(get_translation("Bot didn't recognized parameter '{1}'\n"
                                                      "Received: '{2}'\n"
                                                      "Expected: value of type '{0}'"))
                           .format(*conv_args, parsed_input),
                           is_reaction)
        else:
            print(get_translation("{0} passed string \"{1}\" that can't be parsed in command '{2}'")
                  .format(author, parsed_input, f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
            await send_msg(ctx, f"{author_mention}\n" +
                           add_quotes(get_translation("Bot couldn't parse user "
                                                      "string '{0}' in this command!").format(parsed_input)),
                           is_reaction)
    elif isinstance(error, commands.MissingPermissions):
        await send_msg(ctx, f"{author_mention}\n" + add_quotes(await get_missing_permissions_message(error, author)),
                       is_reaction)
    elif isinstance(error, commands.BotMissingPermissions):
        print(get_translation("Bot doesn't have some permissions"))
        missing_perms = [get_translation(perm.replace("_", " ").replace("guild", "server").title())
                         for perm in error.missing_permissions]
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("Bot don't have these permissions to run this command:")
                                  .capitalize() + "\n- " + "\n- ".join(missing_perms)), is_reaction)
    elif isinstance(error, commands.MissingRole):
        await send_msg(ctx, f"{author_mention}\n" + add_quotes(await get_missing_role_message(error, bot, author)),
                       is_reaction)
    elif isinstance(error, commands.CommandNotFound):
        print(get_translation("{0} entered non-existent command").format(author))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("You entered non-existent command!")), is_reaction)
    elif isinstance(error, commands.UserInputError):
        print(get_translation("{0} entered wrong argument(s) of command '{1}'")
              .format(author, f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("You entered wrong argument(s) of this command!")),
                       is_reaction)
    elif isinstance(error, commands.DisabledCommand):
        print(get_translation("{0} entered disabled command").format(author))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("You entered disabled command!")), is_reaction)
    elif isinstance(error, commands.NoPrivateMessage):
        print(get_translation("{0} entered a command that only works in the guild").format(author))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("This command only works on server!")), is_reaction)
    elif isinstance(error, commands.CommandOnCooldown):
        cooldown_retry = round(error.retry_after, 1) if error.retry_after < 1 else int(error.retry_after)
        if isinstance(cooldown_retry, float) and cooldown_retry.is_integer():
            cooldown_retry = int(cooldown_retry)
        print(get_translation("{0} triggered a command more than {1} time(s) per {2} sec")
              .format(author, error.cooldown.rate, int(error.cooldown.per)))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("You triggered this command more than {0} time(s) per {1} sec.\n"
                                                  "Try again in {2} sec...").format(error.cooldown.rate,
                                                                                    int(error.cooldown.per),
                                                                                    cooldown_retry)),
                       is_reaction)
    elif isinstance(error, HelpCommandArgument):
        pass
    elif isinstance(error, MissingAdminPermissions):
        msg = ""
        if Config.get_settings().bot_settings.admin_role_id is not None:
            msg += await get_missing_role_message(
                commands.MissingRole(Config.get_settings().bot_settings.admin_role_id),
                bot,
                author
            ) + "\n\n"
        msg += await get_missing_permissions_message(commands.MissingPermissions(['administrator']), author)
        await send_msg(ctx, f"{author_mention}\n" + add_quotes(msg), is_reaction)
    else:
        print_unhandled_error(error.original, get_translation("Ignoring exception in command '{0}{1}':")
                              .format(Config.get_settings().bot_settings.prefix, ctx.command))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(error.original.__class__.__name__ +
                                  (": " + ", ".join([str(a) for a in error.original.args])
                                   if len(error.original.args) > 0 else "")), is_reaction)


def print_unhandled_error(error, error_title: str):
    exc = "".join(format_exception(type(error), error, error.__traceback__)).rstrip("\n")
    print(f"{error_title}\n{Fore.RED}{exc}{Style.RESET_ALL}")


async def get_missing_role_message(
        error: commands.MissingRole,
        bot: Union[commands.Bot, Client],
        author: Member,
        interaction=False
):
    if isinstance(error.missing_role, int):
        role = await get_role_string(bot, error.missing_role)
    else:
        role = error.missing_role
    if interaction:
        print(get_translation("{0} don't have role '{1}' to use interaction").format(author, role))
        return get_translation("You don't have role '{0}' to use this interaction!").format(role)
    print(get_translation("{0} don't have role '{1}' to run command").format(author, role))
    return get_translation("You don't have role '{0}' to run this command!").format(role)


async def get_missing_permissions_message(
        error: commands.MissingPermissions,
        author: Member,
        interaction=False
):
    missing_perms = [get_translation(perm.replace("_", " ").replace("guild", "server").title())
                     for perm in error.missing_permissions]
    if interaction:
        print(get_translation("{0} don't have some permissions to use interaction").format(author))
        return get_translation("You don't have these permissions to use this interaction:").capitalize() + \
               "\n- " + "\n- ".join(missing_perms)
    print(get_translation("{0} don't have some permissions to run command").format(author))
    return get_translation("You don't have these permissions to run this command:").capitalize() + \
           "\n- " + "\n- ".join(missing_perms)


async def send_error_on_interaction(
        view_name: str,
        interaction: Interaction,
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, None],
        error: Union[commands.CommandError, Exception],
        is_reaction=False
):
    author, author_mention = interaction.user, interaction.user.mention

    if isinstance(error, commands.MissingPermissions):
        await send_interaction(
            interaction,
            f"{author_mention}\n" + add_quotes(await get_missing_permissions_message(error, author, interaction=True)),
            ephemeral=True,
            ctx=ctx,
            is_reaction=is_reaction
        )
    elif isinstance(error, commands.MissingRole):
        await send_interaction(
            interaction,
            f"{author_mention}\n" +
            add_quotes(await get_missing_role_message(error, interaction.client, author, interaction=True)),
            ephemeral=True,
            ctx=ctx,
            is_reaction=is_reaction
        )
    elif isinstance(error, MissingAdminPermissions):
        msg = ""
        if Config.get_settings().bot_settings.admin_role_id is not None:
            msg += await get_missing_role_message(
                commands.MissingRole(Config.get_settings().bot_settings.admin_role_id),
                interaction.client,
                author,
                interaction=True
            ) + "\n\n"
        msg += await get_missing_permissions_message(
            commands.MissingPermissions(['administrator']),
            author,
            interaction=True
        )
        await send_interaction(
            interaction,
            f"{author_mention}\n" + add_quotes(msg),
            ephemeral=True,
            ctx=ctx,
            is_reaction=is_reaction
        )
    else:
        await send_interaction(
            interaction,
            f"{author_mention}\n" + get_translation("This interaction failed! Try again!") + \
            add_quotes(error.__class__.__name__ +
                       (": " + ", ".join([str(a) for a in error.args]) if len(error.args) > 0 else "")),
            ctx=ctx,
            is_reaction=is_reaction
        )
        if isinstance(ctx, commands.Context):
            ignore_message = get_translation("Ignoring exception in view '{0}' created by command '{1}':") \
                .format(view_name, str(ctx.command))
        else:
            ignore_message = get_translation("Ignoring exception in view '{0}':").format(view_name)
        print_unhandled_error(error, ignore_message)


def func_name(func_number: int = 1):
    return sys._getframe(func_number).f_code.co_name


@contextmanager
def handle_unhandled_error_in_task(func_number: int = 2):
    try:
        yield
    except (KeyboardInterrupt, CancelledError):
        pass
    except BaseException as error:
        print_unhandled_error(error, get_translation("Ignoring exception in internal background task '{0}':")
                              .format(func_name(func_number=func_number + 1)))


@contextmanager
def handle_unhandled_error_in_events(func_number: int = 2):
    try:
        yield
    except KeyboardInterrupt:
        pass
    except BaseException as error:
        print_unhandled_error(error, get_translation("Ignoring exception in internal event '{0}':")
                              .format(func_name(func_number=func_number + 1)))


async def handle_message_for_chat(
        message: Message,
        bot: commands.Bot,
        on_edit=False,
        before_message: Message = None,
        edit_command_content: str = ""
):
    edit_command = len(edit_command_content) != 0
    if message.author.id == bot.user.id or \
            (message.content.startswith(Config.get_settings().bot_settings.prefix) and not edit_command) or \
            str(message.author.discriminator) == "0000" or \
            (len(message.content) == 0 and len(message.attachments) == 0 and len(message.stickers) == 0):
        return

    author_mention = get_author_and_mention(message, bot, False)[1]

    if not Config.get_game_chat_settings().webhook_url or not BotVars.webhook_chat:
        await send_msg(message.channel, f"{author_mention}, " +
                       get_translation("this chat can't work! Game chat disabled!"), True)
    elif not BotVars.is_server_on:
        await send_msg(message.channel, f"{author_mention}\n" +
                       add_quotes(get_translation("server offline").capitalize() + "!"), True)
    elif BotVars.is_restarting:
        await send_msg(message.channel, f"{author_mention}\n" +
                       add_quotes(get_translation("server is restarting!").capitalize()), True)
    elif BotVars.is_stopping and BotVars.watcher_of_log_file is None:
        await send_msg(message.channel, f"{author_mention}\n" +
                       add_quotes(get_translation("server is stopping!").capitalize()), True)
    elif BotVars.is_loading:
        await send_msg(message.channel, f"{author_mention}\n" +
                       add_quotes(get_translation("server is loading!").capitalize()), True)
    else:
        if get_server_players().get("current") == 0:
            await send_msg(message.channel, f"{author_mention}, " +
                           get_translation("No players on server!").lower(), True)
            return

        server_version = get_server_version()
        reply_from_minecraft_user = None
        if server_version.minor < 7:
            if server_version.minor < 3:
                message_length = 108
            elif 3 <= server_version.minor < 6:
                message_length = 112
            else:
                message_length = 1442
            space = u"\U000e0020"
            result_msg = _clean_message(message, edit_command_content)
            if not edit_command:
                result_msg, reply_from_minecraft_user = await _handle_reply_in_message(message, result_msg)
            result_msg, _ = await _handle_components_in_message(
                result_msg,
                message,
                bot,
                only_replace_links=True,
                version_lower_1_7_2=True
            )
            msg = ""
            if result_msg.get("reply", None) is not None:
                msg += space
                if not reply_from_minecraft_user:
                    result_msg["reply"][1] = result_msg["reply"][1].display_name
                if isinstance(result_msg["reply"][-1], list):
                    msg += "".join(result_msg["reply"][:-1] + ["".join(result_msg["reply"][-1])])
                else:
                    msg += "".join(result_msg["reply"])
            if not edit_command:
                msg += f"<{message.author.display_name}> "
            else:
                msg += f"<{before_message.author.name}> "
            if on_edit:
                msg += "*"
            msg += result_msg["content"]
            if (server_version.minor < 6 and len(msg) <= message_length) or \
                    (server_version.minor == 6 and len(msg.encode()) <= message_length):
                if server_version.minor < 3 and "\n" in msg:
                    messages = [m.strip() for m in msg.split("\n")]
                else:
                    messages = [msg if reply_from_minecraft_user is None else msg[1:]]
            else:
                messages = []
                if server_version.minor < 6:
                    if server_version.minor < 3 and "\n" in msg:
                        for m in msg.split("\n"):
                            if len(m) <= message_length:
                                messages.append(m.strip())
                            else:
                                for m_split in wrap(m, message_length, replace_whitespace=False):
                                    messages.append(m_split)
                    else:
                        for m_split in wrap((msg if reply_from_minecraft_user is None else msg[1:]),
                                            message_length, replace_whitespace=False):
                            messages.append(m_split)
                else:
                    split_line = ""
                    byte_line_length = 0
                    for symb in (msg if reply_from_minecraft_user is None else msg[1:]):
                        byte_line_length += len(symb.encode())
                        if byte_line_length > message_length:
                            messages.append(split_line)
                            split_line = symb
                            byte_line_length = len(symb.encode())
                        else:
                            split_line += symb
                    if len(split_line) > 0:
                        messages.append(split_line)
            with connect_rcon() as cl_r:
                for m in messages:
                    cl_r.say(m if m != "" else space)
        else:
            content_name = "contents" if server_version.minor >= 16 else "value"
            result_msg = _clean_message(message, edit_command_content)
            if not edit_command:
                result_msg, reply_from_minecraft_user = await _handle_reply_in_message(message, result_msg)
            result_msg, images_for_preview = await _handle_components_in_message(
                result_msg,
                message, bot,
                store_images_for_preview=server_version.minor >= 16 and
                                         Config.get_game_chat_settings().image_preview.enable_images_preview
            )
            # Building object for tellraw
            res_obj = [""]
            if result_msg.get("reply", None) is not None:
                if not reply_from_minecraft_user:
                    res_obj += _build_nickname_tellraw_for_discord_member(
                        server_version,
                        result_msg["reply"][1],
                        content_name,
                        brackets_color="gray",
                        left_bracket=result_msg["reply"][0],
                        right_bracket=result_msg["reply"][2]
                    )
                else:
                    res_obj += _build_nickname_tellraw_for_minecraft_player(
                        server_version,
                        result_msg["reply"][1],
                        content_name,
                        default_text_color="gray",
                        left_bracket=result_msg["reply"][0],
                        right_bracket=result_msg["reply"][2]
                    )
                _build_components_in_message(res_obj, content_name, result_msg["reply"][-1], "gray")
            if not edit_command:
                res_obj += _build_nickname_tellraw_for_discord_member(server_version, message.author, content_name)
            else:
                res_obj += _build_nickname_tellraw_for_minecraft_player(server_version,
                                                                        before_message.author.name, content_name)
            if on_edit:
                if before_message is not None:
                    result_before = _clean_message(before_message)
                    result_before, _ = await _handle_components_in_message(
                        result_before,
                        before_message,
                        bot,
                        only_replace_links=True
                    )
                    res_obj.append({"text": "*", "color": "gold",
                                    "hoverEvent": {"action": "show_text",
                                                   content_name: shorten_string(result_before["content"], 250)}})
                else:
                    res_obj.append({"text": "*", "color": "gold"})
            _build_components_in_message(res_obj, content_name, result_msg["content"])
            res_obj = _handle_long_tellraw_object(res_obj)

            with connect_rcon() as cl_r:
                if server_version.minor > 7:
                    for obj in res_obj:
                        cl_r.tellraw("@a", obj)
                else:
                    res = _split_tellraw_object(res_obj)
                    for tellraw in res:
                        cl_r.tellraw("@a", tellraw)

            if server_version.minor > 7:
                nicks = _search_mentions_in_message(message, edit_command)
                if len(nicks) > 0:
                    with suppress(ConnectionError, socket.error):
                        with connect_rcon() as cl_r:
                            with times(0, 60, 20, cl_r):
                                for nick in nicks:
                                    announce(
                                        nick,
                                        f"@{message.author.display_name} "
                                        f"-> @{nick if nick != '@a' else 'everyone'}",
                                        cl_r,
                                        server_version
                                    )

            if len(images_for_preview) > 0:
                emoji_count = len([0 for i in images_for_preview if i.get("type", "") == "emoji"])
                if emoji_count > 0:
                    if len(images_for_preview) == emoji_count:
                        if emoji_count > 1:
                            images_for_preview = images_for_preview[:1]
                    else:
                        images_for_preview = [i for i in images_for_preview if i.get("type", "") != "emoji"]
                for image in images_for_preview:
                    with suppress(UnidentifiedImageError):
                        send_image_to_chat(
                            url=image["url"],
                            image_name=image["name"],
                            required_width=image.get("width", None),
                            required_height=image.get("height", None)
                        )


def _handle_long_tellraw_object(tellraw_obj: list):
    if len(dumps(tellraw_obj)) <= MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
        return [tellraw_obj]

    calc_size = 4
    res = []
    tellraw_obj_length = len(tellraw_obj)
    for e in range(tellraw_obj_length):
        if tellraw_obj[e] == "":
            res += [[""]]
        elif isinstance(tellraw_obj[e], dict):
            calc_size += len(dumps(tellraw_obj[e])) + 2
            if calc_size <= MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH and \
                    not (tellraw_obj_length - e > 1 and any(i in tellraw_obj[e + 1].keys()
                                                            for i in ["insertion", "selector", "hoverEvent"]) and
                         tellraw_obj[e]["text"] == "<" and len(res[-1]) > 1):
                res[-1] += [tellraw_obj[e]]
                continue
            if len(dumps(tellraw_obj[e])) + 4 <= MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
                res += [["", tellraw_obj[e]]]
                calc_size = len(dumps(tellraw_obj[e])) + 6
            else:
                for split_str in tellraw_obj[e]["text"].split("\n"):
                    if split_str == "":
                        continue
                    split_elem = tellraw_obj[e].copy()
                    split_elem["text"] = split_str
                    if len(dumps(split_elem)) + 6 > MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
                        split_array = []
                        split_elem["text"] = ""
                        max_wrap_str_length = MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH - 6 - \
                                              len(dumps(split_elem))
                        wraps = wrap(dumps(split_str)[1:-1], max_wrap_str_length, replace_whitespace=False)
                        wraps_slice = 0
                        for i in range(len(wraps)):
                            if wraps_slice > 0:
                                wraps[i] = f"{wraps[i - 1][-wraps_slice:]}{wraps[i]}"
                                if len(wraps[i]) > max_wrap_str_length:
                                    wraps_slice = len(wraps[i]) - max_wrap_str_length
                                else:
                                    wraps_slice = 0
                            while True:
                                try:
                                    if wraps_slice > 0:
                                        parsed_sliced_str = wraps[i][:-wraps_slice] \
                                            .encode("ascii").decode("unicode-escape")
                                    else:
                                        parsed_sliced_str = wraps[i] \
                                            .encode("ascii").decode("unicode-escape")
                                except (UnicodeDecodeError, SyntaxError):
                                    wraps_slice += 1
                                    continue
                                split_array += [parsed_sliced_str]
                                break
                        if wraps_slice > 0:
                            split_array += [wraps[-1][-wraps_slice:].encode("ascii").decode("unicode-escape")]
                        for split_str_ws in split_array:
                            split_elem = tellraw_obj[e].copy()
                            split_elem["text"] = split_str_ws
                            if len(dumps(res[-1])) + \
                                    len(dumps(split_elem)) + 6 > MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
                                res += [["", split_elem]]
                            else:
                                res[-1] += [split_elem]
                    else:
                        added_split = res[-1].copy()
                        added_dict = added_split[-1].copy()
                        added_dict["text"] += f"\n{split_str}"
                        added_split[-1] = added_dict
                        if len(dumps(added_split)) > MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
                            res += [["", split_elem]]
                        else:
                            if res[-1][-1].get("text", "") in ["> ", "*"]:
                                res[-1] += [split_elem]
                            else:
                                res[-1] = added_split
    for elem_res in range(len(res)):
        if elem_res == 0:
            pass
        elif len(res[elem_res][1]["text"].lstrip(" \n")) == 0:
            del res[elem_res][1]
        else:
            res[elem_res][1]["text"] = res[elem_res][1]["text"].lstrip(" \n")
        if len(res[elem_res][-1]["text"].rstrip(" \n")) == 0:
            del res[elem_res][-1]
        else:
            res[elem_res][-1]["text"] = res[elem_res][-1]["text"].rstrip(" \n")
    return res


def _split_tellraw_object(tellraw_obj: Union[list, dict]):
    if not isinstance(tellraw_obj, list):
        tellraw_obj = [tellraw_obj]

    res = []
    for obj in tellraw_obj:
        for elem in obj:
            if elem == "":
                res += [[""]]
            elif isinstance(elem, dict):
                if elem["text"] != "*" and "\n" in elem["text"]:
                    first_elem = True
                    for split_str in elem["text"].split("\n"):
                        split_elem = elem.copy()
                        split_elem["text"] = split_str
                        if first_elem:
                            res[-1] += [split_elem]
                            first_elem = False
                        else:
                            res += [["", split_elem]]
                else:
                    res[-1] += [elem]
    return res


def _clean_message(message: Message, edit_command_content: str = ""):
    result_msg = {}
    if len(edit_command_content) == 0:
        content = message.clean_content.replace("\u200b", "").strip()
    else:
        content = edit_command_content.replace("\u200b", "").strip()
    result_msg["content"] = content
    return result_msg


async def _handle_reply_in_message(message: Message, result_msg: dict) -> Tuple[dict, bool]:
    reply_from_minecraft_user = None
    if message.reference is not None:
        reply_msg = message.reference.resolved
        cnt = reply_msg.clean_content.replace("\u200b", "").strip()
        if reply_msg.author.discriminator == "0000":
            # reply to Minecraft player
            nick = reply_msg.author.display_name
            reply_from_minecraft_user = True
        else:
            # Reply to discord user
            nick = await message.guild.fetch_member(reply_msg.author.id)
            reply_from_minecraft_user = False
        result_msg["reply"] = ["\n -> <", nick, "> ", cnt]
    return result_msg, reply_from_minecraft_user


async def _handle_components_in_message(
        result_msg: dict,
        message: Message,
        bot: commands.Bot,
        only_replace_links=False,
        version_lower_1_7_2=False,
        store_images_for_preview=False
):
    if only_replace_links or version_lower_1_7_2:
        store_images_for_preview = False
    attachments, images_for_preview = _handle_attachments_in_message(message, store_images_for_preview)
    emoji_regex = r"<a?:\w+:\d+>"
    tenor_regex = r"https?://tenor\.com/view"

    async def repl_emoji(match: str):
        obj = search(r"<a?:(?P<name>\w+):(?P<id>\d+)>", match)
        emoji_name = f":{obj.group('name')}:"
        if only_replace_links:
            return emoji_name
        else:
            emoji_id = int(obj.group("id"))
            emoji = bot.get_emoji(emoji_id)
            if emoji is None:
                emoji = utils_get(bot.guilds[0].emojis, id=emoji_id)
            if emoji is None:
                with suppress(NotFound, HTTPException):
                    emoji = await bot.guilds[0].fetch_emoji(emoji_id)
            if isinstance(emoji, Emoji):
                if store_images_for_preview:
                    images_for_preview.append({
                        "type": "emoji",
                        "url": emoji.url,
                        "name": obj.group("name"),
                        "height": 22
                    })
                return {"text": emoji_name, "hyperlink": str(emoji.url)}
            else:
                return emoji_name

    def repl_url(link: str):
        is_tenor = bool(search(tenor_regex, link))
        if store_images_for_preview:
            if is_tenor:
                images_for_preview.append({
                    "type": "link",
                    "url": link,
                    "name": ""
                })
            else:
                with suppress(Timeout):
                    resp = req_head(link, timeout=(3, 6), headers={"User-Agent": UserAgent.get_header()})
                    if resp.status_code == 200 and resp.headers.get("content-length") is not None and \
                            int(resp.headers.get("content-length")) <= 20971520:
                        # Checks if Content-Length not larger than 20 MB
                        if resp.headers.get("content-type") is None or \
                                (resp.headers.get("content-type") is not None and
                                 "image" in resp.headers.get("content-type")):
                            images_for_preview.append({
                                "type": "link",
                                "url": link,
                                "name": ""
                            })
        if only_replace_links:
            if version_lower_1_7_2:
                if is_tenor:
                    return "[gif]"
                elif len(link) > 30:
                    return get_shortened_url(link)
                else:
                    return link
            else:
                return "[gif]" if is_tenor else shorten_string(link, 30)
        else:
            return {
                "text": "[gif]" if is_tenor else shorten_string(link, 30),
                "hyperlink": link if len(link) < 257 else get_shortened_url(link)
            }

    transformations = {
        emoji_regex: repl_emoji,
        URL_REGEX: repl_url
    }
    mass_regex = "|".join(transformations.keys())

    async def repl(obj):
        match = obj.group(0)
        if search(URL_REGEX, match):
            return transformations.get(URL_REGEX)(match)
        else:
            return await transformations.get(emoji_regex)(match)

    for key, ms in result_msg.items():
        if isinstance(ms, list):
            msg = ms.copy()
            msg = msg[-1]
        else:
            msg = ms

        temp_split = []
        if search(mass_regex, msg):
            temp_split = split(mass_regex, msg)
            i = 1
            for m in compile(mass_regex).finditer(msg):
                temp_split.insert(i, (await repl(m)))
                i += 2
        else:
            temp_split.append(msg)

        if attachments.get(key, None) is not None and len(attachments[key]) > 0:
            for i in attachments[key]:
                t_string = [t["text"] if isinstance(t, dict) else t for t in temp_split]
                if len("".join(t_string)) != 0:
                    if isinstance(temp_split[-1], str):
                        temp_split[-1] += " "
                    else:
                        temp_split.append(" ")
                if only_replace_links:
                    temp_split.append(i["text"])
                else:
                    temp_split.append(i)

        if key == "reply":
            if isinstance(temp_split[-1], dict):
                temp_split.append("\n")
            else:
                temp_split[-1] += "\n"

        temp_split = [s for s in temp_split if (isinstance(s, str) and len(s) > 0) or not isinstance(s, str)]

        if isinstance(ms, list):
            result_msg[key] = [ms[0], ms[1], ms[2], "".join(temp_split) if only_replace_links else temp_split]
        else:
            result_msg[key] = "".join(temp_split) if only_replace_links else temp_split
    return result_msg, images_for_preview


def _handle_attachments_in_message(message: Message, store_images_for_preview=False):
    attachments = {}
    messages = [message]
    images_for_preview: List[Dict[str, Union[str, int]]] = []
    if message.reference is not None:
        messages.append(message.reference.resolved)
    for i in range(len(messages)):
        stickers = messages[i].stickers
        if len(stickers) != 0 or len(messages[i].attachments) != 0:
            if i == 0:
                attachments["content"] = []
                iattach = attachments["content"]
            else:
                attachments["reply"] = []
                iattach = attachments["reply"]
            if len(stickers) != 0:
                for sticker in stickers:
                    iattach.append({
                        "text": sticker.name,
                        "hyperlink": sticker.url if len(sticker.url) < 257 else get_shortened_url(sticker.url)
                    })
                    if store_images_for_preview and i == 0:
                        images_for_preview.append({
                            "type": "sticker",
                            "url": sticker.url,
                            "name": sticker.name
                        })
            if len(messages[i].attachments) != 0:
                for attachment in messages[i].attachments:
                    need_hover = True
                    if "." in attachment.filename:
                        a_type = f"[{attachment.filename.split('.')[-1]}]"
                    elif attachment.content_type is not None and \
                            any(i in attachment.content_type for i in ["image", "video", "audio"]):
                        a_type = f"[{attachment.content_type.split('/')[-1]}]"
                    else:
                        need_hover = False
                        a_type = f"[{shorten_string(attachment.filename, max_length=20)}]"
                    iattach.append({
                        "text": a_type,
                        "hyperlink": attachment.url if len(attachment.url) < 257 else get_shortened_url(attachment.url)
                    })
                    if need_hover:
                        iattach[-1].update({"hover": attachment.filename})
                    if store_images_for_preview and i == 0 and \
                            attachment.content_type is not None and "image" in attachment.content_type:
                        images_for_preview.append({
                            "type": "image",
                            "url": attachment.url,
                            "name": attachment.filename
                        })
    return attachments, images_for_preview


def _build_components_in_message(res_obj: list, content_name: str, obj, default_text_color: str = None):
    if isinstance(obj, list):
        for elem in obj:
            if isinstance(elem, dict):
                if "text" not in elem.keys():
                    raise KeyError(f"'text' key not in dict {elem}!")
                if default_text_color is not None:
                    res_obj.append({"text": elem["text"], "color": default_text_color})
                else:
                    res_obj.append({"text": elem["text"]})
                if "hover" in elem.keys():
                    res_obj[-1].update({"hoverEvent": {"action": "show_text",
                                                       content_name: shorten_string(elem["hover"], 250)}})
                if "hyperlink" in elem.keys():
                    res_obj[-1].update({"underlined": True, "color": "blue",
                                        "clickEvent": {"action": "open_url", "value": elem["hyperlink"]}})
            elif isinstance(elem, str):
                if default_text_color is not None:
                    res_obj.append({"text": elem, "color": default_text_color})
                else:
                    res_obj.append({"text": elem})
    else:
        if default_text_color is not None:
            res_obj.append({"text": obj, "color": default_text_color})
        else:
            res_obj.append({"text": obj})


def _search_mentions_in_message(message: Message, edit_command=False) -> set:
    if len(message.mentions) == 0 and len(message.role_mentions) == 0 and \
            not message.mention_everyone and message.reference is None and "@" not in message.content:
        return set()

    nicks = []
    if message.mention_everyone:
        nicks.append("@a")
    else:
        # Check role, user mentions and reply author mention
        members_from_roles = list(chain(*[i.members for i in message.role_mentions]))
        if message.reference is not None and not edit_command:
            if message.reference.resolved.author.discriminator != "0000":
                members_from_roles.append(message.reference.resolved.author)
            else:
                nicks.append(message.reference.resolved.author.name)
        members_from_roles.extend(message.mentions)
        members_from_roles = set(members_from_roles)
        for member in members_from_roles:
            if member.id in [i.user_discord_id for i in Config.get_known_users_list()]:
                nicks.extend([i.user_minecraft_nick for i in Config.get_known_users_list()
                              if i.user_discord_id == member.id])
        server_players = get_server_players().get("players")
        # Check @'minecraft_nick' mentions
        if "@" in message.content:
            seen_players = [i.player_minecraft_nick for i in Config.get_server_config().seen_players]
            seen_players.extend(server_players)
            seen_players = set(seen_players)
            for mc_nick in seen_players:
                if search(rf"@{mc_nick}", message.content):
                    nicks.append(mc_nick)
        nicks = set(nicks)
        # Remove nicks' mentions from author of the initial message
        if message.author.id in [i.user_discord_id for i in Config.get_known_users_list()]:
            for nick in [i.user_minecraft_nick for i in Config.get_known_users_list()
                         if i.user_discord_id == message.author.id]:
                if nick in nicks:
                    nicks.remove(nick)
        # Check if players online
        nicks = [i for i in nicks if i in server_players]
    return set(nicks)


def _build_nickname_tellraw_for_minecraft_player(
        server_version: 'ServerVersion',
        nick: str,
        content_name: str,
        default_text_color: str = None,
        left_bracket: str = "<",
        right_bracket: str = "> "
):
    tellraw_obj = [{"text": left_bracket}]
    if server_version.minor > 7 and len(nick.split()) == 1 and nick in get_server_players().get("players"):
        tellraw_obj += [{"selector": f"@p[name={nick}]"}]
    elif server_version.minor > 7:
        if "☠ " in nick and \
                check_if_string_in_all_translations(translate_text="☠ Obituary ☠", match_text=nick):
            entity = get_translation("Entity")
        else:
            entity = get_translation("Player")
        hover_string = f"{nick}\n" + get_translation("Type: {0}").format(entity) + f"\n{Config.get_offline_uuid(nick)}"
        tellraw_obj += [{
            "text": nick,
            "clickEvent": {"action": "suggest_command", "value": f"/tell {nick} "},
            "hoverEvent": {"action": "show_text", content_name: hover_string}
        }]
    else:
        tellraw_obj += [{
            "text": nick,
            "clickEvent": {"action": "suggest_command", "value": f"/tell {nick} "},
            "hoverEvent": {"action": "show_text", content_name: f"{nick}\n{Config.get_offline_uuid(nick)}"}
        }]
    tellraw_obj += [{"text": right_bracket}]
    if default_text_color is not None:
        for i in range(len(tellraw_obj)):
            tellraw_obj[i]["color"] = default_text_color
    return tellraw_obj


def _build_nickname_tellraw_for_discord_member(
        server_version: 'ServerVersion',
        author: Member,
        content_name: str,
        brackets_color: str = None,
        left_bracket: str = "<",
        right_bracket: str = "> "
):
    hover_string = ["", {"text": f"{author.display_name}\n"
                                 f"{author.name}#{author.discriminator}"}]
    if server_version.minor > 11:
        hover_string += [{"text": "\nShift + "}, {"keybind": "key.attack"}]
    tellraw_obj = [
        {"text": left_bracket},
        {"text": author.display_name,
         "color": "dark_gray",
         "hoverEvent": {"action": "show_text", content_name: hover_string}},
        {"text": right_bracket}
    ]
    if server_version.minor > 7:
        tellraw_obj[-2].update({"insertion": f"@{author.display_name}"})
    if brackets_color is not None:
        for i in range(len(tellraw_obj)):
            if len(tellraw_obj[i].keys()) == 1:
                tellraw_obj[i]["color"] = brackets_color
    return tellraw_obj


def build_nickname_tellraw_for_bot(
        server_version: 'ServerVersion',
        nick: str,
        left_bracket: str = "<",
        right_bracket: str = "> "
) -> List[Dict[str, str]]:
    content_name = "contents" if server_version.minor >= 16 else "value"
    tellraw_obj = [{"text": left_bracket}]
    if server_version.minor > 7:
        hover_string = f"{nick}\n" + get_translation("Type: {0}").format(get_translation("Entity")) + \
                       f"\n{Config.get_offline_uuid(nick)}"
        tellraw_obj += [{
            "text": nick,
            "color": "dark_gray",
            "hoverEvent": {"action": "show_text", content_name: hover_string}
        }]
    else:
        tellraw_obj += [{
            "text": nick,
            "color": "dark_gray",
            "hoverEvent": {"action": "show_text", content_name: f"{nick}\n{Config.get_offline_uuid(nick)}"}
        }]
    tellraw_obj += [{"text": right_bracket}]
    return tellraw_obj


class UserAgent:
    _header: str = None

    @classmethod
    def _get_os(cls):
        if Config.get_os() == OS.Windows:
            return "Windows NT 10.0; Win64; x64"
        elif Config.get_os() == OS.MacOS:
            separator = choice([".", "_"])
            version = choice([
                separator.join(["10", str(randint(13, 15)), str(randint(0, 10))]),
                f"{randint(11, 13)}{separator}0"
            ])
            return f"Macintosh; Intel Mac OS X {version}"
        else:
            return choice(["X11; Linux", "X11; OpenBSD", "X11; Ubuntu; Linux"]) + \
                   choice([" i386", " i686", " amd64", " x86_64"])

    @classmethod
    def _set_header(cls):
        if randint(0, 1):
            # Chrome
            version = f"{randint(70, 99)}.{randint(0, 99)}.{randint(0, 9999)}.{randint(0, 999)}"
            cls._header = f"Mozilla/5.0 ({cls._get_os()}) AppleWebKit/537.36 " \
                          f"(KHTML, like Gecko) Chrome/{version} Safari/537.36"
        else:
            # Firefox
            version = f"{randint(78, 102)}.0"
            cls._header = f"Mozilla/5.0 ({cls._get_os()}; rv:{version}) Gecko/20100101 Firefox/{version}"

    @classmethod
    def get_header(cls):
        if cls._header is None:
            cls._set_header()
        return cls._header


def rgb2hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def has_transparency(img: Image.Image):
    if img.info.get("transparency", None) is not None:
        return True
    if img.mode == "P":
        transparent = img.info.get("transparency", -1)
        for _, index in img.getcolors():
            if index == transparent:
                return True
    elif img.mode == "RGBA":
        extrema = img.getextrema()
        if extrema[3][0] < 255:
            return True

    return False


def get_image_data(url: str):
    if search(r"https?://tenor\.com/view", url):
        with suppress(Timeout):
            text = req_get(url, timeout=(4, 8), headers={"User-Agent": UserAgent.get_header()}).text
            match = search(rf"property=\"og:image\"\scontent=\"(?P<link>{URL_REGEX})?\"", text)
            url = match.group("link") if match is not None else None

    if url is not None:
        match = search(r"[^/]+/(?P<name>[^/\\&?]+\.\w{3,4})(?:[/?&].*$|$)", url)
        if match is not None:
            filename = match.group("name")
        else:
            filename = url.split("/")[-1].split("?", maxsplit=1)[0]
        with suppress(Timeout):
            return dict(
                bytes=BytesIO(req_get(url, timeout=(4, 8), headers={"User-Agent": UserAgent.get_header()}).content),
                name=filename
            )


def send_image_to_chat(url: str, image_name: str, required_width: int = None, required_height: int = None):
    image_data = get_image_data(url)
    if image_data is None:
        return

    if len(image_name) == 0:
        image_name = image_data["name"] if len(image_data["name"]) else "unknown"
    img = Image.open(image_data["bytes"], "r")

    if required_height is not None and \
            required_height < Config.get_game_chat_settings().image_preview.max_height:
        max_height = required_height
    else:
        max_height = Config.get_game_chat_settings().image_preview.max_height

    if required_width is not None and \
            required_width < Config.get_game_chat_settings().image_preview.max_width:
        calc_width = required_height
    else:
        calc_width = Config.get_game_chat_settings().image_preview.max_width

    calc_height = int(round((img.height * 2) / (img.width / calc_width), 0) / 9)
    if calc_height > max_height:
        calc_width = int((calc_width * max_height) / calc_height)
        calc_height = max_height
    img = img.resize((calc_width if calc_width > 0 else 1, calc_height if calc_height > 0 else 1))

    img_has_transparency = has_transparency(img)
    if img_has_transparency and img.mode != "RGBA":
        img = img.convert("RGBA")
    elif not img_has_transparency and img.mode != "RGB":
        img = img.convert("RGB")

    pixels = img.load()
    width, height = img.size

    storage_unit = "mc_chat"

    with disable_logging(disable_log_admin_commands=True, disable_send_command_feedback=True):
        with suppress(ConnectionError, socket.error):
            with connect_rcon() as cl_r:
                max_number_of_arrays = 0
                for y in range(height):
                    tellraw = [
                        {
                            "text": "",
                            "clickEvent": {"action": "open_url",
                                           "value": url if len(url) < 257 else get_shortened_url(url)},
                            "hoverEvent": {"action": "show_text", "contents": shorten_string(image_name, 250)}
                        }
                    ]
                    array_count = 0
                    tellraw_str_length = len(dumps(tellraw, ensure_ascii=False))
                    for x in range(width):
                        if img_has_transparency:
                            r, g, b, a = pixels[x, y]
                            if a < 20:
                                pixel = {"text": "·", "color": rgb2hex(r, g, b)}
                            elif 20 <= a <= 70:
                                pixel = {"text": ":", "color": rgb2hex(r, g, b)}
                            else:
                                pixel = {"text": "┇", "color": rgb2hex(r, g, b)}
                        else:
                            pixel = {"text": "┇", "color": rgb2hex(*pixels[x, y])}
                        pixel_str = len(dumps(pixel, ensure_ascii=False)) + 2

                        if len(f"data modify storage {storage_unit} {array_count + 1} set value ''") + \
                                tellraw_str_length + pixel_str > MAX_RCON_COMMAND_RUN_STR_LENGTH:
                            array_count += 1
                            cl_r.run(f"data modify storage {storage_unit} {array_count} "
                                     f"set value '{dumps(tellraw, ensure_ascii=False)}'")
                            tellraw = [pixel]
                            tellraw_str_length = pixel_str
                        else:
                            tellraw.append(pixel)
                            tellraw_str_length += pixel_str
                    if len(tellraw) > 0:
                        array_count += 1
                        cl_r.run(f"data modify storage {storage_unit} {array_count} "
                                 f"set value '{dumps(tellraw, ensure_ascii=False)}'")
                    cl_r.tellraw("@a", [
                        {"nbt": str(i), "storage": storage_unit, "interpret": True}
                        for i in range(1, array_count + 1)
                    ])
                    if max_number_of_arrays < array_count + 1:
                        max_number_of_arrays = array_count
                for number in range(1, max_number_of_arrays + 1):
                    cl_r.run(f"data remove storage {storage_unit} {number}")


@contextmanager
def disable_logging(disable_log_admin_commands: bool = False, disable_send_command_feedback: bool = False):
    command_regex = r"(?i)gamerule \w+ is currently set to: (?P<value>\w+)"
    log_admin_commands = True
    send_command_feedback = True
    if disable_log_admin_commands or disable_send_command_feedback:
        with suppress(ConnectionError, socket.error):
            with connect_rcon() as cl_r:
                if disable_log_admin_commands:
                    match = search(command_regex, cl_r.run("gamerule logAdminCommands"))
                    if match is not None:
                        log_admin_commands = not (match.group("value") == "false")
                        if log_admin_commands:
                            cl_r.run("gamerule logAdminCommands false")
                if disable_send_command_feedback:
                    match = search(command_regex, cl_r.run("gamerule sendCommandFeedback"))
                    if match is not None:
                        send_command_feedback = not (match.group("value") == "false")
                        if send_command_feedback:
                            cl_r.run("gamerule sendCommandFeedback false")
    yield
    if disable_log_admin_commands or disable_send_command_feedback:
        with suppress(ConnectionError, socket.error):
            with connect_rcon() as cl_r:
                if send_command_feedback and disable_send_command_feedback:
                    cl_r.run("gamerule sendCommandFeedback true")
                if log_admin_commands and disable_log_admin_commands:
                    cl_r.run("gamerule logAdminCommands true")


class ServerVersion:
    def __init__(self, version_string: str):
        parsed_version = version_string
        snapshot_version = False
        snapshot_regex = r"(?P<version>\d+w\d+[a-e~])"
        snapshot_match = search(snapshot_regex, parsed_version)
        if any(i in parsed_version.lower() for i in ["snapshot", "release"]) or snapshot_match is not None:
            print(get_translation("Minecraft server is not in release state! Proceed with caution!"))
            if "snapshot" in parsed_version.lower():
                parsed_version = parsed_version.lower().split("snapshot")[0]
                snapshot_version = True
            elif "release" in parsed_version.lower():
                parsed_version = parsed_version.lower().split("release")[0]
            elif snapshot_match is not None:
                parsed_version = parse_snapshot(snapshot_match.group("version"))
                if parsed_version is None:
                    parsed_version = ""
                snapshot_version = True
        matches = findall(r"\d+", parsed_version)
        if len(matches) < 2:
            raise ValueError(f"Can't parse server version '{version_string}'!")
        self.major = int(matches[0])
        self.minor = int(matches[1])
        self.patch = int(matches[2]) if len(matches) > 2 else 0
        self.version_string = version_string
        if snapshot_version and self.patch > 0:
            self.patch -= 1
        elif snapshot_version and self.minor > 0 and self.patch == 0:
            self.minor -= 1
            self.patch = 10


def get_server_version() -> ServerVersion:
    with connect_query() as cl_q:
        version = cl_q.full_stats.version
    return ServerVersion(version)


def parse_snapshot(version: str) -> Optional[str]:
    with suppress(Timeout):
        answer = req_get(
            url="https://minecraft.fandom.com/api.php",
            params={
                "action": "parse",
                "page": f"Java Edition {version}",
                "prop": "categories",
                "format": "json"
            },
            timeout=(3, 6),
            headers={"User-Agent": UserAgent.get_header()}
        ).json()
        if answer.get("parse", None) is not None and answer["parse"].get("categories", None) is not None:
            for category in answer["parse"]["categories"]:
                if all(i in category["*"].lower() for i in ["java_edition", "snapshots"]) and \
                        version in category["sortkey"]:
                    return category["*"]


def get_server_players() -> dict:
    """Returns dict, keys: current, max, players"""
    with connect_query() as cl_q:
        info = cl_q.full_stats
    return dict(current=info.num_players, max=info.max_players, players=info.players)


def shorten_string(string: str, max_length: int):
    if len(string) > max_length:
        return f"{string[:max_length - 3].strip(' ')}..."
    else:
        return string


def get_shortened_url(url: str):
    for service_url in ["https://clck.ru/--", "https://tinyurl.com/api-create.php"]:
        with suppress(Timeout):
            response = req_post(
                service_url,
                params={"url": url},
                timeout=(3, 6),
                headers={"User-Agent": UserAgent.get_header()}
            )
            if response.ok and response.text != "":
                return response.text
    print(get_translation("Bot couldn't shorten the URL \"{0}\" using link shortening services.").format(url))
    return url[:256]


@contextmanager
def times(fade_in: Union[int, float], duration: Union[int, float], fade_out: Union[int, float], rcon_client):
    rcon_client.run(f"title @a times {fade_in} {duration} {fade_out}")
    yield
    rcon_client.run("title @a reset")


def announce(player: str, message: str, rcon_client, server_version: ServerVersion, subtitle=False):
    if server_version.minor >= 11 and not subtitle:
        player = player if server_version.minor < 14 else f"'{player}'"
        rcon_client.run(f'title {player} actionbar ' + '{' + f'"text":"{message}"' + ',"bold":true,"color":"gold"}')
    else:
        rcon_client.run(f'title {player} subtitle ' + '{' + f'"text":"{message}"' + ',"color":"gold"}')
        rcon_client.run(f'title {player} title ' + '{"text":""}')
    rcon_client.run(play_sound(player, "minecraft:entity.arrow.hit_player", "player", 1, 0.75))


def play_sound(name: str, sound: str, category="master", volume=1, pitch=1.0):
    return f"execute as {name} at @s run playsound {sound} {category} @s ~ ~ ~ {volume} {pitch} 1"


def play_music(name: str, sound: str):
    return play_sound(name, sound, "music", 99999999999999999999999999999999999999)


def stop_music(sound: str, name="@a"):
    return f"stopsound {name} music {sound}"


def get_number_of_digits(number: int):
    count = 0
    while number > 0:
        number //= 10
        count += 1
    return count


def setup_print_handlers():
    if Config.get_settings().bot_settings.log_bot_messages:
        file = open(Config.get_bot_log_name(), "a", encoding="utf8")
    else:
        file = None
    Output_file_handler(file)
    if file is not None:
        Error_file_handler(file)


class Output_file_handler:
    def __init__(self, file=None):
        self.file = file
        self.stdout = sys.stdout
        sys.stdout = self

    def __del__(self):
        sys.stdout = self.stdout
        if self.file is not None:
            self.file.close()

    def write(self, data, **kwargs):
        if data != "\n":
            if self.file is not None:
                self.file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                f"{ANSI_ESCAPE.sub('', data)}")
            self.stdout.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {data}")
        else:
            if self.file is not None:
                self.file.write(data)
            self.stdout.write(data)
        self.flush()
        if kwargs.pop('flush', False):
            self.stdout.flush()

    def flush(self):
        if self.file is not None:
            self.file.flush()


class Error_file_handler:
    def __init__(self, file=None):
        self.file = file
        self.stderr = sys.stderr
        sys.stderr = self

    def __del__(self):
        sys.stderr = self.stderr
        if self.file is not None:
            self.file.close()

    def write(self, data, **kwargs):
        if self.file is not None:
            self.file.write(data)
        self.stderr.write(data)
        self.flush()
        if kwargs.pop('flush', False):
            self.stderr.flush()

    def flush(self):
        if self.file is not None:
            self.file.flush()


if len(argv) > 1 and argv[1] == "-g":
    from components.localization import RuntimeTextHandler

    entities = [
        'Area Effect Cloud', 'Arrow', 'Axolotl', 'Bee', 'Blaze', 'Cave Spider', 'Creeper', 'Drowned', 'Elder Guardian',
        'End Crystal', 'Ender Dragon', 'Enderman', 'Endermite', 'Evoker', 'Frog', 'Ghast', 'Giant', 'Goat', 'Guardian',
        'Hoglin', 'Husk', 'Ravager', 'Illusioner', 'The Killer Bunny', 'Lightning Bolt', 'Llama', 'Magma Cube',
        'Ocelot', 'Panda', 'Phantom', 'Piglin', 'Piglin Brute', 'Pillager', 'Polar Bear', 'Pufferfish', 'Shulker',
        'Silverfish', 'Skeleton', 'Slime', 'Snowball', 'Snow Golem', 'Spectral Arrow', 'Spider', 'Stray', 'Strider',
        'Trader Llama', 'Vex', 'Butcher', 'Cartographer', 'Cleric', 'Farmer', 'Fisherman', 'Fletcher', 'Leatherworker',
        'Librarian', 'Mason', 'Nitwit', 'Shepherd', 'Toolsmith', 'Weaponsmith', 'Villager', 'Iron Golem', 'Vindicator',
        'Warden', 'Witch', 'Wither', 'Wither Skeleton', 'Wolf', 'Zoglin', 'Zombie', 'Zombified Piglin',
        'Zombie Villager', '[Intentional Game Design]', 'Zombie Pigman'
    ]

    for un in UNITS:
        RuntimeTextHandler.add_translation(un)
    for msg in DEATH_MESSAGES:
        RuntimeTextHandler.add_translation(msg)
    for entity in entities:
        RuntimeTextHandler.add_translation(entity)
