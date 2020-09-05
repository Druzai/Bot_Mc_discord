from os import startfile, chdir, path, system, getcwd
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

# json and encrypt :)
IsRewrite = False
if not path.isfile('key'):
    key = Fernet.generate_key()
    with open("key", "wb") as key_file:
        key_file.write(key)
key = open("key", "rb").read()
crypt = Fernet(key)
# Crypt
if not path.isfile('op_keys'):
    open('op_keys', 'wb').write(crypt.encrypt(json.dumps(dict()).encode()))
keys_for_nicks = json.loads(crypt.decrypt(open('op_keys', 'rb').read())).keys()
if not path.isfile('bot.json'):
    config = {
        "Token": None,
        "IP-adress": None,
        "Menu_message_id": None,
        "Ask await time check-ups": True,
        "Await time check-ups": 15,
        "Forceload": False,
        "Await time op": 600,
        "Vk_ask": True,
        "Vk_login": None,
        "Vk_pass": None
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

if config.get("IP-adress"):
    IP_adress = config.get("IP-adress")
else:
    IsRewrite = True
    IP_adress = str(input("Enter server's IP-address from Radmin: "))
    config["IP-adress"] = IP_adress

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

if IsRewrite:
    with open('bot.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("Config saved!")
print("Config loaded!")
current_bot_path = path.abspath(getcwd())
chdir("..")
ansii_com = {"status": "🗨", "list": "📋", "start": "♿", "stop": "⏹", "restart": "🔄"}
IsServerOn = False
IsLoading = False
IsStopping = False
IsReaction = False
IsForceload = config.get("Forceload")
react_auth = ""
op_deop_list = []
bot = commands.Bot(command_prefix='%', description="Server bot")
bot.remove_command('help')


# ANOTHER_COMMANDS
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


async def start_server(ctx):
    global IsServerOn, IsLoading, IsStopping
    IsLoading = True
    print("Loading server")
    await ctx.send("```Loading server.......\nPlease wait)```")
    startfile("Start_bot.bat")
    while True:
        try:
            with Client_q(IP_adress, 25585, timeout=1) as cl_q:
                info = cl_q.basic_stats
            break
        except (BaseException):
            pass
    await ctx.send("```Server's on now```")
    IsLoading = False
    IsServerOn = True
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))


async def stop_server(ctx, How_many_sec=10, IsRestart=False):
    global IsServerOn, IsLoading, IsStopping
    IsStopping = True
    print("Stopping server")
    await ctx.send("```Stopping server.......\nPlease wait " + str(How_many_sec) + " sec.```")
    try:
        with Client_r(IP_adress, 25575, timeout=1) as cl_r:
            cl_r.login('rconpassword')
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
        try:
            with Client_q(IP_adress, 25585, timeout=1) as cl_q:
                info = cl_q.basic_stats
        except (BaseException):
            break
    IsStopping = False
    IsServerOn = False
    print("Server's off now")
    await ctx.send("```Server's off now```")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))


