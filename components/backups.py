import socket
from contextlib import suppress
from datetime import datetime, timedelta
from os import walk, mkdir, remove
from os.path import join as p_join, getsize
from pathlib import Path
from shutil import rmtree
from threading import Thread, Event
from time import sleep
from typing import Union
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED, ZIP_BZIP2, ZIP_LZMA

from discord import Member, Interaction
from discord.ext import commands
from psutil import disk_usage

from components.localization import get_translation
from components.minecraft.connect import get_server_players, get_server_version, connect_rcon
from components.minecraft.game_chat import build_nickname_tellraw_for_bot
from components.utils import (
    get_bot_display_name, add_quotes, get_time_string, get_file_size, get_human_readable_size, get_folder_size,
    get_member_string, send_msg
)
from config.init_config import Config, BotVars, ServerProperties


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

    tellraw_init = []
    if use_rcon:
        tellraw_msg = ""
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
            msg = get_translation(
                "Deleted auto backup dated {0} because of {1}"
            ).format(backup.file_creation_date.strftime(get_translation("%H:%M:%S %d/%m/%Y")), reason)
        else:
            if member_name is not None:
                member = member_name
            else:
                member = get_member_string(bot, backup.initiator)
            msg = get_translation(
                "Deleted backup dated {0} made by {1} because of {2}"
            ).format(backup.file_creation_date.strftime(get_translation("%H:%M:%S %d/%m/%Y")), member, reason)
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


async def warn_about_auto_backups(ctx: Union[commands.Context, Interaction], bot: commands.Bot, is_reaction=False):
    if Config.get_backups_settings().automatic_backup:
        if len(Config.get_server_config().backups) > 0 \
                and handle_backups_limit_and_size(bot) is not None \
                and all([b.initiator for b in Config.get_server_config().backups]):
            await send_msg(
                ctx,
                get_translation("Bot has backups only from members for `{0}` server, "
                                "so keep in mind, that bot will delete oldest backup "
                                "on next auto backup!").format(Config.get_selected_server_from_list().server_name),
                is_reaction=is_reaction
            )
