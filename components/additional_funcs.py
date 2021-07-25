from asyncio import sleep as asleep
from contextlib import contextmanager
from datetime import datetime
from os import chdir, system
from pathlib import Path
from random import choice, randint
from re import search, split, findall
from string import ascii_letters, digits
from sys import platform

from discord import Activity, ActivityType
from discord.ext import commands
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r
from psutil import process_iter, NoSuchProcess

from components.watcher_handle import create_watcher
from config.init_config import Config, Bot_variables

if platform == "win32":
    from os import startfile


async def send_msg(ctx, msg, IsReaction=False):
    if IsReaction:
        await ctx.send(content=msg, delete_after=Config.get_await_time_before_message_deletion())
    else:
        await ctx.send(msg)


async def delete_after_by_msg_id(ctx, message_id):
    await asleep(Config.get_await_time_before_message_deletion())
    msg = await ctx.channel.fetch_message(message_id)
    await msg.delete()


def get_author_and_mention(ctx, bot, IsReaction=False):
    if IsReaction:
        author_mention = Bot_variables.react_auth.mention
        author = Bot_variables.react_auth
    else:
        if hasattr(ctx, 'author'):
            author_mention = ctx.author.mention
            author = ctx.author
        else:
            author_mention = bot.user.mention
            author = bot.user
    return author, author_mention


async def send_status(ctx, IsReaction=False):
    if Bot_variables.IsServerOn:
        await send_msg(ctx, "```Server have already started!```", IsReaction)
    else:
        if Bot_variables.IsLoading:
            await send_msg(ctx, "```Server is loading!```", IsReaction)
        elif Bot_variables.IsStopping:
            await send_msg(ctx, "```Server is stopping!```", IsReaction)
        else:
            await send_msg(ctx, "```Server have already been stopped!```", IsReaction)


async def start_server(ctx, bot, shut_up=False, IsReaction=False):
    Bot_variables.IsLoading = True
    print("Loading server")
    if ctx and not shut_up:
        await send_msg(ctx, "```Loading server.......\nPlease wait)```", IsReaction)
    chdir(Path(Config.get_selected_server_list()[0]))
    try:
        if platform == "linux" or platform == "linux2":
            system("screen -dmS " + Config.get_selected_server_list()[1].replace(" ", "_") +
                   " ./" + Config.get_filename() + ".sh")
        elif platform == "win32":
            startfile(Config.get_filename() + ".bat")
        Bot_variables.server_start_time = int(datetime.now().timestamp())
    except BaseException:
        print("Couldn't open script! Check naming!")
        await send_msg(ctx, "```Couldn't open script because of naming! Retreating...```", IsReaction)
        Bot_variables.IsLoading = False
        if Bot_variables.IsRestarting:
            Bot_variables.IsRestarting = False
        return
    chdir(Config.get_bot_config_path())
    await asleep(5)
    check_time = datetime.now()
    while True:
        if (datetime.now() - check_time).seconds > 1000:
            await send_msg(ctx, "```Error while loading server```", IsReaction)
            Bot_variables.IsLoading = False
            if Bot_variables.IsRestarting:
                Bot_variables.IsRestarting = False
            return
        timedelta_secs = (datetime.now() - check_time).seconds
        if Bot_variables.progress_bar_time:
            percentage = round((timedelta_secs / Bot_variables.progress_bar_time) * 100)
            output_bot = "Loading: " + ((str(percentage) + "%") if percentage < 101 else "100%...")
        else:
            output_bot = "Server, elapsed time: " + (
                str(timedelta_secs // 60) + ":" + f"{(timedelta_secs % 60):02d}" if timedelta_secs // 60 != 0 else str(
                    timedelta_secs % 60) + " sec")
        await bot.change_presence(activity=Activity(type=ActivityType.listening, name=output_bot))
        await asleep(Config.get_await_time_to_sleep())
        try:
            with Client_q(Config.get_local_address(), Bot_variables.port_query, timeout=0.5) as cl_q:
                _ = cl_q.basic_stats
            break
        except BaseException:
            pass
    if Config.get_crossplatform_chat() and Config.get_discord_channel_id_for_crossplatform_chat() and \
            Config.get_webhook_chat():
        create_watcher()
        Bot_variables.watcher_of_log_file.start()
    if Bot_variables.progress_bar_time:
        Bot_variables.progress_bar_time = (Bot_variables.progress_bar_time + (datetime.now() - check_time).seconds) // 2
    else:
        Bot_variables.progress_bar_time = (datetime.now() - check_time).seconds
    author, author_mention = get_author_and_mention(ctx, bot, IsReaction)
    if ctx and not shut_up:
        await send_msg(ctx, author_mention + "\n```Server's on now```", IsReaction)
        print("Server on!")
        if randint(0, 8) == 0:
            await send_msg(ctx, "Kept you waiting, huh?", IsReaction)
    Bot_variables.IsLoading = False
    Bot_variables.IsServerOn = True
    if Bot_variables.IsRestarting:
        Bot_variables.IsRestarting = False
    if Config.get_selected_server_list()[2] != Bot_variables.progress_bar_time:
        mine_dir_list = Config.get_minecraft_dirs_list()
        mine_dir_list[Config.get_selected_minecraft_server_number()][2] = Bot_variables.progress_bar_time
        Config.set_minecraft_dirs_list(mine_dir_list)
    server_dates = Config.read_server_dates()
    server_dates[0] = [datetime.now().strftime("%d/%m/%y, %H:%M:%S"), str(author)]
    Config.save_server_dates(server_dates)
    await bot.change_presence(activity=Activity(type=ActivityType.playing, name="Minecraft Server"))


