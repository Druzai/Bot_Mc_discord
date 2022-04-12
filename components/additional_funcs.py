import inspect
import socket
import sys
import typing
from asyncio import sleep as asleep, Task, CancelledError
from contextlib import contextmanager, suppress, asynccontextmanager
from datetime import datetime, timedelta
from hashlib import md5
from itertools import chain
from json import load, dump, dumps, JSONDecodeError
from os import chdir, system, walk, mkdir, remove
from os.path import basename, join as p_join, getsize, isfile
from pathlib import Path
from random import randint
from re import search, split, findall, sub, compile
from shutil import rmtree
from sys import platform, argv
from textwrap import wrap
from threading import Thread, Event
from time import sleep
from traceback import print_exception
from typing import Tuple, List, Optional
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED, ZIP_BZIP2, ZIP_LZMA

from discord import (
    Activity, ActivityType, Message, Status, Member, Role, MessageType, NotFound, HTTPException, Forbidden, Emoji,
    ChannelType
)
from discord.ext import commands
from discord.utils import get as utils_get
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r, WrongPassword
from psutil import process_iter, NoSuchProcess, disk_usage, Process
from requests import post as req_post, get as req_get

from commands.poll import Poll
from components.decorators import MissingAdminPermissions
from components.localization import get_translation
from components.rss_feed_handle import create_feed_webhook
from components.watcher_handle import create_watcher, create_chat_webhook
from config.init_config import Config, BotVars, ServerProperties

if platform == "win32":
    from os import startfile

UNITS = ("B", "KB", "MB", "GB", "TB", "PB")
DISCORD_SYMBOLS_IN_MESSAGE_LIMIT = 2000
MAX_RCON_COMMAND_STR_LENGTH = 1446
MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH = MAX_RCON_COMMAND_STR_LENGTH - 9 - 2

if len(argv) > 1 and argv[1] == "-g":
    from components.localization import RuntimeTextHandler

    for un in UNITS:
        RuntimeTextHandler.add_translation(un)


