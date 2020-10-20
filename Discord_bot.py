from sys import platform
from os import chdir, path, system, getcwd, listdir
from pathlib import Path
from random import choice, randint
import discord
import vk_api
import asyncio
import json
from cryptography.fernet import Fernet
from datetime import datetime
from discord.ext import commands
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r

if platform == "win32":
    from os import startfile

# variables
IsServerOn = False
IsLoading = False
IsStopping = False
IsRestarting = False
IsReaction = False
ansii_com = {"status": "🗨", "list": "📋", "start": "♿", "stop": "⏹", "restart": "🔄"}  # Symbols for menu
port_querry = 0
port_rcon = 0
rcon_pass = ""
react_auth = ""  # Variable for situation when command calls via reactions, represents author that added reaction
await_time_check_ups = 0  # Variable for awaiting while bot pinging server for info in function server_checkups
await_time_op = 0  # Variable for awaiting while player can be operator
await_sleep = 0  # Variable for awaiting while bot pinging server for info in query and rcon protocol
op_deop_list = []  # List of nicks of players to op and then to deop
Minecraft_dirs_list = []  # List of available to run servers
Mine_dir_numb = 0  # Selected server's number
current_bot_path = path.abspath(getcwd())

# json and encrypt :)
IsRewrite = False
if not path.isfile('key'):
    key = Fernet.generate_key()
    with open("key", "wb") as key_file:
        key_file.write(key)
key = open("key", "rb").read()  # Key to decrypt
crypt = Fernet(key)  # Initialized crypt module with key
# Crypt
if not path.isfile('op_keys'):
    open('op_keys', 'wb').write(crypt.encrypt(json.dumps(dict()).encode()))
keys_for_nicks = json.loads(
    crypt.decrypt(open('op_keys', 'rb').read())).keys()  # Dict for storing codes for each player seen on server
if not path.isfile('bot.json'):
    config = {
        "Token": None,
        "IP-adress": None,
        "Adress_local": None,
        "Menu_message_id": None,
        "Await sleep in connecting to server": -1,
        "Ask await time check-ups": True,
        "Await time check-ups": 15,
        "Await time op": 600,
        "Forceload": False,
        "Vk_ask": True,
        "Vk_login": None,
        "Vk_pass": None,
        "Main_minecraft_dirs": [],
        "Minecaft_dirs_ask": True,
        "Prefered_minecraft_dir": 0
    }
    with open('bot.json', 'w') as f:
        json.dump(config, f, indent=2)
with open('bot.json', 'r') as f:
    config = json.load(f)
# Decrypt
print("Reading config")
if config.get("Token"):
    token = crypt.decrypt(config["Token"].encode()).decode()
else:
    IsRewrite = True
    token = str(input("Token not founded. Enter token: "))
    config["Token"] = crypt.encrypt(token.encode()).decode()
# Getting VK initials
Vk_get = False
if config.get("Vk_login") and config.get("Vk_pass"):
    log_vk = crypt.decrypt(config["Vk_login"].encode()).decode()
    pass_vk = crypt.decrypt(config["Vk_pass"].encode()).decode()
    Vk_get = True
    if config.get("Vk_ask"):
        print("Would you like to change vk account data? y/n")
        if input() == 'y':
            log_vk = str(input("Enter vk login: "))
            pass_vk = str(input("Enter vk pass: "))
            config["Vk_login"] = crypt.encrypt(log_vk.encode()).decode()
            config["Vk_pass"] = crypt.encrypt(pass_vk.encode()).decode()
            IsRewrite = True
        print("Never ask about it again? y/n")
        if input() == 'y':
            config["Vk_ask"] = False
            print("I'll never ask you about it again.")
        else:
            print("Vk account data received. Why man?")
    else:
        print("Vk account data received.")
else:
    if config.get("Vk_ask"):
        print("Would you like to enter vk account data? y/n")
        if input() == 'y':
            log_vk = str(input("Enter vk login: "))
            pass_vk = str(input("Enter vk pass: "))
            config["Vk_login"] = crypt.encrypt(log_vk.encode()).decode()
            config["Vk_pass"] = crypt.encrypt(pass_vk.encode()).decode()
            Vk_get = True
            IsRewrite = True
        print("Never ask about it again? y/n")
        if input() == 'y':
            IsRewrite = True
            config["Vk_ask"] = False
            if config.get("Vk_login") and config.get("Vk_pass"):
                print("I'll never ask you about it again.")
            else:
                print(
                    "Vk account data not received.\nI'll never ask you about it again.\nNote: command %say won't work.")
        else:
            if not config.get("Vk_login") and not config.get("Vk_pass"):
                print("Vk account data received. Why man?")
            else:
                print(
                    "Vk account data not received.\nI'll ask you again *evil laughter*.\nNote: command %say won't work.")
    else:
        print("Vk account data not received.\nNote: command %say won't work.")
