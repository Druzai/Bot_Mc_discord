from os import startfile, chdir, path, system, getcwd
from random import choice, randint
import discord
import vk_api
import asyncio
import json
from cryptography.fernet import Fernet
from datetime import datetime
from discord.ext import commands
from mcstatus import MinecraftServer

# json and encrypt :)
IsRewrite = False
if not path.isfile('key'):
    key = Fernet.generate_key()
    with open("key", "wb") as key_file:
        key_file.write(key)
key = open("key", "rb").read()
crypt = Fernet(key)
# Crypt
if not path.isfile('bot.json'):
    config = {
        "Token": None,
        "IP-adress": None,
        "Menu_message_id": None,
        "Ask Await time": True,
        "Await time check-ups": 10,
        "Vk_ask": True,
        "Vk_login": None,
        "Vk_pass": None
    }
    with open('bot.json', 'w') as f:
        json.dump(config, f, indent=2)
with open('bot.json', 'r') as f:
    config = json.load(f)
# Decrypt
if config.get("Token"):
    config["Token"] = crypt.decrypt(config["Token"].encode()).decode()
if config.get("Vk_login"):
    config["Vk_login"] = crypt.decrypt(config["Vk_login"].encode()).decode()
if config.get("Vk_pass"):
    config["Vk_pass"] = crypt.decrypt(config["Vk_pass"].encode()).decode()
print("Reading config")
if config.get("Token"):
    token = config.get("Token")
else:
    IsRewrite = True
    token = str(input("Token not founded. Enter token: "))
    config["Token"] = crypt.encrypt(token.encode()).decode()

Vk_get = False
if config.get("Vk_login") and config.get("Vk_pass"):
    log_vk = config.get("Vk_login")
    pass_vk = config.get("Vk_pass")
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
        config["Vk_ask"] = False
        if config.get("Vk_login") and config.get("Vk_pass"):
            print("I'll never ask you about it again.")
        else:
            print("Vk account data not received.\nI'll never ask you about it again.\nNote: command %say won't work.")
    else:
        if not config.get("Vk_login") and not config.get("Vk_pass"):
            print("Vk account data received. Why man?")
        else:
            print("Vk account data not received.\nI'll ask you again *evil laughter*.\nNote: command %say won't work.")

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

if config.get("Ask Await time"):
    print("Await time check-ups. Now it set to " + str(config.get("Await time check-ups")) + " seconds. Would you like to change it? y/n")
    if input() == 'y':
        IsRewrite = True
        await_time = int(input("Set await time between check-ups 'Server on/off' (in seconds, int): "))
        config["Await time check-ups"] = await_time
    print("Never ask about it again? y/n")
    if input() == 'y':
        config["Ask Await time"] = False
        print("Await time will be brought from config.")
else:
    await_time = config.get("Await time check-ups")
    print("Await time check-ups set to " + str(config.get("Await time check-ups")) + " seconds.")

if IsRewrite:
    with open('bot.json', 'w') as f:
        json.dump(config, f, indent=2)
    print("Config saved!")
print("Config loaded!")
current_bot_path = path.abspath(getcwd())
chdir("..")
ansii_com = {"status": "🗨", "list": "📋", "start": "♿", "stop": "⏹", "restart": "🔄"}
query = 0
IsServerOn = False
IsLoading = False
IsStopping = False
IsReaction = False
react_auth = ""
LastUpdateTime = datetime.now()
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
    global IsServerOn, IsLoading, IsStopping, query
    IsLoading = True
    print("Loading server")
    await ctx.send("```Loading server.......\nPlease wait)```")
    startfile("Start_bot.bat")
    while True:
        await asyncio.sleep(1)
        try:
            query = MinecraftServer.lookup(IP_adress + ":25585").query()
            break
        except(BaseException):
            pass
    print("Server's on now")
    await ctx.send("```Server's on now```")
    IsLoading = False
    IsServerOn = True
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))


async def stop_server(ctx, How_many_sec=10, IsRestart=False):
    global IsServerOn, IsLoading, IsStopping, query
    IsStopping = True
    chdir("mcrcon")
    command_ = 'mcrcon.exe -H ' + IP_adress + ' -P 25575 -p rconpassword'
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
            command_ += ' -w ' + str(w) + ' "say Server\'s shutting down in ' + str(How_many_sec) + ' seconds"'
        else:
            command_ += ' -w ' + str(w) + ' "say Server\'s restarting in ' + str(How_many_sec) + ' seconds"'
        for i in range(How_many_sec, -1, -w):
            command_ += ' "say ' + str(i) + ' sec to go"'
    command_ += ' stop'
    # print("Stopping server")
    await ctx.send("```Stopping server.......\nPlease wait " + str(How_many_sec) + " sec.```")
    system(command_)
    chdir("..")
    while True:
        await asyncio.sleep(1)
        try:
            query = MinecraftServer.lookup(IP_adress + ":25585").query()
        except(BaseException):
            break
    # await asyncio.sleep(How_many_sec)
    IsStopping = False
    IsServerOn = False
    print("Server's off now")
    await ctx.send("```Server's off now```")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))


async def server_checkups():
    global query, await_time, IsServerOn
    while True:
        await asyncio.sleep(await_time)
        try:
            query = MinecraftServer.lookup(IP_adress + ":25585").query()
            if not IsServerOn:
                IsServerOn = True
            if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 0:
                await bot.change_presence(
                    activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))
        except(BaseException):
            if IsServerOn:
                IsServerOn = False
            if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 2:
                await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))


@bot.event
async def on_ready():
    global IsServerOn, LastUpdateTime, query
    print('------')
    print('Logged in discord as')
    print(bot.user.name)
    print("Discord version ", discord.__version__)
    print('------')
    try:
        query = MinecraftServer.lookup(IP_adress + ":25585").query()
        IsServerOn = True
    except(BaseException):
        IsServerOn = False
    LastUpdateTime = datetime.now()
    if IsServerOn:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))
    else:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))
    print("Bot is ready!")
    print("Starting server check-ups.")
    await server_checkups()


# COMMANDS
@bot.command(pass_context=True)
# @commands.has_role('Майнкрафтер')
async def status(ctx):
    """Shows server status"""
    if IsServerOn:
        await ctx.send("```Server online```")
    else:
        await ctx.send("```Server offline```")


@bot.command(pass_context=True)
# @commands.has_role('Майнкрафтер')
async def list(ctx, command="-u"):
    global query
    if command == "-u":
        try:
            query = MinecraftServer.lookup(IP_adress + ":25585").query()
            if query.players.online == 0:
                await ctx.send("```Игроков на сервере нет```")
            else:
                await ctx.send("```Игроков на сервере - {0}\nИгроки: {1}```".format(query.players.online,
                                                                                    ", ".join(query.players.names)))
        except(BaseException):
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
    if not IsServerOn and not IsStopping and not IsLoading:
        await start_server(ctx)
    else:
        await send_status(ctx)


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def stop(ctx, command="10"):
    """End server"""
    global IsServerOn, IsLoading, IsStopping
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
    emb.add_field(name='menu', value='Создаёт меню-пульт для удобного управления командами')
    emb.add_field(name='say', value='"Петросянит" ( ͡° ͜ʖ ͡°)')
    emb.add_field(name='clear {1}', value='Удаляет {} строк')
    await ctx.send(embed=emb)


@bot.command(pass_context=True)
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
        print(f'У {author2} нет роли для команды')
        await ctx.send(f'{author}, у вас нет роли для выполнения этой команды')
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
    print("Bot/Discord Error: Maybe you need to update discord.py or your token is wrong. ¯\_(ツ)_/¯")
system("pause")