async def stop_server(ctx, bot, How_many_sec=10, IsRestart=False, IsReaction=False):
    Bot_variables.IsStopping = True
    print("Stopping server")
    await send_msg(ctx, "```Stopping server.......\nPlease wait " + str(How_many_sec) + " sec.```",
                   IsReaction)
    try:
        with Client_r(Config.get_local_address(), Bot_variables.port_rcon, timeout=1) as cl_r:
            cl_r.login(Bot_variables.rcon_pass)
            if How_many_sec != 0:
                w = 1
                if How_many_sec > 5:
                    while True:
                        w += 1
                        if How_many_sec % w == 0 and w <= 10:
                            break
                        elif How_many_sec % w == 0 and w > 10:
                            How_many_sec += 1
                            w = 1
                if not IsRestart:
                    cl_r.say('Server\'s shutting down in ' + str(How_many_sec) + ' seconds')
                else:
                    cl_r.say('Server\'s restarting in ' + str(How_many_sec) + ' seconds')
                for i in range(How_many_sec, -1, -w):
                    cl_r.say(str(i) + ' sec to go')
                    await asleep(w)
            cl_r.run("stop")
    except BaseException:
        print("Exception: Couldn't connect to server, so killing it now...")
        await send_msg(ctx, "Couldn't connect to server to shut it down! Killing it now...", IsReaction)
        Bot_variables.IsStopping = False
        kill_server()
        return
    if Bot_variables.watcher_of_log_file.isrunning():
        Bot_variables.watcher_of_log_file.stop()
    while True:
        await asleep(Config.get_await_time_to_sleep())
        try:
            with Client_q(Config.get_local_address(), Bot_variables.port_query, timeout=0.5) as cl_q:
                _ = cl_q.basic_stats
        except BaseException:
            break
    kill_server()
    Bot_variables.IsStopping = False
    Bot_variables.IsServerOn = False
    author, author_mention = get_author_and_mention(ctx, bot, IsReaction)
    print("Server's off now")
    await send_msg(ctx, author_mention + "\n```Server's off now```", IsReaction)
    server_dates = Config.read_server_dates()
    server_dates[1] = [datetime.now().strftime("%d/%m/%y, %H:%M:%S"), str(author)]
    Config.save_server_dates(server_dates)
    await bot.change_presence(activity=Activity(type=ActivityType.listening, name="Server"))


def get_list_of_processes() -> list:
    process_name = "java"
    list_proc = []

    for proc in process_iter():
        parents_name_list = [i.name() for i in proc.parents()]
        if process_name in proc.name() and ("screen" in parents_name_list or
                                            "Discord_bot.exe" in parents_name_list or
                                            "python.exe" in parents_name_list) \
                and abs(int(proc.create_time()) - Bot_variables.server_start_time) < 5:
            list_proc.append(proc)
    return list_proc


def kill_server():
    list_proc = get_list_of_processes()
    if len(list_proc) != 0:
        for p in list_proc:
            try:
                p.kill()
            except NoSuchProcess:
                pass
    Bot_variables.server_start_time = None