async def server_checkups(always_=True):
    global await_time_check_ups, IsServerOn, keys_for_nicks, IsStopping, IsLoading
    while True:
        if await_time_check_ups > 0 and always_:
            await asyncio.sleep(await_time_check_ups)
        try:
            with Client_q(IP_adress, 25585, timeout=1) as cl_q:
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
                    chdir(current_bot_path)
                    orig = json.loads(crypt.decrypt(open('op_keys', 'rb').read()))
                    orig.update(nicks_n_keys_add)
                    keys_for_nicks = orig.keys()
                    open('op_keys', 'wb').write(crypt.encrypt(json.dumps(orig).encode()))
                    orig = {}
                    chdir("..")
            if not IsServerOn:
                IsServerOn = True
            if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 0:
                await bot.change_presence(
                    activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))
        except (BaseException):
            if IsServerOn:
                IsServerOn = False
            if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 2:
                await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))
            if always_ and IsForceload and not IsStopping and not IsLoading:
                for guild in bot.guilds:
                    for channel in guild.channels:
                        try:
                            await channel.fetch_message(menu_id)
                            await start_server(channel)
                            break
                        except(BaseException):
                            pass
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
    try:
        with Client_q(IP_adress, 25585, timeout=1) as cl_q:
            info = cl_q.basic_stats
        IsServerOn = True
    except (BaseException):
        IsServerOn = False
    if IsServerOn:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))
    else:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))
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
            with Client_r(IP_adress, 25575, timeout=1) as cl_r:
                cl_r.login('rconpassword')
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
                           ":" + str((time_ticks % 1000) * 60 // 1000) + "```")
        except (BaseException):
            await ctx.send("```Server online```")
            print("Serv's down via rcon")
        """rcon check daytime cycle"""
    else:
        await ctx.send("```Server offline```")


@bot.command(pass_context=True)
async def list(ctx, command="-u"):
    global IsReaction
    if command == "-u":
        try:
            with Client_q(IP_adress, 25585, timeout=1) as cl_q:
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
    """End server"""
    global IsServerOn, IsLoading, IsStopping
    await server_checkups(False)
    try:
        if int(command) >= 0:
            if IsServerOn and not IsStopping and not IsLoading:
                await stop_server(ctx, int(command))
            else:
                await send_status(ctx)
    except(ValueError):
        raise commands.UserInputError()


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def restart(ctx, command="10"):
    """Restart server"""
    global IsServerOn, IsLoading, IsStopping
    await server_checkups(False)
    try:
        if int(command) >= 0:
            if IsServerOn and not IsStopping and not IsLoading:
                print("Restarting server")
                IsServerOn = False
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
    global IsServerOn, IsLoading, IsStopping, op_deop_list  # , query
    IsFound = False
    IsEmpty = False
    temp_s = []
    # await ctx.channel.purge(limit=1)
    if IsServerOn and not IsStopping and not IsLoading:
        chdir(current_bot_path)
        keys_for_nicks = json.loads(crypt.decrypt(open('op_keys', 'rb').read()))
        chdir("..")
        arg1 = arg1.lower()
        if arg1 in keys_for_nicks.keys():
            for _ in keys_for_nicks.get(arg1):
                temp_s = keys_for_nicks.get(arg1)
                if _ == arg2:
                    IsFound = True
                    op_deop_list.append(arg1)
                    open(current_bot_path + '\\op_log.txt', 'a').write(
                        datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || Opped " + arg1 + " || Reason: " + (
                            ' '.join(args) if args else "None") + "\n")
                    try:
                        with Client_r(IP_adress, 25575, timeout=1) as cl_r:
                            cl_r.login('rconpassword')
                            cl_r.say(arg1 + ' you\'ve opped for ' + str(int(await_time_op / 60)) + ' min ' + str(
                                await_time_op - int(await_time_op / 60) * 60) + ' sec.')
                            cl_r.mkop(arg1)
                    except (BaseException):
                        await ctx.send(ctx.author.mention + ", а сервак-то не работает (по крайней мере я пытался), попробуй-ка позже.")
                        return
                    keys_for_nicks.get(arg1).remove(arg2)
                    await ctx.send("```Code activated```")
                    if await_time_op > 0:
                        if bool(randint(0, 4)):
                            await ctx.send(
                                "Короче, " + ctx.author.mention + ", я тебя op'нул и в благородство играть не буду: приду через "
                                + str(int(await_time_op / 60)) + " минут," +
                                " deop'ну всех - и мы в расчёте. Заодно постараюсь разузнать на кой ляд тебе эта op'ка нужна," +
                                " но я в чужие дела не лезу, если хочешь получить, значит есть за что...")
                        await asyncio.sleep(await_time_op)
                        if arg1 != op_deop_list[-1]:
                            return
                        chdir("..")
                        ops = json.load(open('ops.json', 'r'))
                        chdir("mcrcon")
                        to_delete_ops = []
                        for i in ops:
                            for k, v in i.items():
                                if k == "name":
                                    to_delete_ops.append(v)
                        while True:
                            try:
                                with Client_r(IP_adress, 25575, timeout=1) as cl_r:
                                    cl_r.login('rconpassword')
                                    cl_r.say(arg1 + ' you all will be deoped now.')
                                    for _ in to_delete_ops:
                                        cl_r.deop(_)
                                    list = cl_r.run("list").split(":")[1].split(", ")
                                    for _ in list:
                                        cl_r.run("gamemode 0 " + _)
                                break
                            except (BaseException):
                                pass
                        open(current_bot_path + '\\op_log.txt', 'a').write(datetime.now().strftime("%d/%m/%Y, %H:%M:%S")
                                                                           + " || Deopped all " + str(
                            "|| Note: " + str(len(op_deop_list)) + " people deoped in belated list") if len(
                            op_deop_list) > 1 else "" + "\n")
                        await ctx.send("Ну что, " + ctx.author.mention +
                                       ", кончилось твоё время.. и не только твоё.... Как говорится \"Чики-брики и в дамки!\"")
                        op_deop_list.clear()
                    else:
                        await ctx.send(
                            ctx.author.mention + ", у тебя нет ограничения по времени, но вы все обречены...")
                    chdir("..")
            if temp_s:
                chdir(current_bot_path)
                open('op_keys', 'wb').write(crypt.encrypt(json.dumps(keys_for_nicks).encode()))
                chdir("..")
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
                chdir("..")
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


@bot.command(pass_context=True)
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
            with open(current_bot_path + '\\bot.json', 'w') as f_:
                json.dump(config, f_, indent=2)
    elif command == " ":
        if IsForceload:
            await ctx.send("```Forceload on```")
        else:
            await ctx.send("```Forceload off```")
    else:
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
    emb.add_field(name='forceload {on/off}',
                  value='По {on/off} постоянная загрузка сервера, когда он отключен, без аргументов - статус')
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
    with open(current_bot_path + '\\bot.json', 'w') as f_:
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


# ERRORS
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
