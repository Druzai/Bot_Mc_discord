from asyncio import sleep as asleep
from datetime import datetime
from os import chdir, listdir
from pathlib import Path
from random import choice, randint

import discord
import vk_api
from discord import Activity, ActivityType
from discord.ext import commands
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r

from decorators import role
from commands.additional_funcs import server_checkups, send_error, send_msg, send_status, stop_server, start_server, get_author_and_mention
from commands.poll import Poll
from config.init_config import Bot_variables, Config


class Main_commands(commands.Cog):
    _ansii_com = {"status": "🗨", "list": "📋", "start": "♿", "stop": "⏹", "restart": "🔄",
                 "update": "📶"}  # Symbols for menu

    def __init__(self, bot):
        self._bot = bot
        self._IndPoll = Poll(bot)
        Config.read_server_info()
        print("Server info read!")

    @commands.Cog.listener()
    async def on_ready(self):
        print('------')
        print('Logged in discord as')
        print(self._bot.user.name)
        print("Discord version", discord.__version__)
        print('------')
        await self._bot.change_presence(activity=Activity(type=ActivityType.watching, name="nsfw"))
        print("Bot is ready!")
        print("Starting server check-ups.")
        await server_checkups(bot=self._bot)

    """
    @commands.command(pass_context=True)
    async def debug(self, ctx):
        await send_msg(ctx, "Constants:\nIsServerOn: " + str(IsServerOn) + "\nIsLoading: " + str(IsLoading)
                       + "\nIsStopping: " + str(IsStopping) + "\nIsRestarting: " + str(IsRestarting))
    """

    # COMMANDS
    @commands.command(pass_context=True)
    async def status(self, ctx, IsReaction=False):
        """Shows server status"""
        states = "\n"
        server_dates = Config.read_server_dates()
        for i in range(len(server_dates)):
            if len(server_dates[i]) == 0:
                continue
            if i == 0:
                states += "Server has been started at "
            else:
                states += "Server has been stopped at "
            states += server_dates[i][0] + ", by " + server_dates[i][1]
            if i != len(server_dates):
                states += "\n"
        if Bot_variables.IsServerOn:
            try:
                with Client_r(Config.get_local_address(), Bot_variables.port_rcon, timeout=1) as cl_r:
                    cl_r.login(Bot_variables.rcon_pass)
                    time_ticks = int(cl_r.run("time query daytime").split(" ")[-1])
                message = "Time in minecraft: "
                if 450 <= time_ticks <= 11616:
                    message += "Day, "
                elif 11617 <= time_ticks <= 13800:
                    message += "Sunset, "
                elif 13801 <= time_ticks <= 22550:
                    message += "Night, "
                else:
                    message += "Sunrise, "
                await send_msg(ctx, "```Server online\n" + message + str((6 + time_ticks // 1000) % 24) + ":"
                               + f"{((time_ticks % 1000) * 60 // 1000):02d}" + "\nServer adress: " + Config.get_ip_address() +
                               "\nSelected server: " + Config.get_selected_server_list()[1] + states + "```",
                               IsReaction)
            except BaseException:
                await send_msg(ctx, "```Server online\nServer adress: " + Config.get_ip_address() + "\nSelected server: " +
                               Config.get_selected_server_list()[1] + states + "```", IsReaction)
                print("Serv's down via rcon")
            """rcon check daytime cycle"""
        else:
            await send_msg(ctx, "```Server offline\nServer adress: " + Config.get_ip_address() + "\nSelected server: " +
                           Config.get_selected_server_list()[1] + states + "```", IsReaction)

    @commands.command(pass_context=True, aliases=["ls"])
    async def list(self, ctx, command="-u", IsReaction=False):
        """Shows list of players"""
        if command == "-u":
            try:
                with Client_q(Config.get_local_address(), Bot_variables.port_query, timeout=1) as cl_q:
                    info = cl_q.full_stats
                    if info.num_players == 0:
                        await send_msg(ctx, "```Игроков на сервере нет```", IsReaction)
                    else:
                        await send_msg(ctx, "```Игроков на сервере - {0}\nИгроки: {1}```".format(info.num_players,
                                                                                                 ", ".join(
                                                                                                     info.players)),
                                       IsReaction)
            except BaseException:
                _, author_mention = get_author_and_mention(ctx, self._bot, IsReaction)
                await send_msg(ctx, f"{author_mention}, сервер сейчас выключен", IsReaction)
        else:
            await send_error(ctx, self._bot, commands.UserInputError(), IsReaction=IsReaction)

    @commands.command(pass_context=True)
    @role.has_role_or_default()
    async def start(self, ctx, IsReaction=False):
        """Start server"""
        if not Bot_variables.IsServerOn and not Bot_variables.IsStopping and not Bot_variables.IsLoading:
            await start_server(ctx, bot=self._bot, IsReaction=IsReaction)
        else:
            await send_status(ctx, IsReaction=IsReaction)

    @commands.command(pass_context=True)
    @role.has_role_or_default()
    # TODO: add poll when there's more than 0 player on server, add yes - no in reactions! Do this to make approval
    async def stop(self, ctx, command="0", IsReaction=False):
        """Stop server"""
        try:
            if int(command) >= 0:
                if Bot_variables.IsServerOn and not Bot_variables.IsStopping and not Bot_variables.IsLoading:
                    if Bot_variables.IsDoOp:
                        await send_msg(ctx, "```Some player/s still oped, waiting for them```", IsReaction)
                        return
                    if Config.get_forceload():
                        Config.set_forceload(False)
                    await stop_server(ctx, self._bot, int(command), IsReaction=IsReaction)
                else:
                    await send_status(ctx, IsReaction=IsReaction)
        except ValueError:
            await send_error(ctx, self._bot, commands.UserInputError(), IsReaction=IsReaction)

    @commands.command(pass_context=True)
    @role.has_role_or_default()
    async def restart(self, ctx, command="0", IsReaction=False):
        """Restart server"""
        try:
            if int(command) >= 0:
                if Bot_variables.IsServerOn and not Bot_variables.IsStopping and not Bot_variables.IsLoading:
                    if Bot_variables.IsDoOp:
                        await send_msg(ctx, "```Some player/s still oped, waiting for them```", IsReaction)
                        return
                    Bot_variables.IsRestarting = True
                    print("Restarting server")
                    await stop_server(ctx, self._bot, int(command), True, IsReaction=IsReaction)
                    await start_server(ctx, bot=self._bot, IsReaction=IsReaction)
                else:
                    await send_status(ctx, IsReaction=IsReaction)
        except ValueError:
            await send_error(ctx, self._bot, commands.UserInputError(), IsReaction=IsReaction)

    @commands.command(pass_context=True)
    @role.has_role_or_default()
    async def op(self, ctx, arg1, arg2, *args):
        """Op command
        :arg1 - nick,
        :arg2 - code,
        :*args - comment"""
        IsFound = False
        IsEmpty = False
        Bot_variables.IsDoOp = True
        temp_s = []
        # List of player(s) who used this command, it needed to determinate should bot rewrite 'op_keys' or not
        if Bot_variables.IsServerOn and not Bot_variables.IsStopping and not Bot_variables.IsLoading and not Bot_variables.IsRestarting:
            keys_for_nicks = Config.read_op_keys()
            arg1 = arg1.lower()
            if arg1 in keys_for_nicks.keys():
                for _ in keys_for_nicks.get(arg1):
                    temp_s = keys_for_nicks.get(arg1)
                    if _ == arg2:
                        IsFound = True
                        Bot_variables.op_deop_list.append(arg1)
                        open(Path(Config.get_bot_config_path() + '/op_log.txt'), 'a', encoding='utf-8').write(
                            datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || Opped " + arg1 + " || Reason: " + (
                                ' '.join(args) if args else "None") + "\n")
                        await_time_op = Config.get_await_time_op()
                        try:
                            with Client_r(Config.get_local_address(), Bot_variables.port_rcon, timeout=1) as cl_r:
                                cl_r.login(Bot_variables.rcon_pass)
                                cl_r.say(arg1 + ' you\'ve opped for' + (
                                    "" if await_time_op // 60 == 0 else " " + str(await_time_op // 60) + ' min') + (
                                             "." if await_time_op % 60 == 0 else " " + str(
                                                 await_time_op % 60) + ' sec.'))
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
                            if arg1 != Bot_variables.op_deop_list[-1]:
                                return
                            to_delete_ops = []
                            for i in Config.get_ops_json():
                                for k, v in i.items():
                                    if k == "name":
                                        to_delete_ops.append(v)
                            while True:
                                await asleep(Config.get_await_time_to_sleep())
                                try:
                                    with Client_r(Config.get_local_address(), Bot_variables.port_rcon, timeout=1) as cl_r:
                                        cl_r.login(Bot_variables.rcon_pass)
                                        cl_r.say(arg1 + ' you all will be deoped now.')
                                        for _ in to_delete_ops:
                                            cl_r.deop(_)
                                        list = cl_r.run("list").split(":")[1].split(", ")
                                        for _ in list:
                                            cl_r.run("gamemode 0 " + _)
                                    break
                                except BaseException:
                                    pass
                            Config.append_to_op_log(datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || Deopped all " + (
                                    str("|| Note: " + str(len(Bot_variables.op_deop_list)) + " people deoped in belated list") if len(
                                        Bot_variables.op_deop_list) > 1 else "") + "\n")
                            await ctx.send("Ну что, " + ctx.author.mention +
                                           ", кончилось твоё время.. и не только твоё.... Как говорится \"Чики-брики и в дамки!\"")
                            Bot_variables.op_deop_list.clear()
                            Bot_variables.IsDoOp = False
                        else:
                            await ctx.send(
                                ctx.author.mention + ", у тебя нет ограничения по времени, но вы все обречены...")
                            Bot_variables.IsDoOp = False
                if temp_s:
                    Config.save_op_keys(keys_for_nicks)
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

    @commands.command(pass_context=True)
    # @role.has_role_if_given_in_config()
    @commands.has_permissions(administrator=True)
    async def assoc(self, ctx, arg1: str, arg2, arg3):
        """
        syntax: Nick_Discord +=/-= Nick_minecraft
        """
        id_to_nicks = Config.read_id_to_nicks()
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
            Config.save_id_to_nicks(id_to_nicks)
        else:
            await ctx.send("Wrong 1-st argument! You can mention ONLY members")

    @commands.command(pass_context=True)
    # @role.has_role_if_given_in_config()
    async def codes(self, ctx, arg1):
        member = ctx.author
        id = str(member.id)
        arg1 = arg1.lower()
        id_to_nicks = Config.read_id_to_nicks()
        if arg1 != "" and arg1 in id_to_nicks.keys() and id_to_nicks.get(arg1) == id:
            keys_for_nicks = Config.read_op_keys()
            if arg1 not in keys_for_nicks.keys():
                await ctx.send("Don't have such nickname logged in minecraft")
                return
            message = "For player with nickname " + arg1 + " generated " + str(
                len(keys_for_nicks.get(arg1))) + " codes:\n"
            for value in keys_for_nicks.get(arg1):
                message += "`" + value + "`\n"
            await member.send(message)
        else:
            # Check if /Gendalf_Top exists! TODO: refactor this piece of code!!!
            if Path(Config.get_bot_config_path() + '/Gendalf_Top').is_dir():
                gifs_list = listdir(Path(Config.get_bot_config_path() + '/Gendalf_Top'))
                await member.send('You shall not PASS! Ты не владеешь данным ником :ambulance:',
                                  file=discord.File(Path(Config.get_bot_config_path() + '/Gendalf_Top/' + choice(gifs_list))))
            else:
                print("Folder 'Gendalf_Top' hasn't been found in that path '" + Config.get_bot_config_path() +
                      "'. Maybe you want to create it and fill it with images related to Gendalf :)")
                await member.send('You shall not PASS! Ты не владеешь данным ником :ambulance:')

    @commands.command(pass_context=True)
    async def say(self, ctx):
        """Петросян"""
        vk_login, vk_pass  = Config.get_vk_credentials()
        if vk_login is not None and vk_pass is not None:
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
                chdir(Config.get_bot_config_path())
                try:
                    # Тырим с вк фотки)
                    vk_session = vk_api.VkApi(vk_login, vk_pass)
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

    @commands.command(pass_context=True, aliases=["fl"])
    @role.has_role_or_default()
    async def forceload(self, ctx, command=""):
        if command == "on" and not Config.get_forceload():
            Config.set_forceload(True)
            await ctx.send("```Forceload on```")
        elif command == "off" and Config.get_forceload():
            Config.set_forceload(False)
            await ctx.send("```Forceload off```")
        elif command == "":
            if Config.get_forceload():
                await ctx.send("```Forceload on```")
            else:
                await ctx.send("```Forceload off```")
        else:
            raise commands.UserInputError()

    @commands.command(pass_context=True, aliases=["wl"])
    @role.has_role_or_default()
    async def whitelist(self, ctx, *args):
        if len(args) and args[0] in ["add", "del", "list", "on", "off", "reload"]:
            try:
                with Client_r(Config.get_local_address(), Bot_variables.port_rcon, timeout=1) as cl_r:
                    cl_r.login(Bot_variables.rcon_pass)
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

    @commands.command(pass_context=True, aliases=["servs"])
    @role.has_role_or_default()
    async def servers(self, ctx, *args):
        if len(args) and (args[0] == "list" or args[0] == "select" or args[0] == "show"):
            minecraft_dirs = Config.get_minecraft_dirs_list()
            if args[0] == "list":
                send_ = "```List of servers"
                for i in range(len(minecraft_dirs)):
                    send_ += "\n" + str(i) + ". " + minecraft_dirs[i][1]
                send_ += "```"
                await ctx.send(send_)
            elif args[0] == "select":
                if len(args) < 2:
                    await ctx.send("Э, " + ctx.author.mention + ", где число?")
                    return
                try:
                    if int(args[1]) <= len(minecraft_dirs):
                        if int(args[1]) == Config.get_selected_minecraft_server_number():
                            await ctx.send(
                                "```My, you have chosen selected server, insane?)\n ...Pasan ramsi poputal```")
                            return
                        if Bot_variables.IsServerOn:
                            await ctx.send("```You can't change servers, while some instance(s) is/are still running" +
                                           "\nPlease stop it, before trying again```")
                            return
                        Config.set_selected_minecraft_server(int(args[1]))
                        Config.read_server_info()
                        await ctx.send("```Server properties read!```")
                    else:
                        await ctx.send("```Use server list, there's no such server on the list!```")
                except BaseException:
                    await ctx.send("```Argument for 'select' must be a number!```")
            elif args[0] == "show":
                await ctx.send(
                    "```Selected server #" + str(Config.get_selected_minecraft_server_number()) +
                    ". " + Config.get_selected_server_list()[1] + "```")
            else:
                await ctx.send("```Wrong command!\nCommands: select, list```")
        else:
            await ctx.send("```Commands: select, list, show```")
            raise commands.UserInputError()

    @commands.command(pass_context=True)
    async def help(self, ctx):
        await ctx.channel.purge(limit=1)
        emb = discord.Embed(title='Список всех команд (через %)',
                            color=discord.Color.gold())
        emb.add_field(name='status', value='Возвращает статус сервера')
        emb.add_field(name='list/ls',
                      value='Возвращает список игроков')
        emb.add_field(name='start', value='Запускает сервер')
        emb.add_field(name='stop {10}', value='Останавливает сервер, {} (сек) сколько идёт отсчёт, без аргументов - убирает таймер')
        emb.add_field(name='restart {10}', value='Перезапускает сервер, {} (сек) сколько идёт отсчёт, без аргументов - убирает таймер')
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
        emb.add_field(name='servers/servs {1}',
                      value='Использует список серверов в боте, аргументы {1} - select, list, show.  При select ещё пишется номер сервера из list')
        emb.add_field(name='say', value='"Петросянит" ( ͡° ͜ʖ ͡°)')
        emb.add_field(name='clear/cls {1}',
                      value='Если положительное число удаляет {1} сообщений, если отрицательное - удаляет n сообщений до {1} от начала канала')
        await ctx.send(embed=emb)

    @commands.command(pass_context=True)
    @role.has_role_or_default()
    async def menu(self, ctx):
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
        Config.set_menu_id(str(add_reactions_to.id))
        await add_reactions_to.add_reaction(self._ansii_com.get("status"))
        await add_reactions_to.add_reaction(self._ansii_com.get("list"))
        await add_reactions_to.add_reaction(self._ansii_com.get("start"))
        await add_reactions_to.add_reaction(self._ansii_com.get("stop"))
        await add_reactions_to.add_reaction(self._ansii_com.get("restart"))
        await add_reactions_to.add_reaction(self._ansii_com.get("update"))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id == int(Config.get_menu_id()) and payload.member.id != self._bot.user.id:
            channel = self._bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)
            if payload.emoji.name in self._ansii_com.values():
                Bot_variables.react_auth = payload.member
                if payload.emoji.name == self._ansii_com.get("status"):
                    await self.status(channel, IsReaction=True)
                elif payload.emoji.name == self._ansii_com.get("list"):
                    await self.list(channel, IsReaction=True)
                elif payload.emoji.name == self._ansii_com.get("update"):
                    await server_checkups(bot=self._bot, always_=False)  # TODO: rewrite this line, serv_checkups doesn't proceed after this command!
                    return
                else:
                    if Config.get_role() not in (e.name for e in payload.member.roles):
                        await send_error(channel, self._bot, commands.MissingRole(Config.get_role()), IsReaction=True)
                    else:
                        if payload.emoji.name == self._ansii_com.get("start"):
                            await self.start(channel, IsReaction=True)
                        elif payload.emoji.name == self._ansii_com.get("stop"):
                            await self.stop(channel, command="10", IsReaction=True)
                        elif payload.emoji.name == self._ansii_com.get("restart"):
                            await self.restart(channel, command="10", IsReaction=True)

    @commands.command(pass_context=True, aliases=["cls"])
    # @commands.has_permissions(administrator=True)
    async def clear(self, ctx, count=1):  # TODO: add arg all to clear all msgs in channel
        message_created_time = ""
        try:
            int(str(count))
        except BaseException:
            await ctx.send("Ты дебик? Чё ты там написал? Как мне это понимать? А? '" + str(count) + "' Убейся там!")
        if count > 0:
            if len(await ctx.channel.history(limit=51).flatten()) < 51:
                await ctx.channel.purge(limit=count + 1, bulk=False)
                return
        elif count < 0:
            message_created_time = (await ctx.channel.history(limit=-count, oldest_first=True).flatten())[-1].created_at
            if len(await ctx.channel.history(limit=51, after=message_created_time, oldest_first=True).flatten()) != 51:
                await ctx.channel.purge(limit=None, after=message_created_time, bulk=False)
                return
        else:
            await send_msg(ctx, "Nothing's done!", True)
            return
        if await self._IndPoll.timer(ctx, 5):
            if await self._IndPoll.run(ctx=ctx, remove_logs_after=5):
                if count < 0:
                    await ctx.channel.purge(limit=None, after=message_created_time, bulk=False)
                else:
                    await ctx.channel.purge(limit=count + 1, bulk=False)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await send_error(ctx, self._bot, error)
