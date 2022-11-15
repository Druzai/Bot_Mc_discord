import socket
from asyncio import sleep as asleep
from contextlib import suppress
from datetime import datetime, timedelta
from os import chdir, system
from os.path import isfile
from pathlib import Path
from random import randint
from typing import Union, TYPE_CHECKING

from discord import (
    Activity, ActivityType, TextChannel, VoiceChannel, Thread as ChannelThread, GroupChannel, Interaction, Client
)
from discord.ext import commands

from components.error_handlers import _ignore_some_tasks_errors
from components.localization import get_translation
from components.minecraft.connect import connect_query, get_server_version, get_server_players, connect_rcon
from components.minecraft.game_chat import build_nickname_tellraw_for_bot
from components.utils import (
    get_author, send_msg, add_quotes, get_list_of_processes, get_time_string, delete_after_by_msg, get_bot_display_name,
    kill_server
)
from components.logs.utils import create_watcher
from config.init_config import Config, BotVars, OS

if TYPE_CHECKING:
    from cogs.poll_cog import Poll

if Config.get_os() == OS.Windows:
    from os import startfile


async def start_server(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        backups_thread=None,
        shut_up=False,
        is_reaction=False
):
    BotVars.is_loading = True
    author = get_author(ctx, bot, is_reaction)
    print(get_translation("Loading server by request of {0}").format(author))
    if ctx and not shut_up:
        await send_msg(ctx, add_quotes(get_translation("Loading server.......\nPlease wait)")), is_reaction=is_reaction)
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
                               is_reaction=is_reaction)
            else:
                print(get_translation("Target script of this shortcut '{0}' doesn't exists.")
                      .format(Config.get_selected_server_from_list().start_file_name))
                await send_msg(ctx, add_quotes(get_translation("Couldn't open shortcut because target script "
                                                               "doesn't exists! Retreating...")),
                               is_reaction=is_reaction)
        elif ex.__class__ is not ReferenceError:
            print(get_translation("Couldn't open script! Check naming and extension of the script!"))
            await send_msg(ctx, add_quotes(get_translation("Couldn't open script because of naming! Retreating...")),
                           is_reaction=is_reaction)
        else:
            if len(ex.args) == 0:
                print(get_translation("Couldn't open script because there is no command 'screen'! "
                                      "Install it via packet manager!"))
                await send_msg(ctx, add_quotes(get_translation("Couldn't open script because command 'screen' "
                                                               "wasn't installed! Retreating...")),
                               is_reaction=is_reaction)
            else:
                print(get_translation("Target of this shortcut '{0}' isn't '*.bat' file or '*.cmd' file.")
                      .format(Config.get_selected_server_from_list().start_file_name))
                await send_msg(ctx, add_quotes(get_translation("Couldn't open shortcut because target file "
                                                               "isn't a script! Retreating...")),
                               is_reaction=is_reaction)
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
                           is_reaction=is_reaction)
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
    print(get_translation("Server is running"))
    if ctx and not shut_up:
        await send_msg(ctx, author.mention + "\n" + add_quotes(get_translation("Server is up!")),
                       is_reaction=is_reaction)
        if randint(0, 8) == 0:
            await send_msg(ctx, get_translation("Kept you waiting, huh?"), is_reaction=is_reaction)
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
    author = get_author(ctx, bot, is_reaction)

    if "stop" in [p.command for p in poll.get_polls().values()]:
        if not is_reaction:
            await delete_after_by_msg(ctx.message)
        if not shut_up:
            await ctx.send(get_translation("{0}, bot already has poll on `stop`/`restart` command!")
                           .format(author.mention),
                           delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
        return

    try:
        players_info = get_server_players()
    except (ConnectionError, socket.error):
        if len(get_list_of_processes()) == 0:
            print(get_translation("Bot Exception: Couldn't connect to server, because it's stopped"))
            if not shut_up:
                await send_msg(ctx, add_quotes(get_translation("Couldn't connect to server to shut it down! "
                                                               "Server stopped...")), is_reaction=is_reaction)
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

            if not logged_only_author_accounts and await poll.timer(ctx, ctx.author, 5, "stop"):
                if not await poll.run(channel=ctx.channel if hasattr(ctx, 'channel') else ctx,
                                      message=get_translation("this man {0} trying to stop the server with {1} "
                                                              "player(s) on it. Will you let that happen?")
                                              .format(author.mention, players_info["current"]),
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
                                            if how_many_sec > 0 else "")), is_reaction=is_reaction)

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
                        bot_message = get_translation("Server will shut down in {0} seconds") \
                            .format(str(how_many_sec))
                    else:
                        bot_message = get_translation("Server will restart in {0} seconds").format(str(how_many_sec))

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
                           is_reaction=is_reaction)
    kill_server()
    BotVars.players_login_dict.clear()
    BotVars.auto_shutdown_start_date = None
    BotVars.is_stopping = False
    BotVars.is_server_on = False
    print(get_translation("Server is down"))
    if not shut_up:
        await send_msg(ctx, author.mention + "\n" + add_quotes(get_translation("Server has been shut down!")),
                       is_reaction=is_reaction)
    Config.get_server_config().states.stopped_info.set_state_info(author.id, datetime.now(), bot=author == bot.user)
    Config.save_server_config()
    task = bot.loop.create_task(
        bot.change_presence(activity=Activity(type=ActivityType.listening,
                                              name=Config.get_settings().bot_settings.idle_status)))
    task.add_done_callback(_ignore_some_tasks_errors)
