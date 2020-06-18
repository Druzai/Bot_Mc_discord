from os import startfile, chdir
from re import findall
from random import getrandbits, choice
import discord
import asyncio
from datetime import datetime
from discord.ext import commands

token = open('token.txt', 'r').readline()
IsServerOn = False
IsLoading = False
IsStopping = False
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
    global IsServerOn, IsLoading, IsStopping
    IsLoading = True
    print("Loading server")
    await ctx.send("```Loading server.......\nWait please about 40 seconds)```")
    chdir("D:\Minecraft_server\server_mods")
    startfile("Start_bot.bat")
    await asyncio.sleep(40)
    print("Server's on now")
    await ctx.send("```Server's on now```")
    IsLoading = False
    IsServerOn = True
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))


async def stop_server(ctx, file_name="launch.bat"):
    global IsServerOn, IsLoading, IsStopping
    IsStopping = True
    print("Stopping server")
    await ctx.send("```Stopping server.......\nWait please about 15 seconds```")
    chdir("D:\Minecraft_server\mcrcon")
    startfile(file_name)
    await asyncio.sleep(15)
    IsStopping = False
    IsServerOn = False
    print("Server's off now")
    await ctx.send("```Server's off now```")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))


async def write_list(ctx, need_to_write=True):
    global IsServerOn
    count = 0
    with open("D:\Minecraft_server\mcrcon\list.txt", 'r') as f:
        str_f = f.readline()
        if str_f:
            count = int(findall(r"\d+[/]\d+", str_f)[0].split("/")[0])
            players = str_f.strip().split(":")[1].split(", ")
    if len(str_f) > 0:
        if need_to_write:
            if count == 0:
                await ctx.send("```Игроков на сервере нет```")
            else:
                message = "```Игроков на сервере - " + str(count) + "\nИгроки: " + players[0]
                for i in range(1, len(players)):
                    message += "\n" + " " * 8 + players[i] if i and i % 3 == 0 else ", " + players[i]
                message += "```"
                await ctx.send(message)
        else:
            IsServerOn = True
    else:
        if need_to_write:
            await ctx.send(f"{ctx.author.mention}, сервер сейчас выключен")
        else:
            IsServerOn = False


@bot.event
async def on_ready():
    global IsServerOn, LastUpdateTime
    print('Logged in as')
    print(bot.user.name)
    print("Discord version ", discord.__version__)
    print('------')
    chdir("D:\Minecraft_server\mcrcon")
    startfile("launch_list.bat")
    await write_list(bot, False)
    LastUpdateTime = datetime.now()
    if IsServerOn:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name="Minecraft Server"))
    else:
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))
    print("Bot is ready!")


# COMMANDS
@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def get_status(ctx):
    """Shows server status"""
    if IsServerOn:
        await ctx.send("```Server online```")
    else:
        await ctx.send("```Server offline```")


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def get_list(ctx, command="not"):
    global LastUpdateTime
    if command == "--update" or command == "-u":
        if (datetime.now() - LastUpdateTime).seconds > 5:
            chdir("D:\Minecraft_server\mcrcon")
            startfile("launch_list.bat")
            await write_list(ctx)
            LastUpdateTime = datetime.now()
        else:
            await ctx.send(f"{ctx.author.mention}, обновлять список игроков можно раз в 5 секунд, подождите")
    elif command == "not":
        await write_list(ctx)
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
async def stop(ctx):
    """End server"""
    global IsServerOn, IsLoading, IsStopping
    if IsServerOn and not IsStopping and not IsLoading:
        await stop_server(ctx)
    else:
        await send_status(ctx)


@bot.command(pass_context=True)
@commands.has_role('Майнкрафтер')
async def restart(ctx):
    """Restart server"""
    global IsServerOn, IsLoading, IsStopping
    if IsServerOn and not IsStopping and not IsLoading:
        print("Restarting server")
        IsServerOn = False
        await stop_server(ctx, "launch_r.bat")
        await start_server(ctx)
    else:
        await send_status(ctx)


@bot.command(pass_context=True)
async def say(ctx):
    """Петросян"""
    if bool(getrandbits(1)):
        _300_answers = [
            'Ну, держи!',
            'Ah, shit, here we go again.',
            'Ты сам напросился...'
        ]
        await ctx.send(choice(_300_answers))
        if bool(getrandbits(1)):
            _300_quotes = [
                'Я назову собаку именем твоим...',
                '( ͡° ͜ʖ ͡°)',
            ]
            await ctx.send(choice(_300_quotes))
        else:
            await ctx.send(file=discord.File("D:\Minecraft_server\Ha_\VIXcr28RiVo.jpg"))
    else:
        await ctx.send("Я бы мог рассказать что-то, но мне лень. ( ͡° ͜ʖ ͡°)")
        await ctx.send("Returning to my duties.")


@bot.command(pass_context=True)
async def help(ctx):
    await ctx.channel.purge(limit=1)
    emb = discord.Embed(title='Список всех команд (через %)',
                        color=discord.Color.gold())
    emb.add_field(name='get_status', value='Возвращает статус сервера')
    emb.add_field(name='get_list [--update, -u]',
                  value='Возвращает список игроков (с параметром обновлённый список)')
    emb.add_field(name='start', value='Запускает сервер')
    emb.add_field(name='stop', value='Останавливает сервер')
    emb.add_field(name='restart', value='Перезапускает сервер')
    emb.add_field(name='say', value='"Петросянит" ( ͡° ͜ʖ ͡°)')
    # emb.add_field(name='clear {1}', value='Удаляет {} строк')
    await ctx.send(embed=emb)


@bot.command(pass_context=True)
@commands.has_permissions(administrator=True)
async def clear(ctx, count=1):
    await ctx.channel.purge(limit=int(count) + 1)


# ERRORS
async def send_error(ctx, error):
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


bot.run(token)