# Getting internal and external IP-adresses or DNS-names
if config.get("IP-adress"):
    IP_adress = config.get("IP-adress")
else:
    IsRewrite = True
    IP_adress = str(input("Enter server's real IP-address or DNS-name: "))
    config["IP-adress"] = IP_adress

if config.get("Adress_local"):
    Adress_local = config.get("Adress_local")
else:
    IsRewrite = True
    Adress_local = str(input("Enter server's local address: "))
    config["Adress_local"] = Adress_local
# Getting Menu message id
if config.get("Menu_message_id"):
    menu_id = config.get("Menu_message_id")
else:
    print("Menu message id not found. Would you like to enter it? y/n")
    if input() == 'y':
        IsRewrite = True
        menu_id = str(input("Enter menu message id: "))
        config["Menu_message_id"] = menu_id
    else:
        print("Menu via reactions won't work. To make it work type '%menu' to create new menu and its id.")
# Getting await time check-ups
if config.get("Await time check-ups") >= 0:
    if config.get("Ask await time check-ups"):
        print("Await time check-ups. Now it set to " + str(
            config.get("Await time check-ups")) + " seconds. Would you like to change it? y/n")
        if input() == 'y':
            IsRewrite = True
            await_time_check_ups = int(input("Set await time between check-ups 'Server on/off' (in seconds, int): "))
            config["Await time check-ups"] = await_time_check_ups
        print("Never ask about it again? y/n")
        if input() == 'y':
            IsRewrite = True
            config["Ask await time check-ups"] = False
            print("Await time will be brought from config.")
        await_time_check_ups = config.get("Await time check-ups")
    else:
        await_time_check_ups = config.get("Await time check-ups")
        print("Await time check-ups set to " + str(config.get("Await time check-ups")) + " seconds.")
else:
    IsRewrite = True
    print("Await time check-ups set below zero. Change this option")
    await_time_check_ups = int(input("Set await time between check-ups 'Server on/off' (in seconds, int): "))
    config["Await time check-ups"] = await_time_check_ups
# Getting await time op
if config.get("Await time op") >= 0:
    await_time_op = config.get("Await time op")
    print("Await time op set to " + str(config.get("Await time op")) + " seconds.")
    if config.get("Await time op") == 0:
        print("Limitation doesn't exist, padawan.")
else:
    IsRewrite = True
    print("Await time op set below zero. Change this option")
    await_time_op = int(input("Set await time for op (in seconds, int): "))
    config["Await time op"] = await_time_op
# Getting await time to sleep
if config.get("Await sleep in connecting to server") >= 0:
    await_sleep = config.get("Await sleep in connecting to server")
    print("Await time to sleep set to " + str(await_sleep) + " sec")
    if config.get("Await sleep in connecting to server") == 0:
        print("I'm fast as f*ck, boi")
else:
    IsRewrite = True
    print("Await time to sleep set below zero. Change this option")
    print(
        "Note: If your machine has processor with frequency 2-2.5 GHz, you have to set this option at least to '1' second for the bot to work properly")
    await_sleep = int(input("Set await time to sleep (in seconds, int): "))
    config["Await sleep in connecting to server"] = await_sleep


def change_list_mine(l_ist, o):  # Function to add or delete servers paths in list 'Minecraft_dirs_list'
    force_to_write = False
    l = [["", ""] for _ in range(0, o)]  # Temporal list, it returns in the end
    for j in range(o):
        if len(l_ist) > 0:
            l[j] = l_ist[j]
            l_ist.pop(0)
    i = 0
    while i < o:
        print("This is " + str(i + 1) + " path")
        if l[i][0]:
            print(
                "Current editable minecraft path: " + l[i][0] + "\nWould you like to change path AND its comment? y/n")
        else:
            print("There is no right path")
            force_to_write = True
        if force_to_write or input() == "y":
            force_to_write = False
            l[i][0] = input("Enter right path: ")
            try:
                x = listdir(l[i][0])
                if len(x) > 0:
                    for _ in x:
                        if path.isfile(Path(l[i][0] + '/' + _)) and _ == "server.properties":
                            print("Current comment about this path: '" + (
                                l[i][1] if l[i][1] else "-None-") + "'\nChange it? y/n")
                            t = ""
                            if "y" == input():
                                t = input("Enter comment about this path: ")
                            l[i][1] = t
                            i += 1
                            break
                else:
                    print("This path doesn't contain file server.properties. Try again")
            except(BaseException):
                l[i][0] = ""
                print("This path written wrong, try again")
        else:
            print("Path won't change!")
            i += 1
    return l


