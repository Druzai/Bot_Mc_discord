import inspect
from ast import literal_eval
from asyncio import sleep as asleep
from contextlib import contextmanager, suppress
from datetime import datetime
from hashlib import md5
from itertools import chain
from json import load, dump, JSONDecodeError
from os import chdir, system
from os.path import basename
from pathlib import Path
from random import randint
from re import search, split, findall
from sys import platform, argv
from typing import Tuple, List

from discord import Activity, ActivityType, TextChannel
from discord.ext import commands
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r
from psutil import process_iter, NoSuchProcess
from requests import post as req_post

from commands.poll import Poll
from components.localization import get_translation
from components.watcher_handle import create_watcher
from config.init_config import Config, BotVars

if platform == "win32":
    from os import startfile

__all__ = [
    "server_checkups", "send_error", "send_msg", "send_status", "stop_server", "start_server",
    "get_author_and_mention", "save_to_whitelist_json", "get_whitelist_entry", "get_server_online_mode",
    "get_server_players", "add_quotes", "bot_status", "bot_list", "bot_start", "bot_stop", "bot_restart",
    "connect_rcon", "make_underscored_line"
]


async def send_msg(ctx, msg, is_reaction=False):
    if is_reaction:
        await ctx.send(content=msg,
                       delete_after=Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
    else:
        await ctx.send(msg)


def add_quotes(msg: str) -> str:
    return f"```{msg}```"


async def delete_after_by_msg_id(ctx, message_id):
    await asleep(Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
    msg = await ctx.channel.fetch_message(message_id)
    await msg.delete()


def get_author_and_mention(ctx, bot, is_reaction=False):
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
        await send_msg(ctx, add_quotes(get_translation("server have already started!").capitalize()), is_reaction)
    else:
        if BotVars.is_loading:
            await send_msg(ctx, add_quotes(get_translation("server is loading!").capitalize()), is_reaction)
        elif BotVars.is_stopping:
            await send_msg(ctx, add_quotes(get_translation("server is stopping!").capitalize()), is_reaction)
        else:
            await send_msg(ctx, add_quotes(get_translation("server have already been stopped!").capitalize()),
                           is_reaction)


async def start_server(ctx, bot, shut_up=False, is_reaction=False):
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
    except BaseException:
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
            await bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                        name=Config.get_settings().bot_settings.idle_status))
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
                                                                                           " sec")
        await bot.change_presence(activity=Activity(type=ActivityType.listening, name=output_bot))
        await asleep(Config.get_awaiting_times_settings().await_seconds_when_connecting_via_rcon)
        with suppress(BaseException):
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
    BotVars.is_loading = False
    BotVars.is_server_on = True
    if BotVars.is_restarting:
        BotVars.is_restarting = False
    Config.get_server_config().states.started_info.set_state_info(str(author),
                                                                  datetime.now().strftime("%d/%m/%y, %H:%M:%S"))
    Config.save_server_config()
    await bot.change_presence(activity=Activity(type=ActivityType.playing,
                                                name=Config.get_settings().bot_settings.gaming_status))


