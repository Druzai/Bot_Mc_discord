from sys import platform
from os import chdir, path, system, getcwd, listdir
from pathlib import Path
from random import choice, randint
import discord
import vk_api
from asyncio import sleep as asleep
import json
from cryptography.fernet import Fernet
from datetime import datetime
from discord.ext import commands
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r

if platform == "win32":
    from os import startfile
# TODO: features
#  Make in classes
#  Make rus/eng localization and get it from dict from file or so

# variables
IsServerOn = False
IsLoading = False
IsStopping = False
IsRestarting = False
IsReaction = False
IsDoOp = False
IsVoting = False
ansii_com = {"status": "🗨", "list": "📋", "start": "♿", "stop": "⏹", "restart": "🔄",
             "update": "📶"}  # Symbols for menu
port_querry = 0
port_rcon = 0
rcon_pass = ""
react_auth = ""  # Variable for situation when command calls via reactions, represents author that added reaction
await_time_check_ups = 0  # Variable for awaiting while bot pinging server for info in function server_checkups
await_time_op = 0  # Variable for awaiting while player can be operator
await_sleep = 0  # Variable for awaiting while bot pinging server for info in query and rcon protocol
op_deop_list = []  # List of nicks of players to op and then to deop
Command_role = ""
script_name = ""
Minecraft_dirs_list = []  # List of available to run servers
Mine_dir_numb = 0  # Selected server's number
current_bot_path = path.abspath(getcwd())
await_time_before_message_deletion = 10
poll = [0, 0]
poll_voted_uniq = []
await_date = datetime.now()
Server_Start_Stop = [[], []]  # List 1-st start pos, 2-nd stop pos
Progress_bar_time = 0

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
keys_for_nicks_nicks = json.loads(
    crypt.decrypt(open('op_keys', 'rb').read())).keys()  # Dict for each player nicks seen on server
if not path.isfile('id-to-nicks.json'):
    open('id-to-nicks.json', 'w').write(json.dumps(dict()))