def read_server_properties():
    global port_querry, port_rcon, rcon_pass
    with open(Path(Minecraft_dirs_list[Mine_dir_numb][0] + "/server.properties"), "r") as f:
        for i in f.readlines():
            if i.find("query.port") >= 0:
                port_querry = int(i.split("=")[1])
            if i.find("rcon.port") >= 0:
                port_rcon = int(i.split("=")[1])
            if i.find("rcon.password") >= 0:
                rcon_pass = i.split("=")[1].strip()


# Getting list of available servers
Mine_dir_numb = config.get("Prefered_minecraft_dir")
if config.get("Main_minecraft_dirs"):
    Minecraft_dirs_list = config.get("Main_minecraft_dirs")
    if config.get("Minecaft_dirs_ask"):
        Minecraft_dirs_list = change_list_mine(Minecraft_dirs_list, len(Minecraft_dirs_list))
        config["Main_minecraft_dirs"] = Minecraft_dirs_list
        if "y" == input("Never ask about it again? y/n\n"):
            config["Minecaft_dirs_ask"] = False
            print("Minecraft dirs will be brought from config.")
        IsRewrite = True
    else:
        print("Minecraft dir set to path '" + Minecraft_dirs_list[Mine_dir_numb][0] + "' also known as " +
              (Minecraft_dirs_list[Mine_dir_numb][1] if Minecraft_dirs_list[Mine_dir_numb][1] else "-None-"))
else:
    chdir("..")
    x = listdir(path.abspath(getcwd()))
    if len(x) > 0:
        for _ in x:
            r = Path(path.abspath(getcwd()) + '/' + _)
            if path.isfile(Path(path.abspath(getcwd()) + '/' + _)) and _ == "server.properties":
                Minecraft_dirs_list.append([path.abspath(getcwd()), ""])
                break
    chdir(current_bot_path)
    _ = int(input("How much servers you intend to keep? "))
    Minecraft_dirs_list = change_list_mine(Minecraft_dirs_list, _)
    config["Main_minecraft_dirs"] = Minecraft_dirs_list
    if "y" == input("Never ask about it again? y/n\n"):
        config["Minecaft_dirs_ask"] = False
        print("Minecraft dirs will be brought from config.")
    IsRewrite = True
# Rewriting bot setting if needed
if IsRewrite:
    with open('bot.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("Config saved!")
print("Config loaded!")
IsForceload = config.get("Forceload")
read_server_properties()
print("Server properties read!")
bot = commands.Bot(command_prefix='%', description="Server bot")
bot.remove_command('help')


# Additional commands
async def send_status(ctx):
    global IsServerOn, IsLoading, IsStopping
    if IsServerOn:
        await ctx.send("```Server've already started!```")
    else:
        if IsLoading:
            await ctx.send("```Server is loading!```")
        elif IsStopping:
            await ctx.send("```Server is stopping!```")
        else:
            await ctx.send("```Server've already been stopped!```")


async def start_server(ctx, shut_up=False):
    global IsServerOn, IsLoading, IsRestarting
    IsLoading = True
    print("Loading server")
    if ctx and not shut_up:
        await ctx.send("```Loading server.......\nPlease wait)```")
    chdir(Path(Minecraft_dirs_list[Mine_dir_numb][0]))
    if platform == "linux" or platform == "linux2":
        system("screen -dmS " + Minecraft_dirs_list[Mine_dir_numb][1] + " ./Start_bot.sh")
    elif platform == "win32":
        startfile("Start_bot.bat")
    chdir(current_bot_path)
    await asyncio.sleep(5)
    check_time = datetime.now()
    while True:
        if (datetime.now() - check_time).seconds > 300:
            await ctx.send("```Error while loading server```")
            IsLoading = False
            if IsRestarting:
                IsRestarting = False
            return
        await asyncio.sleep(await_sleep)
        try:
            with Client_q(Adress_local, port_querry, timeout=0.5) as cl_q:
                info = cl_q.basic_stats
            break
        except (BaseException):
            pass
    if ctx:
        await ctx.send("```Server's on now```")
        if randint(0, 8) == 0:
            await asyncio.sleep(1)
            await ctx.send("Kept you waiting, huh?")
    IsLoading = False
    IsServerOn = True
    if IsRestarting:
        IsRestarting = False
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))