async def stop_server(ctx, bot, poll, how_many_sec=10, is_restart=False, is_reaction=False):
    no_connection = False
    players_count = 0

    try:
        players_count = len(get_server_players())
    except BaseException:
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
                                      remove_logs_after=5):
                    return

        BotVars.is_stopping = True
        print(get_translation("Stopping server"))
        await send_msg(ctx, add_quotes(get_translation("Stopping server.......\nPlease wait {0} sec.")
                                       .format(str(how_many_sec))), is_reaction)

        with connect_rcon() as cl_r:
            if players_count == 0:
                how_many_sec = 0
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

                cl_r.tellraw("@a", ["", {"text": "<"}, {"text": bot.user.display_name, "color": "dark_gray"},
                                    {"text": "> " + bot_message}])
                for i in range(how_many_sec, -1, -w):
                    cl_r.tellraw("@a", ["", {"text": "<"}, {"text": bot.user.display_name, "color": "dark_gray"},
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
            except BaseException:
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
                                                                  datetime.now().strftime("%d/%m/%y, %H:%M:%S"))
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
                    and abs(int(proc.create_time()) - BotVars.server_start_time) < 5:
                list_proc.append(proc)
    return list_proc


def kill_server():
    list_proc = get_list_of_processes()
    if len(list_proc) != 0:
        for p in list_proc:
            with suppress(NoSuchProcess):
                p.kill()
    BotVars.server_start_time = None


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
        if not BotVars.is_server_on:
            BotVars.is_server_on = True
        if (BotVars.watcher_of_log_file is None or not BotVars.watcher_of_log_file.is_running()) and \
                Config.get_cross_platform_chat_settings().enable_cross_platform_chat and \
                Config.get_cross_platform_chat_settings().channel_id and \
                Config.get_cross_platform_chat_settings().webhook_url:
            if BotVars.watcher_of_log_file is None:
                create_watcher()
            BotVars.watcher_of_log_file.start()
        number_match = findall(r", \d+", bot.guilds[0].get_member(bot.user.id).activities[0].name)
        if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 0 or info.num_players != 0 or \
                (len(number_match) > 0 and number_match[0].split(" ")[-1] != 0):
            await bot.change_presence(activity=Activity(type=ActivityType.playing,
                                                        name=Config.get_settings().bot_settings.gaming_status +
                                                             ", " + str(info.num_players) +
                                                             get_translation(" player(s) online")))
    except BaseException:
        if len(get_list_of_processes()) == 0:
            if BotVars.is_server_on:
                BotVars.is_server_on = False
            if BotVars.watcher_of_log_file is not None and BotVars.watcher_of_log_file.is_running():
                BotVars.watcher_of_log_file.stop()
        if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 2:
            await bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                        name=Config.get_settings().bot_settings.idle_status +
                                                             (" 🤔" if len(
                                                                 get_list_of_processes()) != 0 else "")))
        if Config.get_settings().bot_settings.forceload and not BotVars.is_stopping \
                and not BotVars.is_loading and not BotVars.is_restarting:
            sent = False
            for guild in bot.guilds:
                if sent:
                    break
                for channel in guild.channels:
                    if not isinstance(channel, TextChannel):
                        continue
                    with suppress(BaseException):
                        if Config.get_settings().bot_settings.menu_id is not None:
                            await channel.fetch_message(Config.get_settings().bot_settings.menu_id)
                        await send_msg(ctx=channel,
                                       msg=add_quotes(get_translation("Bot detected: Server\'s offline!\n"
                                                                      "Time: {0}\n"
                                                                      "Starting up server again!").format(
                                           datetime.now().strftime("%d/%m/%y, %H:%M:%S"))),
                                       is_reaction=True)
                        await start_server(ctx=channel, bot=bot, shut_up=True, is_reaction=True)
                        sent = True
                        break
    if Config.get_awaiting_times_settings().await_seconds_in_check_ups > 0:
        await asleep(Config.get_awaiting_times_settings().await_seconds_in_check_ups)