async def send_msg(ctx, msg: str, is_reaction=False):
    if is_reaction:
        await ctx.send(content=msg,
                       delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
    else:
        await ctx.send(msg)


def add_quotes(msg: str) -> str:
    return f"```{msg}```"


async def delete_after_by_msg(message, ctx=None, without_delay=False):
    if isinstance(message, Message):
        await message.delete(
            delay=Config.get_timeouts_settings().await_seconds_before_message_deletion if not without_delay else None)
    elif isinstance(message, int):
        await (await ctx.channel.fetch_message(message)).delete(
            delay=Config.get_timeouts_settings().await_seconds_before_message_deletion if not without_delay else None)


def get_author_and_mention(ctx, bot: commands.Bot, is_reaction=False):
    if is_reaction:
        author_mention = BotVars.react_auth.mention
        author = BotVars.react_auth
    else:
        if hasattr(ctx, 'author'):
            author_mention = ctx.author.mention
            author = ctx.author
        else:
            author_mention = bot.user.mention
            author = bot.user
    return author, author_mention


async def send_status(ctx, is_reaction=False):
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


async def start_server(ctx, bot: commands.Bot, backups_thread=None, shut_up=False, is_reaction=False):
    BotVars.is_loading = True
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
    print(get_translation("Loading server by request of {0}").format(author))
    if ctx and not shut_up:
        await send_msg(ctx, add_quotes(get_translation("Loading server.......\nPlease wait)")), is_reaction)
    chdir(Config.get_selected_server_from_list().working_directory)
    try:
        if not isfile(Config.get_selected_server_from_list().start_file_name):
            raise FileNotFoundError()
        if platform == "linux" or platform == "linux2":
            if ".sh" not in Config.get_selected_server_from_list().start_file_name:
                raise NameError()
            code = system(f"screen -dmS {Config.get_selected_server_from_list().server_name.replace(' ', '_')} "
                          f"./{Config.get_selected_server_from_list().start_file_name}")
            if code != 0:
                raise ReferenceError()
        elif platform == "win32":
            is_file_exists = False
            for ext in [".bat", ".cmd", ".lnk"]:
                if ext in Config.get_selected_server_from_list().start_file_name:
                    is_file_exists = True
                    break
            if not is_file_exists:
                raise NameError()
            startfile(Config.get_selected_server_from_list().start_file_name)
    except (NameError, ValueError, FileNotFoundError, ReferenceError) as ex:
        chdir(Config.get_bot_config_path())
        if ex.__class__ is not ReferenceError:
            print(get_translation("Couldn't open script! Check naming and extension of the script!"))
            await send_msg(ctx, add_quotes(get_translation("Couldn't open script because of naming! Retreating...")),
                           is_reaction)
        else:
            print(get_translation("Couldn't open script because there is no command 'screen'! "
                                  "Install it via packet manager!"))
            await send_msg(ctx, add_quotes(get_translation("Couldn't open script because command 'screen' "
                                                           "wasn't installed! Retreating...")), is_reaction)
        BotVars.is_loading = False
        if BotVars.is_restarting:
            BotVars.is_restarting = False
        return
    chdir(Config.get_bot_config_path())
    check_time = datetime.now()
    last_change_presence = datetime.now() - timedelta(seconds=4)
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
        if (datetime.now() - last_change_presence).seconds >= 4:
            if Config.get_selected_server_from_list().server_loading_time:
                percentage = round((timedelta_secs / Config.get_selected_server_from_list().server_loading_time) * 100)
                output_bot = get_translation("Loading: ") + ((str(percentage) + "%") if percentage < 101 else "100%...")
            else:
                output_bot = get_translation("{0}, elapsed time: ") \
                                 .format(Config.get_settings().bot_settings.idle_status) \
                             + get_time_string(timedelta_secs, True)
            await bot.change_presence(activity=Activity(type=ActivityType.listening, name=output_bot))
            last_change_presence = datetime.now()
        await asleep(Config.get_timeouts_settings().await_seconds_when_connecting_via_rcon)
        with suppress(ConnectionError, socket.error):
            with connect_query() as cl_q:
                _ = cl_q.basic_stats
            break
    if (Config.get_cross_platform_chat_settings().enable_cross_platform_chat and
        Config.get_cross_platform_chat_settings().channel_id and
        Config.get_cross_platform_chat_settings().webhook_url) or Config.get_secure_auth().enable_secure_auth:
        create_watcher()
        BotVars.watcher_of_log_file.start()
    if Config.get_selected_server_from_list().server_loading_time:
        Config.get_selected_server_from_list().server_loading_time = \
            (Config.get_selected_server_from_list().server_loading_time + (datetime.now() - check_time).seconds) // 2
    else:
        Config.get_selected_server_from_list().server_loading_time = (datetime.now() - check_time).seconds
    Config.save_config()
    print(get_translation("Server on!"))
    if ctx and not shut_up:
        await send_msg(ctx, author_mention + "\n" + add_quotes(get_translation("Server's on now")), is_reaction)
        if randint(0, 8) == 0:
            await send_msg(ctx, get_translation("Kept you waiting, huh?"), is_reaction)
    if backups_thread is not None:
        backups_thread.skip()
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


async def stop_server(ctx, bot: commands.Bot, poll: Poll,
                      how_many_sec=10, is_restart=False, shut_up=False, is_reaction=False):
    no_connection = False
    players_info = None

    if "stop" in [p.command for p in poll.get_polls().values()]:
        if not is_reaction:
            await delete_after_by_msg(ctx.message)
        if not shut_up:
            await ctx.send(get_translation("{0}, bot already has poll on `stop`/`restart` command!")
                           .format(ctx.author.mention),
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

    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
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
                if not await poll.run(ctx=ctx,
                                      message=get_translation("this man {0} trying to stop the server with {1} "
                                                              "player(s) on it. Will you let that happen?")
                                              .format(get_author_and_mention(ctx, bot, is_reaction)[1],
                                                      players_info["current"]),
                                      command="stop",
                                      needed_role=Config.get_settings().bot_settings.managing_commands_role_id,
                                      remove_logs_after=5):
                    return
            elif not logged_only_author_accounts:
                await delete_after_by_msg(ctx.message)
        elif players_info["current"] == 0:
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
                        tellraw_init = ["", {"text": "<"}, {"text": get_bot_display_name(bot), "color": "dark_gray"},
                                        {"text": "> "}]
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
        while True:
            await asleep(Config.get_timeouts_settings().await_seconds_when_connecting_via_rcon)
            try:
                with connect_query() as cl_q:
                    _ = cl_q.basic_stats
            except (ConnectionError, socket.error):
                break
    else:
        print(get_translation("Bot Exception: Couldn't connect to server, so killing it now..."))
        if not shut_up:
            await send_msg(ctx,
                           add_quotes(get_translation("Couldn't connect to server to shut it down! Killing it now...")),
                           is_reaction)
    kill_server()
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

    basename_of_executable = basename(argv[0])
    process_name = "java"
    list_proc = []

    for proc in process_iter():
        with suppress(NoSuchProcess):
            parents_name_list = [i.name() for i in proc.parents()]
            if process_name in proc.name() and ("screen" in parents_name_list or
                                                basename_of_executable in parents_name_list or
                                                "python.exe" in parents_name_list) \
                    and Config.get_selected_server_from_list().working_directory == proc.cwd():
                list_proc.append(proc)
    BotVars.java_processes = list_proc
    return list_proc


def kill_server():
    list_proc = get_list_of_processes()
    if len(list_proc) != 0:
        for p in list_proc:
            with suppress(NoSuchProcess):
                p.kill()


def get_bot_display_name(bot: commands.Bot):
    for member in bot.guilds[0].members:
        if member.id == bot.user.id:
            return member.display_name
    return bot.user.display_name


async def get_member_name(bot: commands.Bot, id: int):
    member = bot.guilds[0].get_member(id)
    if member is not None:
        member = f"{member.display_name}#{member.discriminator}"
    else:
        try:
            member = await bot.guilds[0].fetch_member(id)
            member = f"{member.display_name}#{member.discriminator}"
        except (HTTPException, Forbidden):
            try:
                user = await bot.fetch_user(id)
                member = f"{user.name}#{user.discriminator}"
            except (HTTPException, NotFound):
                member = "invalid-user"
    return member


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
                        if not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting:
                            break

                players_count = 0
                if BotVars.is_server_on:
                    with suppress(ConnectionError, socket.error):
                        players_count = get_server_players().get("current")
                    if players_count != 0:
                        if BotVars.is_auto_backup_disable:
                            BotVars.is_auto_backup_disable = False

                if not BotVars.is_auto_backup_disable:
                    print(get_translation("Starting auto backup"))
                    handle_backups_limit_and_size(self._bot, auto_backups=True)

                    # Creating auto backup
                    file_name = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
                    next(create_zip_archive(self._bot, file_name,
                                            Path(Config.get_selected_server_from_list().working_directory,
                                                 Config.get_backups_settings().name_of_the_backups_folder).as_posix(),
                                            Path(Config.get_selected_server_from_list().working_directory,
                                                 ServerProperties().level_name).as_posix(),
                                            Config.get_backups_settings().compression_method), None)
                    Config.add_backup_info(file_name=file_name)
                    Config.save_server_config()
                    print(get_translation("Backup completed!"))

                if BotVars.is_server_on and players_count == 0:
                    if not BotVars.is_auto_backup_disable:
                        BotVars.is_auto_backup_disable = True

                if not BotVars.is_server_on:
                    if not BotVars.is_auto_backup_disable:
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


def create_zip_archive(bot: commands.Bot, zip_name: str, zip_path: str, dir_path: str, compression,
                       forced=False, user=None):
    """
    recursively .zip a directory
    """
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
    total = 0
    dt = datetime.now()
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
            tellraw_init = ["", {"text": "<"}, {"text": get_bot_display_name(bot), "color": "dark_gray"},
                            {"text": "> "}]
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
                        cl_r.say(get_translation("Starting backup triggered by {0} in 3 seconds...") \
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
                    timedelta_secs = (datetime.now() - dt).seconds
                    if timedelta_secs % 4 == 0:
                        percent = round(100 * current / total)
                        yield add_quotes(f"diff\n{percent}% {get_time_string(timedelta_secs, True)} '{afn}'\n"
                                         f"- |{'█' * (percent // 5)}{' ' * (20 - percent // 5)}|")
                tries = 0
                while tries < 3:
                    with suppress(PermissionError):
                        with open(fn, mode="rb") as f:
                            f.read(1)
                        z.write(fn, arcname=afn)
                        break
                    tries += 1
                    sleep(1)
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
                if server_version.patch < 7:
                    cl_r.say(get_translation("Backup completed!"))
                else:
                    cl_r.tellraw("@a", tellraw_init + [{"text": get_translation("Backup completed!"),
                                                        "color": "dark_green"}])
    BotVars.is_backing_up = False


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
                member = bot.guilds[0].get_member(backup.initiator)
                if member is not None:
                    member = f"{member.display_name}#{member.discriminator}"
                else:
                    member = "invalid-user"
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
                cl_r.tellraw("@a", ["", {"text": "<"}, {"text": get_bot_display_name(bot), "color": "dark_gray"},
                                    {"text": "> "}, {"text": msg, "color": "red"}])
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


def get_human_readable_size(size, stop_unit=None, round=False):
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


async def warn_about_auto_backups(ctx, bot: commands.Bot):
    if Config.get_backups_settings().automatic_backup:
        if len(Config.get_server_config().backups) > 0 \
                and handle_backups_limit_and_size(bot) is not None \
                and all([b.initiator for b in Config.get_server_config().backups]):
            await ctx.send(get_translation("Bot has backups only from members for '{0}' server, "
                                           "so keep in mind, that bot will delete oldest backup "
                                           "on next auto backup!")
                           .format(Config.get_selected_server_from_list().server_name))


def get_half_members_count_with_role(bot: commands.Bot, role: int):
    count = 0
    for m in bot.guilds[0].members:
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


async def server_checkups(bot: commands.Bot, backups_thread: BackupsThread, poll):
    try:
        info = get_server_players()
        if info.get("current") != 0:
            to_save = False
            for player in info.get("players"):
                if player not in [i.player_minecraft_nick for i in Config.get_server_config().seen_players]:
                    Config.add_to_seen_players_list(player)
                    to_save = True
            if to_save:
                Config.save_server_config()
            if BotVars.is_auto_backup_disable:
                BotVars.is_auto_backup_disable = False
        if not BotVars.is_server_on:
            BotVars.is_server_on = True
        if (BotVars.watcher_of_log_file is None or not BotVars.watcher_of_log_file.is_running()) and \
                ((Config.get_cross_platform_chat_settings().enable_cross_platform_chat and
                  Config.get_cross_platform_chat_settings().channel_id and
                  Config.get_cross_platform_chat_settings().webhook_url) or
                 Config.get_secure_auth().enable_secure_auth):
            if BotVars.watcher_of_log_file is None:
                create_watcher()
            BotVars.watcher_of_log_file.start()
        if not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting:
            task = bot.loop.create_task(bot.change_presence(
                activity=Activity(type=ActivityType.playing,
                                  name=Config.get_settings().bot_settings.gaming_status
                                       + ", " + str(info.get("current")) + get_translation(" player(s) online"))))
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
                                   msg=add_quotes(get_translation("Bot detected: Server is idle for "
                                                                  "{0} without players!\n"
                                                                  "Time: {1}\n"
                                                                  "Shutting down server now!")
                                                  .format(get_time_string(Config.get_timeouts_settings()
                                                                          .calc_before_shutdown),
                                                          datetime.now()
                                                          .strftime(get_translation("%H:%M:%S %d/%m/%Y")))),
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
                           msg=add_quotes(get_translation("Bot detected: Server's offline!\n"
                                                          "Time: {0}\n"
                                                          "Starting up server again!")
                                          .format(datetime.now().strftime(get_translation("%H:%M:%S %d/%m/%Y")))),
                           is_reaction=True)
            await start_server(ctx=channel, bot=bot, backups_thread=backups_thread, shut_up=True)
    if Config.get_secure_auth().enable_secure_auth:
        check_if_ips_expired()
    if Config.get_timeouts_settings().await_seconds_in_check_ups > 0:
        await asleep(Config.get_timeouts_settings().await_seconds_in_check_ups)


async def bot_status(ctx, bot: commands.Bot, is_reaction=False):
    states = ""
    bot_message = ""
    states_info = Config.get_server_config().states
    if states_info.started_info.date is not None and states_info.started_info.user is not None:
        if not states_info.started_info.bot:
            states += get_translation("Server has been started at {0} by member {1}") \
                          .format(states_info.started_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y")),
                                  await get_member_name(bot, states_info.started_info.user)) + "\n"
        else:
            states += get_translation("Server has started at {0}") \
                          .format(states_info.started_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))) + "\n"
    if states_info.stopped_info.date is not None and states_info.stopped_info.user is not None:
        if not states_info.stopped_info.bot:
            states += get_translation("Server has been stopped at {0} by member {1}") \
                          .format(states_info.stopped_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y")),
                                  await get_member_name(bot, states_info.stopped_info.user)) + "\n"
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
    if BotVars.is_server_on:
        try:
            server_version = get_server_version()
            bot_message = get_translation("server online").capitalize() + "\n" + bot_message
            if server_version.minor > 7:
                # Rcon check daytime cycle
                with connect_rcon() as cl_r:
                    time_ticks = int(cl_r.run("time query daytime").split(" ")[-1])
                message = get_translation("Time in Minecraft: ")
                if 450 <= time_ticks <= 11616:
                    message += get_translation("Day, ")
                elif 11617 <= time_ticks <= 13800:
                    message += get_translation("Sunset, ")
                elif 13801 <= time_ticks <= 22550:
                    message += get_translation("Night, ")
                else:
                    message += get_translation("Sunrise, ")
                message += str((6 + time_ticks // 1000) % 24) + ":" + f"{((time_ticks % 1000) * 60 // 1000):02d}\n"
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
        bot_message = get_translation("server offline").capitalize() + "\n" + bot_message
        bot_message += server_info + states
        await send_msg(ctx, add_quotes(bot_message), is_reaction)


async def bot_list(ctx, bot: commands.Bot, is_reaction=False):
    try:
        info = get_server_players()
        if info.get("current") == 0:
            await send_msg(ctx, add_quotes(get_translation("There are no players on the server")), is_reaction)
        else:
            players_dict = {p: None for p in info.get("players")}
            if Config.get_secure_auth().enable_secure_auth:
                for player in Config.get_auth_users():
                    if player.nick in players_dict.keys() and player.logged:
                        non_expired_ips = [ip.expires_on_date for ip in player.ip_addresses
                                           if ip.expires_on_date is not None and datetime.now() < ip.expires_on_date]
                        if len(non_expired_ips) > 0:
                            players_dict[player.nick] = max(non_expired_ips) - \
                                                        timedelta(days=Config.get_secure_auth().days_before_ip_expires)
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


async def bot_start(ctx, bot: commands.Bot, backups_thread, is_reaction=False):
    if not BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and \
            not BotVars.is_backing_up and not BotVars.is_restoring:
        await start_server(ctx, bot=bot, backups_thread=backups_thread, is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_stop(ctx, command, bot: commands.Bot, poll: Poll, is_reaction=False):
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


async def bot_restart(ctx, command, bot: commands.Bot, poll: Poll, backups_thread: BackupsThread, is_reaction=False):
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


async def bot_clear(ctx, poll: Poll, subcommand: str = None, count: int = None, discord_mentions=None):
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
            if delete_limit == 0 or len(await ctx.channel.history(limit=lim).flatten()) <= delete_limit:
                await ctx.channel.purge(limit=1, bulk=False)
                await ctx.channel.purge(limit=count, check=check_condition, bulk=False)
                return
        elif count < 0:
            message_created = (await ctx.channel.history(limit=-count, oldest_first=True).flatten())[-1]
            if delete_limit == 0 or len(await ctx.channel.history(limit=delete_limit + 1, after=message_created,
                                                                  oldest_first=True).flatten()) <= delete_limit:
                await ctx.channel.purge(limit=None, check=check_condition, after=message_created, bulk=False)
                return
        else:
            await send_msg(ctx, get_translation("Nothing's done!"), True)
            return
    elif subcommand == "all":
        if delete_limit == 0 or len(await ctx.channel.history(limit=delete_limit + 1).flatten()) <= delete_limit:
            await ctx.channel.purge(limit=1, bulk=False)
            await ctx.channel.purge(limit=None, check=check_condition, bulk=False)
            return
    elif subcommand == "reply":
        message_created = ctx.message.reference.resolved
        if delete_limit == 0 or len(await ctx.channel.history(limit=delete_limit + 1, after=message_created,
                                                              oldest_first=True).flatten()) <= delete_limit:
            await ctx.channel.purge(limit=None, check=check_condition, after=message_created, bulk=False)
            return
    if await poll.timer(ctx, 5, "clear"):
        if ctx.channel in [p.ctx.channel for p in poll.get_polls().values() if p.command == "clear"]:
            await delete_after_by_msg(ctx.message)
            await ctx.send(get_translation("{0}, bot already has poll on `clear` command for this channel!")
                           .format(ctx.author.mention),
                           delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
            return
        if await poll.run(ctx=ctx,
                          message=get_translation("this man {0} trying to delete some history"
                                                  " of this channel. Will you let that happen?")
                                  .format(ctx.author.mention),
                          command="clear",
                          remove_logs_after=5):
            if subcommand == "all" or subcommand == "reply" or count < 0:
                await ctx.channel.purge(limit=None, check=check_condition, after=message_created, bulk=False)
            else:
                await ctx.channel.purge(limit=1, bulk=False)
                await ctx.channel.purge(limit=count, check=check_condition, bulk=False)
    else:
        await delete_after_by_msg(ctx.message)


async def bot_dm_clear(ctx, bot: commands.Bot, subcommand: str = None, count: int = None):
    message_created = None
    if count is not None:
        count += 1
    if subcommand is None:
        if count < 0:
            message_created = (await ctx.channel.history(limit=-count, oldest_first=True).flatten())[-1]
        elif count == 0:
            await send_msg(ctx, get_translation("Nothing's done!"), True)
            return
    elif subcommand == "reply":
        message_created = ctx.message.reference.resolved

    async for msg in ctx.channel.history(limit=count, after=message_created):
        if msg.author == bot.user and msg.type == MessageType.default:
            await msg.delete()


async def bot_backup(ctx, bot: commands.Bot, is_reaction=False):
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
            bot_message += "\n" + get_translation("Initiator: ") + await get_member_name(bot, backup.initiator)
        if backup.restored_from:
            bot_message += "\n\t" + get_translation("The world of the server was restored from this backup")
    await send_msg(ctx, add_quotes(bot_message), is_reaction)


async def bot_associate(ctx, bot: commands.Bot, discord_mention: Member, assoc_command: str, minecraft_nick: str):
    need_to_save = False

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
    elif assoc_command == "del":
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


async def bot_associate_info(ctx, for_me: bool, show: str = None):
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


def parse_params_for_help(command_params: dict, string_to_add: str, create_params_dict=False) -> Tuple[str, dict]:
    params = {}
    converter = False
    for arg_name, arg_data in command_params.items():
        if arg_data.annotation != inspect._empty and hasattr(arg_data.annotation, 'converter') \
                and isinstance(arg_data.annotation.converter, typing._GenericAlias):
            converter = True
        if create_params_dict:
            if arg_data.annotation != inspect._empty:
                if not getattr(arg_data.annotation, '__name__', None) is None:
                    params[arg_name] = getattr(arg_data.annotation, '__name__', None)
                elif hasattr(arg_data.annotation, 'converter'):
                    params[arg_name] = sub(r"\w*?\.", "", str(arg_data.annotation.converter))
                    if not isinstance(arg_data.annotation.converter, typing._GenericAlias):
                        params[arg_name] = params[arg_name].strip("<>").lstrip("class").strip("' ")
                else:
                    params[arg_name] = sub(r"\w*?\.", "", str(arg_data.annotation))
            elif arg_data.annotation == inspect._empty and arg_data.default != inspect._empty:
                params[arg_name] = type(arg_data.default).__name__
            else:
                params[arg_name] = "Any"

        if arg_data.default != inspect._empty or arg_data.kind == arg_data.VAR_POSITIONAL:
            add_data = ""
            if bool(arg_data.default) and arg_data.kind != arg_data.VAR_POSITIONAL:
                add_data = f"'{arg_data.default}'" if isinstance(arg_data.default, str) else str(
                    arg_data.default)
            string_to_add += f" [{arg_name}" + (f" = {add_data}" if add_data else "") + \
                             ("..." if arg_data.kind == arg_data.VAR_POSITIONAL or converter else "") + "]"
        else:
            string_to_add += f" <{arg_name}>"
    return string_to_add, params


def create_webhooks():
    if Config.get_rss_feed_settings().enable_rss_feed:
        create_feed_webhook()
    if Config.get_cross_platform_chat_settings().enable_cross_platform_chat:
        create_chat_webhook()


def check_if_ips_expired():
    removed = True
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


def parse_subcommands_for_help(command, all_params=False) -> Tuple[List[str], List[str]]:
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


async def send_help_of_command(ctx, command):
    subcommands_names, subcommands = parse_subcommands_for_help(command, True)
    str_help = f"{Config.get_settings().bot_settings.prefix}{command}"
    str_help += " " + " | ".join(subcommands_names) if len(subcommands_names) else ""
    str_params, params = parse_params_for_help(command.clean_params, "", True)
    if len(str_params):
        str_help += " |" + str_params if len(subcommands_names) else str_params

    str_help += "\n\n" + get_translation("Description") + ":\n"
    str_help += get_translation(f'help_{str(command).replace(" ", "_")}') \
                    .format(prefix=Config.get_settings().bot_settings.prefix) + "\n\n"
    if len(command.aliases):
        str_help += get_translation("Aliases") + ": " + ", ".join(command.aliases) + "\n\n"

    if len(subcommands):
        str_help += get_translation("Subcommands") + ":\n" + "\n".join(subcommands) + "\n\n"

    if len(params.keys()):
        str_help += get_translation("Parameters") + ":\n"
        for arg_name, arg_type in params.items():
            str_help += f"{arg_name}: {arg_type}\n" + \
                        get_translation(f'help_{str(command).replace(" ", "_")}_{arg_name}') \
                            .format(prefix=Config.get_settings().bot_settings.prefix,
                                    code_length=Config.get_secure_auth().code_length) + "\n\n"
    await ctx.send(add_quotes(f"\n{str_help}"))


def find_subcommand(subcommands, command, pos: int):
    if hasattr(command, "all_commands") and len(command.all_commands) != 0:
        pos += 1
        for subcomm_name, subcomm in command.all_commands.items():
            if subcomm_name == subcommands[pos]:
                if len(subcommands) == pos + 1:
                    return subcomm
                else:
                    return find_subcommand(subcommands, subcomm, pos)


def make_underscored_line(line):
    """This func underscores int, float or strings without spaces!"""
    underscore = "\u0332"
    if isinstance(line, int) or isinstance(line, float):
        return underscore + underscore.join(str(line))
    elif isinstance(line, str):
        return underscore.join(line) + underscore


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
async def handle_rcon_error(ctx):
    try:
        yield
    except (ConnectionError, socket.error):
        if BotVars.is_server_on:
            await ctx.send(add_quotes(get_translation("Couldn't connect to server, try again(")))
        else:
            await ctx.send(add_quotes(get_translation("server offline").capitalize()))


def get_offline_uuid(username):
    data = bytearray(md5(("OfflinePlayer:" + username).encode()).digest())
    data[6] &= 0x0f  # clear version
    data[6] |= 0x30  # set to version 3
    data[8] &= 0x3f  # clear variant
    data[8] |= 0x80  # set to IETF variant
    uuid = data.hex()
    return "-".join((uuid[:8], uuid[8:12], uuid[12:16], uuid[16:20], uuid[20:]))


def get_whitelist_entry(username):
    return dict(uuid=get_offline_uuid(username), name=username)


def save_to_whitelist_json(entry: dict):
    whitelist = [entry]
    filepath = Path(Config.get_selected_server_from_list().working_directory + "/whitelist.json")
    if filepath.exists():
        with suppress(JSONDecodeError):
            with open(filepath, "r", encoding="utf8") as file:
                whitelist = load(file)
            whitelist.append(entry)
    with open(filepath, "w", encoding="utf8") as file:
        dump(whitelist, file, indent=2)


def check_and_delete_from_whitelist_json(username: str):
    filepath = Path(Config.get_selected_server_from_list().working_directory + "/whitelist.json")
    is_entry_deleted = False
    if filepath.exists():
        with suppress(JSONDecodeError):
            with open(filepath, "r", encoding="utf8") as file:
                whitelist = load(file)
        for entry in range(len(whitelist)):
            if whitelist[entry]["name"] == username:
                whitelist.remove(whitelist[entry])
                is_entry_deleted = True
        if is_entry_deleted:
            with open(filepath, "w", encoding="utf8") as file:
                dump(whitelist, file, indent=2)
    return is_entry_deleted


# Handling errors
async def send_error(ctx, bot: commands.Bot, error, is_reaction=False):
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
    if isinstance(error, commands.MissingRequiredArgument):
        print(get_translation("{0} didn't input the argument").format(author))
        await send_msg(ctx, f"{author_mention}\n" + add_quotes(get_translation("enter all arguments").capitalize()),
                       is_reaction)
    elif isinstance(error, commands.MissingPermissions):
        print(get_translation("{0} don't have some permissions to run command").format(author))
        missing_perms = [get_translation(perm.replace('_', ' ')
                                         .replace('guild', 'server').title()) for perm in error.missing_perms]
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("to run this command you don't have these permissions:")
                                  .capitalize() + "\n- " + "\n- ".join(missing_perms)),
                       is_reaction)
    elif isinstance(error, commands.BotMissingPermissions):
        print(get_translation("Bot doesn't have some permissions"))
        missing_perms = [get_translation(perm.replace('_', ' ')
                                         .replace('guild', 'server').title()) for perm in error.missing_perms]
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("to run this command bot don't have these permissions:")
                                  .capitalize() + "\n- " + "\n- ".join(missing_perms)),
                       is_reaction)
    elif isinstance(error, commands.MissingRole):
        if isinstance(error.missing_role, int):
            role = bot.guilds[0].get_role(error.missing_role)
            if role is None:
                role = "@deleted-role"
            else:
                role = role.name
        else:
            role = error.missing_role
        print(get_translation("{0} don't have role '{1}' to run command").format(author, role))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("you don't have role '{0}' to run this command").capitalize()
                                  .format(role)),
                       is_reaction)
    elif isinstance(error, commands.CommandNotFound):
        print(get_translation("{0} entered non-existent command").format(author))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("you entered non-existent command").capitalize()),
                       is_reaction)
    elif isinstance(error, commands.UserInputError):
        print(get_translation("{0} entered wrong argument(s) of command").format(author))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("you entered wrong argument(s) of this command").capitalize()),
                       is_reaction)
    elif isinstance(error, commands.DisabledCommand):
        print(get_translation("{0} entered disabled command").format(author))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("you entered disabled command").capitalize()),
                       is_reaction)
    elif isinstance(error, commands.NoPrivateMessage):
        print(get_translation("{0} entered a command that only works in the guild").format(author))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("this command only works on server").capitalize()),
                       is_reaction)
    elif isinstance(error, commands.CommandOnCooldown):
        print(get_translation("{0} triggered a command more than {1} time(s) per {2} sec")
              .format(author, error.cooldown.rate, int(error.cooldown.per)))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("You triggered this command more than {0} time(s) per {1} sec\n"
                                                  "Try again in {2} sec").format(error.cooldown.rate,
                                                                                 int(error.cooldown.per),
                                                                                 int(error.retry_after))))
    elif isinstance(error, commands.CheckFailure):
        pass
    elif isinstance(error, MissingAdminPermissions):
        if Config.get_settings().bot_settings.admin_role_id is not None:
            await send_error(ctx, bot,
                             commands.MissingRole(Config.get_settings().bot_settings.admin_role_id), is_reaction)
        await send_error(ctx, bot, commands.MissingPermissions(['administrator']), is_reaction)
    else:
        print(get_translation("Ignoring exception in command '{0}{1}':")
              .format(Config.get_settings().bot_settings.prefix, ctx.command))
        print_exception(type(error), error, error.__traceback__, file=sys.stderr)
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(", ".join([str(a) for a in error.original.args])), is_reaction)


