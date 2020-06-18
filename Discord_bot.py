import os
from random import randint, choice
import discord
import asyncio
from discord.ext import commands

token = open('token.txt', 'r').readline()
IsServerOn = False
IsLoading = False
IsStopping = False
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
    # os.system("D:\Minecraft_server\server_mods\Test.bat")
    os.chdir("D:\Minecraft_server\server_mods")
    os.startfile("Start_bot.bat")
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
    os.chdir("D:\Minecraft_server\mcrcon")
    os.startfile(file_name)
    await asyncio.sleep(15)
    IsStopping = False
    IsServerOn = False
    print("Server's off now")
    await ctx.send("```Server's off now```")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name="Server"))


@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    #print(bot.user.id)
    print("Discord version ", discord.__version__)
    print('------')
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
    if randint(2):
        _300_answers = [
            'Ну, держи!',
            'Ah, shit, here we go again.',
            'Ты сам напросился...'
        ]
        await ctx.send(choice(_300_answers))
        if randint(2):
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
                        color=discord.Color.green())
    emb.add_field(name='get_status', value='Возвращает статус сервера')
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
    if isinstance(error, commands.MissingRequiredArgument):
        print(f'{ctx.author} не указал аргумент')
        await ctx.send(f'{ctx.author}, пожалуйста, введи все аргументы ')
    if isinstance(error, commands.MissingPermissions):
        print(f'У {ctx.author} мало прав для команды')
        await ctx.send(f'{ctx.author}, у вас недостаточно прав для выполнения этой команды')
    if isinstance(error, commands.MissingRole):
        print(f'У {ctx.author} нет роли для команды')
        await ctx.send(f'{ctx.author}, у вас нет роли для выполнения этой команды')
    if isinstance(error, commands.CommandNotFound):
        print(f'{ctx.author} ввёл несуществующую команду')
        await ctx.send(f'{ctx.author}, вы ввели несуществующую команду')
    if isinstance(error, commands.UserInputError):
        print(f'{ctx.author} неправильно ввёл команду')
        await ctx.send(f'{ctx.author}, вы неправильно ввели команду')
    if isinstance(error, commands.DisabledCommand):
        print(f'{ctx.author} ввёл отключённую команду')
        await ctx.send(f'{ctx.author}, вы ввели отлючённую команду')


@get_status.error
async def get_status_error(ctx, error):
    await send_error(ctx, error)


@start.error
async def start_error(ctx, error):
    await send_error(ctx, error)


@restart.error
async def restart_error(ctx, error):
    await send_error(ctx, error)


@stop.error
async def stop_error(ctx, error):
    await send_error(ctx, error)


@clear.error
async def clear_error(ctx, error):
    await send_error(ctx, error)


@bot.event
async def on_command_error(ctx, error):
    await send_error(ctx, error)


bot.run(token)