id_to_nicks = json.loads(open('id-to-nicks.json', 'r').read())  # Dict for func associate
if not path.isfile('bot.json'):
    config = {
        "Token": None,
        "IP-adress": None,
        "Adress_local": None,
        "Menu_message_id": None,
        "Command role for discord": "",
        "Name of *.bat or *.sh file": "",
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
        "Prefered_minecraft_dir": 0,
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
# Getting naming of the script file
if config.get("Name of *.bat or *.sh file"):
    script_name = config.get("Name of *.bat or *.sh file")
    print(
        "Bot will search for file '" + script_name + ".bat' or '" + script_name + ".sh' in main minecraft directory to start the server!")
else:
    IsRewrite = True
    print("Set name of file-script for bot to start the server with it\n")
    script_name = input()
    config["Name of *.bat or *.sh file"] = script_name
# Getting discord role for specific commands
if config.get("Command role for discord"):
    Command_role = config.get("Command role for discord")
    print("Current role for some commands is '" + Command_role + "'")
else:
    IsRewrite = True
    print("Set discord role for some specific commands such as start, stop, etc.\n")
    Command_role = input()
    config["Command role for discord"] = Command_role
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
    l = [["", "", 0] for _ in range(0, o)]  # Temporal list, it returns in the end
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
                                t = input("Enter comment about this path (IMPORTANT on Linux comment WITHOUT spaces): ")
                            l[i][1] = t
                            i += 1
                            break
                else:
                    print("This path doesn't contain file server.properties. Try again")
            except BaseException:
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


def server_start_stop_states(ToWrite=False):
    global Server_Start_Stop
    if ToWrite:
        with open(Path(Minecraft_dirs_list[Mine_dir_numb][0] + "/StartStopStates.json"), "w") as f_:
            json.dump(Server_Start_Stop, f_, indent=2)
    else:
        if not path.isfile(Path(Minecraft_dirs_list[Mine_dir_numb][0] + "/StartStopStates.json")):
            Server_Start_Stop = [[], []]
            with open(Path(Minecraft_dirs_list[Mine_dir_numb][0] + "/StartStopStates.json"), "w") as f_:
                json.dump(Server_Start_Stop, f_, indent=2)
        else:
            with open(Path(Minecraft_dirs_list[Mine_dir_numb][0] + "/StartStopStates.json"), "r") as f_:
                Server_Start_Stop = json.load(f_)


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
# Getting Server start & stop states
server_start_stop_states()
# Getting progress bar time for selected server
Progress_bar_time = Minecraft_dirs_list[Mine_dir_numb][2]
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
async def send_status(ctx, IsReaction=False):
    global IsServerOn, IsLoading, IsStopping
    if IsServerOn:
        msg = "```Server've already started!```"
    else:
        if IsLoading:
            msg = "```Server is loading!```"
        elif IsStopping:
            msg = "```Server is stopping!```"
        else:
            msg = "```Server've already been stopped!```"
    if IsReaction:
        await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
    else:
        await ctx.send(msg)


async def start_server(ctx, shut_up=False, IsReaction=False):
    global IsServerOn, IsLoading, IsRestarting, Server_Start_Stop, Progress_bar_time, Minecraft_dirs_list
    IsLoading = True
    print("Loading server")
    if ctx and not shut_up:
        msg = "```Loading server.......\nPlease wait)```"
        if IsReaction:
            await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
        else:
            await ctx.send(msg)
    chdir(Path(Minecraft_dirs_list[Mine_dir_numb][0]))
    if platform == "linux" or platform == "linux2":
        system("screen -dmS " + Minecraft_dirs_list[Mine_dir_numb][1] + " ./" + script_name + ".sh")
    elif platform == "win32":
        startfile(script_name + ".bat")
    chdir(current_bot_path)
    await asleep(5)
    check_time = datetime.now()
    while True:
        if (datetime.now() - check_time).seconds > 600:
            msg = "```Error while loading server```"
            if IsReaction:
                await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
            else:
                await ctx.send(msg)
            IsLoading = False
            if IsRestarting:
                IsRestarting = False
            return
        timedelta_secs = (datetime.now() - check_time).seconds
        if Progress_bar_time:
            percentage = round((timedelta_secs / Progress_bar_time) * 100)
            output_bot = "Loading: " + (str(percentage) + "%") if percentage < 101 else "100%..."
        else:
            output_bot = "Server, elapsed time: " + (
                str(timedelta_secs // 60) + ":" + f"{(timedelta_secs % 60):02d}" if timedelta_secs // 60 != 0 else str(
                    timedelta_secs % 60) + " sec")
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=output_bot))
        await asleep(await_sleep)
        try:
            with Client_q(Adress_local, port_querry, timeout=0.5) as cl_q:
                info = cl_q.basic_stats
            break
        except BaseException:
            pass
    if Progress_bar_time:
        Progress_bar_time = (Progress_bar_time + (datetime.now() - check_time).seconds) // 2
    else:
        Progress_bar_time = (datetime.now() - check_time).seconds
    if IsReaction:
        author_mention = react_auth.mention
        author = react_auth
    else:
        author_mention = ctx.author.mention
        author = ctx.author
    if ctx:
        msg = author_mention + "\n```Server's on now```"
        if randint(0, 8) == 0:
            msg += "\nKept you waiting, huh?"
        if IsReaction:
            await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
        else:
            await ctx.send(msg)
    IsLoading = False
    IsServerOn = True
    if IsRestarting:
        IsRestarting = False
    if Minecraft_dirs_list[Mine_dir_numb][2] != Progress_bar_time:
        Minecraft_dirs_list[Mine_dir_numb][2] = Progress_bar_time
        config["Main_minecraft_dirs"] = Minecraft_dirs_list
        with open(Path(current_bot_path + '/bot.json'), 'w') as f_:
            json.dump(config, f_, indent=2)
    Server_Start_Stop[0] = [datetime.now().strftime("%d/%m/%y, %H:%M:%S"), str(author)]
    server_start_stop_states(True)
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))