async def bot_status(ctx, is_reaction=False):
    states = ""
    states_info = Config.get_server_config().states
    if states_info.started_info.date is not None and states_info.started_info.user is not None:
        states += get_translation("Server has been started at {0}, by {1}").format(states_info.started_info.date,
                                                                                   states_info.started_info.user) \
                  + "\n"
    if states_info.stopped_info.date is not None and states_info.stopped_info.user is not None:
        states += get_translation("Server has been stopped at {0}, by {1}").format(states_info.stopped_info.date,
                                                                                   states_info.stopped_info.user) \
                  + "\n"
    states = states.strip("\n")
    if BotVars.is_server_on:
        try:
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
            await send_msg(ctx, add_quotes(get_translation("server online").capitalize() + "\n" +
                                           get_translation("Server address: ") +
                                           Config.get_settings().bot_settings.ip_address + "\n"
                                           + message + str((6 + time_ticks // 1000) % 24) + ":"
                                           + f"{((time_ticks % 1000) * 60 // 1000):02d}"
                                           + "\n" + get_translation("Selected server: ") +
                                           Config.get_selected_server_from_list().server_name + "\n" + states),
                           is_reaction)
        except BaseException:
            await send_msg(ctx,
                           add_quotes(get_translation("server online").capitalize() + "\n" +
                                      get_translation("Server address: ") +
                                      Config.get_settings().bot_settings.ip_address +
                                      "\n" + get_translation("Server thinking...") +
                                      "\n" + get_translation("Selected server: ") +
                                      Config.get_selected_server_from_list().server_name + "\n" + states),
                           is_reaction)
            print(get_translation("Server's down via rcon"))
    else:
        await send_msg(ctx, add_quotes(get_translation("server offline").capitalize() + "\n" +
                                       get_translation("Server address: ") +
                                       Config.get_settings().bot_settings.ip_address +
                                       "\n" + get_translation("Selected server: ") +
                                       Config.get_selected_server_from_list().server_name +
                                       "\n" + states),
                       is_reaction)


async def bot_list(ctx, bot, is_reaction=False):
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
    except BaseException:
        author_mention = get_author_and_mention(ctx, bot, is_reaction)[1]
        await send_msg(ctx, f"{author_mention}, " + get_translation("server offline"), is_reaction)


async def bot_start(ctx, bot, is_reaction=False):
    if not BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading:
        await start_server(ctx, bot=bot, is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_stop(ctx, command, bot, poll, is_reaction=False):
    if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading:
        if BotVars.is_doing_op:
            await send_msg(ctx, add_quotes(get_translation("Some player(s) still oped, waiting for them")),
                           is_reaction)
            return
        if Config.get_settings().bot_settings.forceload:
            Config.get_settings().bot_settings.forceload = False
            Config.save_config()
        await stop_server(ctx, bot, poll, int(command), is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_restart(ctx, command, bot, poll, is_reaction=False):
    if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading:
        if BotVars.is_doing_op:
            await send_msg(ctx, add_quotes(get_translation("Some player(s) still oped, waiting for them")),
                           is_reaction)
            return
        BotVars.is_restarting = True
        print(get_translation("Restarting server"))
        await stop_server(ctx, bot, poll, int(command), True, is_reaction=is_reaction)
        await start_server(ctx, bot, is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_clear(ctx, poll: Poll, subcommand: str = None, count: int = None):
    message_created = None
    mentions = set()
    if len(ctx.message.role_mentions):
        mentions.update(ctx.message.mentions)
    if len(ctx.message.role_mentions):
        for role in ctx.message.role_mentions:
            mentions.update(role.members)
    if len(mentions):
        check_condition = lambda m: m.author in mentions and m.id not in poll.get_polls_msg_ids()
    elif len(mentions) == 0 and not len(ctx.message.channel_mentions):
        check_condition = lambda m: m.id not in poll.get_polls_msg_ids()
    else:
        await ctx.send(get_translation("You should mention ONLY members or roles of this server!"))
        return
    delete_limit = Config.get_settings().bot_settings.deletion_messages_limit_without_poll + 1

    if subcommand is None:
        if count > 0:
            if delete_limit == 0 or len(await ctx.channel.history(limit=count + 1).flatten()) <= delete_limit:
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
        if await poll.run(ctx=ctx,
                          message=get_translation("this man {0} trying to delete some history"
                                                  " of this channel. Will you let that happen?")
                                  .format(ctx.author.mention),
                          remove_logs_after=5):
            if count < 0 or subcommand == "reply":
                await ctx.channel.purge(limit=None, check=check_condition, after=message_created, bulk=False)
            else:
                await ctx.channel.purge(limit=count + 1, check=check_condition, bulk=False)


def parse_params_for_help(command_params: dict, string_to_add: str, create_params_dict=False) -> Tuple[str, dict]:
    params = {}
    for arg_name, arg_data in command_params.items():
        if create_params_dict:
            if arg_data.annotation != inspect._empty:
                if not getattr(arg_data.annotation, '__name__', None) is None:
                    params[arg_name] = getattr(arg_data.annotation, '__name__', None)
                else:
                    params[arg_name] = str(arg_data.annotation).replace("typing.", "")
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
                             ("..." if arg_data.kind == arg_data.VAR_POSITIONAL else "") + "]"
        else:
            string_to_add += f" <{arg_name}>"
    return string_to_add, params


def parse_subcommands_for_help(command, all_params=False) -> Tuple[List[str], List[str]]:
    if not hasattr(command, "commands") or len(command.commands) == 0:
        return [], []

    if not all_params:
        return [c.name for c in command.commands], []

    subcommands = []
    for subcommand in command.commands:
        subcommands.append(parse_params_for_help(subcommand.clean_params, subcommand.name)[0])
    return [c.name for c in command.commands], subcommands


async def send_help_of_command(ctx, command):
    subcommands_names, subcommands = parse_subcommands_for_help(command, True)
    str_help = f"{Config.get_settings().bot_settings.prefix}{command}"
    str_help += " " + " | ".join(subcommands_names) if len(subcommands_names) else ""
    str_params, params = parse_params_for_help(command.clean_params, "", True)
    if len(str_params):
        str_help += " |" + str_params if len(subcommands_names) else str_params

    str_help += "\n\n" + get_translation("Description") + ":\n"
    str_help += get_translation(f'help_{"_".join(str(command).split())}') \
                    .format(prefix=Config.get_settings().bot_settings.prefix) + "\n\n"
    if len(command.aliases):
        str_help += get_translation("Aliases") + ": " + ", ".join(command.aliases) + "\n\n"

    if len(subcommands):
        str_help += get_translation("Subcommands") + ":\n" + "\n".join(subcommands) + "\n\n"

    if len(params.keys()):
        str_help += get_translation("Parameters") + ":\n"
        for arg_name, arg_type in params.items():
            str_help += f"{arg_name}: {arg_type}\n" + \
                        get_translation(f'help_{"_".join(str(command).split())}_{arg_name}') \
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


def get_server_online_mode():
    filepath = Path(Config.get_selected_server_from_list().working_directory + "/server.properties")
    if not filepath.exists():
        raise RuntimeError(get_translation("File '{0}' doesn't exist!").format(filepath.as_posix()))
    with open(filepath, "r") as f:
        for i in f.readlines():
            if i.find("online-mode") >= 0:
                return literal_eval(i.split("=")[1].capitalize())


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
        print(get_translation("{0} entered a command that only works in the guild"))
        await send_msg(ctx, f"{author_mention}\n" +
                       add_quotes(get_translation("this command only works on server").capitalize()),
                       is_reaction)
    elif isinstance(error, commands.CheckFailure):
        pass
    else:
        print(", ".join(error.args))
        await send_msg(ctx, f"{author_mention}\n" + add_quotes(", ".join(error.original.args)), is_reaction)


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
        if len(get_server_players()) > 0:
            result_msg = _handle_custom_emojis(message)
            result_msg = await _handle_reply_in_message(message, result_msg)
            result_msg = _handle_urls_and_attachments_in_message(result_msg, message)

            # Building object for tellraw
            res_obj = ["", {"text": "<"}, {"text": message.author.display_name, "color": "dark_gray"},
                       {"text": "> "}]
            if result_msg.get("reply", None) is not None:
                if isinstance(result_msg.get("reply"), list) and isinstance(result_msg.get("reply")[1], str):
                    res_obj.extend([{"text": result_msg.get("reply")[0], "color": "gray"},
                                    {"text": result_msg.get("reply")[1], "color": "dark_gray"}])
                    _build_if_urls_in_message(res_obj, result_msg.get("reply")[2], "gray")
                else:
                    _build_if_urls_in_message(res_obj, result_msg.get("reply"), "gray")
            if on_edit:
                result_before = _handle_custom_emojis(before_message)
                result_before = _handle_urls_and_attachments_in_message(result_before, before_message, True)
                content_name = "contents" if get_server_version() >= 1.16 else "value"
                res_obj.append({"text": "*", "color": "gold",
                                "hoverEvent": {"action": "show_text", content_name: result_before.get("content")}})
            _build_if_urls_in_message(res_obj, result_msg.get("content"), None)

            with connect_rcon() as cl_r:
                cl_r.tellraw("@a", res_obj)

            delete_user_message = False
            nicks = _search_mentions_in_message(message)
            if len(nicks) > 0:
                with suppress(BaseException):
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
        await delete_after_by_msg_id(message, message.id)


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
            result_msg["reply"] = f"\n -> {cnt}\n"
        else:
            # Reply to discord user
            nick = (await message.guild.fetch_member(reply_msg.author.id)).display_name
            result_msg["reply"] = ["\n -> <", nick, f"> {cnt}\n"]
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
                if (key == "content" and len("".join(temp_split)) != 0) or \
                        (key == "reply" and "".join(temp_split) != "> "):
                    temp_split.append(" ")
                if only_replace_links:
                    temp_split.append(i[0])
                else:
                    temp_split.append(i)

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


def get_server_version() -> float:
    with connect_query() as cl_q:
        version = cl_q.full_stats.version
    if search(r"\d+\.\d+\.\d+", version):
        matches = findall(r"\d+", version)
        return float(f"{matches[0]}.{matches[1]}")
    elif search(r"\d+\.\d+", version):
        return float(version)


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
    if get_server_version() >= 1.11 and not subtitle:
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
