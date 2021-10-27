import inspect
import socket
import sys
from ast import literal_eval
from asyncio import sleep as asleep
from contextlib import contextmanager, suppress
from datetime import datetime
from hashlib import md5
from itertools import chain
from json import load, dump, JSONDecodeError
from os import chdir, system, walk, mkdir, remove
from os.path import basename, join as p_join, getsize
from pathlib import Path
from random import randint
from re import search, split, findall, sub, compile
from shutil import rmtree
from sys import platform, argv
from threading import Thread, Event
from time import sleep
from typing import Tuple, List
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED, ZIP_BZIP2, ZIP_LZMA

from discord import Activity, ActivityType, TextChannel, Message, Status, Member, Role
from discord.errors import NotFound, Forbidden, HTTPException
from discord.ext import commands
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r
from psutil import process_iter, NoSuchProcess, disk_usage
from requests import post as req_post

from commands.poll import Poll
from components.decorators import MissingAdminPermissions
from components.localization import get_translation
from components.rss_feed_handle import create_feed_webhook
from components.watcher_handle import create_watcher, create_chat_webhook
from config.init_config import Config, BotVars

if platform == "win32":
    from os import startfile

UNITS = ("B", "KB", "MB", "GB", "TB", "PB")

if len(argv) > 1 and argv[1] == "-g":
    from components.localization import RuntimeTextHandler

    for un in UNITS:
        RuntimeTextHandler.add_translation(un)