async def stop_server(ctx, How_many_sec=10, IsRestart=False, IsReaction=False):
    global IsServerOn, IsStopping, Server_Start_Stop
    IsStopping = True
    print("Stopping server")
    msg = "```Stopping server.......\nPlease wait " + str(How_many_sec) + " sec.```"
    if IsReaction:
        await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
    else:
        await ctx.send(msg)
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
                    await asleep(w)
            cl_r.run("stop")
    except BaseException:
        print("Exeption: Couldn't connect to server, check its connection")
        msg = "Couldn't connect to server to shut it down!"
        if IsReaction:
            await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
        else:
            await ctx.send(msg)
        return
    while True:
        await asleep(await_sleep)
        try:
            with Client_q(Adress_local, port_querry, timeout=0.5) as cl_q:
                info = cl_q.basic_stats
        except BaseException:
            break
    IsStopping = False
    IsServerOn = False
    if IsReaction:
        author_mention = react_auth.mention
        author = react_auth
    else:
        author_mention = ctx.author.mention
        author = ctx.author
    print("Server's off now")
    msg = author_mention + "\n```Server's off now```"
    if IsReaction:
        await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
    else:
        await ctx.send(msg)
    Server_Start_Stop[1] = [datetime.now().strftime("%d/%m/%y, %H:%M:%S"), str(author)]
    server_start_stop_states(True)
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))