async def server_checkups(bot, always=True):
    while True:
        try:
            with Client_q(Config.get_local_address(), Bot_variables.port_query, timeout=1) as cl_q:
                info = cl_q.full_stats
            if info.num_players != 0:
                nicks_n_keys_add = {}
                for i in info.players:
                    i = i.lower()
                    if i not in Config.read_op_keys().keys():
                        nicks_n_keys_add.update({i: [generate_access_code() for _ in range(25)]})
                if nicks_n_keys_add:
                    print("New codes generated")
                    for k, v in nicks_n_keys_add.items():
                        print("For player with nickname " + k + " generated these codes:")
                        for c in v:
                            print("\t" + c)
                    orig_op = Config.read_op_keys()
                    orig_op.update(nicks_n_keys_add)
                    Config.save_op_keys(orig_op)
                    orig_op.clear()
            if not Bot_variables.IsServerOn:
                Bot_variables.IsServerOn = True
            if Config.get_crossplatform_chat() and Config.get_discord_channel_id_for_crossplatform_chat() and \
                    Config.get_webhook_chat():
                create_watcher()
                Bot_variables.watcher_of_log_file.start()
            try:
                if int(bot.guilds[0].get_member(bot.user.id).activities[0].name.split(", ")[1].split(" ")[
                           0]) != 0 or info.num_players != 0:
                    await bot.change_presence(
                        activity=Activity(type=ActivityType.playing,
                                          name="Minecraft Server, " + str(
                                              info.num_players) + " player(s) online"))
            except BaseException:
                if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 0 or info.num_players != 0:
                    await bot.change_presence(
                        activity=Activity(type=ActivityType.playing,
                                          name="Minecraft Server, " + str(
                                              info.num_players) + " player(s) online"))
        except BaseException:
            if len(get_list_of_processes()) == 0:
                if Bot_variables.IsServerOn:
                    Bot_variables.IsServerOn = False
                if Bot_variables.watcher_of_log_file is not None and Bot_variables.watcher_of_log_file.isrunning():
                    Bot_variables.watcher_of_log_file.stop()
            if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 2:
                await bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                            name="Server" + (" thinking..." if len(
                                                                get_list_of_processes()) != 0 else "")))
            if always and Config.get_forceload() and not Bot_variables.IsStopping \
                    and not Bot_variables.IsLoading and not Bot_variables.IsRestarting:
                for guild in bot.guilds:
                    for channel in guild.channels:
                        try:
                            await channel.fetch_message(Config.get_menu_id())
                            await send_msg(ctx=channel,
                                           msg=f'```Bot detected: Server\'s offline!\nTime: {datetime.now().strftime("%d/%m/%y, %H:%M:%S")}\nStarting up server again!```',
                                           IsReaction=True)
                            await start_server(ctx=channel, bot=bot, shut_up=True)
                            break
                        except BaseException:
                            pass
        if Config.get_await_time_check_ups() > 0 and always:
            await asleep(Config.get_await_time_check_ups())
        if not always:
            break


def generate_access_code(length=16, sep='-', sep_interval=4) -> str:
    """Генератор кодов доступа
    Частота повторений символов вариативная для кода
    в пределах от 1 к 2, до 1 к 1000
    :param length: Длинна кода в символах, без учёта разделителей
    :param sep: Символ разделитель внутри кода, для читаемости
    :param sep_interval: Шаг раздела, 0 для отключения разделения
    :return: Код доступа
    """
    alphabit = digits + ascii_letters
    code = ''
    duplicate_chance = randint(1, 1000)
    for i in range(length):
        if i and sep_interval and not i % sep_interval:
            code += sep
        candidat_symb = choice(alphabit)
        while candidat_symb in code and randint(0, duplicate_chance):
            candidat_symb = choice(alphabit)
        code += candidat_symb
    return code


