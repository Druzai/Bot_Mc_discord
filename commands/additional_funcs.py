from asyncio import sleep as asleep
from datetime import datetime
from os import chdir, system
from pathlib import Path
from random import choice, randint
from string import ascii_letters, digits
from sys import platform

from discord import Activity, ActivityType
from discord.ext import commands
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r

from config.init_config import Config, Bot_variables

if platform == "win32":
    from os import startfile


async def send_msg(ctx, msg, IsReaction=False):
    if IsReaction:
        await ctx.send(content=msg, delete_after=Config.get_await_time_before_message_deletion())
    else:
        await ctx.send(msg)


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
    if Bot_variables.progress_bar_time:
        Bot_variables.progress_bar_time = (Bot_variables.progress_bar_time + (datetime.now() - check_time).seconds) // 2
    else:
        Bot_variables.progress_bar_time = (datetime.now() - check_time).seconds
    author, author_mention = get_author_and_mention(ctx, bot, IsReaction)
    if ctx and not shut_up:
        await send_msg(ctx, author_mention + "\n```Server's on now```", IsReaction)
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
        print("Exeption: Couldn't connect to server, check its connection")
        await send_msg(ctx, "Couldn't connect to server to shut it down!", IsReaction)
        Bot_variables.IsStopping = False
        return
    while True:
        await asleep(Config.get_await_time_to_sleep())
        try:
            with Client_q(Config.get_local_address(), Bot_variables.port_query, timeout=0.5) as cl_q:
                _ = cl_q.basic_stats
        except BaseException:
            break
    Bot_variables.IsStopping = False
    Bot_variables.IsServerOn = False
    author, author_mention = get_author_and_mention(ctx, bot, IsReaction)
    print("Server's off now")
    await send_msg(ctx, author_mention + "\n```Server's off now```", IsReaction)
    server_dates = Config.read_server_dates()
    server_dates[1] = [datetime.now().strftime("%d/%m/%y, %H:%M:%S"), str(author)]
    Config.save_server_dates(server_dates)
    # server_start_stop_states(True)
    await bot.change_presence(activity=Activity(type=ActivityType.listening, name="Server"))


async def server_checkups(bot, always_=True):
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
                    # orig = json.loads(crypt.decrypt(open(Path(current_bot_path + '/op_keys'), 'rb').read()))
                    # orig.update(nicks_n_keys_add)
                    # keys_for_nicks_nicks = orig.keys()
                    # open(Path(current_bot_path + '/op_keys'), 'wb').write(crypt.encrypt(json.dumps(orig).encode()))
                    # orig.clear()
            if not Bot_variables.IsServerOn:
                Bot_variables.IsServerOn = True
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
            if Bot_variables.IsServerOn:
                Bot_variables.IsServerOn = False
            if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 2:
                await bot.change_presence(activity=Activity(type=ActivityType.listening, name="Server"))
            if always_ and Config.get_forceload() and not Bot_variables.IsStopping \
                    and not Bot_variables.IsLoading and not Bot_variables.IsRestarting:
                for guild in bot.guilds:
                    for channel in guild.channels:
                        try:
                            await channel.fetch_message(Config.get_menu_id())
                            await send_msg(ctx=channel,
                                           msg=f'```Bot detected: Server\'s offline!\nTime: {datetime.now().strftime("%d/%m/%y, %H:%M:%S")}\nStarting up server again!```',
                                           IsReaction=True)
                            await start_server(ctx=channel, shut_up=True)
                            break
                        except BaseException:
                            pass
        if Config.get_await_time_check_ups() > 0 and always_:
            await asleep(Config.get_await_time_check_ups())
        if not always_:
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