async def handle_message_for_chat(message: Message, bot: commands.Bot,
                                  on_edit=False, before_message: Message = None, edit_command: bool = False):
    if message.author == bot.user or (message.content.startswith(Config.get_settings().bot_settings.prefix) and
                                      not edit_command) or str(message.author.discriminator) == "0000" or \
            (len(message.content) == 0 and len(message.attachments) == 0):
        return

    author_mention = get_author_and_mention(message, bot, False)[1]

    if not Config.get_cross_platform_chat_settings().channel_id or \
            not Config.get_cross_platform_chat_settings().webhook_url:
        await send_msg(message.channel, f"{author_mention}, " +
                       get_translation("this chat can't work! Cross-platform chat disabled!"), True)
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
            result_msg = _clean_message(message, edit_command)
            if not edit_command:
                result_msg, reply_from_minecraft_user = await _handle_reply_in_message(message, result_msg)
            result_msg = await _handle_components_in_message(result_msg, message, bot, only_replace_links=True,
                                                             edit_command=edit_command, version_lower_1_7_2=True)
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
        elif get_server_players().get("current") > 0:
            content_name = "contents" if server_version.minor >= 16 else "value"
            result_msg = _clean_message(message, edit_command)
            if not edit_command:
                result_msg, reply_from_minecraft_user = await _handle_reply_in_message(message, result_msg)
            result_msg = await _handle_components_in_message(result_msg, message, bot,
                                                             edit_command=edit_command)
            # Building object for tellraw
            res_obj = [""]
            if result_msg.get("reply", None) is not None:
                if not reply_from_minecraft_user:
                    res_obj += _build_nickname_tellraw_for_discord_member(server_version.minor, result_msg["reply"][1],
                                                                          content_name, brackets_color="gray",
                                                                          left_bracket=result_msg["reply"][0],
                                                                          right_bracket=result_msg["reply"][2])
                else:
                    res_obj += _build_nickname_tellraw_for_minecraft_player(server_version.minor,
                                                                            result_msg["reply"][1], content_name,
                                                                            default_text_color="gray",
                                                                            left_bracket=result_msg["reply"][0],
                                                                            right_bracket=result_msg["reply"][2])
                _build_components_in_message(res_obj, content_name, result_msg["reply"][-1], "gray")
            if not edit_command:
                res_obj += _build_nickname_tellraw_for_discord_member(server_version.minor, message.author,
                                                                      content_name)
            else:
                res_obj += _build_nickname_tellraw_for_minecraft_player(server_version.minor,
                                                                        before_message.author.name, content_name)
            if on_edit:
                if before_message is not None:
                    result_before = _clean_message(before_message)
                    result_before = await _handle_components_in_message(result_before, before_message, bot,
                                                                        only_replace_links=True)
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
                                    announce(nick,
                                             f"@{message.author.display_name} "
                                             f"-> @{nick if nick != '@a' else 'everyone'}",
                                             cl_r)
        else:
            await send_msg(message.channel, f"{author_mention}, " +
                           get_translation("No players on server!").lower(), True)