async def stop_server(ctx, How_many_sec=10, IsRestart=False):
    global IsServerOn, IsStopping
    IsStopping = True
    print("Stopping server")
    await ctx.send("```Stopping server.......\nPlease wait " + str(How_many_sec) + " sec.```")
    try:
        with Client_r(Adress_local, port_rcon, timeout=1) as cl_r:
            cl_r.login(rcon_pass)
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
                    await asyncio.sleep(w)
            cl_r.run("stop")
    except (BaseException):
        print("Exeption: Couldn't connect to server, check its connection")
        pass
    while True:
        await asyncio.sleep(await_sleep)
        try:
            with Client_q(Adress_local, port_querry, timeout=0.5) as cl_q:
                info = cl_q.basic_stats
        except (BaseException):
            break
    IsStopping = False
    IsServerOn = False
    print("Server's off now")
    await ctx.send("```Server's off now```")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))


async def server_checkups(always_=True):
    global await_time_check_ups, IsServerOn, keys_for_nicks, IsStopping, IsLoading, IsRestarting
    while True:
        try:
            with Client_q(Adress_local, port_querry, timeout=1) as cl_q:
                info = cl_q.full_stats
            if info.num_players != 0:
                nicks_n_keys_add = {}
                for i in info.players:
                    i = i.lower()
                    if i not in keys_for_nicks:
                        nicks_n_keys_add.update({i: [generate_access_code() for _ in range(25)]})
                if nicks_n_keys_add:
                    print("New codes generated")
                    for k, v in nicks_n_keys_add.items():
                        print("For player with nickname " + k + " generated these codes:")
                        for c in v:
                            print("\t" + c)
                    orig = json.loads(crypt.decrypt(open(Path(current_bot_path + '/op_keys'), 'rb').read()))
                    orig.update(nicks_n_keys_add)
                    keys_for_nicks = orig.keys()
                    open(Path(current_bot_path + '/op_keys'), 'wb').write(crypt.encrypt(json.dumps(orig).encode()))
                    orig = {}
            if not IsServerOn:
                IsServerOn = True
            try:
                if int(bot.guilds[0].get_member(bot.user.id).activities[0].name.split(", ")[1].split(" ")[0]) != 0 or info.num_players != 0:
                    await bot.change_presence(
                        activity=discord.Activity(type=discord.ActivityType.playing,
                                                  name="Minecraft Server, " + str(
                                                      info.num_players) + " player(s) online"))
            except(BaseException):
                if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 0 or info.num_players != 0:
                    await bot.change_presence(
                        activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server, " + str(
                            info.num_players) + " player(s) online"))
        except (BaseException):
            if IsServerOn:
                IsServerOn = False
            if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 2:
                await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))
            if always_ and IsForceload and not IsStopping and not IsLoading and not IsRestarting:
                for guild in bot.guilds:
                    for channel in guild.channels:
                        try:
                            await channel.fetch_message(menu_id)
                            await channel.send(
                                f'```Bot detected: Server\'s offline!\nTime: {datetime.now().strftime("%d/%m, %H:%M:%S")}\nStarting up server again!```')
                            await start_server(channel, True)
                            break
                        except(BaseException):
                            pass
        if await_time_check_ups > 0 and always_:
            await asyncio.sleep(await_time_check_ups)
        if not always_:
            break


def generate_access_code(length=16, sep='-', sep_interval=4) -> str:
    """Генератор кодов доступа
    Частота повторений символов вариативна для кода
    в пределах от 1 к 2, до 1 к 1000
    :param length: Длинна кода в символах, без учёта разделителей
    :param sep: Символ разделитель внутри кода, для читаемости
    :param sep_interval: Шаг раздела, 0 для отключния разделения
    :return: Код доступа
    """
    alphabit = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
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


@bot.event
async def on_ready():
    global IsServerOn
    print('------')
    print('Logged in discord as')
    print(bot.user.name)
    print("Discord version ", discord.__version__)
    print('------')
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="nsfw"))
    print("Bot is ready!")
    print("Starting server check-ups.")
    await server_checkups()