async def server_checkups(always_=True):
    global await_time_check_ups, IsServerOn, keys_for_nicks_nicks, IsStopping, IsLoading, IsRestarting
    while True:
        try:
            with Client_q(Adress_local, port_querry, timeout=1) as cl_q:
                info = cl_q.full_stats
            if info.num_players != 0:
                nicks_n_keys_add = {}
                for i in info.players:
                    i = i.lower()
                    if i not in keys_for_nicks_nicks:
                        nicks_n_keys_add.update({i: [generate_access_code() for _ in range(25)]})
                if nicks_n_keys_add:
                    print("New codes generated")
                    for k, v in nicks_n_keys_add.items():
                        print("For player with nickname " + k + " generated these codes:")
                        for c in v:
                            print("\t" + c)
                    orig = json.loads(crypt.decrypt(open(Path(current_bot_path + '/op_keys'), 'rb').read()))
                    orig.update(nicks_n_keys_add)
                    keys_for_nicks_nicks = orig.keys()
                    open(Path(current_bot_path + '/op_keys'), 'wb').write(crypt.encrypt(json.dumps(orig).encode()))
                    orig = {}
            if not IsServerOn:
                IsServerOn = True
            try:
                if int(bot.guilds[0].get_member(bot.user.id).activities[0].name.split(", ")[1].split(" ")[
                           0]) != 0 or info.num_players != 0:
                    await bot.change_presence(
                        activity=discord.Activity(type=discord.ActivityType.playing,
                                                  name="Minecraft Server, " + str(
                                                      info.num_players) + " player(s) online"))
            except BaseException:
                if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 0 or info.num_players != 0:
                    await bot.change_presence(
                        activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server, " + str(
                            info.num_players) + " player(s) online"))
        except BaseException:
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
                                f'```Bot detected: Server\'s offline!\nTime: {datetime.now().strftime("%d/%m/%y, %H:%M:%S")}\nStarting up server again!```')
                            await start_server(channel, True)
                            break
                        except BaseException:
                            pass
        if await_time_check_ups > 0 and always_:
            await asleep(await_time_check_ups)
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
async def status(ctx, IsReaction=False):
    """Shows server status"""
    states = "\n"
    for i in range(len(Server_Start_Stop)):
        if len(Server_Start_Stop[i]) == 0:
            continue
        if i == 0:
            states += "Server has been started at "
        else:
            states += "Server has been stopped at "
        states += Server_Start_Stop[i][0] + ", by " + Server_Start_Stop[i][1]
        if i != len(Server_Start_Stop):
            states += "\n"
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
            msg = "```Server online\n" + message + str((6 + time_ticks // 1000) % 24) + ":" + \
                  f"{((time_ticks % 1000) * 60 // 1000):02d}" + "\nServer adress: " + IP_adress + "\nSelected server: " \
                  + Minecraft_dirs_list[Mine_dir_numb][1] + states + "```"
            if IsReaction:
                await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
            else:
                await ctx.send(msg)

        except BaseException:
            msg = "```Server online\nServer adress: " + IP_adress + "\nSelected server: " + \
                  Minecraft_dirs_list[Mine_dir_numb][1] + states + "```"
            if IsReaction:
                await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
            else:
                await ctx.send(msg)
            print("Serv's down via rcon")
        """rcon check daytime cycle"""
    else:
        msg = "```Server offline\nServer adress: " + IP_adress + "\nSelected server: " + \
              Minecraft_dirs_list[Mine_dir_numb][1] + states + "```"
        if IsReaction:
            await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
        else:
            await ctx.send(msg)


@bot.command(pass_context=True)
async def list(ctx, command="-u", IsReaction=False):
    """Shows list of players"""
    # global IsReaction
    if command == "-u":
        try:
            with Client_q(Adress_local, port_querry, timeout=1) as cl_q:
                info = cl_q.full_stats
                if info.num_players == 0:
                    msg = "```Игроков на сервере нет```"
                else:
                    msg = "```Игроков на сервере - {0}\nИгроки: {1}```".format(info.num_players,
                                                                               ", ".join(info.players))
                if IsReaction:
                    await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
                else:
                    await ctx.send(msg)
        except BaseException:
            if IsReaction:
                author_mention = react_auth.mention
                msg = f"{author_mention}, сервер сейчас выключен"
                await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
            else:
                author_mention = ctx.author.mention
                await ctx.send(f"{author_mention}, сервер сейчас выключен")
    else:
        await send_error(ctx, commands.UserInputError(), IsReaction=IsReaction)


@bot.command(pass_context=True)
@commands.has_role(Command_role)
async def start(ctx, IsReaction=False):
    """Start server"""
    global IsServerOn, IsLoading, IsStopping
    if not IsServerOn and not IsStopping and not IsLoading:
        await start_server(ctx, IsReaction=IsReaction)
    else:
        await send_status(ctx, IsReaction=IsReaction)


@bot.command(pass_context=True)
@commands.has_role(Command_role)  # TODO: add poll when there's more than 0 player on server
async def stop(ctx, command="10", IsReaction=False):
    """Stop server"""
    global IsServerOn, IsLoading, IsStopping, IsForceload, IsDoOp
    try:
        if int(command) >= 0:
            if IsServerOn and not IsStopping and not IsLoading:
                if IsDoOp:
                    await ctx.send("```Some player/s still oped, waiting for them```")
                    return
                if IsForceload:
                    IsForceload = False
                    config["Forceload"] = IsForceload
                    await ctx.send("```Forceload off```")
                    with open(Path(current_bot_path + '/bot.json'), 'w') as f_:
                        json.dump(config, f_, indent=2)
                await stop_server(ctx, int(command), IsReaction=IsReaction)
            else:
                await send_status(ctx, IsReaction=IsReaction)
    except(ValueError):
        await send_error(ctx, commands.UserInputError(), IsReaction=IsReaction)


@bot.command(pass_context=True)
@commands.has_role(Command_role)
async def restart(ctx, command="10", IsReaction=False):
    """Restart server"""
    global IsServerOn, IsLoading, IsStopping, IsRestarting, IsDoOp
    try:
        if int(command) >= 0:
            if IsServerOn and not IsStopping and not IsLoading:
                if IsDoOp:
                    await ctx.send("```Some player/s still oped, waiting for them```")
                    return
                IsRestarting = True
                print("Restarting server")
                await stop_server(ctx, int(command), True, IsReaction=IsReaction)
                await start_server(ctx, IsReaction=IsReaction)
            else:
                await send_status(ctx, IsReaction=IsReaction)
    except(ValueError):
        await send_error(ctx, commands.UserInputError(), IsReaction=IsReaction)


@bot.command(pass_context=True)
@commands.has_role(Command_role)
async def op(ctx, arg1, arg2, *args):
    """Op command
    :arg1 - nick,
    :arg2 - code,
    :*args - comment"""
    global IsServerOn, IsLoading, IsStopping, op_deop_list, IsDoOp
    IsFound = False
    IsEmpty = False
    IsDoOp = True
    temp_s = []  # List of player(s) who used this command, it need to determinate should bot rewrite 'op_keys' or not
    if IsServerOn and not IsStopping and not IsLoading and not IsRestarting:
        keys_for_nicks = json.loads(crypt.decrypt(open(Path(current_bot_path + '/op_keys'), 'rb').read()))
        arg1 = arg1.lower()
        if arg1 in keys_for_nicks.keys():
            for _ in keys_for_nicks.get(arg1):
                temp_s = keys_for_nicks.get(arg1)
                if _ == arg2:
                    IsFound = True
                    op_deop_list.append(arg1)
                    open(Path(current_bot_path + '/op_log.txt'), 'a', encoding='utf-8').write(
                        datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || Opped " + arg1 + " || Reason: " + (
                            ' '.join(args) if args else "None") + "\n")
                    try:
                        with Client_r(Adress_local, port_rcon, timeout=1) as cl_r:
                            cl_r.login(rcon_pass)
                            cl_r.say(arg1 + ' you\'ve opped for' + (
                                "" if await_time_op // 60 == 0 else " " + str(await_time_op // 60) + ' min') + (
                                         "." if await_time_op % 60 == 0 else " " + str(await_time_op % 60) + ' sec.'))
                            cl_r.mkop(arg1)
                    except BaseException:
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
                        await asleep(await_time_op)
                        if arg1 != op_deop_list[-1]:
                            return
                        ops = json.load(open(Path(Minecraft_dirs_list[Mine_dir_numb][0] + '/ops.json'), 'r'))
                        to_delete_ops = []
                        for i in ops:
                            for k, v in i.items():
                                if k == "name":
                                    to_delete_ops.append(v)
                        while True:
                            await asleep(await_sleep)
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
                            except BaseException:
                                pass
                        open(Path(current_bot_path + '/op_log.txt'), 'a', encoding='utf-8').write(
                            datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || Deopped all " + (
                                str("|| Note: " + str(len(op_deop_list)) + " people deoped in belated list") if len(
                                    op_deop_list) > 1 else "") + "\n")
                        await ctx.send("Ну что, " + ctx.author.mention +
                                       ", кончилось твоё время.. и не только твоё.... Как говорится \"Чики-брики и в дамки!\"")
                        op_deop_list.clear()
                        IsDoOp = False
                    else:
                        await ctx.send(
                            ctx.author.mention + ", у тебя нет ограничения по времени, но вы все обречены...")
                        IsDoOp = False
            if temp_s:
                open(Path(current_bot_path + '/op_keys'), 'wb').write(
                    crypt.encrypt(json.dumps(keys_for_nicks).encode()))
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
# @commands.has_role(Command_role)
@commands.has_permissions(administrator=True)
async def assoc(ctx, arg1: str, arg2, arg3):
    """
    syntax: Nick_Discord +=/-= Nick_minecraft
    """
    global id_to_nicks
    comm_operators = ["+=", "-="]
    if arg1.startswith("<@!"):
        try:
            id = arg1[3:-1]
            int(id)
        except BaseException:
            await ctx.send("Wrong 1-st argument used!")
            return
        arg3 = arg3.lower()
        if arg2 == comm_operators[0]:
            if arg3 not in id_to_nicks.keys():
                id_to_nicks[arg3] = id
                await ctx.send("Now " + arg1 + " associates with nick in minecraft " + arg3)
            else:
                await ctx.send("Existing `mention to nick` link!")
        elif arg2 == comm_operators[1]:
            if arg3 in id_to_nicks.keys():
                del id_to_nicks[arg3]
                await ctx.send("Now link " + arg1 + " -> " + arg3 + " do not exist!")
            else:
                await ctx.send("Doesn't have `mention to nick` link already!")
        else:
            await ctx.send("Wrong command syntax! Right example: `%assoc @me += My_nick`")
        with open('id-to-nicks.json', 'w') as f:
            json.dump(id_to_nicks, f, indent=2)
    else:
        await ctx.send("Wrong 1-st argument! You can mention ONLY members")