# Handling errors
async def send_error(ctx, bot, error, IsReaction=False):
    author, author_mention = get_author_and_mention(ctx, bot, IsReaction)
    if isinstance(error, commands.MissingRequiredArgument):
        print(f'{author} не указал аргумент')
        await send_msg(ctx, f'{author_mention}, пожалуйста, введи все аргументы', IsReaction)
    elif isinstance(error, commands.MissingPermissions):
        print(f'У {author} мало прав для команды')
        await send_msg(ctx, f'{author_mention}, у вас недостаточно прав для выполнения этой команды',
                       IsReaction)
    elif isinstance(error, commands.MissingRole):
        print(f'У {author} нет роли "{error.missing_role}" для команды')
        await send_msg(ctx,
                       f'{author_mention}, у вас нет роли "{error.missing_role}" для выполнения этой команды',
                       IsReaction)
    elif isinstance(error, commands.CommandNotFound):
        print(f'{author} ввёл несуществующую команду')
        await send_msg(ctx, f'{author_mention}, вы ввели несуществующую команду', IsReaction)
    elif isinstance(error, commands.UserInputError):
        print(f'{author} неправильно ввёл аргумент(ы) команды')
        await send_msg(ctx, f'{author_mention}, вы неправильно ввели агрумент(ы) команды', IsReaction)
    elif isinstance(error, commands.DisabledCommand):
        print(f'{author} ввёл отключённую команду')
        await send_msg(ctx, f'{author_mention}, вы ввели отлючённую команду', IsReaction)
    else:
        print(", ".join(error.args))
        await send_msg(ctx, ", ".join(error.args), IsReaction)


async def handle_message_for_chat(message, bot, need_to_delete_on_error: bool, on_edit=False, before_message=None):
    if message.author == bot.user or message.content.startswith(Config.get_prefix()) or str(
            message.author.discriminator) == "0000" or len(message.content) == 0 or \
            message.channel.id != int(Config.get_discord_channel_id_for_crossplatform_chat()):
        return

    _, author_mention = get_author_and_mention(message, bot, False)
    delete_user_message = True

    if not Config.get_discord_channel_id_for_crossplatform_chat() or not Config.get_webhook_chat():
        await send_msg(message.channel, f"{author_mention}, this chat can't work! Crossplatform chat disabled!",
                       True)
    elif not Bot_variables.IsServerOn:
        await send_msg(message.channel, f"{author_mention}, server offline!", True)
    elif Bot_variables.IsRestarting:
        await send_msg(message.channel, f"{author_mention}, server is restarting!", True)
    elif Bot_variables.IsStopping and Bot_variables.watcher_of_log_file is None:
        await send_msg(message.channel, f"{author_mention}, server is stopping!", True)
    elif Bot_variables.IsLoading:
        await send_msg(message.channel, f"{author_mention}, server is loading!", True)
    else:
        result_msg = _handle_custom_emojis(message)
        result_msg = await _handle_reply_in_message(message, result_msg)
        result_msg = await _handle_mentions_in_message(message, result_msg)

        # Building object for tellraw
        res_obj = ["", {"text": "<"}, {"text": message.author.display_name, "color": "dark_gray"},
                   {"text": "> "}]
        if result_msg.get("reply", None) is not None:
            if isinstance(result_msg.get("reply"), list):
                res_obj.extend([{"text": result_msg.get("reply")[0], "color": "gray"},
                                {"text": result_msg.get("reply")[1], "color": "dark_gray"},
                                {"text": result_msg.get("reply")[2], "color": "gray"}])
            else:
                res_obj.append({"text": result_msg.get("reply"), "color": "gray"})
        if on_edit:
            result_before = _handle_custom_emojis(before_message)
            result_before = await _handle_mentions_in_message(before_message, result_before)
            if float(get_server_version()) >= 1.16:
                res_obj.append({"text": "*", "color": "gold",
                                "hoverEvent": {"action": "show_text", "contents": result_before.get("content")}})
            else:
                res_obj.append({"text": "*", "color": "gold",
                                "hoverEvent": {"action": "show_text", "value": result_before.get("content")}})
        res_obj.append({"text": result_msg.get("content")})

        with Client_r(Config.get_local_address(), Bot_variables.port_rcon, timeout=1) as cl_r:
            cl_r.login(Bot_variables.rcon_pass)
            answ = cl_r.tellraw("@a", res_obj)
            # TODO: Replace with checking via query num of players for localization!

        if answ == '':
            delete_user_message = False
            nicks = _search_mentions_in_message(result_msg.get("content"))
            if len(nicks) > 0:
                try:
                    with Client_r(Config.get_local_address(), Bot_variables.port_rcon, timeout=1) as cl_r:
                        cl_r.login(Bot_variables.rcon_pass)
                        with times(500, 2500, 1500, cl_r):
                            for nick in nicks:
                                announce(nick,
                                         f"@{message.author.display_name} -> @{nick if nick != '@a' else 'everyone'}",
                                         cl_r)
                except BaseException:
                    pass
        else:
            await send_msg(message.channel, f"{author_mention}, {answ.lower()}!", True)

    if delete_user_message and need_to_delete_on_error:
        await delete_after_by_msg_id(message, message.id)


