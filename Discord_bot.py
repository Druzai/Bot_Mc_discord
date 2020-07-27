from os import startfile, chdir, path, system
from random import choice, randint
import discord
import vk_api
import asyncio
from datetime import datetime
from discord.ext import commands
from mcstatus import MinecraftServer

print("Reading token")
if path.isfile('token.txt'):
    token = open('token.txt', 'r').readline()
else:
    print("File not founded. Enter token.")
    token = str(input())
    with open('token.txt', 'w') as tk:
        tk.write(token)
    print("File with token created.")
print("Done!")
Vk_get = False
print("Reading file 'vk_l_p.txt' for login & password")
if path.isfile('vk_l_p.txt'):
    with open('vk_l_p.txt', 'r') as f:
        log_vk = f.readline()
        pass_vk = f.readline()
    Vk_get = True
    print("File founded and read\nDone!")
else:
    print("File not founded. Would you like to enter vk account data? y/n")
    if input() == 'y':
        log_vk = str(input("Enter vk login: "))
        pass_vk = str(input("Enter vk pass: "))
        Vk_get = True
        print("Done!")
    else:
        print("Vk account data not received\nOk, a cat is fine too...\nNote: command %say won't work")
IP_addr = str(input("Enter server's IP-address from Radmin: ")) # Сделать отдельный файл или ещё лучше json
await_time = int(input("Set await time between check-ups 'Server on/off' (in seconds, int): "))
if path.isfile('menu_id.txt'):
    menu_id = open('menu_id.txt', 'r').readline()
else:
    print("File not founded. Would you like to enter menu message id. y/n")
    if input() == 'y':
        menu_id = str(input("Enter menu message id: "))
        with open('menu_id.txt', 'w') as mi:
            mi.write(menu_id)
        print("File with menu message id created.")
    else:
        print("Menu via reactions won't work. To make it work type '%menu' to create new menu.")
print("All done!")
current_bot_path = path.dirname(path.realpath('token.txt'))
chdir("..")
query = 0
IsServerOn = False
IsLoading = False
IsStopping = False
IsReaction = False
react_auth_mention = ""
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
            query = MinecraftServer.lookup(IP_addr + ":25585").query()
            break
        except(BaseException):
            pass
    print("Server's on now")
    await ctx.send("```Server's on now```")
    IsLoading = False
    IsServerOn = True
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))


async def stop_server(ctx, How_many_sec=10, IsRestart=False):
    global IsServerOn, IsLoading, IsStopping
    IsStopping = True
    chdir("mcrcon")
    command_ = 'mcrcon.exe -H ' + IP_addr + ' -P 25575 -p rconpassword'
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
    print("Stopping server")
    await ctx.send("```Stopping server.......\nPlease wait " + str(How_many_sec + 1) + " sec.```")
    system(command_)
    chdir("..")
    await asyncio.sleep(How_many_sec + 1)
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
            query = MinecraftServer.lookup(IP_addr + ":25585").query()
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
        query = MinecraftServer.lookup(IP_addr + ":25585").query()
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
@commands.has_role('Майнкрафтер')
async def status(ctx):
    """Shows server status"""
    if IsServerOn:
        await ctx.send("```Server online```")
    else:
        await ctx.send("```Server offline```")


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def list(ctx, command="-u"):
    global query
    if command == "-u":
        try:
            query = MinecraftServer.lookup(IP_addr + ":25585").query()
            if query.players.online == 0:
                await ctx.send("```Игроков на сервере нет```")
            else:
                await ctx.send("```Игроков на сервере - {0}\nИгроки: {1}```".format(query.players.online,
                                                                                    ", ".join(query.players.names)))
        except(BaseException):
            if IsReaction:
                author = react_auth_mention
            else:
                author = ctx.author.mention
            await ctx.send(f"{author}, сервер сейчас выключен")
    else:
        await send_error(ctx, error=commands.UserInputError)


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
    if IsServerOn and not IsStopping and not IsLoading:
        await stop_server(ctx, int(command))
    else:
        await send_status(ctx)


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def restart(ctx, command="10"):
    """Restart server"""
    global IsServerOn, IsLoading, IsStopping
    if IsServerOn and not IsStopping and not IsLoading:
        print("Restarting server")
        IsServerOn = False
        await stop_server(ctx, int(command), True)
        await start_server(ctx)
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
            try:
                # Тырим с вк фотки)
                own_id = choice(_300_communities)
                chdir("BOT_Folder")
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
    global menu_id
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
    open(current_bot_path + '\\menu_id.txt', 'w').write(menu_id)
    await add_reactions_to.add_reaction("🗨")
    await add_reactions_to.add_reaction("📋")
    await add_reactions_to.add_reaction("♿")
    await add_reactions_to.add_reaction("⏹")
    await add_reactions_to.add_reaction("🔄")

@bot.event
async def on_raw_reaction_add(payload):
    global IsReaction, react_auth_mention
    if payload.message_id == int(menu_id) and payload.member.id != bot.user.id:
        if payload.emoji.name == "🗨" or payload.emoji.name == "📋" or payload.emoji.name == "♿" or payload.emoji.name == "⏹" or payload.emoji.name == "🔄":
            IsReaction = True
            react_auth_mention = payload.member.mention
            channel = bot.get_channel(payload.channel_id)
            if payload.emoji.name == "🗨":
                await status(channel)
            elif payload.emoji.name == "📋":
                await list(channel)
            elif payload.emoji.name == "♿":
                await start(channel)
            elif payload.emoji.name == "⏹":
                await stop(channel)
            elif payload.emoji.name == "🔄":
                await restart(channel)
            IsReaction = False
            message = await channel.fetch_message(payload.message_id)
            user = bot.get_user(payload.user_id)
            await message.remove_reaction(payload.emoji, user)
            await asyncio.sleep(10)
            messages = await channel.history(limit=20).flatten()
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
        author = react_auth_mention
    else:
        author = ctx.author.mention
    if isinstance(error, commands.MissingRequiredArgument):
        print(f'{ctx.author} не указал аргумент')
        await ctx.send(f'{author}, пожалуйста, введи все аргументы ')
    if isinstance(error, commands.MissingPermissions):
        print(f'У {ctx.author} мало прав для команды')
        await ctx.send(f'{author}, у вас недостаточно прав для выполнения этой команды')
    if isinstance(error, commands.MissingRole):
        print(f'У {ctx.author} нет роли для команды')
        await ctx.send(f'{author}, у вас нет роли для выполнения этой команды')
    if isinstance(error, commands.CommandNotFound):
        print(f'{ctx.author} ввёл несуществующую команду')
        await ctx.send(f'{author}, вы ввели несуществующую команду')
    if isinstance(error, commands.UserInputError):
        print(f'{ctx.author} неправильно ввёл команду или её аргументы')
        await ctx.send(f'{author}, вы неправильно ввели команду или её агрументы')
    if isinstance(error, commands.DisabledCommand):
        print(f'{ctx.author} ввёл отключённую команду')
        await ctx.send(f'{author}, вы ввели отлючённую команду')


@bot.event
async def on_command_error(ctx, error):
    await send_error(ctx, error)


try:
    bot.run(token)
except(BaseException):
    print("Error: Maybe you need to update discord.py")
system("pause")