async def send_msg(ctx, msg: str, is_reaction=False):
    if is_reaction:
        await ctx.send(content=msg,
                       delete_after=Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
    else:
        await ctx.send(msg)


def add_quotes(msg: str) -> str:
    return f"```{msg}```"


async def delete_after_by_msg(message, ctx=None):
    if isinstance(message, Message):
        await message.delete(delay=Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
    elif isinstance(message, int):
        await (await ctx.channel.fetch_message(message)) \
            .delete(delay=Config.get_awaiting_times_settings().await_seconds_before_message_deletion)


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
            await send_msg(ctx, add_quotes(get_translation("Bot is backing up server!").capitalize()), is_reaction)
        else:
            await send_msg(ctx, add_quotes(get_translation("server have already started!").capitalize()), is_reaction)
    else:
        if BotVars.is_backing_up:
            await send_msg(ctx, add_quotes(get_translation("Bot is backing up server!").capitalize()), is_reaction)
        elif BotVars.is_restoring:
            await send_msg(ctx, add_quotes(get_translation("Bot is restoring server from backup!").capitalize()),
                           is_reaction)
        elif BotVars.is_loading:
            await send_msg(ctx, add_quotes(get_translation("server is loading!").capitalize()), is_reaction)
        elif BotVars.is_stopping:
            await send_msg(ctx, add_quotes(get_translation("server is stopping!").capitalize()), is_reaction)
        else:
            await send_msg(ctx, add_quotes(get_translation("server have already been stopped!").capitalize()),
                           is_reaction)


async def start_server(ctx, bot: commands.Bot, backups_thread=None, shut_up=False, is_reaction=False):
    BotVars.is_loading = True
    print(get_translation("Loading server"))
    if ctx and not shut_up:
        await send_msg(ctx, add_quotes(get_translation("Loading server.......\nPlease wait)")), is_reaction)
    chdir(Config.get_selected_server_from_list().working_directory)
    try:
        if platform == "linux" or platform == "linux2":
            if ".sh" not in Config.get_selected_server_from_list().start_file_name:
                raise NameError()
            system("screen -dmS " + Config.get_selected_server_from_list().server_name.replace(" ", "_") +
                   " ./" + Config.get_selected_server_from_list().start_file_name)
        elif platform == "win32":
            if ".bat" not in Config.get_selected_server_from_list().start_file_name:
                raise NameError()
            startfile(Config.get_selected_server_from_list().start_file_name)
        BotVars.server_start_time = int(datetime.now().timestamp())
    except (NameError, ValueError):
        print(get_translation("Couldn't open script! Check naming and extension of the script!"))
        await send_msg(ctx, add_quotes(get_translation("Couldn't open script because of naming! Retreating...")),
                       is_reaction)
        BotVars.is_loading = False
        if BotVars.is_restarting:
            BotVars.is_restarting = False
        return
    chdir(Config.get_bot_config_path())
    await asleep(5)
    check_time = datetime.now()
    while True:
        if len(get_list_of_processes()) == 0:
            await send_msg(ctx, add_quotes(get_translation("Error while loading server! Retreating...")),
                           is_reaction)
            bot.loop.create_task(bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                                       name=Config.get_settings().bot_settings.idle_status)))
            BotVars.is_loading = False
            if BotVars.is_restarting:
                BotVars.is_restarting = False
            return
        timedelta_secs = (datetime.now() - check_time).seconds
        if Config.get_selected_server_from_list().server_loading_time:
            percentage = round((timedelta_secs / Config.get_selected_server_from_list().server_loading_time) * 100)
            output_bot = get_translation("Loading: ") + ((str(percentage) + "%") if percentage < 101 else "100%...")
        else:
            output_bot = get_translation("{0}, elapsed time: ") \
                             .format(Config.get_settings().bot_settings.idle_status) + \
                         (str(timedelta_secs // 60) + ":" +
                          f"{(timedelta_secs % 60):02d}" if timedelta_secs // 60 != 0 else str(timedelta_secs % 60) +
                                                                                           get_translation(" sec"))
        await bot.change_presence(activity=Activity(type=ActivityType.listening, name=output_bot))
        await asleep(Config.get_awaiting_times_settings().await_seconds_when_connecting_via_rcon)
        with suppress(ConnectionError, socket.error):
            with connect_query() as cl_q:
                _ = cl_q.basic_stats
            break
    if Config.get_cross_platform_chat_settings().enable_cross_platform_chat and \
            Config.get_cross_platform_chat_settings().channel_id and \
            Config.get_cross_platform_chat_settings().webhook_url:
        create_watcher()
        BotVars.watcher_of_log_file.start()
    if Config.get_selected_server_from_list().server_loading_time:
        Config.get_selected_server_from_list().server_loading_time = \
            (Config.get_selected_server_from_list().server_loading_time + (datetime.now() - check_time).seconds) // 2
    else:
        Config.get_selected_server_from_list().server_loading_time = (datetime.now() - check_time).seconds
    Config.save_config()
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
    if ctx and not shut_up:
        await send_msg(ctx, author_mention + "\n" + add_quotes(get_translation("Server's on now")), is_reaction)
        print(get_translation("Server on!"))
        if randint(0, 8) == 0:
            await send_msg(ctx, get_translation("Kept you waiting, huh?"), is_reaction)
    if backups_thread is not None:
        backups_thread.skip()
    BotVars.is_loading = False
    BotVars.is_server_on = True
    if BotVars.is_restarting:
        BotVars.is_restarting = False
    Config.get_server_config().states.started_info.set_state_info(str(author),
                                                                  datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    Config.save_server_config()
    bot.loop.create_task(bot.change_presence(activity=Activity(type=ActivityType.playing,
                                                               name=Config.get_settings().bot_settings.gaming_status)))


async def stop_server(ctx, bot: commands.Bot, poll: Poll, how_many_sec=10, is_restart=False, is_reaction=False):
    no_connection = False
    players_count = 0

    if "stop" in [p.command for p in poll.get_polls().values()]:
        if not is_reaction:
            await delete_after_by_msg(ctx.message)
        await ctx.send(get_translation("{0}, bot already has poll on `stop`/`restart` command!")
                       .format(ctx.author.mention),
                       delete_after=Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
        return

    try:
        players_count = len(get_server_players())
    except (ConnectionError, socket.error):
        if len(get_list_of_processes()) == 0:
            print(get_translation("Bot Exception: Couldn't connect to server, because it's stopped"))
            await send_msg(ctx,
                           add_quotes(get_translation("Couldn't connect to server to shut it down! Server stopped...")),
                           is_reaction)
            BotVars.is_stopping = False
            BotVars.is_server_on = False
            return
        no_connection = True

    if not no_connection:
        if players_count > 0:
            if await poll.timer(ctx, 5, "stop"):
                if not await poll.run(ctx=ctx,
                                      message=get_translation("this man {0} trying to stop the server with {1} "
                                                              "player(s) on it. Will you let that happen?")
                                              .format(get_author_and_mention(ctx, bot, is_reaction)[1], players_count),
                                      command="stop",
                                      needed_role=Config.get_settings().bot_settings.role,
                                      remove_logs_after=5):
                    return
            else:
                await delete_after_by_msg(ctx.message)
        if players_count == 0:
            how_many_sec = 0

        BotVars.is_stopping = True
        print(get_translation("Stopping server"))
        await send_msg(ctx, add_quotes(get_translation("Stopping server") + "......." +
                                       ("\n" + get_translation("Please wait {0} sec.").format(str(how_many_sec))
                                        if how_many_sec > 0 else "")), is_reaction)

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
                    bot_message = get_translation("Server\'s shutting down in {0} seconds").format(str(how_many_sec))
                else:
                    bot_message = get_translation("Server\'s restarting in {0} seconds").format(str(how_many_sec))

                bot_display_name = get_bot_display_name(bot)
                cl_r.tellraw("@a", ["", {"text": "<"}, {"text": bot_display_name, "color": "dark_gray"},
                                    {"text": "> " + bot_message}])
                for i in range(how_many_sec, -1, -w):
                    cl_r.tellraw("@a", ["", {"text": "<"}, {"text": bot_display_name, "color": "dark_gray"},
                                        {"text": "> " + get_translation("{0} sec to go").format(str(i))}])
                    await asleep(w)
            cl_r.run("stop")

        if BotVars.watcher_of_log_file.is_running():
            BotVars.watcher_of_log_file.stop()
        while True:
            await asleep(Config.get_awaiting_times_settings().await_seconds_when_connecting_via_rcon)
            try:
                with connect_query() as cl_q:
                    _ = cl_q.basic_stats
            except (ConnectionError, socket.error):
                break
    else:
        print(get_translation("Bot Exception: Couldn't connect to server, so killing it now..."))
        await send_msg(ctx,
                       add_quotes(get_translation("Couldn't connect to server to shut it down! Killing it now...")),
                       is_reaction)
    kill_server()
    BotVars.is_stopping = False
    BotVars.is_server_on = False
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
    print(get_translation("Server's off now"))
    await send_msg(ctx, author_mention + "\n" + add_quotes(get_translation("Server's off now")), is_reaction)
    Config.get_server_config().states.stopped_info.set_state_info(str(author),
                                                                  datetime.now().strftime("%d/%m/%Y %H:%M:%S"))
    Config.save_server_config()
    await bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                name=Config.get_settings().bot_settings.idle_status))


def get_list_of_processes() -> list:
    basename_of_executable = basename(argv[0])
    process_name = "java"
    list_proc = []

    for proc in process_iter():
        with suppress(NoSuchProcess):
            parents_name_list = [i.name() for i in proc.parents()]
            if process_name in proc.name() and ("screen" in parents_name_list or
                                                basename_of_executable in parents_name_list or
                                                "python.exe" in parents_name_list) \
                    and (BotVars.server_start_time is None or
                         abs(int(proc.create_time()) - BotVars.server_start_time) < 5):
                list_proc.append(proc)
    return list_proc


def kill_server():
    list_proc = get_list_of_processes()
    if len(list_proc) != 0:
        for p in list_proc:
            with suppress(NoSuchProcess):
                p.kill()
    BotVars.server_start_time = None


def get_bot_display_name(bot: commands.Bot):
    for member in bot.guilds[0].members:
        if member.id == bot.user.id:
            return member.display_name
    return bot.user.display_name


class BackupsThread(Thread):
    def __init__(self, bot):
        super().__init__()
        self.name = "BackupsThread"
        self.daemon = True
        self._skip = Event()
        self._bot = bot
        self._terminate = False

    def run(self):
        while True:
            is_skipped = self._skip.wait(Config.get_backups_settings().period_of_automatic_backups * 60)
            if self._terminate:
                break
            if is_skipped:
                self._skip.clear()
                continue

            if not BotVars.is_backing_up and not BotVars.is_restoring and Config.get_backups_settings().automatic_backup:
                if BotVars.is_loading or BotVars.is_stopping or BotVars.is_restarting:
                    while True:
                        sleep(Config.get_awaiting_times_settings().await_seconds_when_connecting_via_rcon)
                        if not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting:
                            break

                players_count = 0
                if BotVars.is_server_on:
                    with suppress(ConnectionError, socket.error):
                        players_count = len(get_server_players())
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
                                                 get_from_server_properties("level-name")).as_posix(),
                                            Config.get_backups_settings().compression_method), None)
                    Config.add_backup_info(file_name=file_name)
                    Config.save_server_config()

                if BotVars.is_server_on and players_count == 0:
                    if not BotVars.is_auto_backup_disable:
                        BotVars.is_auto_backup_disable = True

                if not BotVars.is_server_on:
                    if not BotVars.is_auto_backup_disable:
                        BotVars.is_auto_backup_disable = True

    def skip(self):
        self._skip.set()

    def join(self, timeout=None):
        self._terminate = True
        self.skip()
        sleep(0.5)


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
            with connect_query() as cl_q:
                if cl_q.full_stats:
                    use_rcon = True
    if use_rcon:
        bot_display_name = get_bot_display_name(bot)

    if use_rcon:
        tellraw = ["", {"text": "<"}, {"text": bot_display_name, "color": "dark_gray"}, {"text": "> "}]
        if forced:
            tellraw.append({"text": get_translation("Starting backup triggered by {0}...")
                           .format(f"{user.display_name}#{user.discriminator}"), "color": "yellow"})
        else:
            tellraw.append({"text": get_translation("Starting automatic backup..."), "color": "aqua"})
        with connect_rcon() as cl_r:
            cl_r.tellraw("@a", tellraw)
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
                        if timedelta_secs // 60 != 0:
                            date_t = str(timedelta_secs // 60) + ":" + f"{(timedelta_secs % 60):02d}"
                        else:
                            date_t = str(timedelta_secs % 60) + get_translation(" sec")
                        yield add_quotes(f"diff\n{percent}% {date_t} '{afn}'\n"
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
        timedelta_secs = (datetime.now() - dt).seconds
        if timedelta_secs // 60 != 0:
            date_t = str(timedelta_secs // 60) + ":" + f"{(timedelta_secs % 60):02d}"
        else:
            date_t = str(timedelta_secs % 60) + get_translation(" sec")
        backup_size = get_file_size(f"{zip_path}/{zip_name}.zip")
        backup_size_str = get_human_readable_size(backup_size, round=True)
        world_folder_size = get_folder_size(Config.get_selected_server_from_list().working_directory,
                                            get_from_server_properties("level-name"))
        world_folder_size_str = get_human_readable_size(world_folder_size, stop_unit=backup_size_str.split(" ")[-1],
                                                        round=True)
        yield add_quotes(get_translation("Done in {0}\nCompression method: {1}").format(date_t, compression) +
                         f"\n{world_folder_size_str} -> {backup_size_str} " +
                         (f"(x{world_folder_size // backup_size})"
                          if round(world_folder_size / backup_size, 1).is_integer()
                          else f"(x{world_folder_size / backup_size:.1f})"))
    if use_rcon:
        with connect_rcon() as cl_r:
            cl_r.tellraw("@a",
                         ["", {"text": "<"}, {"text": bot_display_name, "color": "dark_gray"}, {"text": "> "},
                          {"text": get_translation("Backup completed!"), "color": "green"}])
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
    if limit is not None:
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


def send_message_of_deleted_backup(bot: commands.Bot, reason: str, backup=None):
    if backup is not None:
        if backup.initiator is None:
            msg = get_translation("Deleted auto backup '{0}.zip' because of {1}").format(backup.file_name, reason)
        else:
            msg = get_translation("Deleted backup '{0}.zip' made by {1} because of {2}").format(backup.file_name,
                                                                                                backup.initiator,
                                                                                                reason)
    else:
        msg = get_translation("Deleted all backups because of {0}").format(reason)
    with suppress(ConnectionError, socket.error):
        with connect_rcon() as cl_r:
            cl_r.tellraw("@a",
                         ["", {"text": "<"}, {"text": get_bot_display_name(bot), "color": "dark_gray"}, {"text": "> "},
                          {"text": msg, "color": "red"}])
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
        if average_backup_size < free:
            break
        if Config.get_backups_settings().size_limit is not None and \
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


def get_half_members_count_with_role(bot: commands.Bot):
    count = 0
    for m in bot.guilds[0].members:
        if not m.bot and m.status != Status.offline:
            if Config.get_settings().bot_settings.role:
                if Config.get_settings().bot_settings.role in (e.name for e in m.roles):
                    count += 1
            else:
                count += 1
    if count < 2:
        return count
    return count // 2


async def server_checkups(bot: commands.Bot):
    try:
        with connect_query() as cl_q:
            info = cl_q.full_stats
        if info.num_players != 0:
            to_save = False
            for player in info.players:
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
                Config.get_cross_platform_chat_settings().enable_cross_platform_chat and \
                Config.get_cross_platform_chat_settings().channel_id and \
                Config.get_cross_platform_chat_settings().webhook_url:
            if BotVars.watcher_of_log_file is None:
                create_watcher()
            BotVars.watcher_of_log_file.start()
        if not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting:
            bot.loop.create_task(bot.change_presence(activity=Activity(type=ActivityType.playing,
                                                                       name=Config.get_settings().bot_settings.gaming_status
                                                                            + ", " + str(info.num_players) +
                                                                            get_translation(" player(s) online"))))
    except (ConnectionError, socket.error):
        if len(get_list_of_processes()) == 0:
            if BotVars.is_server_on:
                BotVars.is_server_on = False
            if BotVars.watcher_of_log_file is not None and BotVars.watcher_of_log_file.is_running():
                BotVars.watcher_of_log_file.stop()
        if not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting:
            bot.loop.create_task(bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                                       name=Config.get_settings().bot_settings.idle_status +
                                                                            (" 🤔" if len(
                                                                                get_list_of_processes()) != 0 else ""))))
        if Config.get_settings().bot_settings.forceload and not BotVars.is_stopping \
                and not BotVars.is_loading and not BotVars.is_restarting:
            for channel in bot.guilds[0].channels:
                if not isinstance(channel, TextChannel):
                    continue
                with suppress(NotFound, Forbidden, HTTPException):
                    if Config.get_settings().bot_settings.menu_id is not None:
                        await channel.fetch_message(Config.get_settings().bot_settings.menu_id)
                    await send_msg(ctx=channel,
                                   msg=add_quotes(get_translation("Bot detected: Server\'s offline!\n"
                                                                  "Time: {0}\n"
                                                                  "Starting up server again!").format(
                                       datetime.now().strftime("%d/%m/%Y %H:%M:%S"))),
                                   is_reaction=True)
                    await start_server(ctx=channel, bot=bot, shut_up=True, is_reaction=True)
                    break
    if Config.get_awaiting_times_settings().await_seconds_in_check_ups > 0:
        await asleep(Config.get_awaiting_times_settings().await_seconds_in_check_ups)


async def bot_status(ctx, is_reaction=False):
    states = ""
    bot_message = ""
    states_info = Config.get_server_config().states
    if states_info.started_info.date is not None and states_info.started_info.user is not None:
        states += get_translation("Server has been started at {0}, by {1}").format(states_info.started_info.date,
                                                                                   states_info.started_info.user) + "\n"
    if states_info.stopped_info.date is not None and states_info.stopped_info.user is not None:
        states += get_translation("Server has been stopped at {0}, by {1}").format(states_info.stopped_info.date,
                                                                                   states_info.stopped_info.user) + "\n"
    states = states.strip("\n")
    bot_message += get_translation("Server address: ") + Config.get_settings().bot_settings.ip_address + "\n"
    if BotVars.is_backing_up:
        bot_message += get_translation("Server is backing up") + "\n"
    if BotVars.is_restoring:
        bot_message += get_translation("Server is restoring from backup") + "\n"
    if BotVars.is_server_on:
        try:
            bot_message = get_translation("server online").capitalize() + "\n" + bot_message
            with connect_rcon() as cl_r:
                """rcon check daytime cycle"""
                time_ticks = int(cl_r.run("time query daytime").split(" ")[-1])
            message = get_translation("Time in minecraft: ")
            if 450 <= time_ticks <= 11616:
                message += get_translation("Day, ")
            elif 11617 <= time_ticks <= 13800:
                message += get_translation("Sunset, ")
            elif 13801 <= time_ticks <= 22550:
                message += get_translation("Night, ")
            else:
                message += get_translation("Sunrise, ")
            message += str((6 + time_ticks // 1000) % 24) + ":" + f"{((time_ticks % 1000) * 60 // 1000):02d}\n"
            bot_message += message + get_translation("Selected server: ") + \
                           Config.get_selected_server_from_list().server_name + "\n" + states
            await send_msg(ctx, add_quotes(bot_message), is_reaction)
        except (ConnectionError, socket.error):
            bot_message += get_translation("Server thinking...") + "\n" + get_translation("Selected server: ") + \
                           Config.get_selected_server_from_list().server_name + "\n" + states
            await send_msg(ctx, add_quotes(bot_message), is_reaction)
            print(get_translation("Server's down via rcon"))
    else:
        bot_message = get_translation("server offline").capitalize() + "\n" + bot_message
        bot_message += get_translation("Selected server: ") + Config.get_selected_server_from_list().server_name + \
                       "\n" + states
        await send_msg(ctx, add_quotes(bot_message), is_reaction)


async def bot_list(ctx, bot: commands.Bot, is_reaction=False):
    try:
        with connect_query() as cl_q:
            info = cl_q.full_stats
        if info.num_players == 0:
            await send_msg(ctx, add_quotes(get_translation("There are no players on the server")), is_reaction)
        else:
            await send_msg(ctx, add_quotes(get_translation("There are {0} player(s)"
                                                           "\nPlayer(s): {1}").format(info.num_players,
                                                                                      ", ".join(info.players))),
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
            await send_msg(ctx, add_quotes(get_translation("Some player(s) still oped, waiting for them")),
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
            await send_msg(ctx, add_quotes(get_translation("Some player(s) still oped, waiting for them")),
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
                           delete_after=Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
            return
        if await poll.run(ctx=ctx,
                          message=get_translation("this man {0} trying to delete some history"
                                                  " of this channel. Will you let that happen?")
                                  .format(ctx.author.mention),
                          command="clear",
                          remove_logs_after=5):
            if count < 0 or subcommand == "reply":
                await ctx.channel.purge(limit=None, check=check_condition, after=message_created, bulk=False)
            else:
                await ctx.channel.purge(limit=1, bulk=False)
                await ctx.channel.purge(limit=count, check=check_condition, bulk=False)
    else:
        await delete_after_by_msg(ctx.message)


async def bot_backup(ctx, is_reaction=False):
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
                       backup.file_creation_date.strftime("%d/%m/%Y %H:%M:%S")
        bot_message += "\n" + get_translation("Backup size: ") + \
                       get_human_readable_size(get_file_size(Config.get_selected_server_from_list().working_directory,
                                                             Config.get_backups_settings().name_of_the_backups_folder,
                                                             f"{backup.file_name}.zip"))
        if backup.reason is None and backup.initiator is None:
            bot_message += "\n" + get_translation("Reason: ") + get_translation("Automatic backup")
        else:
            bot_message += "\n" + get_translation("Reason: ") + \
                           (backup.reason if backup.reason else get_translation("Not stated"))
            bot_message += "\n" + get_translation("Initiator: ") + backup.initiator
        if backup.restored_from:
            bot_message += "\n\t" + get_translation("The world of the server was restored from this backup")
    await send_msg(ctx, add_quotes(bot_message), is_reaction)


def parse_params_for_help(command_params: dict, string_to_add: str, create_params_dict=False) -> Tuple[str, dict]:
    params = {}
    converter = False
    for arg_name, arg_data in command_params.items():
        if arg_data.annotation != inspect._empty and hasattr(arg_data.annotation, 'converter'):
            converter = True
        if create_params_dict:
            if arg_data.annotation != inspect._empty:
                if not getattr(arg_data.annotation, '__name__', None) is None:
                    params[arg_name] = getattr(arg_data.annotation, '__name__', None)
                elif hasattr(arg_data.annotation, 'converter'):
                    params[arg_name] = sub(r"\w*?\.", "", str(arg_data.annotation.converter))
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


def parse_subcommands_for_help(command, all_params=False) -> Tuple[List[str], List[str]]:
    if not hasattr(command, "commands") or len(command.commands) == 0:
        return [], []
    command_commands = sorted(command.commands, key=lambda c: c.name)

    if not all_params:
        return [c.name for c in command_commands], []

    subcommands = []
    for subcommand in command_commands:
        sub_sub_commands_line = parse_subcommands_for_help(subcommand)[0]
        if sub_sub_commands_line:
            sub_sub_commands_line = " " + " | ".join(sub_sub_commands_line) if len(sub_sub_commands_line) else ""
            sub_command, *sub_command_params = \
                parse_params_for_help(subcommand.clean_params, subcommand.name)[0].split()
            subcommands.append(sub_command + sub_sub_commands_line + (" | " if len(sub_sub_commands_line) > 0 else "") +
                               " ".join(sub_command_params))
        else:
            subcommands.append(parse_params_for_help(subcommand.clean_params, subcommand.name)[0])
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
                            .format(prefix=Config.get_settings().bot_settings.prefix) + "\n\n"
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
def connect_rcon():
    with Client_r(Config.get_settings().bot_settings.local_address, BotVars.port_rcon, timeout=1) as cl_r:
        cl_r.login(BotVars.rcon_pass)
        yield cl_r


@contextmanager
def connect_query():
    with Client_q(Config.get_settings().bot_settings.local_address, BotVars.port_query, timeout=1) as cl_q:
        yield cl_q


def get_offline_uuid(username):
    data = bytearray(md5(("OfflinePlayer:" + username).encode()).digest())
    data[6] &= 0x0f  # clear version
    data[6] |= 0x30  # set to version 3
    data[8] &= 0x3f  # clear variant
    data[8] |= 0x80  # set to IETF variant
    uuid = data.hex()
    return '-'.join((uuid[:8], uuid[8:12], uuid[12:16], uuid[16:20], uuid[20:]))


def get_whitelist_entry(username):
    return dict(name=username, uuid=get_offline_uuid(username))


def save_to_whitelist_json(entry: dict):
    whitelist = [entry]
    filepath = Path(Config.get_selected_server_from_list().working_directory + "/whitelist.json")
    if filepath.is_file():
        try:
            with open(filepath, "r", encoding="utf8") as file:
                whitelist = load(file)
            whitelist.append(entry)
        except JSONDecodeError:
            pass
    with open(filepath, "w", encoding="utf8") as file:
        dump(whitelist, file)


def get_from_server_properties(setting: str):
    """
    Parameters
    ----------
    setting : str
        can be "online-mode" or "level-name"
    """
    filepath = Path(Config.get_selected_server_from_list().working_directory + "/server.properties")
    if not filepath.exists():
        raise RuntimeError(get_translation("File '{0}' doesn't exist!").format(filepath.as_posix()))
    with open(filepath, "r") as f:
        for i in f.readlines():
            if i.find(setting) >= 0:
                if setting == "online-mode":
                    return literal_eval(i.split("=")[1].capitalize())
                elif setting == "level-name":
                    return i.split("=")[1].strip(" \n")


# Handling errors
async def send_error(ctx, bot, error, is_reaction=False):
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
        print(get_translation("{0} don't have role '{1}' to run command").format(author, error.missing_role))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("you don't have role '{0}' to run this command").capitalize()
                                  .format(error.missing_role)),
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
        if Config.get_settings().bot_settings.admin_role != "":
            await send_error(ctx, bot, commands.MissingRole(Config.get_settings().bot_settings.admin_role), is_reaction)
        await send_error(ctx, bot, commands.MissingPermissions(['administrator']), is_reaction)
    else:
        print(", ".join(error.args))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(", ".join([str(a) for a in error.original.args])), is_reaction)


async def handle_message_for_chat(message, bot, need_to_delete_on_error: bool, on_edit=False, before_message=None):
    if message.author == bot.user or message.content.startswith(Config.get_settings().bot_settings.prefix) or str(
            message.author.discriminator) == "0000" or (len(message.content) == 0 and len(message.attachments) == 0) \
            or message.channel.id != int(Config.get_cross_platform_chat_settings().channel_id):
        return

    author_mention = get_author_and_mention(message, bot, False)[1]
    delete_user_message = True

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
        if server_version < 7:
            await send_msg(message.channel, f"{author_mention}, " +
                           get_translation("version of your minecraft server is lower than `1.7.2` "
                                           "so bot can't send messages from discord to minecraft!"),
                           is_reaction=True)
        elif len(get_server_players()) > 0:
            result_msg = _handle_custom_emojis(message)
            result_msg = await _handle_reply_in_message(message, result_msg)
            result_msg = _handle_urls_and_attachments_in_message(result_msg, message)

            # Building object for tellraw
            res_obj = [""]
            if result_msg.get("reply", None) is not None:
                if len(result_msg.get("reply")) == 3:
                    res_obj.extend([{"text": result_msg.get("reply")[0], "color": "gray"},
                                    {"text": result_msg.get("reply")[1], "color": "dark_gray"}])
                    _build_if_urls_in_message(res_obj, result_msg.get("reply")[2], "gray")
                else:
                    _build_if_urls_in_message(res_obj, result_msg.get("reply"), "gray")
            res_obj += [{"text": "<"}, {"text": message.author.display_name, "color": "dark_gray"}, {"text": "> "}]
            if on_edit:
                result_before = _handle_custom_emojis(before_message)
                result_before = _handle_urls_and_attachments_in_message(result_before, before_message, True)
                content_name = "contents" if server_version >= 16 else "value"
                res_obj.append({"text": "*", "color": "gold",
                                "hoverEvent": {"action": "show_text", content_name: result_before.get("content")}})
            _build_if_urls_in_message(res_obj, result_msg.get("content"), None)

            with connect_rcon() as cl_r:
                if server_version > 7:
                    cl_r.tellraw("@a", res_obj)
                else:
                    res = []
                    for elem in res_obj:
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
                    for tellraw in res:
                        cl_r.tellraw("@a", tellraw)

            delete_user_message = False
            nicks = _search_mentions_in_message(message)
            if len(nicks) > 0:
                with suppress(ConnectionError, socket.error):
                    with connect_rcon() as cl_r:
                        with times(0, 60, 20, cl_r):
                            for nick in nicks:
                                announce(nick,
                                         f"@{message.author.display_name} -> @{nick if nick != '@a' else 'everyone'}",
                                         cl_r)
        else:
            await send_msg(message.channel, f"{author_mention}, " +
                           get_translation("No players on server!").lower(), True)

    if delete_user_message and need_to_delete_on_error:
        await delete_after_by_msg(message)


def _handle_custom_emojis(message):
    result_msg = {}
    content = message.clean_content
    if search(r"<:\w+:\d+>", content.replace("​", "").strip()):
        temp_split = split(r"<:\w+:\d+>", content.replace("​", "").strip())
        temp_arr = list(findall(r"<:\w+:\d+>", content.replace("​", "").strip()))
        i = 1
        for emoji in temp_arr:
            temp_split.insert(i, findall(r"\w+", emoji)[0])
            i += 2
        result_msg["content"] = "".join(temp_split)
    else:
        result_msg["content"] = content.replace("​", "").strip()
    return result_msg


async def _handle_reply_in_message(message, result_msg):
    if message.reference is not None:
        reply_msg = message.reference.resolved
        cnt = reply_msg.clean_content.strip()
        cnt = cnt.replace("​", "")
        if reply_msg.author.discriminator == "0000":
            # reply to minecraft player
            cnt = cnt.replace("**<", "<").replace(">**", ">")
            result_msg["reply"] = f"\n -> {cnt}"
        else:
            # Reply to discord user
            nick = (await message.guild.fetch_member(reply_msg.author.id)).display_name
            result_msg["reply"] = ["\n -> <", nick, f"> {cnt}"]
    return result_msg


def _handle_urls_and_attachments_in_message(result_msg, message, only_replace_links=False):
    attachments = _handle_attachments_in_message(message)
    for key, ms in result_msg.items():
        if isinstance(ms, list):
            msg = ms.copy()
            msg = msg[-1]
        else:
            msg = ms

        temp_split = []
        url_regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+'
        if search(url_regex, msg):
            temp_split = split(url_regex, msg)
            temp_arr = list(findall(url_regex, msg))
            i = 1
            for link in temp_arr:
                if only_replace_links:
                    temp_split.insert(i,
                                      shorten_url(link, 30) if "tenor" not in link and "view" not in link else "[gif]")
                else:
                    temp_split.insert(i,
                                      (shorten_url(link, 30) if "tenor" not in link and "view" not in link else "[gif]",
                                       link if len(link) < 257 else get_clck_ru_url(link)))
                i += 2
        else:
            temp_split.append(msg)

        if attachments.get(key, None) is not None and len(attachments[key]) > 0:
            for i in attachments[key]:
                t_string = [t[0] if isinstance(t, tuple) else t for t in temp_split]
                if (key == "content" and len("".join(t_string)) != 0) or \
                        (key == "reply" and "".join(t_string) != "> "):
                    temp_split.append(" ")
                if only_replace_links:
                    temp_split.append(i[0])
                else:
                    temp_split.append(i)

        if key == "reply":
            temp_split.append("\n")

        if isinstance(ms, list):
            result_msg[key] = [ms[0], ms[1], "".join(temp_split) if only_replace_links else temp_split]
        else:
            result_msg[key] = "".join(temp_split) if only_replace_links else temp_split
    return result_msg


def _handle_attachments_in_message(message):
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
                if attachment.content_type is None:
                    a_type = "[file]"
                else:
                    if "image" in attachment.content_type:
                        if "image/gif" in attachment.content_type:
                            a_type = "[gif]"
                        else:
                            a_type = "[img]"
                    elif "video" in attachment.content_type or "audio" in attachment.content_type:
                        a_type = f"[{attachment.content_type.split('/')[-1]}]"
                    else:
                        a_type = "[file]"
                iattach.append((a_type,
                                attachment.url if len(attachment.url) < 257 else get_clck_ru_url(attachment.url)))
    return attachments


def _build_if_urls_in_message(res_obj, obj, default_text_color):
    if isinstance(obj, list):
        for elem in obj:
            if isinstance(elem, tuple):
                res_obj.append({"text": elem[0], "underlined": True, "color": "blue",
                                "clickEvent": {"action": "open_url", "value": elem[1]}})
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


def _search_mentions_in_message(message) -> list:
    if len(message.mentions) == 0 and len(message.role_mentions) == 0 and not message.mention_everyone:
        return []

    nicks = []
    if message.mention_everyone:
        nicks.append("@a")
    else:
        # Check role and user mentions
        members_from_roles = list(chain(*[i.members for i in message.role_mentions]))
        members_from_roles.extend(message.mentions)
        members_from_roles = set(members_from_roles)
        for member in members_from_roles:
            if member.id in [i.user_discord_id for i in Config.get_known_users_list()]:
                nicks.extend([i.user_minecraft_nick for i in Config.get_known_users_list()
                              if i.user_discord_id == member.id])

        players_nicks_from_discord = [i.display_name if i.display_name else i.name for i in message.mentions]
        server_players = get_server_players()
        if len(members_from_roles) > 0:
            nicks = [i for i in nicks if i in server_players]
        # Check @'minecraft_nick' mentions
        for nick in players_nicks_from_discord:
            if nick in server_players:
                nicks.append(nick)
    return set(nicks)


def get_server_version() -> int:
    """Gets minor version of server"""
    with connect_query() as cl_q:
        version = cl_q.full_stats.version
    matches = findall(r"\d+", version)
    return int(matches[1])


def get_server_players() -> tuple:
    with connect_query() as cl_q:
        players = cl_q.full_stats.players
    return players


def shorten_url(url: str, max_length: int):
    if len(url) > max_length:
        return url[:max_length] + "..."
    else:
        return url


def get_clck_ru_url(url: str):
    return req_post("https://clck.ru/--", params={"url": url}).text


@contextmanager
def times(fade_in, duration, fade_out, rcon_client):
    rcon_client.run(f"title @a times {fade_in} {duration} {fade_out}")
    yield
    rcon_client.run("title @a reset")


def announce(player, message, rcon_client, subtitle=False):
    if get_server_version() >= 11 and not subtitle:
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


class Print_file_handler:
    def __init__(self):
        if Config.get_settings().bot_settings.log_bot_messages:
            self.file = open(Config.get_bot_log_name(), "a", encoding="utf8")
        else:
            self.file = None
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