# COMMANDS
@bot.command(pass_context=True)
async def status(ctx):
    """Shows server status"""
    await server_checkups(False)
    if IsServerOn:
        try:
            with Client_r(Adress_local, port_rcon, timeout=1) as cl_r:
                cl_r.login(rcon_pass)
                time_ticks = int(cl_r.run("time query daytime").split(" ")[2])
            message = "Time in minecraft: "
            if 450 <= time_ticks <= 11616:
                message += "Day, "
            elif 11617 <= time_ticks <= 13800:
                message += "Sunset, "
            elif 13801 <= time_ticks <= 22550:
                message += "Night, "
            else:
                message += "Sunrise, "
            await ctx.send("```Server online\n" + message + str((6 + time_ticks // 1000) % 24) +
                           ":" + str((time_ticks % 1000) * 60 // 1000) + "\nServer adress: " + IP_adress + "```")
        except (BaseException):
            await ctx.send("```Server online\nServer adress: " + IP_adress + "```")
            print("Serv's down via rcon")
        """rcon check daytime cycle"""
    else:
        await ctx.send("```Server offline\nServer adress: " + IP_adress + "```")


@bot.command(pass_context=True)
async def list(ctx, command="-u"):
    """Shows list of players"""
    global IsReaction
    if command == "-u":
        try:
            with Client_q(Adress_local, port_querry, timeout=1) as cl_q:
                info = cl_q.full_stats
                if info.num_players == 0:
                    await ctx.send("```Игроков на сервере нет```")
                else:
                    await ctx.send("```Игроков на сервере - {0}\nИгроки: {1}```".format(info.num_players,
                                                                                        ", ".join(info.players)))
        except (BaseException):
            if IsReaction:
                author = react_auth.mention
            else:
                author = ctx.author.mention
            await ctx.send(f"{author}, сервер сейчас выключен")
    else:
        raise commands.UserInputError()


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def start(ctx):
    """Start server"""
    global IsServerOn, IsLoading, IsStopping
    await server_checkups(False)
    if not IsServerOn and not IsStopping and not IsLoading:
        await start_server(ctx)
    else:
        await send_status(ctx)


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def stop(ctx, command="10"):
    """Stop server"""
    global IsServerOn, IsLoading, IsStopping, IsForceload
    await server_checkups(False)
    try:
        if int(command) >= 0:
            if IsServerOn and not IsStopping and not IsLoading:
                if IsForceload:
                    IsForceload = False
                    config["Forceload"] = IsForceload
                    await ctx.send("```Forceload off```")
                    with open(Path(current_bot_path + '/bot.json'), 'w') as f_:
                        json.dump(config, f_, indent=2)
                await stop_server(ctx, int(command))
            else:
                await send_status(ctx)
    except(ValueError):
        raise commands.UserInputError()


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def restart(ctx, command="10"):
    """Restart server"""
    global IsServerOn, IsLoading, IsStopping, IsRestarting
    await server_checkups(False)
    try:
        if int(command) >= 0:
            if IsServerOn and not IsStopping and not IsLoading:
                IsRestarting = True
                print("Restarting server")
                await stop_server(ctx, int(command), True)
                await start_server(ctx)
            else:
                await send_status(ctx)
    except(ValueError):
        raise commands.UserInputError()


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def op(ctx, arg1, arg2, *args):
    """Op command
    :arg1 - nick,
    :arg2 - code,
    :*args - comment"""
    global IsServerOn, IsLoading, IsStopping, op_deop_list
    IsFound = False
    IsEmpty = False
    temp_s = []  # List of player(s) who used this command, it need to determinate should bot rewrite 'op_keys' or not
    if IsServerOn and not IsStopping and not IsLoading:
        keys_for_nicks = json.loads(crypt.decrypt(open(Path(current_bot_path + '/op_keys'), 'rb').read()))
        arg1 = arg1.lower()
        if arg1 in keys_for_nicks.keys():
            for _ in keys_for_nicks.get(arg1):
                temp_s = keys_for_nicks.get(arg1)
                if _ == arg2:
                    IsFound = True
                    op_deop_list.append(arg1)
                    open(Path(current_bot_path + '/op_log.txt'), 'a').write(
                        datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || Opped " + arg1 + " || Reason: " + (
                            ' '.join(args) if args else "None") + "\n")
                    try:
                        with Client_r(Adress_local, port_rcon, timeout=1) as cl_r:
                            cl_r.login(rcon_pass)
                            cl_r.say(arg1 + ' you\'ve opped for ' + str(int(await_time_op / 60)) + ' min ' + str(
                                await_time_op - int(await_time_op / 60) * 60) + ' sec.')
                            cl_r.mkop(arg1)
                    except (BaseException):
                        await ctx.send(
                            ctx.author.mention + ", а сервак-то не работает (по крайней мере я пытался), попробуй-ка позже.")
                        return
                    keys_for_nicks.get(arg1).remove(arg2)
                    await ctx.send("```Code activated```")
                    if await_time_op > 0:
                        if randint(0, 2) == 1:
                            await ctx.send(
                                "Короче, " + ctx.author.mention + ", я тебя op'нул и в благородство играть не буду: приду через "
                                + str(int(await_time_op / 60)) + " минут," +
                                " deop'ну всех - и мы в расчёте. Заодно постараюсь разузнать на кой ляд тебе эта op'ка нужна," +
                                " но я в чужие дела не лезу, если хочешь получить, значит есть за что...")
                        await asyncio.sleep(await_time_op)
                        if arg1 != op_deop_list[-1]:
                            return
                        ops = json.load(open(Path(Minecraft_dirs_list[Mine_dir_numb][0] + '/ops.json'), 'r'))
                        to_delete_ops = []
                        for i in ops:
                            for k, v in i.items():
                                if k == "name":
                                    to_delete_ops.append(v)
                        while True:
                            await asyncio.sleep(await_sleep)
                            try:
                                with Client_r(Adress_local, port_rcon, timeout=1) as cl_r:
                                    cl_r.login(rcon_pass)
                                    cl_r.say(arg1 + ' you all will be deoped now.')
                                    for _ in to_delete_ops:
                                        cl_r.deop(_)
                                    list = cl_r.run("list").split(":")[1].split(", ")
                                    for _ in list:
                                        cl_r.run("gamemode 0 " + _)
                                break
                            except (BaseException):
                                pass
                        open(Path(current_bot_path + '/op_log.txt'), 'a').write(
                            datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
                            + " || Deopped all " + str(
                                "|| Note: " + str(len(op_deop_list)) + " people deoped in belated list") if len(
                                op_deop_list) > 1 else "" + "\n")
                        await ctx.send("Ну что, " + ctx.author.mention +
                                       ", кончилось твоё время.. и не только твоё.... Как говорится \"Чики-брики и в дамки!\"")
                        op_deop_list.clear()
                    else:
                        await ctx.send(
                            ctx.author.mention + ", у тебя нет ограничения по времени, но вы все обречены...")
            if temp_s:
                open(Path(current_bot_path + 'op_keys'), 'wb').write(crypt.encrypt(json.dumps(keys_for_nicks).encode()))
            else:
                IsEmpty = True
        else:
            await ctx.send(
                "Эй, такого ника в моей базе нету. Давай по новой, " + ctx.author.mention + ", всё х\\*\\*ня.")
            IsFound = True
        if not IsFound and not IsEmpty:
            await ctx.send(ctx.author.mention + ", код не найден. Не получилось, не фортануло, братан.")
        elif IsEmpty:
            await ctx.send(ctx.author.mention + ", я вам op'ку не дам, потому что у вас рабочих кодов нету!")
    else:
        await send_status(ctx)


@bot.command(pass_context=True)
async def say(ctx):
    """Петросян"""
    global Vk_get
    if Vk_get:
        if bool(randint(0, 3)):
            _300_answers = [
                'Ну, держи!',
                'Ah, shit, here we go again.',
                'Ты сам напросился...',
                'Не следовало тебе меня спрашивать...',
                'Ха-ха-ха-ха.... Извини',
                '( ͡° ͜ʖ ͡°)',
                'Ну что пацаны, аниме?',
                'Ну чё, народ, погнали, на\\*уй! Ё\\*\\*\\*ный в рот!'
            ]
            _300_communities = [
                -45045130,  # - Хрень, какой-то паблик
                -45523862,  # - Томат
                -67580761,  # - КБ
                -57846937,  # - MDK
                -12382740,  # - ЁП
                -45745333,  # - 4ch
                -76628628,  # - Silvername
            ]
            own_id = choice(_300_communities)
            chdir(current_bot_path)
            try:
                # Тырим с вк фотки)
                vk_session = vk_api.VkApi(log_vk, pass_vk)
                vk_session.auth()
                vk = vk_session.get_api()
                photos_count = vk.photos.get(owner_id=own_id, album_id="wall", count=1).get('count')
                photo_sizes = vk.photos.get(owner_id=own_id,
                                            album_id="wall",
                                            count=1,
                                            offset=randint(0, photos_count) - 1).get('items')[0].get('sizes')
                max_photo_height = 0
                photo_url = ""
                for i in photo_sizes:
                    if i.get('height') > max_photo_height:
                        max_photo_height = i.get('height')
                for i in photo_sizes:
                    if i.get('height') == max_photo_height:
                        photo_url = i.get('url')
                        break
                e = discord.Embed(title=choice(_300_answers),
                                  color=discord.Color.from_rgb(randint(0, 255), randint(0, 255), randint(0, 255)))
                e.set_image(url=photo_url)
                await ctx.send(embed=e)
            except(BaseException):
                e = discord.Embed(title="Ошибка vk:  Что-то пошло не так",
                                  color=discord.Color.red())
                e.set_image(
                    url="http://cdn.bolshoyvopros.ru/files/users/images/bd/02/bd027e654c2fbb9f100e372dc2156d4d.jpg")
                await ctx.send(embed=e)
        else:
            await ctx.send("Я бы мог рассказать что-то, но мне лень. ( ͡° ͜ʖ ͡°)\nReturning to my duties.")
    else:
        e = discord.Embed(title="Ошибка vk:  Не введены данные аккаунта",
                          color=discord.Color.red())
        e.set_image(url="http://cdn.bolshoyvopros.ru/files/users/images/bd/02/bd027e654c2fbb9f100e372dc2156d4d.jpg")
        await ctx.send(embed=e)


@bot.command(pass_context=True, aliases=["fl"])
@commands.has_role('Майнкрафтер')
async def forceload(ctx, command=" "):
    global IsForceload
    if command == "on" or command == "off":
        rw = False
        if command == "on":
            if not IsForceload:
                IsForceload = True
                rw = True
                config["Forceload"] = IsForceload
                await ctx.send("```Forceload on```")
        elif command == "off":
            if IsForceload:
                IsForceload = False
                rw = True
                config["Forceload"] = IsForceload
                await ctx.send("```Forceload off```")
        if rw:
            with open(Path(current_bot_path + '/bot.json'), 'w') as f_:
                json.dump(config, f_, indent=2)
    elif command == " ":
        if IsForceload:
            await ctx.send("```Forceload on```")
        else:
            await ctx.send("```Forceload off```")
    else:
        raise commands.UserInputError()


@bot.command(pass_context=True, aliases=["wl"])
@commands.has_role('Майнкрафтер')
async def whitelist(ctx, *args):
    if len(args) and (args[0] == "add" or args[0] == "del" or args[0] == "list" or args[0] == "on" or args[0] == "off"):
        try:
            with Client_r(Adress_local, port_rcon, timeout=1) as cl_r:
                cl_r.login(rcon_pass)
                if args[0] == "on":
                    cl_r.run("whitelist on")
                elif args[0] == "off":
                    cl_r.run("whitelist off")
                elif args[0] == "add":
                    cl_r.run("whitelist add", args[1])
                elif args[0] == "del":
                    cl_r.run("whitelist remove", args[1])
                elif args[0] == "list":
                    white_list = cl_r.run("whitelist list")
                    white_list = white_list.split(':')
                    white_list[0] += ":"
                    await ctx.send("```" + "\n".join(white_list) + "```")
                else:
                    await ctx.send("```Wrong command!```")
        except (BaseException):
            await ctx.send("```Couldn't connect to server, try again(```")
            pass
    else:
        await ctx.send("```Commands: on, off, add, del, list```")
        raise commands.UserInputError()


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def server(ctx, *args):
    global Mine_dir_numb
    if len(args) and (args[0] == "list" or args[0] == "select" or args[0] == "show"):
        if args[0] == "list":
            send_ = "```List of servers"
            for i in range(len(Minecraft_dirs_list)):
                send_ += "\n" + str(i) + ". " + Minecraft_dirs_list[i][1]
            send_ += "```"
            await ctx.send(send_)
        elif args[0] == "select":
            if len(args) < 2:
                await ctx.send("Э, " + ctx.author.mention + ", где число?")
                return
            try:
                if int(args[1]) <= len(Minecraft_dirs_list):
                    if int(args[1]) == Mine_dir_numb:
                        await ctx.send("```My, you selected selected server, insane?)```")
                        return
                    Mine_dir_numb = int(args[1])
                    read_server_properties()
                    await ctx.send("```Server properties read!```")
                    config["Prefered_minecraft_dir"] = Mine_dir_numb
                    with open(Path(current_bot_path + '/bot.json'), 'w') as f_:
                        json.dump(config, f_, indent=2)
                else:
                    await ctx.send("```Use server list, there's no such server on the list!```")
            except(BaseException):
                await ctx.send("```Argument for 'select' must be a number!```")
        elif args[0] == "show":
            await ctx.send(
                "```Selected server #" + str(Mine_dir_numb) + ". " + Minecraft_dirs_list[Mine_dir_numb][1] + "```")
        else:
            await ctx.send("```Wrong command!\nCommands: select, list```")
    else:
        await ctx.send("```Commands: select, list, show```")
        raise commands.UserInputError()


@bot.command(pass_context=True)
async def help(ctx):
    await ctx.channel.purge(limit=1)
    emb = discord.Embed(title='Список всех команд (через %)',
                        color=discord.Color.gold())
    emb.add_field(name='status', value='Возвращает статус сервера')
    emb.add_field(name='list',
                  value='Возвращает список игроков')
    emb.add_field(name='start', value='Запускает сервер')
    emb.add_field(name='stop {10}', value='Останавливает сервер, {} (сек) сколько идёт отсчёт, 0 убирает таймер')
    emb.add_field(name='restart {10}', value='Перезапускает сервер, {} (сек) сколько идёт отсчёт, 0 убирает таймер')
    emb.add_field(name='op {1} {2} {3}',
                  value='Даёт op\'ку на {1} ник по {2} коду {3} c комментарием причины, если надо')
    emb.add_field(name='menu', value='Создаёт меню-пульт для удобного управления командами')
    emb.add_field(name='forceload/fl {on/off}',
                  value='По {on/off} постоянная загрузка сервера, когда он отключен, без аргументов - статус')
    emb.add_field(name='whitelist/wl {1}',
                  value='Использует whitelist с сервера майна, аргументы {1} - on, off, add, del, list.  С add и del ещё пишется ник игрока')
    emb.add_field(name='server {1}',
                  value='Использует список серверов в боте, аргументы {1} - select, list, show.  При select ещё пишется номер сервера из list')
    emb.add_field(name='say', value='"Петросянит" ( ͡° ͜ʖ ͡°)')
    emb.add_field(name='clear {1}', value='Удаляет {1} строк')
    await ctx.send(embed=emb)


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def menu(ctx):
    global menu_id, config
    await ctx.channel.purge(limit=1)
    emb = discord.Embed(title='Список всех команд через реакции',
                        color=discord.Color.teal())
    emb.add_field(name='status', value=':speech_left:')
    emb.add_field(name='list',
                  value=':clipboard:')
    emb.add_field(name='start', value=':wheelchair:')
    emb.add_field(name='stop 10', value=':stop_button:')
    emb.add_field(name='restart 10', value=':arrows_counterclockwise:')
    add_reactions_to = await ctx.send(embed=emb)
    menu_id = str(add_reactions_to.id)
    config["Menu_message_id"] = menu_id
    with open(Path(current_bot_path + '/bot.json'), 'w') as f_:
        json.dump(config, f_, indent=2)
    await add_reactions_to.add_reaction(ansii_com.get("status"))
    await add_reactions_to.add_reaction(ansii_com.get("list"))
    await add_reactions_to.add_reaction(ansii_com.get("start"))
    await add_reactions_to.add_reaction(ansii_com.get("stop"))
    await add_reactions_to.add_reaction(ansii_com.get("restart"))


@bot.event
async def on_raw_reaction_add(payload):
    global IsReaction, react_auth
    if payload.message_id == int(menu_id) and payload.member.id != bot.user.id:
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = bot.get_user(payload.user_id)
        await message.remove_reaction(payload.emoji, user)
        if payload.emoji.name in ansii_com.values():
            IsReaction = True
            react_auth = payload.member
            if payload.emoji.name == ansii_com.get("status"):
                await status(channel)
            elif payload.emoji.name == ansii_com.get("list"):
                await list(channel)
            else:
                if 'Майнкрафтер' not in str(payload.member.roles):
                    await send_error(channel, commands.MissingRole('Майнкрафтер'))
                else:
                    if payload.emoji.name == ansii_com.get("start"):
                        await start(channel)
                    elif payload.emoji.name == ansii_com.get("stop"):
                        await stop(channel)
                    elif payload.emoji.name == ansii_com.get("restart"):
                        await restart(channel)
            IsReaction = False
            await asyncio.sleep(10)
            # Code below deletes all messages up to menu message
            # It's working, but not working fully as intended)
            messages = await channel.history(limit=35).flatten()
            pu = 0
            for i in messages:
                if i.id == int(menu_id):
                    break
                pu += 1
            await channel.purge(limit=pu)


@bot.command(pass_context=True)
# @commands.has_permissions(administrator=True)
async def clear(ctx, count=1):
    await ctx.channel.purge(limit=int(count) + 1)


# Handling errors
async def send_error(ctx, error):
    if IsReaction:
        author = react_auth.mention
        author2 = react_auth
    else:
        author = ctx.author.mention
        author2 = ctx.author
    if isinstance(error, commands.MissingRequiredArgument):
        print(f'{author2} не указал аргумент')
        await ctx.send(f'{author}, пожалуйста, введи все аргументы ')
    if isinstance(error, commands.MissingPermissions):
        print(f'У {author2} мало прав для команды')
        await ctx.send(f'{author}, у вас недостаточно прав для выполнения этой команды')
    if isinstance(error, commands.MissingRole):
        print(f'У {author2} нет роли "{error.missing_role}" для команды')
        await ctx.send(f'{author}, у вас нет роли "{error.missing_role}" для выполнения этой команды')
    if isinstance(error, commands.CommandNotFound):
        print(f'{author2} ввёл несуществующую команду')
        await ctx.send(f'{author}, вы ввели несуществующую команду')
    if isinstance(error, commands.UserInputError):
        print(f'{author2} неправильно ввёл аргумент(ы) команды')
        await ctx.send(f'{author}, вы неправильно ввели агрумент(ы) команды')
    if isinstance(error, commands.DisabledCommand):
        print(f'{author2} ввёл отключённую команду')
        await ctx.send(f'{author}, вы ввели отлючённую команду')


@bot.event
async def on_command_error(ctx, error):
    await send_error(ctx, error)


try:
    bot.run(token)
except(BaseException):
    print("Bot/Discord Error: Maybe you need to update discord.py or your token is wrong.")
system("pause")
