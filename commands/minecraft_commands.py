from asyncio import sleep as asleep
from contextlib import suppress
from datetime import datetime
from os import remove
from pathlib import Path
from random import randint
from sys import argv

import discord
from discord.ext import commands, tasks

from commands.poll import Poll
from components import decorators
from components.additional_funcs import *
from components.localization import get_translation
from config.init_config import BotVars, Config


class MinecraftCommands(commands.Cog):
    _emoji_symbols = {"status": "🗨", "list": "📋", "backup": "💾", "start": "♿",
                      "stop 10": "⏹", "restart 10": "🔄", "update": "📶"}  # Symbols for menu

    def __init__(self, bot: commands.Bot, poll: Poll):
        self._bot: commands.Bot = bot
        self._IndPoll: Poll = poll
        self.checkups_task.start()
        self._backups_thread = BackupsThread(self._bot)
        if len(argv) == 1:
            self._backups_thread.start()

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
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, mention_everyone=True, add_reactions=True,
                                  embed_links=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def stop(self, ctx, timeout: int = 0):
        """Stop server"""
        await bot_stop(ctx, timeout, self._bot, self._IndPoll)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, mention_everyone=True, add_reactions=True,
                                  embed_links=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def restart(self, ctx, timeout: int = 0):
        """Restart server"""
        await bot_restart(ctx, timeout, self._bot, self._IndPoll)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def op(self, ctx, minecraft_nick: str, *, reasons: str = ""):
        """
        Op command
        :param reasons: comment"""
        BotVars.is_doing_op = True
        if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and not BotVars.is_restarting:
            if len(get_server_players()) == 0:
                await ctx.send(f"{ctx.author.mention}, " +
                               get_translation("There are no players on the server").lower() + "!")
                BotVars.is_doing_op = False
                return

            if minecraft_nick not in [p.player_minecraft_nick for p in Config.get_server_config().seen_players]:
                await ctx.send(get_translation("{0}, I didn't see this nick on server, son! "
                                               "Go to the server via this nick before...").format(ctx.author.mention))
                BotVars.is_doing_op = False
                return

            if minecraft_nick not in [u.user_minecraft_nick for u in Config.get_known_users_list()] or \
                    ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()
                                          if u.user_minecraft_nick == minecraft_nick]:
                await ctx.send(get_translation("{0}, this nick isn't bound to you, use {1}assoc first...")
                               .format(ctx.author.mention, Config.get_settings().bot_settings.prefix))
                BotVars.is_doing_op = False
                return

            if minecraft_nick in [p.player_minecraft_nick for p in Config.get_server_config().seen_players] and \
                    [p.number_of_times_to_op for p in Config.get_server_config().seen_players
                     if p.player_minecraft_nick == minecraft_nick][0] == 0:
                await ctx.send(get_translation("{0}, you had run out of attempts to get opped for `{1}` nick!")
                               .format(ctx.author.mention, minecraft_nick))
                BotVars.is_doing_op = False
                return

            if minecraft_nick not in get_server_players():
                await ctx.send(get_translation("{0}, I didn't see this nick `{1}` online!")
                               .format(ctx.author.mention, minecraft_nick))
                BotVars.is_doing_op = False
                return

            BotVars.op_deop_list.append(minecraft_nick)
            Config.append_to_op_log(datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || " + get_translation("Opped ") +
                                    minecraft_nick + " || " + get_translation("Reason: ") +
                                    (reasons if reasons else "None"))
            await_time_op = Config.get_awaiting_times_settings().await_seconds_when_opped
            try:
                with connect_rcon() as cl_r:
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
                return
            await ctx.send(add_quotes(get_translation("Bot has given you an operator")))
            if await_time_op > 0:
                if randint(0, 2) == 1:
                    await ctx.send(
                        get_translation(
                            "So {0}, I opped you, but I'm not going to pretend like I did it to win favors upstairs. "
                            "I'll come in {1} min, deop everyone and we're even. "
                            "I don't give a shit why you want this op and mind my own business. "
                            "If you want to be opped, well, you must have your reasons...")
                            .format(ctx.author.mention, str(await_time_op // 60)))
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
                        with connect_rcon() as cl_r:
                            cl_r.say(minecraft_nick + get_translation(" you all will be deoped now."))
                            for player in to_delete_ops:
                                cl_r.deop(player)
                            list = cl_r.run("list").split(":")[1].split(", ")
                            for player in list:
                                cl_r.run(f"gamemode 0 {player}")
                        break
                Config.append_to_op_log(
                    datetime.now().strftime("%d/%m/%Y, %H:%M:%S") + " || " + get_translation("Deopped all ") +
                    (str(get_translation("|| Note: ") + str(len(BotVars.op_deop_list)) +
                         get_translation(" people deoped in belated list")) if len(BotVars.op_deop_list) > 1 else ""))
                await ctx.send(get_translation("Well, {0}, your time is over... and not only yours...\n"
                                               "As they say \"Cheeki breeki i v damké!\"").format(ctx.author.mention))
                BotVars.op_deop_list.clear()
            else:
                await ctx.send(get_translation("{0}, you have no time limit, but you are all doomed...")
                               .format(ctx.author.mention))

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
                await ctx.send(get_translation("Wrong command syntax! Right example: `{0}assoc @me +=/-= My_nick`.")
                               .format(Config.get_settings().bot_settings.prefix))
            if need_to_save:
                Config.save_config()
        else:
            await ctx.send(get_translation("Wrong 1-st argument! You can mention ONLY members of this server."))

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def ops(self, ctx, for_who: str, show: str):
        """
        Get info about ops
        :param for_who: string, "me" or "everyone"
        :param show: "seen" or "all"
        """
        if for_who not in ["me", "everyone"] or show not in ["seen", "all"]:
            await ctx.send(get_translation("Syntax:") +
                           f" `{Config.get_settings().bot_settings.prefix}ops <'me', 'everyone'> <'seen', 'all'>`")
            raise commands.UserInputError()

        message = ""
        if for_who == "me":
            if ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()]:
                await ctx.send(get_translation("{0}, you have no bound nicks").format(ctx.author.mention))
                return

            user_nicks = [u.user_minecraft_nick for u in Config.get_known_users_list()
                          if u.user_discord_id == ctx.author.id]
            user_players_data = {}

            for m_nick in user_nicks:
                for p in Config.get_seen_players_list():
                    if p.player_minecraft_nick == m_nick:
                        user_players_data.update({p.player_minecraft_nick: p.number_of_times_to_op})
                        user_nicks.remove(m_nick)
            if show == "all":
                user_players_data.update({n: -1 for n in user_nicks})

            message = get_translation("{0}, bot has these data on your nicks and number of remaining uses:") \
                          .format(ctx.author.mention) + "\n```"
            for k, v in user_players_data.items():
                message += f"{k}: {str(v) if v >= 0 else get_translation('not seen on server')}\n"
        elif for_who == "everyone":
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

            message = get_translation("{0}, bot has these data on your nicks and number of remaining uses:") \
                          .format(ctx.author.mention) + "\n```"
            for k, v in users_to_nicks.items():
                if not len(v) or (show == "seen" and all([isinstance(i, str) for i in v])):
                    continue
                member = await ctx.guild.fetch_member(k)
                message += f"{member.display_name}#{member.discriminator}:\n"
                for item in v:
                    if show == "all" and isinstance(item, str):
                        message += f"\t{item}: " + get_translation("not seen on server") + "\n"
                    elif isinstance(item, dict):
                        message += f"\t{list(item.items())[0][0]}: {str(list(item.items())[0][1])}\n"

        if message[-3:] == "```":
            message += "-----"
        message += "```"
        await ctx.send(message)

    @commands.group(pass_context=True, aliases=["fl"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def forceload(self, ctx):
        if Config.get_settings().bot_settings.forceload:
            await ctx.send(add_quotes(get_translation("Forceload on")))
        else:
            await ctx.send(add_quotes(get_translation("Forceload off")))

    @forceload.command(pass_context=True, name="on")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def f_on(self, ctx):
        Config.get_settings().bot_settings.forceload = True
        Config.save_config()
        await ctx.send(add_quotes(get_translation("Forceload on")))

    @forceload.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def f_off(self, ctx):
        Config.get_settings().bot_settings.forceload = False
        Config.save_config()
        await ctx.send(add_quotes(get_translation("Forceload off")))

    @commands.group(pass_context=True, aliases=["wl"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def whitelist(self, ctx):
        await ctx.send(add_quotes(get_translation("Wrong syntax, subcommands:") + " on, off, add, del, list, reload"))
        raise commands.UserInputError()

    @whitelist.command(pass_context=True, name="add")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_add(self, ctx, minecraft_nick: str):
        try:
            with connect_rcon() as cl_r:
                if get_from_server_properties("online-mode"):
                    cl_r.run("whitelist add", minecraft_nick)
                else:
                    save_to_whitelist_json(get_whitelist_entry(minecraft_nick))
                    cl_r.run("whitelist reload")
                await ctx.send(add_quotes(get_translation("Added {0} to the whitelist").format(minecraft_nick)))
        except BaseException:
            if BotVars.is_server_on:
                await ctx.send(add_quotes(get_translation("Couldn't connect to server, try again(")))
            else:
                await ctx.send(add_quotes(get_translation("server offline").capitalize()))

    @whitelist.command(pass_context=True, name="del")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_del(self, ctx, minecraft_nick: str):
        try:
            with connect_rcon() as cl_r:
                cl_r.run("whitelist remove", minecraft_nick)
                await ctx.send(add_quotes(get_translation("Removed {0} from the whitelist").format(minecraft_nick)))
        except BaseException:
            if BotVars.is_server_on:
                await ctx.send(add_quotes(get_translation("Couldn't connect to server, try again(")))
            else:
                await ctx.send(add_quotes(get_translation("server offline").capitalize()))

    @whitelist.command(pass_context=True, name="list")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_list(self, ctx):
        try:
            with connect_rcon() as cl_r:
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
        except BaseException:
            if BotVars.is_server_on:
                await ctx.send(add_quotes(get_translation("Couldn't connect to server, try again(")))
            else:
                await ctx.send(add_quotes(get_translation("server offline").capitalize()))

    @whitelist.command(pass_context=True, name="on")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_on(self, ctx):
        try:
            with connect_rcon() as cl_r:
                cl_r.run("whitelist on")
                await ctx.send(add_quotes(get_translation("Turned on the whitelist")))
        except BaseException:
            if BotVars.is_server_on:
                await ctx.send(add_quotes(get_translation("Couldn't connect to server, try again(")))
            else:
                await ctx.send(add_quotes(get_translation("server offline").capitalize()))

    @whitelist.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_off(self, ctx):
        try:
            with connect_rcon() as cl_r:
                cl_r.run("whitelist off")
                await ctx.send(add_quotes(get_translation("Turned off the whitelist")))
        except BaseException:
            if BotVars.is_server_on:
                await ctx.send(add_quotes(get_translation("Couldn't connect to server, try again(")))
            else:
                await ctx.send(add_quotes(get_translation("server offline").capitalize()))

    @whitelist.command(pass_context=True, name="reload")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_reload(self, ctx):
        try:
            with connect_rcon() as cl_r:
                cl_r.run("whitelist reload")
                await ctx.send(add_quotes(get_translation("Reloaded the whitelist")))
        except BaseException:
            if BotVars.is_server_on:
                await ctx.send(add_quotes(get_translation("Couldn't connect to server, try again(")))
            else:
                await ctx.send(add_quotes(get_translation("server offline").capitalize()))

    @commands.group(pass_context=True, aliases=["servs"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def servers(self, ctx):
        await ctx.send(add_quotes(get_translation("Wrong syntax, subcommands:") + " select, list, show"))
        raise commands.UserInputError()

    @servers.command(pass_context=True, name="show")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_show(self, ctx):
        await ctx.send(add_quotes(get_translation("Selected server") + ": " +
                                  Config.get_selected_server_from_list().server_name +
                                  f" [{str(Config.get_settings().selected_server_number)}]"))

    @servers.command(pass_context=True, name="select")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_select(self, ctx, selected_server: int):
        if 0 < selected_server <= len(Config.get_settings().servers_list):
            if selected_server == Config.get_settings().selected_server_number:
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
            Config.get_settings().selected_server_number = selected_server
            Config.save_config()
            await ctx.send(add_quotes(get_translation("Selected server") + ": " +
                                      Config.get_selected_server_from_list().server_name +
                                      f" [{str(Config.get_settings().selected_server_number)}]"))
            Config.read_server_info()
            await ctx.send(add_quotes(get_translation("Server properties read!")))
        else:
            await ctx.send(add_quotes(get_translation("Use server list, there's no such "
                                                      "server number on the list!")))

    @servers.command(pass_context=True, name="list")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_list(self, ctx):
        send_ = "```" + get_translation("List of servers") + ":"
        for i in range(len(Config.get_settings().servers_list)):
            send_ += "\n[" + (make_underscored_line(i + 1)
                              if i + 1 == Config.get_settings().selected_server_number else str(i + 1)) + "] " + \
                     Config.get_settings().servers_list[i].server_name
        send_ += "```"
        await ctx.send(send_)

    @commands.group(pass_context=True, aliases=["bc"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def backup(self, ctx):
        await bot_backup(ctx)

    @backup.command(pass_context=True, name="on")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_on(self, ctx):
        if not Config.get_backups_settings().automatic_backup:
            Config.get_backups_settings().automatic_backup = True
            Config.save_config()
        await warn_about_auto_backups(ctx, self._bot)
        await ctx.send(add_quotes(get_translation("Automatic backups on")))

    @backup.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_off(self, ctx):
        if Config.get_backups_settings().automatic_backup:
            Config.get_backups_settings().automatic_backup = False
            Config.save_config()
        await ctx.send(add_quotes(get_translation("Automatic backups off")))

    @backup.command(pass_context=True, name="period")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_period(self, ctx, minutes: int = None):
        if minutes is not None and minutes > 0:
            Config.get_backups_settings().period_of_automatic_backups = minutes
            Config.save_config()
            await ctx.send(add_quotes(get_translation("Automatic backups period set to {0} min").format(minutes)))
        elif minutes is None:
            await ctx.send(add_quotes(get_translation("Automatic backups period set to {0} min")
                                      .format(Config.get_backups_settings().period_of_automatic_backups)))
        else:
            await ctx.send(add_quotes(get_translation("Automatic backups period can't be lower than 0!")))

    @backup.group(pass_context=True, name="method", invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_method(self, ctx, compression_method: str = None):
        if compression_method is not None and \
                compression_method.upper() in Config.get_backups_settings().supported_compression_methods:
            Config.get_backups_settings().compression_method = compression_method.upper()
            Config.save_config()
            await ctx.send(add_quotes(get_translation("Compression method set to {0}").format(compression_method)))
        elif compression_method is None:
            await ctx.send(add_quotes(get_translation("Current compression method - {0}")
                                      .format(Config.get_backups_settings().compression_method)))
        else:
            await ctx.send(add_quotes(get_translation("Bot doesn't have such compression method!\nSupported:") + "\n- "
                                      + "\n- ".join(Config.get_backups_settings().supported_compression_methods)))

    @b_method.command(name="list")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def b_m_list(self, ctx):
        await ctx.send(add_quotes(get_translation("Supported compression methods:") + "\n- " +
                                  "\n- ".join(Config.get_backups_settings().supported_compression_methods)))

    @backup.command(pass_context=True, name="force")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @commands.cooldown(rate=1, per=60)
    @decorators.has_role_or_default()
    async def b_force(self, ctx, *, reason: str = None):
        if not BotVars.is_loading and not BotVars.is_stopping and \
                not BotVars.is_restarting and not BotVars.is_restoring and not BotVars.is_backing_up:
            b_reason = handle_backups_limit_and_size(self._bot)
            if b_reason:
                await ctx.send(add_quotes(get_translation("Can't create backup because of {0}\n"
                                                          "Delete some backup to proceed!").format(b_reason)))
                return
            await warn_about_auto_backups(ctx, self._bot)

            msg = await ctx.send(add_quotes(get_translation("Starting backup...")))
            file_name = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
            for string in create_zip_archive(self._bot, file_name,
                                             Path(Config.get_selected_server_from_list().working_directory,
                                                  Config.get_backups_settings().name_of_the_backups_folder).as_posix(),
                                             Path(Config.get_selected_server_from_list().working_directory,
                                                  get_from_server_properties("level-name")).as_posix(),
                                             Config.get_backups_settings().compression_method, forced=True,
                                             user=ctx.author):
                await msg.edit(content=string)
            Config.add_backup_info(file_name=file_name, reason=reason,
                                   initiator=f"{ctx.author.display_name}#{ctx.author.discriminator}")
            Config.save_server_config()
            self._backups_thread.skip()
        else:
            await send_status(ctx)

    @backup.command(pass_context=True, name="restore")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_restore(self, ctx, backup_number: int):
        if not BotVars.is_server_on and not BotVars.is_loading and not BotVars.is_stopping and \
                not BotVars.is_restarting and not BotVars.is_backing_up:
            if 0 < backup_number <= len(Config.get_server_config().backups):
                await ctx.send(add_quotes(get_translation("Starting restore...")))
                restore_from_zip_archive(Config.get_server_config().backups[backup_number - 1].file_name,
                                         Path(Config.get_selected_server_from_list().working_directory,
                                              Config.get_backups_settings().name_of_the_backups_folder).as_posix(),
                                         Path(Config.get_selected_server_from_list().working_directory,
                                              get_from_server_properties("level-name")).as_posix())
                await ctx.send(add_quotes(get_translation("Done!")))
                self._backups_thread.skip()
            else:
                await ctx.send(add_quotes(get_translation("Bot doesn't have backup with that number "
                                                          "in backups list for current server!")))
        else:
            await send_status(ctx)

    @backup.group(pass_context=True, name="del")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_del(self, ctx, backup_number: int):
        if 0 < backup_number <= len(Config.get_server_config().backups):
            if Config.get_server_config().backups[backup_number - 1].initiator is not None:
                if "backup_del" in [p.command for p in self._IndPoll.get_polls().values()]:
                    await delete_after_by_msg(ctx.message)
                    await ctx.send(get_translation("{0}, bot already has poll on `backup del` command!")
                                   .format(ctx.author.mention),
                                   delete_after=Config.get_awaiting_times_settings()
                                   .await_seconds_before_message_deletion)
                    return

                if await self._IndPoll.timer(ctx, 5, "backup_del"):
                    if not await self._IndPoll.run(ctx=ctx,
                                                   message=get_translation(
                                                       "this man {0} trying to delete {1} backup by {2} of '{3}' "
                                                       "server. Will you let that happen?")
                                                           .format(ctx.author.mention,
                                                                   Config.get_server_config().backups[
                                                                       backup_number - 1].file_name + ".zip",
                                                                   Config.get_server_config().backups[
                                                                       backup_number - 1].initiator,
                                                                   Config.get_selected_server_from_list().server_name),
                                                   command="backup_del",
                                                   needed_role=Config.get_settings().bot_settings.role,
                                                   need_for_voting=get_half_members_count_with_role(self._bot),
                                                   remove_logs_after=5):
                        return
                else:
                    await delete_after_by_msg(ctx.message)

            backup = Config.get_server_config().backups[backup_number - 1]
            remove(Path(Config.get_selected_server_from_list().working_directory,
                        Config.get_backups_settings().name_of_the_backups_folder, f"{backup.file_name}.zip"))
            send_message_of_deleted_backup(self._bot,
                                           f"{ctx.author.display_name}#{ctx.author.discriminator}", backup)
            Config.get_server_config().backups.remove(backup)
            Config.save_server_config()
            await ctx.send(add_quotes(get_translation("Deleted backup {0}.zip of '{1}' server")
                                      .format(backup.file_name, Config.get_selected_server_from_list().server_name)))
        else:
            await ctx.send(add_quotes(get_translation("Bot doesn't have backup with that number "
                                                      "in backups list for current server!")))

    @b_del.command(pass_context=True, name="all")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_d_all(self, ctx):
        if "backup_del_all" in [p.command for p in self._IndPoll.get_polls().values()]:
            await delete_after_by_msg(ctx.message)
            await ctx.send(get_translation("{0}, bot already has poll on `backup del all` command!")
                           .format(ctx.author.mention),
                           delete_after=Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
            return

        if await self._IndPoll.timer(ctx, 5, "backup_del_all"):
            if not await self._IndPoll.run(ctx=ctx,
                                           message=get_translation(
                                               "this man {0} trying to delete all backups of '{1}' server. "
                                               "Will you let that happen?")
                                                   .format(ctx.author.mention,
                                                           Config.get_selected_server_from_list().server_name),
                                           command="backup_del_all",
                                           needed_role=Config.get_settings().bot_settings.role,
                                           need_for_voting=get_half_members_count_with_role(self._bot),
                                           remove_logs_after=5):
                return
        else:
            await delete_after_by_msg(ctx.message)

        for backup in Config.get_server_config().backups:
            remove(Path(Config.get_selected_server_from_list().working_directory,
                        Config.get_backups_settings().name_of_the_backups_folder, f"{backup.file_name}.zip"))
        send_message_of_deleted_backup(self._bot, f"{ctx.author.display_name}#{ctx.author.discriminator}")
        Config.get_server_config().backups.clear()
        Config.save_server_config()
        await ctx.send(add_quotes(get_translation("Deleted all backups of '{0}' server")
                                  .format(Config.get_selected_server_from_list().server_name)))

    @backup.command(pass_context=True, name="list")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def b_list(self, ctx):
        if len(Config.get_server_config().backups) > 0:
            message = get_translation("List of backups for '{0}' server:") \
                          .format(Config.get_selected_server_from_list().server_name) + "\n"
            i = 1
            for backup in Config.get_server_config().backups:
                message += f"[{i}] " + get_translation("Date: ") + \
                           backup.file_creation_date.strftime("%d/%m/%Y %H:%M:%S")
                message += "\n\t" + get_translation("Backup size: ") + \
                           get_human_readable_size(
                               get_file_size(Config.get_selected_server_from_list().working_directory,
                                             Config.get_backups_settings().name_of_the_backups_folder,
                                             f"{backup.file_name}.zip"))
                if backup.reason is None and backup.initiator is None:
                    message += "\n\t" + get_translation("Reason: ") + get_translation("Automatic backup") + "\n"
                else:
                    message += "\n\t" + get_translation("Reason: ") + \
                               (backup.reason if backup.reason else get_translation("Not stated"))
                    message += "\n\t" + get_translation("Initiator: ") + backup.initiator + "\n"
                i += 1
            await ctx.send(add_quotes(message))
        else:
            await ctx.send(add_quotes(get_translation("There are no backups for '{0}' server!")
                                      .format(Config.get_selected_server_from_list().server_name)))

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True,
                                  embed_links=True, add_reactions=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def menu(self, ctx):
        await ctx.channel.purge(limit=1)
        emb = discord.Embed(title=get_translation("List of commands via reactions"),
                            color=discord.Color.teal())
        for key, value in self._emoji_symbols.items():
            emb.add_field(name=key, value=value)
        add_reactions_to = await ctx.send(embed=emb)
        Config.get_settings().bot_settings.menu_id = add_reactions_to.id
        Config.save_config()
        for emote in self._emoji_symbols.values():
            await add_reactions_to.add_reaction(emote)

    @tasks.loop()
    async def checkups_task(self):
        await server_checkups(self._bot)

    @checkups_task.before_loop
    async def before_checkups(self):
        await self._bot.wait_until_ready()
        print(get_translation("Starting minecraft server check-ups"))

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
                elif payload.emoji.name == self._emoji_symbols.get("backup"):
                    await bot_backup(channel, is_reaction=True)
                elif payload.emoji.name == self._emoji_symbols.get("update"):
                    if self.checkups_task.is_running():
                        self.checkups_task.restart()
                    return
                else:
                    if Config.get_settings().bot_settings.role == "" or \
                            Config.get_settings().bot_settings.role in (e.name for e in payload.member.roles):
                        if payload.emoji.name == self._emoji_symbols.get("start"):
                            await bot_start(channel, self._bot, is_reaction=True)
                        elif payload.emoji.name == self._emoji_symbols.get("stop 10"):
                            await bot_stop(channel, command="10", bot=self._bot, poll=self._IndPoll, is_reaction=True)
                        elif payload.emoji.name == self._emoji_symbols.get("restart 10"):
                            await bot_restart(channel, command="10", bot=self._bot,
                                              poll=self._IndPoll, is_reaction=True)
                    else:
                        await send_error(channel, self._bot,
                                         commands.MissingRole(Config.get_settings().bot_settings.role),
                                         is_reaction=True)