@bot.command(pass_context=True)
# @commands.has_role(Command_role)
async def codes(ctx, arg1):
    member = ctx.author
    id = str(member.id)
    arg1 = arg1.lower()
    if arg1 != "" and arg1 in id_to_nicks.keys() and id_to_nicks.get(arg1) == id:
        keys_for_nicks = json.loads(crypt.decrypt(open(Path(current_bot_path + '/op_keys'), 'rb').read()))
        if arg1 not in keys_for_nicks.keys():
            await ctx.send("Don't have such nickname logged in minecraft")
            return
        message = "For player with nickname " + arg1 + " generated " + str(len(keys_for_nicks.get(arg1))) + " codes:\n"
        for value in keys_for_nicks.get(arg1):
            message += "`" + value + "`\n"
        await member.send(message)
    else:
        # Check if /Gendalf_Top exists!
        if Path(current_bot_path + '/Gendalf_Top').is_dir():
            gifs_list = listdir(Path(current_bot_path + '/Gendalf_Top'))
            await member.send('You shall not PASS! Ты не владеешь данным ником :ambulance:',
                              file=discord.File(Path(current_bot_path + '/Gendalf_Top/' + choice(gifs_list))))
        else:
            print("Folder 'Gendalf_Top' hasn't been found in that path '" + current_bot_path +
                  "'. Maybe you want to create it and fill it with images related to Gendalf :)")
            await member.send('You shall not PASS! Ты не владеешь данным ником :ambulance:')


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
            except BaseException:
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
@commands.has_role(Command_role)
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
@commands.has_role(Command_role)
async def whitelist(ctx, *args):
    if len(args) and (args[0] == "add" or args[0] == "del" or args[0] == "list" or args[0] == "on" or args[0] == "off"
                      or args[0] == "reload"):
        try:
            with Client_r(Adress_local, port_rcon, timeout=1) as cl_r:
                cl_r.login(rcon_pass)
                if args[0] == "on":
                    white_list = cl_r.run("whitelist on")
                    await ctx.send("```" + white_list + "```")
                elif args[0] == "off":
                    white_list = cl_r.run("whitelist off")
                    await ctx.send("```" + white_list + "```")
                elif args[0] == "add":
                    white_list = cl_r.run("whitelist add", args[1])
                    await ctx.send("```" + white_list + "```")
                elif args[0] == "del":
                    white_list = cl_r.run("whitelist remove", args[1])
                    await ctx.send("```" + white_list + "```")
                elif args[0] == "list":
                    white_list = cl_r.run("whitelist list")
                    white_list = white_list.split(':')
                    white_list[0] += ":"
                    await ctx.send("```" + "\n".join(white_list) + "```")
                elif args[0] == "reload":
                    white_list = cl_r.run("whitelist reload")
                    await ctx.send("```" + white_list + "```")
                else:
                    await ctx.send("```Wrong command!```")
        except BaseException:
            await ctx.send("```Couldn't connect to server, try again(```")
            pass
    else:
        await ctx.send("```Commands: on, off, add, del, list```")
        raise commands.UserInputError()