def _handle_custom_emojis(message):
    result_msg = {}
    if search(r"<:\w+:\d+>", message.content.strip()):
        temp_split = split(r"<:\w+:\d+>", message.content.strip())
        temp_arr = list(findall(r"<:\w+:\d+>", message.content.strip()))
        i = 1
        for emoji in temp_arr:
            temp_split.insert(i, findall(r"\w+", emoji)[0])
            i += 2
        result_msg["content"] = "".join(temp_split)
    else:
        result_msg["content"] = message.content.strip()
    return result_msg


async def _handle_reply_in_message(message, result_msg):
    if message.reference is not None:
        reply_msg = message.reference.resolved
        if reply_msg.author.discriminator == "0000":
            # reply to minecraft player
            cnt = reply_msg.content.strip()
            cnt = cnt.replace("**<", "<").replace(">**", ">")
            result_msg["reply"] = f"\n -> {cnt}\n"
        else:
            # Reply to discord user
            nick = (await message.guild.fetch_member(reply_msg.author.id)).display_name
            result_msg["reply"] = ["\n -> <", nick, f"> {reply_msg.content.strip()}\n"]
    return result_msg


async def _handle_mentions_in_message(message, result_msg):
    for key, ms in result_msg.items():
        if isinstance(ms, list):
            msg = ms.copy()
            msg = msg[-1]
        else:
            msg = ms
        if search(r"<@!\d+>", msg):
            temp_split = split(r"<@!\d+>", msg)
            temp_arr = list(findall(r"<@!\d+>", msg))
            i = 1
            for mention in temp_arr:
                ins = "@" + (await message.guild.fetch_member(int(findall(r"\d+", mention)[0]))).display_name
                temp_split.insert(i, ins)
                i += 2
            if isinstance(ms, list):
                result_msg[key] = [ms[0], ms[1], "".join(temp_split)]
            else:
                result_msg[key] = "".join(temp_split)
    return result_msg


def _search_mentions_in_message(result_msg) -> list:
    players_nicks_minecraft = get_server_players()
    players_nicks_from_discord = [i[1:] for i in findall(r"@.+", result_msg)]
    nicks = []
    for nick in players_nicks_from_discord:
        if nick in players_nicks_minecraft:
            nicks.append(nick)
        elif nick == "everyone":
            nicks.clear()
            nicks.append("@a")
            break
    return nicks


def get_server_version() -> str:
    with Client_q(Config.get_local_address(), Bot_variables.port_query, timeout=1) as cl_r:
        version = cl_r.full_stats.version
    return version


def get_server_players() -> list:
    with Client_q(Config.get_local_address(), Bot_variables.port_query, timeout=1) as cl_r:
        players = cl_r.full_stats.players
    return players


@contextmanager
def times(fade_in, duration, fade_out, rcon_client):
    rcon_client.run(f"title @a times {fade_in} {duration} {fade_out}")
    yield
    rcon_client.run("title @a reset")


def announce(player, message, rcon_client):
    if float(get_server_version()) >= 1.11:
        rcon_client.run(f'title {player} actionbar ' + '{' + f'"text":"{message}"' + ',"bold":true,"color":"gold"}')
    else:
        rcon_client.run(f'title {player} title ' + '{"text":" "}')
        rcon_client.run(f'title {player} subtitle ' + '{' + f'"text":"{message}"' + ',"color":"gold"}')
    rcon_client.run(playsound(player, "minecraft:entity.arrow.hit_player", "player", 1, 0.75))


def playsound(name, sound, category="master", volume=1, pitch=1):
    return f"/execute as {name} at @s run playsound {sound} {category} @s ~ ~ ~ {volume} {pitch} 1"


def playmusic(name, sound):
    return playsound(name, sound, "music", 99999999999999999999999999999999999999)


def stopmusic(sound, name="@a"):
    return f"/stopsound {name} music {sound}"