def _handle_long_tellraw_object(tellraw_obj):
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


def _split_tellraw_object(tellraw_obj):
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


def _clean_message(message: Message, edit_command=False):
    result_msg = {}
    content = message.clean_content.replace("\u200b", "").strip()
    if edit_command:
        content = compile(rf"^{Config.get_settings().bot_settings.prefix}edit\s").sub("", content, count=1)
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


async def _handle_components_in_message(result_msg: dict, message: Message, bot: commands.Bot,
                                        only_replace_links=False, edit_command=False, version_lower_1_7_2=False):
    # TODO: For now 'webhook.edit_message' doesn't support attachments, wait for discord.py 2.0
    attachments = _handle_attachments_in_message(message) if not edit_command else {}
    url_regex = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+"

    async def repl_emoji(obj: str):
        emoji_name = search(r":\w+:", obj).group(0)
        if only_replace_links:
            return emoji_name
        else:
            emoji_id = int(search(r"\d+", obj).group(0))
            emoji = bot.get_emoji(emoji_id)
            if emoji is None:
                emoji = utils_get(bot.guilds[0].emojis, id=emoji_id)
            if emoji is None:
                with suppress(NotFound, HTTPException):
                    emoji = await bot.guilds[0].fetch_emoji(emoji_id)
            if isinstance(emoji, Emoji):
                return {"text": emoji_name, "hyperlink": str(emoji.url)}
            else:
                return emoji_name

    def repl_url(link: str):
        if only_replace_links:
            if version_lower_1_7_2:
                if "tenor" in link and "view" in link:
                    return "[gif]"
                elif len(link) > 30:
                    return get_clck_ru_url(link)
                else:
                    return link
            else:
                return "[gif]" if "tenor" in link and "view" in link else shorten_string(link, 30)
        else:
            return {"text": "[gif]" if "tenor" in link and "view" in link else shorten_string(link, 30),
                    "hyperlink": link if len(link) < 257 else get_clck_ru_url(link)}

    transformations = {
        r"<:\w+:\d+>": repl_emoji,
        url_regex: repl_url
    }
    mass_regex = "|".join(transformations.keys())

    async def repl(obj):
        match = obj.group(0)
        if search(url_regex, match):
            return transformations.get(url_regex)(match)
        else:
            return await transformations.get(r"<:\w+:\d+>")(match)

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
    return result_msg