@bot.command(pass_context=True)
@commands.has_role(Command_role)
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
                        await ctx.send("```My, you have chosen selected server, insane?)\n ...Pasan ramsi poputal```")
                        return
                    if IsServerOn:
                        await ctx.send("```You can't change servers, while some instance(s) is/are still running" +
                                       "\nPlease stop it, before trying again```")
                        return
                    Mine_dir_numb = int(args[1])
                    read_server_properties()
                    server_start_stop_states()
                    await ctx.send("```Server properties read!```")
                    config["Prefered_minecraft_dir"] = Mine_dir_numb
                    with open(Path(current_bot_path + '/bot.json'), 'w') as f_:
                        json.dump(config, f_, indent=2)
                else:
                    await ctx.send("```Use server list, there's no such server on the list!```")
            except BaseException:
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
    emb.add_field(name='assoc {1} {2} {3}',
                  value='Ассоциирует {1} упоминание ника в дискорде по {2} команде (+=/-=) (добавить или удалить) {3} c ником в майнкрафте **для админа**')
    emb.add_field(name='codes {1}', value='Даёт коды на {1} ник в лс')
    emb.add_field(name='menu', value='Создаёт меню-пульт для удобного управления командами')
    emb.add_field(name='forceload/fl {on/off}',
                  value='По {on/off} постоянная загрузка сервера, когда он отключен, без аргументов - статус')
    emb.add_field(name='whitelist/wl {1}',
                  value='Использует whitelist с сервера майна, аргументы {1} - on, off, add, del, list, reload.  С add и del ещё пишется ник игрока')
    emb.add_field(name='server {1}',
                  value='Использует список серверов в боте, аргументы {1} - select, list, show.  При select ещё пишется номер сервера из list')
    emb.add_field(name='say', value='"Петросянит" ( ͡° ͜ʖ ͡°)')
    emb.add_field(name='clear {1}',
                  value='Если положительное число удаляет {1} сообщений, если отрицательное - удаляет n сообщений до {1} от начала канала')
    await ctx.send(embed=emb)


