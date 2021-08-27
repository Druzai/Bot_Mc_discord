from asyncio import sleep as asleep, CancelledError
from contextlib import suppress
from datetime import datetime
from random import randint

import discord
from discord.ext import commands
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r

from components.additional_funcs import server_checkups, send_error, send_msg, send_status, stop_server, start_server, \
    get_author_and_mention, save_to_whitelist_json, get_whitelist_entry, get_server_online_mode, get_server_players
from config.init_config import BotVars, Config
from decorators import role


class MinecraftCommands(commands.Cog):
    _emoji_symbols = {"status": "🗨", "list": "📋", "start": "♿",
                      "stop": "⏹", "restart": "🔄", "update": "📶"}  # Symbols for menu

    def __init__(self, bot: commands.Bot):
        self._bot: commands.Bot = bot

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    async def status(self, ctx, is_reaction=False):
        """Shows server status"""
        states = ""
        states_info = Config.get_server_config().states
        if states_info.started_info.date is not None and states_info.started_info.user is not None:
            states += f"Server has been started at {states_info.started_info.date}," \
                      f" by {states_info.started_info.user}\n"
        if states_info.stopped_info.date is not None and states_info.stopped_info.user is not None:
            states += f"Server has been stopped at {states_info.stopped_info.date}," \
                      f" by {states_info.stopped_info.user}\n"
        states = states.strip("\n")
        if BotVars.is_server_on:
            try:
                with Client_r(Config.get_settings().bot_settings.local_address,
                              BotVars.port_rcon, timeout=1) as cl_r:
                    cl_r.login(BotVars.rcon_pass)
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
                await send_msg(ctx, "```Server online\n" + "Server address: " +
                               Config.get_settings().bot_settings.ip_address + "\n"
                               + message + str((6 + time_ticks // 1000) % 24) + ":"
                               + f"{((time_ticks % 1000) * 60 // 1000):02d}" + "\nSelected server: " +
                               Config.get_selected_server_from_list().server_name + "\n" + states + "```",
                               is_reaction)
            except BaseException:
                await send_msg(ctx,
                               "```Server online\nServer address: " + Config.get_settings().bot_settings.ip_address +
                               "\nServer thinking...\nSelected server: " +
                               Config.get_selected_server_from_list().server_name + "\n" + states + "```", is_reaction)
                print("Server's down via rcon")
            """rcon check daytime cycle"""
        else:
            await send_msg(ctx, "```Server offline\nServer address: " + Config.get_settings().bot_settings.ip_address +
                           "\nSelected server: " + Config.get_selected_server_from_list().server_name +
                           "\n" + states + "```",
                           is_reaction)

    @commands.command(pass_context=True, aliases=["ls"])
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    async def list(self, ctx, command="-u", is_reaction=False):
        """Shows list of players"""
        if command == "-u":
            try:
                with Client_q(Config.get_settings().bot_settings.local_address, BotVars.port_query,
                              timeout=1) as cl_q:
                    info = cl_q.full_stats
                if info.num_players == 0:
                    await send_msg(ctx, "```Игроков на сервере нет```", is_reaction)
                else:
                    await send_msg(ctx, "```Игроков на сервере - {0}\nИгроки: {1}```".format(info.num_players,
                                                                                             ", ".join(info.players)),
                                   is_reaction)
            except BaseException:
                _, author_mention = get_author_and_mention(ctx, self._bot, is_reaction)
                await send_msg(ctx, f"{author_mention}, сервер сейчас выключен", is_reaction)
        else:
            await send_error(ctx, self._bot, commands.UserInputError(), is_reaction=is_reaction)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    async def start(self, ctx, is_reaction=False):
        """Start server"""
        if not BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading:
            await start_server(ctx, bot=self._bot, is_reaction=is_reaction)
        else:
            await send_status(ctx, is_reaction=is_reaction)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    # TODO: add poll when there's more than 0 player on server, add yes - no in reactions! Do this to make approval
    async def stop(self, ctx, command="0", is_reaction=False):
        """Stop server"""
        try:
            if int(command) >= 0:
                if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading:
                    if BotVars.is_doing_op:
                        await send_msg(ctx, "```Some player/s still oped, waiting for them```", is_reaction)
                        return
                    if Config.get_settings().bot_settings.forceload:
                        Config.get_settings().bot_settings.forceload = False
                        Config.save_config()
                    await stop_server(ctx, self._bot, int(command), is_reaction=is_reaction)
                else:
                    await send_status(ctx, is_reaction=is_reaction)
        except ValueError:
            await send_error(ctx, self._bot, commands.UserInputError(), is_reaction=is_reaction)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    async def restart(self, ctx, command="0", is_reaction=False):
        """Restart server"""
        try:
            if int(command) >= 0:
                if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading:
                    if BotVars.is_doing_op:
                        await send_msg(ctx, "```Some player/s still oped, waiting for them```", is_reaction)
                        return
                    BotVars.is_restarting = True
                    print("Restarting server")
                    await stop_server(ctx, self._bot, int(command), True, is_reaction=is_reaction)
                    await start_server(ctx, bot=self._bot, is_reaction=is_reaction)
                else:
                    await send_status(ctx, is_reaction=is_reaction)
        except ValueError:
            await send_error(ctx, self._bot, commands.UserInputError(), is_reaction=is_reaction)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    async def op(self, ctx, minecraft_nick, *args):
        """
        Op command
        :param args: comment"""
        BotVars.is_doing_op = True
        if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and not BotVars.is_restarting:
            if minecraft_nick not in [p.player_minecraft_nick for p in Config.get_server_config().seen_players]:
                await ctx.send(f"{ctx.author.mention}, не видел такого ника на сервере, сынок! "
                               "Отметься на сервере перед опкой...")
                return

            if minecraft_nick not in [u.user_minecraft_nick for u in Config.get_known_users_list()] or \
                    ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()
                                          if u.user_minecraft_nick == minecraft_nick]:
                await ctx.send(f"{ctx.author.mention}, к тебе не привязан этот {minecraft_nick} ник, воспользуйся "
                               f"{Config.get_settings().bot_settings.prefix}assoc...")
                return

            if minecraft_nick in [p.player_minecraft_nick for p in Config.get_server_config().seen_players] and \
                    [p.number_of_times_to_op for p in Config.get_server_config().seen_players
                     if p.player_minecraft_nick == minecraft_nick][0] == 0:
                await ctx.send(f"{ctx.author.mention}, вы исчерпали кол-во попыток опнуться для данного "
                               f"{minecraft_nick} аккаунта!")
                return

            if minecraft_nick not in get_server_players():
                await ctx.send(f"{ctx.author.mention}, я не вижу в сети данный аккаунт `{minecraft_nick}`!")
                return

            BotVars.op_deop_list.append(minecraft_nick)
            Config.append_to_op_log(datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || Opped " +
                                    minecraft_nick + " || Reason: " + (" ".join(args) if args else "None"))
            await_time_op = Config.get_awaiting_times_settings().await_seconds_when_opped
            try:
                with Client_r(Config.get_settings().bot_settings.local_address,
                              BotVars.port_rcon, timeout=1) as cl_r:
                    cl_r.login(BotVars.rcon_pass)
                    cl_r.say(minecraft_nick + ' you\'ve opped for' + (
                        "" if await_time_op // 60 == 0 else " " + str(await_time_op // 60) + ' min') + (
                                 "." if await_time_op % 60 == 0 else " " + str(
                                     await_time_op % 60) + ' sec.'))
                    cl_r.mkop(minecraft_nick)
                Config.decrease_number_to_op_for_player(minecraft_nick)
                Config.save_server_config()
            except BaseException:
                await ctx.send(ctx.author.mention +
                               ", а сервак-то не работает (по крайней мере я пытался), попробуй-ка позже.")
                return
            await ctx.send("```Code activated```")
            if await_time_op > 0:
                if randint(0, 2) == 1:
                    await ctx.send(
                        f"Короче, {ctx.author.mention}, я тебя op'нул и в благородство играть не буду: приду через "
                        + str(int(await_time_op / 60)) + " мин," +
                        " deop'ну всех - и мы в расчёте. Заодно постараюсь разузнать на кой ляд тебе эта op'ка нужна," +
                        " но я в чужие дела не лезу, если хочешь получить, значит есть за что...")
                await asleep(await_time_op)
                if minecraft_nick != BotVars.op_deop_list[-1]:
                    return
                to_delete_ops = []
                for i in Config.get_ops_json():
                    for k, v in i.items():
                        if k == "name":
                            to_delete_ops.append(v)
                while True:
                    await asleep(
                        Config.get_awaiting_times_settings().await_seconds_when_connecting_via_rcon)
                    try:  # TODO: replace with suppress(BaseException) !!!
                        with Client_r(Config.get_settings().bot_settings.local_address,
                                      BotVars.port_rcon, timeout=1) as cl_r:
                            cl_r.login(BotVars.rcon_pass)
                            cl_r.say(minecraft_nick + ' you all will be deoped now.')
                            for player in to_delete_ops:
                                cl_r.deop(player)
                            list = cl_r.run("list").split(":")[1].split(", ")
                            for player in list:
                                cl_r.run(f"gamemode 0 {player}")
                        break
                    except BaseException:
                        pass
                Config.append_to_op_log(datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || Deopped all " +
                                        (str("|| Note: " + str(len(BotVars.op_deop_list)) +
                                             " people deoped in belated list") if len(
                                            BotVars.op_deop_list) > 1 else ""))
                await ctx.send("Ну что, " + ctx.author.mention +
                               ", кончилось твоё время.. и не только твоё.... Как говорится \"Чики-брики и в дамки!\"")
                BotVars.op_deop_list.clear()
            else:
                await ctx.send(f"{ctx.author.mention}, у тебя нет ограничения по времени, но вы все обречены...")

            if len(BotVars.op_deop_list) == 0:
                BotVars.is_doing_op = False
        else:
            await send_status(ctx)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def assoc(self, ctx, discord_mention: str, assoc_command, minecraft_nick):
        """
        syntax: Nick_Discord +=/-= Nick_minecraft
        """
        comm_operators = ["+=", "-="]
        if discord_mention.startswith("<@!"):
            need_to_save = False
            try:
                discord_id = int(discord_mention[3:-1])
            except BaseException:
                await ctx.send("Wrong 1-st argument used!")
                return
            if assoc_command == comm_operators[0]:
                if minecraft_nick in [u.user_minecraft_nick for u in Config.get_known_users_list()] and \
                        discord_id in [u.user_discord_id for u in Config.get_known_users_list()
                                       if u.user_minecraft_nick == minecraft_nick]:
                    await ctx.send("Existing `mention to nick` link!")
                else:
                    need_to_save = True
                    Config.add_to_known_users_list(minecraft_nick, discord_id)
                    await ctx.send("Now " + discord_mention + " associates with nick in minecraft " + minecraft_nick)
            elif assoc_command == comm_operators[1]:
                if minecraft_nick in [u.user_minecraft_nick for u in Config.get_known_users_list()] and \
                        discord_id in [u.user_discord_id for u in Config.get_known_users_list()]:
                    need_to_save = True
                    Config.remove_from_known_users_list(minecraft_nick, discord_id)
                    await ctx.send("Now link " + discord_mention + " -> " + minecraft_nick + " do not exist!")
                else:
                    await ctx.send("Doesn't have `mention to nick` link already!")
            else:
                await ctx.send("Wrong command syntax! Right example: "
                               f"`{Config.get_settings().bot_settings.prefix}assoc @me +=/-= My_nick`")
            if need_to_save:
                Config.save_config()
        else:
            await ctx.send("Wrong 1-st argument! You can mention ONLY members")

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    async def ops(self, ctx, for_who, missing=None):
        """
        Get info about ops
        :param for_who: string, "me" or "all"
        :param missing: None or "missing"
        """
        if for_who not in ["me", "all"] or missing not in [None, "missing"]:
            await ctx.send(f"Syntax: `{Config.get_settings().bot_settings.prefix}ops ['me', 'all'] ('missing')`")
            raise commands.UserInputError()

        message = ""
        if for_who == "me":
            if ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()]:
                await ctx.send(f"{ctx.author.mention}, у вас нету привязанных ников!")
                return

            user_nicks = [u.user_minecraft_nick for u in Config.get_known_users_list()
                          if u.user_discord_id == ctx.author.id]
            user_players_data = {}

            for m_nick in user_nicks:
                for p in Config.get_seen_players_list():
                    if p.player_minecraft_nick == m_nick:
                        user_players_data.update({p.player_minecraft_nick: p.number_of_times_to_op})
                        user_nicks.remove(m_nick)
            if missing:
                user_players_data.update({n: -1 for n in user_nicks})

            message = f"{ctx.author.mention}, у вас есть такие данные по никам и кол-ву оставшихся использований:\n```"
            for k, v in user_players_data.items():
                message += f"{k}: {str(v) if v >= 0 else 'не замечен на сервере'}\n"
        elif for_who == "all":
            if not ctx.author.guild_permissions.administrator:
                raise commands.MissingPermissions(['administrator'])

            users_to_nicks = {}
            for user in Config.get_known_users_list():
                if users_to_nicks.get(user.user_discord_id, None) is None:
                    users_to_nicks.update({user.user_discord_id: []})
                users_to_nicks[user.user_discord_id].append(user.user_minecraft_nick)

            for user_id in users_to_nicks.keys():
                for p in Config.get_seen_players_list():
                    if p.player_minecraft_nick in users_to_nicks[user_id]:
                        users_to_nicks[user_id].remove(p.player_minecraft_nick)
                        users_to_nicks[user_id].append({p.player_minecraft_nick: p.number_of_times_to_op})

            message = f"{ctx.author.mention}, у бота есть такие данные по никам и кол-ву оставшихся использований:\n```"
            for k, v in users_to_nicks.items():
                if not len(v) or (not missing and all([isinstance(i, str) for i in v])):
                    continue
                member = await ctx.guild.fetch_member(k)
                message += f"{member.display_name}#{member.discriminator}:\n"
                for item in v:
                    if missing and isinstance(item, str):
                        message += f"\t{item}: не замечен на сервере\n"
                    elif isinstance(item, dict):
                        message += f"\t{list(item.items())[0][0]}: {str(list(item.items())[0][1])}\n"

        if message[-3:] == "```":
            message += "-----"
        message += "```"
        await ctx.send(message)

    @commands.command(pass_context=True, aliases=["fl"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    async def forceload(self, ctx, command=""):
        if command == "on" and not Config.get_settings().bot_settings.forceload:
            Config.get_settings().bot_settings.forceload = True
            Config.save_config()
            await ctx.send("```Forceload on```")
        elif command == "off" and Config.get_settings().bot_settings.forceload:
            Config.get_settings().bot_settings.forceload = False
            Config.save_config()
            await ctx.send("```Forceload off```")
        elif command == "":
            if Config.get_settings().bot_settings.forceload:
                await ctx.send("```Forceload on```")
            else:
                await ctx.send("```Forceload off```")
        else:
            raise commands.UserInputError()

    @commands.command(pass_context=True, aliases=["wl"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    async def whitelist(self, ctx, *args):
        if len(args) and args[0] in ["add", "del", "list", "on", "off", "reload"]:
            try:
                with Client_r(Config.get_settings().bot_settings.local_address,
                              BotVars.port_rcon, timeout=1) as cl_r:
                    cl_r.login(BotVars.rcon_pass)
                    if args[0] == "on":
                        white_list = cl_r.run("whitelist on")
                        await ctx.send("```" + white_list + "```")
                    elif args[0] == "off":
                        white_list = cl_r.run("whitelist off")
                        await ctx.send("```" + white_list + "```")
                    elif args[0] == "add":
                        if get_server_online_mode():
                            white_list = cl_r.run("whitelist add", args[1])
                            await ctx.send("```" + white_list + "```")
                        else:
                            save_to_whitelist_json(get_whitelist_entry(args[1]))
                            _ = cl_r.run("whitelist reload")
                            await ctx.send(f"```Added {args[1]} to the whitelist```")
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
        else:
            raise commands.UserInputError("```Commands: on, off, add, del, list, reload```")

    @commands.command(pass_context=True, aliases=["servs"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    async def servers(self, ctx, *args):
        if len(args) and args[0] in ["list", "select", "show"]:
            if args[0] == "list":
                send_ = "```List of servers"
                for i in range(len(Config.get_settings().servers_list)):
                    send_ += "\n№ " + str(i) + ". " + Config.get_settings().servers_list[i].server_name
                send_ += "```"
                await ctx.send(send_)
            elif args[0] == "select":
                if len(args) < 2:
                    await ctx.send("Э, " + ctx.author.mention + ", где число?")
                    return
                try:
                    if int(args[1]) <= len(Config.get_settings().servers_list):
                        if int(args[1]) == Config.get_settings().selected_server_number:
                            await ctx.send(
                                "```My, you have chosen selected server, insane?)\n ...Pasan ramsi poputal```")
                            return
                        if BotVars.is_server_on:
                            await ctx.send("```You can't change servers, while some instance(s) is/are still running" +
                                           "\nPlease stop it, before trying again```")
                            return

                        if BotVars.watcher_of_log_file is not None:
                            BotVars.watcher_of_log_file.stop()
                            BotVars.watcher_of_log_file = None
                        Config.get_settings().selected_server_number = int(args[1])
                        Config.save_config()
                        await ctx.send("```Selected server № " + str(Config.get_settings().selected_server_number) +
                                       ". " + Config.get_selected_server_from_list().server_name + "```")
                        Config.read_server_info()
                        await ctx.send("```Server properties read!```")
                    else:
                        await ctx.send("```Use server list, there's no such server on the list!```")
                except ValueError:
                    await ctx.send("```Argument for 'select' must be a number!```")
            elif args[0] == "show":
                await ctx.send("```Selected server № " + str(Config.get_settings().selected_server_number) +
                               ". " + Config.get_selected_server_from_list().server_name + "```")
            else:
                await ctx.send("```Wrong command!\nCommands: select, list```")
        else:
            await ctx.send("```Commands: select, list, show```")
            raise commands.UserInputError()

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True,
                                  embed_links=True, add_reactions=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    async def menu(self, ctx):
        await ctx.channel.purge(limit=1)
        emb = discord.Embed(title='Список всех команд через реакции',
                            color=discord.Color.teal())
        emb.add_field(name='status', value=':speech_left:')
        emb.add_field(name='list', value=':clipboard:')
        emb.add_field(name='start', value=':wheelchair:')
        emb.add_field(name='stop 10', value=':stop_button:')
        emb.add_field(name='restart 10', value=':arrows_counterclockwise:')
        emb.add_field(name='update', value=':signal_strength:')
        add_reactions_to = await ctx.send(embed=emb)
        Config.get_settings().bot_settings.menu_id = add_reactions_to.id
        Config.save_config()
        for emote in self._emoji_symbols.values():
            await add_reactions_to.add_reaction(emote)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.message_id == Config.get_settings().bot_settings.menu_id and payload.member.id != self._bot.user.id:
            channel = self._bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)
            if payload.emoji.name in self._emoji_symbols.values():
                BotVars.react_auth = payload.member
                if payload.emoji.name == self._emoji_symbols.get("status"):
                    await self.status(channel, is_reaction=True)
                elif payload.emoji.name == self._emoji_symbols.get("list"):
                    await self.list(channel, is_reaction=True)
                elif payload.emoji.name == self._emoji_symbols.get("update"):
                    if BotVars.server_checkups_task is not None:
                        BotVars.server_checkups_task.cancel()
                        with suppress(CancelledError):
                            await BotVars.server_checkups_task  # await for task cancellation
                    BotVars.server_checkups_task = self._bot.loop.create_task(server_checkups(self._bot))
                    return
                else:
                    if Config.get_settings().bot_settings.role == "" or \
                            Config.get_settings().bot_settings.role in (e.name for e in payload.member.roles):
                        if payload.emoji.name == self._emoji_symbols.get("start"):
                            await self.start(channel, is_reaction=True)
                        elif payload.emoji.name == self._emoji_symbols.get("stop"):
                            await self.stop(channel, command="10", is_reaction=True)
                        elif payload.emoji.name == self._emoji_symbols.get("restart"):
                            await self.restart(channel, command="10", is_reaction=True)
                    else:
                        await send_error(channel, self._bot,
                                         commands.MissingRole(Config.get_settings().bot_settings.role),
                                         is_reaction=True)