def _handle_attachments_in_message(message: Message):
    attachments = {}
    messages = [message]
    if message.reference is not None:
        messages.append(message.reference.resolved)
    for i in range(len(messages)):
        if len(messages[i].attachments) != 0:
            if i == 0:
                attachments["content"] = []
                iattach = attachments["content"]
            else:
                attachments["reply"] = []
                iattach = attachments["reply"]
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
                iattach.append({"text": a_type,
                                "hyperlink": attachment.url if len(attachment.url) < 257
                                else get_clck_ru_url(attachment.url)})
                if need_hover:
                    iattach[-1].update({"hover": attachment.filename})
    return attachments


def _build_components_in_message(res_obj, content_name: str, obj, default_text_color: str = None):
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


def _build_nickname_tellraw_for_minecraft_player(server_version: int, nick: str, content_name: str,
                                                 default_text_color: str = None, left_bracket: str = "<",
                                                 right_bracket: str = "> "):
    tellraw_obj = [{"text": left_bracket}]
    if server_version > 7 and len(nick.split()) == 1 and nick in get_server_players().get("players"):
        tellraw_obj += [{"selector": f"@p[name={nick}]"}]
    elif server_version > 7:
        hover_string = ["", {"text": f"{nick}\n" + get_translation("Type: Player") + f"\n{get_offline_uuid(nick)}"}]
        if server_version > 11:
            hover_string += [{"text": "\nShift + "}, {"keybind": "key.attack"}]
        tellraw_obj += [{"text": nick,
                         "insertion": f"/tell {nick} ",
                         "hoverEvent": {"action": "show_text", content_name: hover_string}}]
    else:
        tellraw_obj += [{"text": nick,
                         "hoverEvent": {"action": "show_text",
                                        content_name: ["", {"text": f"{nick}\n{get_offline_uuid(nick)}"}]}}]
    tellraw_obj += [{"text": right_bracket}]
    if default_text_color is not None:
        for i in range(len(tellraw_obj)):
            tellraw_obj[i]["color"] = default_text_color
    return tellraw_obj