@bot.command(pass_context=True)
@commands.has_role(Command_role)
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
    emb.add_field(name='update', value=':signal_strength:')
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
    await add_reactions_to.add_reaction(ansii_com.get("update"))


@bot.event
async def on_raw_reaction_add(payload):
    global react_auth
    if payload.message_id == int(menu_id) and payload.member.id != bot.user.id:
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        user = bot.get_user(payload.user_id)
        await message.remove_reaction(payload.emoji, user)
        if payload.emoji.name in ansii_com.values():
            react_auth = payload.member
            if payload.emoji.name == ansii_com.get("status"):
                await status(channel, IsReaction=True)
            elif payload.emoji.name == ansii_com.get("list"):
                await list(channel, IsReaction=True)
            elif payload.emoji.name == ansii_com.get("update"):
                await server_checkups(False)
                return
            else:
                if Command_role not in str(payload.member.roles):
                    await send_error(channel, commands.MissingRole(Command_role), IsReaction=True)
                else:
                    if payload.emoji.name == ansii_com.get("start"):
                        await start(channel, IsReaction=True)
                    elif payload.emoji.name == ansii_com.get("stop"):
                        await stop(channel, IsReaction=True)
                    elif payload.emoji.name == ansii_com.get("restart"):
                        await restart(channel, IsReaction=True)


