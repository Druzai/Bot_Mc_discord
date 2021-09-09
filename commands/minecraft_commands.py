from asyncio import sleep as asleep, CancelledError
from contextlib import suppress
from datetime import datetime
from random import randint

import discord
from discord.ext import commands
from mcipc.rcon import Client as Client_r

from components import decorators
from components.additional_funcs import *
from components.localization import get_translation
from config.init_config import BotVars, Config


class MinecraftCommands(commands.Cog):
    _emoji_symbols = {"status": "🗨", "list": "📋", "start": "♿",
                      "stop": "⏹", "restart": "🔄", "update": "📶"}  # Symbols for menu

    def __init__(self, bot: commands.Bot):
        self._bot: commands.Bot = bot

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    async def status(self, ctx):
        """Shows server status"""
        await bot_status(ctx)

    @commands.command(pass_context=True, aliases=["ls"])
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    async def list(self, ctx):
        """Shows list of players"""
        await bot_list(ctx, self._bot)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def start(self, ctx):
        """Start server"""
        await bot_start(ctx, self._bot)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def stop(self, ctx, sub_command=0):
        """Stop server"""
        await bot_stop(ctx, sub_command, self._bot)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def restart(self, ctx, sub_command=0):
        """Restart server"""
        await bot_restart(ctx, sub_command, self._bot)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def op(self, ctx, minecraft_nick: str, *reasons: str):
        """
        Op command
        :param reasons: comment"""
        BotVars.is_doing_op = True
        if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and not BotVars.is_restarting:
            if minecraft_nick not in [p.player_minecraft_nick for p in Config.get_server_config().seen_players]:
                await ctx.send(get_translation("{0}, I didn't see this nick on server, son!"
                                               "Go to the server via this nick before...").format(ctx.author.mention))
                # await ctx.send(f"{ctx.author.mention}, не видел такого ника на сервере, сынок! "
                #                "Отметься на сервере перед опкой...")
                return

            if minecraft_nick not in [u.user_minecraft_nick for u in Config.get_known_users_list()] or \
                    ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()
                                          if u.user_minecraft_nick == minecraft_nick]:
                await ctx.send(get_translation("{0}, this nick isn't bound to you, use {1}assoc first...")
                               .format(ctx.author.mention, Config.get_settings().bot_settings.prefix))
                # await ctx.send(f"{ctx.author.mention}, к тебе не привязан этот {minecraft_nick} ник, воспользуйся "
                #                f"{Config.get_settings().bot_settings.prefix}assoc...")
                return

            if minecraft_nick in [p.player_minecraft_nick for p in Config.get_server_config().seen_players] and \
                    [p.number_of_times_to_op for p in Config.get_server_config().seen_players
                     if p.player_minecraft_nick == minecraft_nick][0] == 0:
                await ctx.send(get_translation("{0}, you had run out of attempts to get opped for `{1}` nick!")
                               .format(ctx.author.mention, minecraft_nick))
                # await ctx.send(f"{ctx.author.mention}, вы исчерпали кол-во попыток опнуться для данного "
                #                f"{minecraft_nick} аккаунта!")
                return

            if minecraft_nick not in get_server_players():
                await ctx.send(get_translation("{0}, I didn't see this nick `{1}` online!")
                               .format(ctx.author.mention, minecraft_nick))
                # await ctx.send(f"{ctx.author.mention}, я не вижу в сети данный аккаунт `{minecraft_nick}`!")
                return

            BotVars.op_deop_list.append(minecraft_nick)
            Config.append_to_op_log(datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || " + get_translation("Opped ") +
                                    minecraft_nick + " || " + get_translation("Reason: ") +
                                    (" ".join(reasons) if reasons else "None"))
            await_time_op = Config.get_awaiting_times_settings().await_seconds_when_opped
            try:
                with Client_r(Config.get_settings().bot_settings.local_address,
                              BotVars.port_rcon, timeout=1) as cl_r:
                    cl_r.login(BotVars.rcon_pass)
                    cl_r.say(minecraft_nick + get_translation(" you've opped for") + (
                        "" if await_time_op // 60 == 0 else " " + str(await_time_op // 60) + get_translation(" min")) +
                             ("." if await_time_op % 60 == 0 else " " + str(await_time_op % 60) +
                                                                  get_translation(" sec") + "."))
                    cl_r.mkop(minecraft_nick)
                Config.decrease_number_to_op_for_player(minecraft_nick)
                Config.save_server_config()
            except BaseException:
                await ctx.send(get_translation("{0}, server isn't working (at least I've tried), try again later...")
                               .format(ctx.author.mention))
                # await ctx.send(ctx.author.mention +
                #                ", а сервак-то не работает (по крайней мере я пытался), попробуй-ка позже.")
                return
            await ctx.send(add_quotes(get_translation("Code activated")))
            if await_time_op > 0:
                if randint(0, 2) == 1:
                    # await ctx.send(
                    #     f"Короче, {ctx.author.mention}, я тебя op'нул и в благородство играть не буду: приду через "
                    #     + str(int(await_time_op / 60)) + " мин," +
                    #     " deop'ну всех - и мы в расчёте. Заодно постараюсь разузнать на кой ляд тебе эта op'ка нужна," +
                    #     " но я в чужие дела не лезу, если хочешь получить, значит есть за что...")
                    await ctx.send(
                        get_translation(
                            "So {0}, I opped you, but I'm not going to pretend like I did it to win favors upstairs. "
                            "I'll come in {1} min, deop everyone and we're even. "
                            "I don't give a shit why you want this op and mind my own business. "
                            "If you want to be opped, well, you must have your reasons...")
                            .format(ctx.author.mention, str(int(await_time_op / 60))))
                    """
                    So {0}, I opped you, but I'm not going to pretend like I did it to win favors upstairs.
                    I'll come in {1} min, deop everyone and we're even.
                    I don't give a shit why you want this op and mind my own business.
                    If you want to be opped, well, you must have your reasons...
                    """
                    """
                    "Короче, {0}, я тебя op'нул и в благородство играть не буду: приду через {1} мин, deop'ну всех - и мы в расчёте. 
                    Хрен его знает, на кой ляд тебе эта op'ка сдалась, но я в чужие дела не лезу, если хочешь получить, значит есть на что..."
                    """
                    """
                    So Marked One, I saved you, but I'm not going to pretend like I did it to win favors upstairs. 
                    You'll do some jobs for me and we're even. 
                    Besides, keeping you busy might be a good way to deal with your amnesia. 
                    And I'll see what I can find out about your problem. 
                    I don't give a shit why you want this Strelok guy and mind my own business. 
                    If you want to kill him, well, you must have your reasons.
                    """
                    """
                    Короче, Меченый, я тебя спас и в благородство играть не буду: выполнишь для меня пару заданий – и мы в расчете. 
                    Заодно посмотрим, как быстро у тебя башка после амнезии прояснится. 
                    А по твоей теме постараюсь разузнать. 
                    Хрен его знает, на кой ляд тебе этот Стрелок сдался, но я в чужие дела не лезу, хочешь убить, значит есть за что…
                    """
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
                    with suppress(BaseException):
                        with Client_r(Config.get_settings().bot_settings.local_address,
                                      BotVars.port_rcon, timeout=1) as cl_r:
                            cl_r.login(BotVars.rcon_pass)
                            cl_r.say(minecraft_nick + get_translation(" you all will be deoped now."))
                            for player in to_delete_ops:
                                cl_r.deop(player)
                            list = cl_r.run("list").split(":")[1].split(", ")
                            for player in list:
                                cl_r.run(f"gamemode 0 {player}")
                        break
                Config.append_to_op_log(
                    datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || " + get_translation("Deopped all ") +
                    (str("|| Note: " + str(len(BotVars.op_deop_list)) +
                         " people deoped in belated list") if len(BotVars.op_deop_list) > 1 else ""))
                await ctx.send(get_translation("Well, {0}, your time is over... and not only yours...\n"
                                               "As they say \"Cheeki breeki i v damké!\"").format(ctx.author.mention))
                # await ctx.send("Ну что, " + ctx.author.mention +
                #              ", кончилось твоё время.. и не только твоё.... Как говорится \"Чики-брики и в дамки!\"")
                BotVars.op_deop_list.clear()
            else:
                await ctx.send(get_translation("{0}, you have no time limit, but you are all doomed...")
                               .format(ctx.author.mention))
                # await ctx.send(f"{ctx.author.mention}, у тебя нет ограничения по времени, но вы все обречены...")

            if len(BotVars.op_deop_list) == 0:
                BotVars.is_doing_op = False
        else:
            await send_status(ctx)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def assoc(self, ctx, discord_mention: str, assoc_command: str, minecraft_nick: str):
        """
        Associates discord user with nick in minecraft
        syntax: Nick_Discord +=/-= Nick_minecraft
        """
        comm_operators = ["+=", "-="]
        if discord_mention.startswith("<@!"):
            need_to_save = False
            try:
                discord_id = int(discord_mention[3:-1])
            except BaseException:
                await ctx.send(get_translation("Wrong 1-st argument used!"))
                return
            if assoc_command == comm_operators[0]:
                if minecraft_nick in [u.user_minecraft_nick for u in Config.get_known_users_list()] and \
                        discord_id in [u.user_discord_id for u in Config.get_known_users_list()
                                       if u.user_minecraft_nick == minecraft_nick]:
                    await ctx.send(get_translation("Existing `mention to nick` link!"))
                else:
                    need_to_save = True
                    Config.add_to_known_users_list(minecraft_nick, discord_id)
                    await ctx.send(get_translation("Now {0} associates with nick in minecraft {1}")
                                   .format(discord_mention, minecraft_nick))
            elif assoc_command == comm_operators[1]:
                if minecraft_nick in [u.user_minecraft_nick for u in Config.get_known_users_list()] and \
                        discord_id in [u.user_discord_id for u in Config.get_known_users_list()]:
                    need_to_save = True
                    Config.remove_from_known_users_list(minecraft_nick, discord_id)
                    await ctx.send(get_translation("Now link {0} -> {1} do not exist!")
                                   .format(discord_mention, minecraft_nick))
                else:
                    await ctx.send(get_translation("Doesn't have `mention to nick` link already!"))
            else:
                await ctx.send(get_translation("Wrong command syntax! Right example: `{0}assoc @me +=/-= My_nick`")
                               .format(Config.get_settings().bot_settings.prefix))
            if need_to_save:
                Config.save_config()
        else:
            await ctx.send(get_translation("Wrong 1-st argument! You can mention ONLY members"))

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def ops(self, ctx, for_who: str, missing: str):
        """
        Get info about ops
        :param for_who: string, "me" or "all"
        :param missing: "seen" or "missing"
        """
        if for_who not in ["me", "all"] or missing not in ["seen", "missing"]:
            await ctx.send(get_translation("Syntax:") +
                           f" `{Config.get_settings().bot_settings.prefix}ops <'me', 'all'> <'seen', 'missing'>`")
            raise commands.UserInputError()

        message = ""
        if for_who == "me":
            if ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()]:
                await ctx.send(get_translation("{0}, you have no bound nicks").format(ctx.author.mention))
                # await ctx.send(f"{ctx.author.mention}, у вас нету привязанных ников!")
                return

            user_nicks = [u.user_minecraft_nick for u in Config.get_known_users_list()
                          if u.user_discord_id == ctx.author.id]
            user_players_data = {}

            for m_nick in user_nicks:
                for p in Config.get_seen_players_list():
                    if p.player_minecraft_nick == m_nick:
                        user_players_data.update({p.player_minecraft_nick: p.number_of_times_to_op})
                        user_nicks.remove(m_nick)
            if missing == "missing":
                user_players_data.update({n: -1 for n in user_nicks})

            message = get_translation("{0}, bot has these data on your nick and number of remaining uses:") \
                          .format(ctx.author.mention) + "\n```"
            # message = f"{ctx.author.mention}, у вас есть такие данные по никам и кол-ву оставшихся использований:\n```"
            for k, v in user_players_data.items():
                message += f"{k}: {str(v) if v >= 0 else get_translation('not seen on server')}\n"
                # message += f"{k}: {str(v) if v >= 0 else 'не замечен на сервере'}\n"
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

            message = get_translation("{0}, bot has these data on your nick and number of remaining uses:") \
                          .format(ctx.author.mention) + "\n```"
            # message = f"{ctx.author.mention}, у бота есть такие данные по никам и кол-ву оставшихся использований:\n```"
            for k, v in users_to_nicks.items():
                if not len(v) or (missing == "seen" and all([isinstance(i, str) for i in v])):
                    continue
                member = await ctx.guild.fetch_member(k)
                message += f"{member.display_name}#{member.discriminator}:\n"
                for item in v:
                    if missing == "missing" and isinstance(item, str):
                        message += f"\t{item}: " + get_translation("not seen on server") + "\n"
                        # message += f"\t{item}: не замечен на сервере\n"
                    elif isinstance(item, dict):
                        message += f"\t{list(item.items())[0][0]}: {str(list(item.items())[0][1])}\n"

        if message[-3:] == "```":
            message += "-----"
        message += "```"
        await ctx.send(message)

    @commands.command(pass_context=True, aliases=["fl"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def forceload(self, ctx, sub_command=""):
        if sub_command == "on" and not Config.get_settings().bot_settings.forceload:
            Config.get_settings().bot_settings.forceload = True
            Config.save_config()
            await ctx.send(add_quotes(get_translation("Forceload on")))
        elif sub_command == "off" and Config.get_settings().bot_settings.forceload:
            Config.get_settings().bot_settings.forceload = False
            Config.save_config()
            await ctx.send(add_quotes(get_translation("Forceload off")))
        elif sub_command == "":
            if Config.get_settings().bot_settings.forceload:
                await ctx.send(add_quotes(get_translation("Forceload on")))
            else:
                await ctx.send(add_quotes(get_translation("Forceload off")))
        else:
            raise commands.UserInputError()

    @commands.command(pass_context=True, aliases=["wl"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def whitelist(self, ctx, sub_command: str, minecraft_nick=""):
        if sub_command in ["add", "del", "list", "on", "off", "reload"]:
            try:
                with Client_r(Config.get_settings().bot_settings.local_address,
                              BotVars.port_rcon, timeout=1) as cl_r:
                    cl_r.login(BotVars.rcon_pass)
                    if sub_command == "on":
                        cl_r.run("whitelist on")
                        await ctx.send(add_quotes(get_translation("Turned on the whitelist")))
                    elif sub_command == "off":
                        cl_r.run("whitelist off")
                        await ctx.send(add_quotes(get_translation("Turned off the whitelist")))
                    elif sub_command == "add":
                        if get_server_online_mode():
                            cl_r.run("whitelist add", minecraft_nick)
                        else:
                            save_to_whitelist_json(get_whitelist_entry(minecraft_nick))
                            cl_r.run("whitelist reload")
                        await ctx.send(add_quotes(get_translation("Added {0} to the whitelist").format(minecraft_nick)))
                    elif sub_command == "del":
                        cl_r.run("whitelist remove", minecraft_nick)
                        await ctx.send(add_quotes(get_translation("Removed {0} from the whitelist")
                                                  .format(minecraft_nick)))
                    elif sub_command == "list":
                        white_list = cl_r.run("whitelist list")
                        if ":" in white_list:
                            players = white_list.split(':')[1].split(", ")
                            if " and " in players[-1]:
                                players[-1], last_player = players[-1].split(" and ")
                                players.append(last_player)
                            await ctx.send(add_quotes(get_translation("There are {0} players in whitelist\n{1}")
                                                      .format(len(players), ", ".join(players))))
                        else:
                            await ctx.send(add_quotes(get_translation("There are no whitelisted players")))
                    elif sub_command == "reload":
                        cl_r.run("whitelist reload")
                        await ctx.send(add_quotes(get_translation("Reloaded the whitelist")))
                    else:
                        await ctx.send(add_quotes(get_translation("Wrong command!")))
            except BaseException:
                await ctx.send(add_quotes(get_translation("Couldn't connect to server, try again(")))
        else:
            await ctx.send(add_quotes(get_translation("Commands:") + " on, off, add, del, list, reload"))
            raise commands.UserInputError()

    @commands.command(pass_context=True, aliases=["servs"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def servers(self, ctx, sub_command: str, selected_server=None):
        if sub_command in ["list", "select", "show"]:
            if sub_command == "list":
                send_ = "```" + get_translation("List of servers")
                for i in range(len(Config.get_settings().servers_list)):
                    send_ += "\n№ " + str(i) + ". " + Config.get_settings().servers_list[i].server_name
                send_ += "```"
                await ctx.send(send_)
            elif sub_command == "select":
                if selected_server is None:
                    # await ctx.send("Э, " + ctx.author.mention + ", где число?")
                    await ctx.send(get_translation("Hey, {0}, where's number?").format(ctx.author.mention))
                    return
                try:
                    if int(selected_server) <= len(Config.get_settings().servers_list):
                        if int(selected_server) == Config.get_settings().selected_server_number:
                            await ctx.send(add_quotes(get_translation("My, you have chosen selected server, insane?)\n"
                                                                      " ...Patsan ramsi poputal")))
                            return
                        if BotVars.is_server_on:
                            await ctx.send(add_quotes(get_translation(
                                "You can't change servers, while some instance(s) is/are still running\n"
                                "Please stop them, before trying again")))
                            return

                        if BotVars.watcher_of_log_file is not None:
                            BotVars.watcher_of_log_file.stop()
                            BotVars.watcher_of_log_file = None
                        Config.get_settings().selected_server_number = int(selected_server)
                        Config.save_config()
                        await ctx.send(add_quotes(get_translation("Selected server") +
                                                  " № " + str(Config.get_settings().selected_server_number) +
                                                  ". " + Config.get_selected_server_from_list().server_name))
                        Config.read_server_info()
                        await ctx.send(add_quotes(get_translation("Server properties read!")))
                    else:
                        await ctx.send(add_quotes(get_translation("Use server list, there's no such "
                                                                  "server number on the list!")))
                except ValueError:
                    await ctx.send(add_quotes(get_translation("Argument for 'select' must be a number!")))
            elif sub_command == "show":
                await ctx.send(add_quotes(get_translation("Selected server") +
                                          " № " + str(Config.get_settings().selected_server_number) +
                                          ". " + Config.get_selected_server_from_list().server_name))
        else:
            await ctx.send(add_quotes(get_translation("Commands:") + " select, list, show"))
            raise commands.UserInputError()

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True,
                                  embed_links=True, add_reactions=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def menu(self, ctx):
        await ctx.channel.purge(limit=1)
        emb = discord.Embed(title=get_translation("List of commands via reactions"),
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
                    await bot_status(channel, is_reaction=True)
                elif payload.emoji.name == self._emoji_symbols.get("list"):
                    await bot_list(channel, self._bot, is_reaction=True)
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
                            await bot_start(channel, self._bot, is_reaction=True)
                        elif payload.emoji.name == self._emoji_symbols.get("stop"):
                            await bot_stop(channel, command="10", bot=self._bot, is_reaction=True)
                        elif payload.emoji.name == self._emoji_symbols.get("restart"):
                            await bot_restart(channel, command="10", bot=self._bot, is_reaction=True)
                    else:
                        await send_error(channel, self._bot,
                                         commands.MissingRole(Config.get_settings().bot_settings.role),
                                         is_reaction=True)