def _build_nickname_tellraw_for_discord_member(server_version: int, author: Member, content_name: str,
                                               brackets_color: str = None, left_bracket: str = "<",
                                               right_bracket: str = "> "):
    hover_string = ["", {"text": f"{author.display_name}\n"
                                 f"{author.name}#{author.discriminator}"}]
    if server_version > 11:
        hover_string += [{"text": "\nShift + "}, {"keybind": "key.attack"}]
    tellraw_obj = [{"text": left_bracket},
                   {"text": author.display_name, "color": "dark_gray",
                    "hoverEvent": {"action": "show_text", content_name: hover_string}},
                   {"text": right_bracket}]
    if server_version > 7:
        tellraw_obj[-2].update({"insertion": f"@{author.display_name}"})
    if brackets_color is not None:
        for i in range(len(tellraw_obj)):
            if len(tellraw_obj[i].keys()) == 1:
                tellraw_obj[i]["color"] = brackets_color
    return tellraw_obj


class ServerVersion:
    def __init__(self, version_string: str):
        parsed_version = version_string
        snapshot_version = False
        if any(i in parsed_version.lower() for i in ["snapshot", "release"]) or search(r"\d+w\d+a", parsed_version):
            print(get_translation("Minecraft server is not in release state! Proceed with caution!"))
            if "snapshot" in parsed_version.lower():
                parsed_version = parsed_version.lower().split("snapshot")[0]
                snapshot_version = True
            elif "release" in parsed_version.lower():
                parsed_version = parsed_version.lower().split("release")[0]
            elif search(r"\d+w\d+a", parsed_version):
                parsed_version = parse_snapshot(parsed_version)
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
    answer = req_get(url="https://minecraft.fandom.com/api.php",
                     params={
                         "action": "parse",
                         "page": f"Java Edition {version}",
                         "prop": "categories",
                         "format": "json"
                     }).json()
    if answer.get("parse", None) is not None and answer["parse"].get("categories", None) is not None:
        for category in answer["parse"]["categories"]:
            if "snapshots" in category["*"].lower():
                return category["*"]