@bot.command(pass_context=True)
# @commands.has_permissions(administrator=True) # TODO: if 50+ messages give poll!, remember id message when bot sends "@everyone", purge after this msg_id, and clear as usual after
async def clear(ctx, count=1):
    global poll, await_date, IsVoting
    try:
        int(str(count))
    except BaseException:
        await ctx.send("Ты дебик? Чё ты там написал? Как мне это понимать? А? '" + str(count) + "' Убейся там!")
    if count > 0:
        await ctx.channel.purge(limit=int(count) + 1, bulk=False)
    else:
        if (datetime.now() - await_date).seconds > 30:
            await ctx.send("@everyone, this man " + ctx.author.mention +
                           " trying to delete whole history of this channel. Will you let that happen? Vote with `%yes` or `%no`. To win the poll need 2 votes! So keep it up! I'm waiting")
            reset_poll()
            IsVoting = True
            while poll[0] < 2 and poll[1] < 2:
                await asleep(1)
            if poll[0] == 2 and poll[1] < 2:
                message_created_time = (await ctx.channel.history(limit=-count, oldest_first=True).flatten())[
                    -1].created_at
                await ctx.channel.purge(limit=None, after=message_created_time, bulk=False)
            else:
                await ctx.send("Well, you're save for now")
            await_date = datetime.now()
            IsVoting = False
        else:
            await ctx.send(
                ctx.author.mention + ", what are you doing? Time hasn't passed yet. I have 30 secs timer! Waiting...")


def reset_poll():
    global poll, poll_voted_uniq
    poll = [0, 0]
    poll_voted_uniq.clear()


@bot.command(pass_context=True)
async def yes(ctx):
    global poll, poll_voted_uniq
    if not IsVoting:
        await ctx.send("I don't see opened poll :japanese_goblin:")
    else:
        if ctx.author.id not in poll_voted_uniq:
            poll_voted_uniq.append(ctx.author.id)
            poll[0] += 1
            await ctx.send("Current numbers: yes - " + str(poll[0]) + ", no - " + str(poll[1]))
        else:
            await ctx.send("You've already voted!")


@bot.command(pass_context=True)
async def no(ctx):
    global poll, poll_voted_uniq
    if not IsVoting:
        await ctx.send("I don't see opened poll :japanese_goblin:")
    else:
        if ctx.author.id not in poll_voted_uniq:
            poll_voted_uniq.append(ctx.author.id)
            poll[1] += 1
            await ctx.send("Current numbers: yes - " + str(poll[0]) + ", no - " + str(poll[1]))
        else:
            await ctx.send("You've already voted!")


# Handling errors
async def send_error(ctx, error, IsReaction=False):
    if IsReaction:
        author_mention = react_auth.mention
        author = react_auth
    else:
        author_mention = ctx.author.mention
        author = ctx.author
    msg = ""
    if isinstance(error, commands.MissingRequiredArgument):
        print(f'{author} не указал аргумент')
        msg = f'{author_mention}, пожалуйста, введи все аргументы '
    if isinstance(error, commands.MissingPermissions):
        print(f'У {author} мало прав для команды')
        msg = f'{author_mention}, у вас недостаточно прав для выполнения этой команды'
    if isinstance(error, commands.MissingRole):
        print(f'У {author} нет роли "{error.missing_role}" для команды')
        msg = f'{author_mention}, у вас нет роли "{error.missing_role}" для выполнения этой команды'
    if isinstance(error, commands.CommandNotFound):
        print(f'{author} ввёл несуществующую команду')
        msg = f'{author_mention}, вы ввели несуществующую команду'
    if isinstance(error, commands.UserInputError):
        print(f'{author} неправильно ввёл аргумент(ы) команды')
        msg = f'{author_mention}, вы неправильно ввели агрумент(ы) команды'
    if isinstance(error, commands.DisabledCommand):
        print(f'{author} ввёл отключённую команду')
        msg = f'{author_mention}, вы ввели отлючённую команду'
    if msg:
        if IsReaction:
            await ctx.send(content=msg, delete_after=await_time_before_message_deletion)
        else:
            await ctx.send(msg)


@bot.event
async def on_command_error(ctx, error):
    await send_error(ctx, error)


try:
    bot.run(token)
except BaseException:
    print("Bot/Discord Error: Maybe you need to update discord.py or your token is wrong.")
system("pause")