def get_server_players() -> dict:
    """Returns dict, keys: current, max, players"""
    with connect_query() as cl_q:
        info = cl_q.full_stats
    return dict(current=info.num_players, max=info.max_players, players=info.players)


def shorten_string(string: str, max_length: int):
    if len(string) > max_length:
        return f"{string[:max_length].strip(' ')}..."
    else:
        return string


def get_clck_ru_url(url: str):
    return req_post("https://clck.ru/--", params={"url": url}).text


@contextmanager
def times(fade_in, duration, fade_out, rcon_client):
    rcon_client.run(f"title @a times {fade_in} {duration} {fade_out}")
    yield
    rcon_client.run("title @a reset")


def announce(player, message, rcon_client, subtitle=False):
    if get_server_version().minor >= 11 and not subtitle:
        rcon_client.run(f'title {player} actionbar ' + '{' + f'"text":"{message}"' + ',"bold":true,"color":"gold"}')
    else:
        rcon_client.run(f'title {player} subtitle ' + '{' + f'"text":"{message}"' + ',"color":"gold"}')
        rcon_client.run(f'title {player} title ' + '{"text":""}')
    rcon_client.run(play_sound(player, "minecraft:entity.arrow.hit_player", "player", 1, 0.75))


def play_sound(name, sound, category="master", volume=1, pitch=1.0):
    return f"/execute as {name} at @s run playsound {sound} {category} @s ~ ~ ~ {volume} {pitch} 1"


def play_music(name, sound):
    return play_sound(name, sound, "music", 99999999999999999999999999999999999999)


def stop_music(sound, name="@a"):
    return f"/stopsound {name} music {sound}"


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
                ansi_escape = compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
                self.file.write(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] "
                                f"{ansi_escape.sub('', data)}")
            self.stdout.write(f"[{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}] {data}")
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
