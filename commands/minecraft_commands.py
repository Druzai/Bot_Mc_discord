import socket
from asyncio import sleep as asleep
from contextlib import suppress
from datetime import datetime
from os import remove
from pathlib import Path
from random import randint
from re import search
from sys import argv
from typing import TYPE_CHECKING

from discord import Embed, Color as d_Color, DMChannel, Member, RawReactionActionEvent
from discord.ext import commands, tasks
from psutil import disk_usage

from components import decorators
from components.additional_funcs import (
    server_checkups, send_error, send_status, save_to_whitelist_json, get_whitelist_entry, get_server_players,
    add_quotes, bot_status, bot_list, bot_start, bot_stop, bot_restart, connect_rcon, make_underscored_line,
    get_human_readable_size, create_zip_archive, restore_from_zip_archive, get_file_size, BackupsThread,
    get_folder_size, send_message_of_deleted_backup, handle_backups_limit_and_size, bot_backup, delete_after_by_msg,
    get_half_members_count_with_role, warn_about_auto_backups, get_archive_uncompressed_size, get_bot_display_name,
    get_server_version, DISCORD_SYMBOLS_IN_MESSAGE_LIMIT, get_number_of_digits, bot_associate, bot_associate_info,
    get_time_string, bot_shutdown_info, bot_forceload_info, get_member_name, handle_rcon_error,
    check_and_delete_from_whitelist_json, IPv4Address
)
from components.localization import get_translation
from config.init_config import BotVars, Config, ServerProperties

if TYPE_CHECKING:
    from commands.poll import Poll


class MinecraftCommands(commands.Cog):
    _emoji_symbols = {"status": "🗨", "list": "📋", "backup": "💾", "start": "♿",
                      "stop 10": "⏹", "restart 10": "🔄", "update": "📶"}  # Symbols for menu

    def __init__(self, bot: commands.Bot):
        self._bot: commands.Bot = bot
        self._IndPoll: 'Poll' = bot.get_cog("Poll")
        self._backups_thread = BackupsThread(self._bot)
        if len(argv) == 1:
            self._backups_thread.start()

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    async def status(self, ctx: commands.Context):
        """Shows server status"""
        await bot_status(ctx, self._bot)

    @commands.command(pass_context=True, aliases=["ls"])
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    async def list(self, ctx: commands.Context):
        """Shows list of players"""
        await bot_list(ctx, self._bot)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def start(self, ctx: commands.Context):
        """Start server"""
        await bot_start(ctx, self._bot, self._backups_thread)

    @commands.command(pass_context=True, ignore_extra=False)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, mention_everyone=True, add_reactions=True,
                                  embed_links=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def stop(self, ctx: commands.Context, timeout: int = 0):
        """Stop server"""
        await bot_stop(ctx, timeout, self._bot, self._IndPoll)

    @commands.command(pass_context=True, ignore_extra=False)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, mention_everyone=True, add_reactions=True,
                                  embed_links=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def restart(self, ctx: commands.Context, timeout: int = 0):
        """Restart server"""
        await bot_restart(ctx, timeout, self._bot, self._IndPoll, self._backups_thread)

    @commands.group(pass_context=True, invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def op(self, ctx: commands.Context, minecraft_nick: str, *, reasons: str = ""):
        doing_opping = BotVars.is_doing_op
        BotVars.is_doing_op = True
        if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and not BotVars.is_restarting:
            if get_server_players().get("current") == 0:
                await ctx.send(f"{ctx.author.mention}, " +
                               get_translation("There are no players on the server").lower() + "!")
                BotVars.is_doing_op = doing_opping
                return

            if minecraft_nick not in [p.player_minecraft_nick for p in Config.get_server_config().seen_players]:
                await ctx.send(get_translation("{0}, I didn't see this nick on server, son! "
                                               "Go to the server via this nick before...").format(ctx.author.mention))
                BotVars.is_doing_op = doing_opping
                return

            if minecraft_nick not in [u.user_minecraft_nick for u in Config.get_known_users_list()] or \
                    ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()
                                          if u.user_minecraft_nick == minecraft_nick]:
                await ctx.send(get_translation("{0}, this nick isn't bound to you, use `{1}associate add` first...")
                               .format(ctx.author.mention, Config.get_settings().bot_settings.prefix))
                BotVars.is_doing_op = doing_opping
                return

            if minecraft_nick in [p.player_minecraft_nick for p in Config.get_server_config().seen_players] and \
                    [p.number_of_times_to_op for p in Config.get_server_config().seen_players
                     if p.player_minecraft_nick == minecraft_nick][0] == 0:
                await ctx.send(get_translation("{0}, you had run out of attempts to get an operator for `{1}` nick!")
                               .format(ctx.author.mention, minecraft_nick))
                BotVars.is_doing_op = doing_opping
                return

            if minecraft_nick not in get_server_players().get("players"):
                await ctx.send(get_translation("{0}, I didn't see this nick `{1}` online!")
                               .format(ctx.author.mention, minecraft_nick))
                BotVars.is_doing_op = doing_opping
                return

            if minecraft_nick in BotVars.op_deop_list:
                await ctx.send(get_translation("{0}, you've already been given an operator!")
                               .format(ctx.author.mention))
                BotVars.is_doing_op = doing_opping
                return

            BotVars.op_deop_list.append(minecraft_nick)
            Config.append_to_op_log(datetime.now().strftime("%d/%m/%Y %H:%M:%S") + " || " + get_translation("Opped ") +
                                    minecraft_nick + (" || " + get_translation("Reason: ") + reasons
                                                      if reasons else ""))
            await_time_op = Config.get_timeouts_settings().await_seconds_when_opped
            bot_display_name = get_bot_display_name(self._bot)
            server_version = get_server_version()
            try:
                with connect_rcon() as cl_r:
                    bot_message = f"{minecraft_nick}, " + get_translation("you've been given an operator for") + \
                                  f" {get_time_string(await_time_op)}."
                    if server_version.minor < 7:
                        cl_r.say(bot_message)
                    else:
                        cl_r.tellraw("@a", ["", {"text": "<"}, {"text": bot_display_name, "color": "dark_gray"},
                                            {"text": "> " + bot_message}])
                    cl_r.mkop(minecraft_nick)
                Config.decrease_number_to_op_for_player(minecraft_nick)
                Config.save_server_config()
            except (ConnectionError, socket.error):
                await ctx.send(get_translation("{0}, server isn't working (at least I've tried), try again later...")
                               .format(ctx.author.mention))
                return
            await ctx.send(add_quotes(get_translation("Now {0} is an operator!")
                                      .format(f"{ctx.author.display_name}#{ctx.author.discriminator}")))
            if await_time_op > 0:
                if randint(0, 2) == 1:
                    await ctx.send(
                        get_translation(
                            "So {0}, I gave you an operator, but I'm not going to pretend like "
                            "I did it to win favors upstairs. "
                            "I'll come in {1}, take away operator from everyone and we're even. "
                            "I don't give a shit why you want this operator and mind my own business. "
                            "If you want it, well, you must have your reasons..."
                        ).format(ctx.author.mention, get_time_string(await_time_op)))
                await asleep(await_time_op)
                if minecraft_nick != BotVars.op_deop_list[-1]:
                    return
                to_delete_ops = Config.get_list_of_ops(server_version)
                while True:
                    await asleep(Config.get_timeouts_settings().await_seconds_when_connecting_via_rcon)
                    with suppress(ConnectionError, socket.error):
                        if server_version.minor < 13:
                            gamemode = 0
                        else:
                            gamemode = "survival"
                        with connect_rcon() as cl_r:
                            bot_message = f"{minecraft_nick}, " + get_translation("an operator will be taken away "
                                                                                  "from you all will now.")
                            if server_version.minor < 7:
                                cl_r.say(bot_message)
                            else:
                                cl_r.tellraw("@a", ["", {"text": "<"}, {"text": bot_display_name, "color": "dark_gray"},
                                                    {"text": "> " + bot_message}])
                            for player in to_delete_ops:
                                cl_r.deop(player)
                            if server_version.minor < 4:
                                for player in get_server_players()["players"]:
                                    if server_version.minor > 2:
                                        cl_r.run(f"gamemode {gamemode} {player}")
                                    else:
                                        cl_r.run(f"gamemode {player} {gamemode}")
                            else:
                                cl_r.run(f"gamemode {gamemode} @a")
                            if server_version.minor > 2:
                                cl_r.run(f"defaultgamemode {gamemode}")
                        break
                Config.append_to_op_log(
                    datetime.now().strftime("%d/%m/%Y %H:%M:%S") + " || " + get_translation("Deopped all ") +
                    (str(get_translation("|| Note: ") +
                         get_translation("from {0} people in belated list operator was taken away")
                         .format(len(BotVars.op_deop_list))) if len(BotVars.op_deop_list) > 1 else ""))
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

    @op.command(pass_context=True, name="history", aliases=["hist"], ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def o_history(self, ctx: commands.Context, messages_from_end: int = 0):
        if messages_from_end < 0:
            await ctx.send(add_quotes(get_translation("Wrong 1-st argument used!") + "\n" +
                                      get_translation("Integer must be above {0}!").format(0)))
            return
        log = Config.get_op_log() if messages_from_end < 1 else Config.get_op_log()[-messages_from_end:]
        if "".join(log) == "":
            await ctx.send(add_quotes(get_translation("There is no history of giving an operator to players yet...")))
            return
        log = [lg for lg in log if not lg.split("||")[1].lstrip().startswith("Deop")]
        for line in range(len(log)):
            arr = log[line].split("||")
            date = datetime.strptime(arr[0].strip(), "%d/%m/%Y %H:%M:%S").strftime(get_translation("%H:%M %d/%m/%Y"))
            log[line] = f"{date} <{' '.join(arr[1].strip().split()[1:])}>" + \
                        (f": {' '.join(arr[2].strip().split()[1:])}" if len(arr) == 3 else "") + "\n"
        if len("".join(log)) + 6 > DISCORD_SYMBOLS_IN_MESSAGE_LIMIT:
            msg = ""
            msg_length = 0
            for line in log:
                if msg_length + len(line) + 6 > DISCORD_SYMBOLS_IN_MESSAGE_LIMIT:
                    await ctx.send(add_quotes(msg))
                    msg = ""
                    msg_length = 0
                msg += line
                msg_length += len(line)
            if len(msg) > 0:
                await ctx.send(add_quotes(msg))
        else:
            await ctx.send(add_quotes("".join(log)))

    @op.command(pass_context=True, name="info", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def o_info(self, ctx: commands.Context, for_who: str, show: str):
        """
        Get info about ops
        :param for_who: "me" or "everyone"
        :param show: "seen" or "all"
        """
        if for_who not in ["me", "everyone"] or show not in ["seen", "all"]:
            await ctx.send(get_translation("Syntax:") +
                           f" `{Config.get_settings().bot_settings.prefix}op info <'me', 'everyone'> <'seen', 'all'>`")
            raise commands.UserInputError()

        message = await bot_associate_info(ctx, for_me=for_who == "me", show=show)
        await ctx.send(message)

    @op.command(pass_context=True, name="timeout", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def o_timeout(self, ctx: commands.Context, new_value: int = None):
        if new_value is None:
            await ctx.send(add_quotes(get_translation("Timeout for being operator in Minecraft set to {0} sec.")
                                      .format(Config.get_timeouts_settings().await_seconds_when_opped).strip(".") +
                                      (f" ({get_time_string(Config.get_timeouts_settings().await_seconds_when_opped)})"
                                       if Config.get_timeouts_settings().await_seconds_when_opped > 59 else "") +
                                      ("\n" + get_translation("Limitation doesn't exist, padawan.")
                                       if Config.get_timeouts_settings().await_seconds_when_opped == 0 else "")))
        elif new_value < 0:
            await ctx.send(add_quotes(get_translation("Wrong 1-st argument used!") + "\n" +
                                      get_translation("Integer must be above or equal {0}!").format(0)))
        elif new_value > 1440:
            await ctx.send(add_quotes(get_translation("Wrong 1-st argument used!") + "\n" +
                                      get_translation("Integer must be below or equal {0}!").format(1440)))
        else:
            Config.get_timeouts_settings().await_seconds_when_opped = new_value
            await ctx.send(
                add_quotes(get_translation("Timeout for being operator in Minecraft set to {0} sec.")
                           .format(new_value).strip(".") + "!" +
                           (f" ({get_time_string(new_value)})" if new_value > 59 else "") +
                           ("\n" + get_translation("Limitation doesn't exist, padawan.") if new_value == 0 else "")))
            Config.save_config()

    @commands.group(pass_context=True, aliases=["assoc"], invoke_without_command=True, ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def associate(self, ctx: commands.Context, for_who: str):
        """Associates discord user with nick in Minecraft"""
        if for_who not in ["me", "everyone"]:
            await ctx.send(get_translation("Syntax:") +
                           f" `{Config.get_settings().bot_settings.prefix}associate <'me', 'everyone'>`")
            raise commands.UserInputError()
        message = await bot_associate_info(ctx, for_me=for_who == "me")
        await ctx.send(message)

    @associate.command(pass_context=True, name="add", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def a_add(self, ctx: commands.Context, discord_mention: Member, *, minecraft_nick: str):
        await bot_associate(ctx, self._bot, discord_mention, "add", minecraft_nick)

    @associate.command(pass_context=True, name="del", aliases=["remove"], ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def a_del(self, ctx: commands.Context, discord_mention: Member, *, minecraft_nick: str):
        await bot_associate(ctx, self._bot, discord_mention, "del", minecraft_nick)

    @commands.group(pass_context=True, aliases=["auth"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def authorize(self, ctx: commands.Context):
        msg = get_translation("Secure authorization on") if Config.get_secure_auth().enable_secure_auth \
            else get_translation("Secure authorization off")
        msg += "\n" + get_translation("Login attempts allowed - {0}") \
            .format(Config.get_secure_auth().max_login_attempts)
        msg += "\n" + get_translation("Session expiration time in days - {0}") \
            .format(Config.get_secure_auth().days_before_ip_expires)
        msg += "\n" + get_translation("Code expiration time in minutes - {0}") \
            .format(Config.get_secure_auth().mins_before_code_expires)

        msg += "\n\n" + get_translation("Information about authorized users:") + "\n"
        if len(Config.get_auth_users()) == 0:
            msg += "-----"
        else:
            user_nicks = Config.get_user_nicks()
            for k, v in user_nicks.items():
                msg += f"{k}:\n"
                for ip in v:
                    msg += f"\t{ip[0]}: {ip[1]}\n"
        await ctx.send(add_quotes(msg))

    @authorize.command(pass_context=True, name="on")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def a_on(self, ctx: commands.Context):
        Config.get_secure_auth().enable_secure_auth = True
        Config.save_config()
        await ctx.send(add_quotes(get_translation("Secure authorization on")))

    @authorize.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def a_off(self, ctx: commands.Context):
        Config.get_secure_auth().enable_secure_auth = False
        Config.save_config()
        await ctx.send(add_quotes(get_translation("Secure authorization off")))

    @authorize.command(pass_context=True, name="login", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_role_or_default()
    async def a_login(self, ctx: commands.Context, nick: str, code: str):
        if not Config.get_secure_auth().enable_secure_auth:
            await ctx.send(add_quotes(get_translation("Secure authorization is disabled. Enable it to proceed!")))
            return
        code = code.upper()
        ip_info = Config.get_users_ip_address_info(nick, code=code)
        if ip_info is None:
            await ctx.send(add_quotes(get_translation("Bot couldn't find nick and/or code "
                                                      "in the IP-addresses without access!")))
            return
        if len([1 for p in self._IndPoll.get_polls().values() if p.command == f"auth login {nick}"]) > 0:
            await delete_after_by_msg(ctx.message)
            await ctx.send(get_translation("{0}, bot already has poll on `auth login {1}` command!")
                           .format(ctx.author.mention, nick),
                           delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
            return
        bound_user = None
        for user in Config.get_known_users_list():
            if user.user_minecraft_nick == nick:
                bound_user = await self._bot.guilds[0].fetch_member(user.user_discord_id)
                break
        if (bound_user is not None and bound_user.id != ctx.author.id) or \
                (isinstance(ctx.channel, DMChannel) and bound_user is None):
            await ctx.send(add_quotes(get_translation("You don't have this nick in associations!")))
            return

        if ip_info.code == code:
            if ip_info.code_expires_on_date is None or ip_info.code_expires_on_date < datetime.now():
                await ctx.send(add_quotes(get_translation("This code expired! Try to login again to get another one!")))
                return
            if bound_user is None:
                if not await self._IndPoll.run(channel=ctx.channel,
                                               message=get_translation("this man {0} trying to login as `{1}`. "
                                                                       "Bot requesting create link {0} -> {1}. "
                                                                       "Will you let that happen?")
                                                       .format(ctx.author.mention, nick),
                                               command=f"auth login {nick}",
                                               needed_role=Config.get_settings().bot_settings.admin_role_id,
                                               need_for_voting=1,
                                               timeout=Config.get_secure_auth().mins_before_code_expires * 60,
                                               admin_needed=True,
                                               remove_logs_after=5):
                    return
                # Associate member with this nick
                Config.add_to_known_users_list(nick, ctx.author.id)
                Config.save_config()
            Config.update_ip_address(nick, ip_info.ip_address, whitelist=True)
            Config.save_auth_users()
            await ctx.send(get_translation("{0}, bot gave access to the nick `{1}` with IP-address `{2}`!")
                           .format(ctx.author.mention, nick, ip_info.ip_address))
        else:
            await ctx.send(add_quotes(get_translation("Your code for this nick is wrong. Try again.")))

    @authorize.command(pass_context=True, name="banlist")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_role_or_default()
    async def a_banlist(self, ctx: commands.Context):
        async with handle_rcon_error(ctx):
            banned_ips = Config.get_list_of_banned_ips_and_reasons(get_server_version())
            if len(banned_ips) > 0:
                reason_str = get_translation("Reason: ")
                outline = (3 + len(reason_str)) * " "
                n = "\n"
                await ctx.send(add_quotes(
                    get_translation("List of banned IP-addresses:") +
                    "\n- " + "\n- ".join([f"{e['ip']}" +
                                          (f"\n  {reason_str}'{e['reason'].replace(f'{n}', f'{n}{outline}')}'"
                                           if e['reason'] is not None else "")
                                          for e in banned_ips])))
            else:
                await ctx.send(add_quotes(get_translation("There are no banned IP-addresses!")))

    @authorize.command(pass_context=True, name="ban")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_role_or_default()
    async def a_ban(self, ctx: commands.Context, ip: IPv4Address, *, reason: str = None):
        has_admin_rights = False
        if not isinstance(ctx.channel, DMChannel):
            with suppress(decorators.MissingAdminPermissions):
                if decorators.is_admin(ctx):
                    has_admin_rights = True

        if not has_admin_rights and not Config.get_secure_auth().enable_secure_auth:
            await ctx.send(add_quotes(get_translation("Secure authorization is disabled. Enable it to proceed!")))
            return

        if not has_admin_rights:
            if ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()]:
                await ctx.send(get_translation("{0}, you don't have bound nicks, use `{1}associate add` first...")
                               .format(ctx.author.mention, Config.get_settings().bot_settings.prefix))
                return
            bound_nicks = [u.user_minecraft_nick for u in Config.get_known_users_list()
                           if u.user_discord_id == ctx.author.id]
            have_ip = False
            for user in Config.get_auth_users():
                if user.nick not in bound_nicks:
                    continue
                for ip_addr in user.ip_addresses:
                    if ip_addr.ip_address == ip:
                        have_ip = True
                    if have_ip:
                        break
                if have_ip:
                    break
            if not have_ip:
                await ctx.send(get_translation("{0}, there are no nicks in your possession "
                                               "that were logged on with this IP-address").format(ctx.author.mention))
                return

        async with handle_rcon_error(ctx):
            server_version = get_server_version()
            with connect_rcon() as cl_r:
                if reason is not None and server_version.minor > 2:
                    if server_version.minor < 7 or (server_version.minor == 7 and server_version.patch < 6):
                        reason = reason.replace("\n", " ")
                    cl_r.run(f"ban-ip {ip} {reason}")
                else:
                    cl_r.run(f"ban-ip {ip}")
            reason_str = ""
            if reason is not None:
                reason_str = " " + get_translation("with reason '{0}'").format(reason)
            await ctx.send(add_quotes(get_translation("Banned IP-address {0}{1}!").format(ip, reason_str)))
            Config.remove_ip_address(ip)
            Config.save_auth_users()

    @authorize.command(pass_context=True, aliases=["pardon"], name="unban", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def a_unban(self, ctx: commands.Context, ip: IPv4Address):
        if len(Config.get_list_of_banned_ips_and_reasons(get_server_version())) == 0:
            await ctx.send(add_quotes(get_translation("There are no banned IP-addresses!")))
            return

        async with handle_rcon_error(ctx):
            with connect_rcon() as cl_r:
                cl_r.run(f"pardon-ip {ip}")
            await ctx.send(add_quotes(get_translation("Unbanned IP-address {0}!").format(ip)))

    @authorize.group(pass_context=True, name="revoke", invoke_without_command=True, ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def a_revoke(self, ctx: commands.Context, ip: IPv4Address, nick: str = None):
        if not Config.get_secure_auth().enable_secure_auth:
            await ctx.send(add_quotes(get_translation("Secure authorization is disabled. Enable it to proceed!")))
            return

        if len(Config.get_auth_users()) == 0:
            await ctx.send(add_quotes(get_translation("Bot has no users who tried to enter "
                                                      "or entered Minecraft server!")))
            return

        has_admin_rights = False
        with suppress(decorators.MissingAdminPermissions):
            if decorators.is_admin(ctx):
                has_admin_rights = True

        bound_nicks = None
        if not has_admin_rights:
            if ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()]:
                await ctx.send(get_translation("{0}, you don't have bound nicks, use `{1}associate add` first...")
                               .format(ctx.author.mention, Config.get_settings().bot_settings.prefix))
                return
            bound_nicks = [u.user_minecraft_nick for u in Config.get_known_users_list()
                           if u.user_discord_id == ctx.author.id]

        possible_matches = []
        for user in Config.get_auth_users():
            if nick is not None and user.nick != nick or \
                    (has_admin_rights and bound_nicks is not None and nick not in bound_nicks):
                continue
            for ip_addr in user.ip_addresses:
                if ip_addr.ip_address == ip:
                    possible_matches.append(user.nick)
            if nick is not None and user.nick == nick:
                break

        if len(possible_matches) == 0:
            if has_admin_rights:
                await ctx.send(get_translation("{0}, there are no nicks that were logged on with this IP-address")
                               .format(ctx.author.mention))
            else:
                await ctx.send(get_translation("{0}, there are no nicks in your possession "
                                               "that were logged on with this IP-address").format(ctx.author.mention))
            return
        Config.remove_ip_address(ip, possible_matches)
        Config.save_auth_users()
        try:
            server_players = get_server_players().get("players")
            available_players_to_kick = [p for p in possible_matches if p in server_players]
        except (ConnectionError, socket.error):
            available_players_to_kick = []
        await ctx.send(f"{ctx.author.mention}\n" +
                       add_quotes(get_translation("These nicks were revoked with this IP-address:") +
                                  "\n- " + "\n- ".join(possible_matches)))
        if len(available_players_to_kick) > 0:
            with suppress(ConnectionError, socket.error):
                with connect_rcon() as cl_r:
                    for p in available_players_to_kick:
                        cl_r.kick(p, get_translation("One of the sessions for this nick has been ended"))
            await ctx.send(f"{ctx.author.mention}\n" + add_quotes(get_translation("These nicks bound this IP-address "
                                                                                  "were kicked from Minecraft server:")
                                                                  + "\n- " + "\n- ".join(available_players_to_kick)))

    @a_revoke.command(pass_context=True, name="all")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def a_r_all(self, ctx: commands.Context):
        if not Config.get_secure_auth().enable_secure_auth:
            await ctx.send(add_quotes(get_translation("Secure authorization is disabled. Enable it to proceed!")))
            return

        if len(Config.get_auth_users()) == 0:
            await ctx.send(add_quotes(get_translation("Bot has no users who tried to enter "
                                                      "or entered Minecraft server!")))
            return

        nicks_to_revoke = [pl.nick for pl in Config.get_auth_users()]
        try:
            server_players = get_server_players().get("players")
            available_players_to_kick = [p for p in nicks_to_revoke if p in server_players]
        except (ConnectionError, socket.error):
            available_players_to_kick = []

        Config.get_auth_users().clear()
        Config.save_auth_users()
        await ctx.send(f"{ctx.author.mention}\n" + add_quotes(get_translation("All these nicks were revoked:") +
                                                              "\n- " + "\n- ".join(nicks_to_revoke)))
        if len(available_players_to_kick) > 0:
            with suppress(ConnectionError, socket.error):
                with connect_rcon() as cl_r:
                    for p in available_players_to_kick:
                        cl_r.kick(p, get_translation("All sessions for this nick have been ended"))
            await ctx.send(f"{ctx.author.mention}\n" +
                           add_quotes(get_translation("These nicks were kicked from Minecraft server:")
                                      + "\n- " + "\n- ".join(available_players_to_kick)))

    @commands.group(pass_context=True, aliases=["sch"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def schedule(self, ctx: commands.Context):
        msg = bot_shutdown_info(with_timeout=Config.get_settings().bot_settings.auto_shutdown) + \
              "\n\n" + bot_forceload_info()
        await ctx.send(add_quotes(msg))

    @schedule.group(pass_context=True, name="shutdown", aliases=["sd"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def s_shutdown(self, ctx: commands.Context):
        await ctx.send(add_quotes(bot_shutdown_info()))

    @s_shutdown.command(pass_context=True, name="on")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_s_on(self, ctx: commands.Context):
        Config.get_settings().bot_settings.auto_shutdown = True
        Config.save_config()
        await ctx.send(add_quotes(bot_shutdown_info(with_timeout=True)))

    @s_shutdown.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_s_off(self, ctx: commands.Context):
        Config.get_settings().bot_settings.auto_shutdown = False
        Config.save_config()
        await ctx.send(add_quotes(bot_shutdown_info()))

    @s_shutdown.command(pass_context=True, name="timeout", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_s_timeout(self, ctx: commands.Context, new_value: int = None):
        if new_value is None:
            await ctx.send(add_quotes(bot_shutdown_info(with_timeout=True, only_timeout=True)))
        elif new_value < 0:
            await ctx.send(add_quotes(get_translation("Wrong 1-st argument used!") + "\n" +
                                      get_translation("Integer must be above or equal {0}!").format(0)))
        elif new_value > 86400:
            await ctx.send(add_quotes(get_translation("Wrong 1-st argument used!") + "\n" +
                                      get_translation("Integer must be below or equal {0}!").format(86400)))
        else:
            Config.get_timeouts_settings().await_seconds_before_shutdown = new_value
            Config.save_config()
            await ctx.send(add_quotes(bot_shutdown_info(with_timeout=True, only_timeout=True)))

    @schedule.group(pass_context=True, name="forceload", aliases=["fl"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def s_forceload(self, ctx: commands.Context):
        await ctx.send(add_quotes(bot_forceload_info()))

    @s_forceload.command(pass_context=True, name="on")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_f_on(self, ctx: commands.Context):
        Config.get_settings().bot_settings.forceload = True
        Config.save_config()
        await ctx.send(add_quotes(bot_forceload_info()))

    @s_forceload.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_f_off(self, ctx: commands.Context):
        Config.get_settings().bot_settings.forceload = False
        Config.save_config()
        await ctx.send(add_quotes(bot_forceload_info()))

    @commands.group(pass_context=True, aliases=["wl"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def whitelist(self, ctx: commands.Context):
        if ServerProperties().white_list:
            await ctx.send(add_quotes(get_translation("The server only allows players from the list of allowed nicks")))
        else:
            await ctx.send(add_quotes(get_translation("The server allows players regardless of their nick")))

    @whitelist.command(pass_context=True, name="add", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_add(self, ctx: commands.Context, minecraft_nick: str):
        async with handle_rcon_error(ctx):
            version = get_server_version()
            with connect_rcon() as cl_r:
                if ServerProperties().online_mode or version.minor < 7 or (version.minor == 7 and version.patch < 6):
                    cl_r.run("whitelist add", minecraft_nick)
                else:
                    save_to_whitelist_json(get_whitelist_entry(minecraft_nick))
                    cl_r.run("whitelist reload")
                await ctx.send(add_quotes(get_translation("Added {0} to the list of allowed nicks")
                                          .format(minecraft_nick)))

    @whitelist.command(pass_context=True, name="del", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_del(self, ctx: commands.Context, minecraft_nick: str):
        async with handle_rcon_error(ctx):
            version = get_server_version()
            with connect_rcon() as cl_r:
                msg = cl_r.run("whitelist remove", minecraft_nick)
                entry_deleted = False
                if version.minor > 7 or (version.minor == 7 and version.patch > 5):
                    entry_deleted = check_and_delete_from_whitelist_json(minecraft_nick)
                    if entry_deleted:
                        cl_r.run("whitelist reload")
                if search(r"Removed [\w ]+ from the whitelist", msg) or entry_deleted:
                    await ctx.send(add_quotes(get_translation("Removed {0} from the list of allowed nicks")
                                              .format(minecraft_nick)))
                else:
                    await ctx.send(add_quotes(get_translation("Nick not found in the list of allowed nicks")))

    @whitelist.command(pass_context=True, name="list", aliases=["ls"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_list(self, ctx: commands.Context):
        async with handle_rcon_error(ctx):
            with connect_rcon() as cl_r:
                white_list = cl_r.run("whitelist list")
                if ":" in white_list:
                    players = [p.strip() for p in white_list.split(":", maxsplit=1)[1].split(",")]
                    if " and " in players[-1]:
                        players[-1], last_player = players[-1].split(" and ")
                        players.append(last_player)
                    await ctx.send(add_quotes(get_translation("Allowed nicks - {0}:\n{1}")
                                              .format(len(players), "- " + "\n- ".join(players))))
                else:
                    await ctx.send(add_quotes(get_translation("No nicks allowed to login")))

    @whitelist.command(pass_context=True, name="on")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_on(self, ctx: commands.Context):
        async with handle_rcon_error(ctx):
            with connect_rcon() as cl_r:
                cl_r.run("whitelist on")
                await ctx.send(add_quotes(get_translation("The server is forbidden to let players not "
                                                          "from the list of allowed nicknames")))

    @whitelist.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_off(self, ctx: commands.Context):
        async with handle_rcon_error(ctx):
            with connect_rcon() as cl_r:
                cl_r.run("whitelist off")
                await ctx.send(add_quotes(get_translation("The server is allowed to let any players regardless "
                                                          "of the list of allowed nicknames")))

    @whitelist.command(pass_context=True, name="reload")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def w_reload(self, ctx: commands.Context):
        async with handle_rcon_error(ctx):
            with connect_rcon() as cl_r:
                cl_r.run("whitelist reload")
                await ctx.send(add_quotes(get_translation("Reloaded the list of allowed nicks")))

    @commands.group(pass_context=True, aliases=["serv"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def server(self, ctx: commands.Context):
        await ctx.send(add_quotes(get_translation("Selected server") + ": " +
                                  Config.get_selected_server_from_list().server_name +
                                  f" [{str(Config.get_settings().selected_server_number)}]"))

    @server.command(pass_context=True, name="select", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_select(self, ctx: commands.Context, selected_server: int):
        if 0 < selected_server <= len(Config.get_settings().servers_list):
            if selected_server == Config.get_settings().selected_server_number:
                await ctx.send(add_quotes(get_translation("My, you have chosen selected server, insane?)\n"
                                                          " ...Patsan ramsi poputal")))
                return
            if BotVars.is_server_on or BotVars.is_loading or BotVars.is_stopping or BotVars.is_restarting:
                await ctx.send(add_quotes(
                    get_translation("You can't change server, while some instance is still running\n"
                                    "Please stop it, before trying again")))
                return

            if BotVars.watcher_of_log_file is not None:
                BotVars.watcher_of_log_file.stop()
                BotVars.watcher_of_log_file = None
            Config.get_settings().selected_server_number = selected_server
            Config.save_config()
            await ctx.send(add_quotes(get_translation("Selected server") + ": " +
                                      Config.get_selected_server_from_list().server_name +
                                      f" [{str(Config.get_settings().selected_server_number)}]"))
            print(get_translation("Selected server") + f" - '{Config.get_selected_server_from_list().server_name}'")
            Config.read_server_info()
            await ctx.send(add_quotes(get_translation("Server properties read!")))
            print(get_translation("Server info read!"))
        else:
            await ctx.send(add_quotes(get_translation("Use server list, there's no such "
                                                      "server number on the list!")))

    @server.command(pass_context=True, name="list", aliases=["ls"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def s_list(self, ctx: commands.Context):
        total_numb = get_number_of_digits(len(Config.get_settings().servers_list))
        send_ = "```" + get_translation("List of servers") + ":"
        for i in range(1, len(Config.get_settings().servers_list) + 1):
            first_additional_space = (total_numb - get_number_of_digits(i)) * " "
            send_ += f"\n{first_additional_space}[" + \
                     (make_underscored_line(i) if i == Config.get_settings().selected_server_number else str(i)) + \
                     "] " + Config.get_settings().servers_list[i - 1].server_name
        send_ += "```"
        await ctx.send(send_)

    @commands.group(pass_context=True, aliases=["bc"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def backup(self, ctx: commands.Context):
        await bot_backup(ctx, self._bot)

    @backup.command(pass_context=True, name="on")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_on(self, ctx: commands.Context):
        if not Config.get_backups_settings().automatic_backup:
            Config.get_backups_settings().automatic_backup = True
            Config.save_config()
        await warn_about_auto_backups(ctx, self._bot)
        await ctx.send(add_quotes(get_translation("Automatic backups enabled")))

    @backup.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_off(self, ctx: commands.Context):
        if Config.get_backups_settings().automatic_backup:
            Config.get_backups_settings().automatic_backup = False
            Config.save_config()
        await ctx.send(add_quotes(get_translation("Automatic backups disabled")))

    @backup.command(pass_context=True, name="period", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_period(self, ctx: commands.Context, minutes: int = None):
        if minutes is not None and minutes > 0:
            Config.get_backups_settings().period_of_automatic_backups = minutes
            Config.save_config()
            await ctx.send(add_quotes(get_translation("Automatic backups period set to {0} min").format(minutes)))
        elif minutes is None:
            await ctx.send(add_quotes(get_translation("Automatic backups period set to {0} min")
                                      .format(Config.get_backups_settings().period_of_automatic_backups)))
        else:
            await ctx.send(add_quotes(get_translation("Automatic backups period can't be lower than 0!")))

    @backup.group(pass_context=True, name="method", invoke_without_command=True, ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_method(self, ctx: commands.Context, compression_method: str = None):
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

    @b_method.command(pass_context=True, name="list", aliases=["ls"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def b_m_list(self, ctx: commands.Context):
        await ctx.send(add_quotes(get_translation("Supported compression methods:") + "\n- " +
                                  "\n- ".join(Config.get_backups_settings().supported_compression_methods)))

    @backup.command(pass_context=True, name="force")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @commands.cooldown(rate=1, per=15)
    @decorators.has_role_or_default()
    async def b_force(self, ctx: commands.Context, *, reason: str = None):
        if not BotVars.is_loading and not BotVars.is_stopping and \
                not BotVars.is_restarting and not BotVars.is_restoring and not BotVars.is_backing_up:
            b_reason = handle_backups_limit_and_size(self._bot)
            if b_reason:
                await ctx.send(add_quotes(get_translation("Can't create backup because of {0}\n"
                                                          "Delete some backups to proceed!").format(b_reason)))
                return
            await warn_about_auto_backups(ctx, self._bot)

            print(get_translation("Starting backup triggered by {0}")
                  .format(f"{ctx.author.display_name}#{ctx.author.discriminator}"))
            msg = await ctx.send(add_quotes(get_translation("Starting backup...")))
            file_name = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
            list_obj = None
            for obj in create_zip_archive(self._bot, file_name,
                                          Path(Config.get_selected_server_from_list().working_directory,
                                               Config.get_backups_settings().name_of_the_backups_folder).as_posix(),
                                          Path(Config.get_selected_server_from_list().working_directory,
                                               ServerProperties().level_name).as_posix(),
                                          Config.get_backups_settings().compression_method, forced=True,
                                          user=ctx.author):
                if isinstance(obj, str):
                    await msg.edit(content=obj)
                elif isinstance(obj, list):
                    list_obj = obj
            Config.add_backup_info(file_name=file_name, reason=reason, initiator=ctx.author.id)
            Config.save_server_config()
            self._backups_thread.skip()
            print(get_translation("Backup completed!"))
            if isinstance(list_obj, list):
                await ctx.send(add_quotes(get_translation("Bot couldn't archive some files to this backup!")))
                print(get_translation("Bot couldn't archive some files to this backup, they located in path '{0}'")
                      .format(Path(Config.get_selected_server_from_list().working_directory,
                                   ServerProperties().level_name).as_posix()))
                print(get_translation("List of these files:"))
                print(", ".join(list_obj))
        else:
            await send_status(ctx)

    @backup.command(pass_context=True, name="restore", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_restore(self, ctx: commands.Context, backup_number: int):
        if not BotVars.is_server_on and not BotVars.is_loading and not BotVars.is_stopping and \
                not BotVars.is_restarting and not BotVars.is_backing_up:
            if 0 < backup_number <= len(Config.get_server_config().backups):
                level_name = ServerProperties().level_name
                free_space = disk_usage(Config.get_selected_server_from_list().working_directory).free
                bc_folder_bytes = get_folder_size(Config.get_selected_server_from_list().working_directory,
                                                  level_name)
                uncompressed_size = get_archive_uncompressed_size(
                    Config.get_selected_server_from_list().working_directory,
                    Config.get_backups_settings().name_of_the_backups_folder,
                    f"{Config.get_server_config().backups[backup_number - 1].file_name}.zip")
                if free_space + bc_folder_bytes <= uncompressed_size:
                    await ctx.send(
                        add_quotes(get_translation("There are not enough space on disk to restore from backup!"
                                                   "\nFree - {0}\nRequired at least - {1}"
                                                   "\nDelete some backups to proceed!")
                                   .format(get_human_readable_size(free_space + bc_folder_bytes),
                                           get_human_readable_size(uncompressed_size))))
                    return
                await ctx.send(add_quotes(get_translation("Starting restore from backup...")))
                restore_from_zip_archive(Config.get_server_config().backups[backup_number - 1].file_name,
                                         Path(Config.get_selected_server_from_list().working_directory,
                                              Config.get_backups_settings().name_of_the_backups_folder).as_posix(),
                                         Path(Config.get_selected_server_from_list().working_directory,
                                              level_name).as_posix())
                for backup in Config.get_server_config().backups:
                    if backup.restored_from:
                        backup.restored_from = False
                Config.get_server_config().backups[backup_number - 1].restored_from = True
                Config.save_server_config()
                await ctx.send(add_quotes(get_translation("Done!")))
                self._backups_thread.skip()
            else:
                await ctx.send(add_quotes(get_translation("Bot doesn't have backup with this number "
                                                          "in backups list for current server!")))
        else:
            await send_status(ctx)

    @backup.group(pass_context=True, name="del", aliases=["remove"], invoke_without_command=True, ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_del(self, ctx: commands.Context, backup_number: int):
        if len(Config.get_server_config().backups) == 0:
            await ctx.send(add_quotes(get_translation("There are no backups for '{0}' server!")
                                      .format(Config.get_selected_server_from_list().server_name)))
            return

        if 0 < backup_number <= len(Config.get_server_config().backups):
            if Config.get_server_config().backups[backup_number - 1].initiator is not None:
                if "backup_del" in [p.command for p in self._IndPoll.get_polls().values()]:
                    await delete_after_by_msg(ctx.message)
                    await ctx.send(get_translation("{0}, bot already has poll on `backup del` command!")
                                   .format(ctx.author.mention),
                                   delete_after=Config.get_timeouts_settings()
                                   .await_seconds_before_message_deletion)
                    return

                if await self._IndPoll.timer(ctx, 5, "backup_del"):
                    member = await get_member_name(self._bot,
                                                   Config.get_server_config().backups[backup_number - 1].initiator)
                    if not await self._IndPoll. \
                            run(channel=ctx.channel,
                                message=get_translation(
                                    "this man {0} trying to delete {1} backup by {2} of '{3}' "
                                    "server. Will you let that happen?")
                                        .format(ctx.author.mention,
                                                Config.get_server_config().backups[backup_number - 1].file_name +
                                                ".zip", member, Config.get_selected_server_from_list().server_name),
                                command="backup_del",
                                needed_role=Config.get_settings().bot_settings.managing_commands_role_id,
                                need_for_voting=get_half_members_count_with_role(ctx.channel,
                                                                                 Config.get_settings().bot_settings
                                                                                         .managing_commands_role_id),
                                remove_logs_after=5):
                        return
                else:
                    await delete_after_by_msg(ctx.message)

            backup = Config.get_server_config().backups[backup_number - 1]
            remove(Path(Config.get_selected_server_from_list().working_directory,
                        Config.get_backups_settings().name_of_the_backups_folder, f"{backup.file_name}.zip"))
            send_message_of_deleted_backup(self._bot, f"{ctx.author.display_name}#{ctx.author.discriminator}", backup,
                                           member_name=await get_member_name(self._bot, backup.initiator))
            Config.get_server_config().backups.remove(backup)
            Config.save_server_config()
            await ctx.send(add_quotes(get_translation("Deleted backup {0}.zip of '{1}' server")
                                      .format(backup.file_name, Config.get_selected_server_from_list().server_name)))
        else:
            await ctx.send(add_quotes(get_translation("Bot doesn't have backup with this number "
                                                      "in backups list for current server!")))

    @b_del.command(pass_context=True, name="all")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def b_d_all(self, ctx: commands.Context):
        if len(Config.get_server_config().backups) == 0:
            await ctx.send(add_quotes(get_translation("There are no backups for '{0}' server!")
                                      .format(Config.get_selected_server_from_list().server_name)))
            return

        if "backup_del_all" in [p.command for p in self._IndPoll.get_polls().values()]:
            await delete_after_by_msg(ctx.message)
            await ctx.send(get_translation("{0}, bot already has poll on `backup del all` command!")
                           .format(ctx.author.mention),
                           delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
            return

        if await self._IndPoll.timer(ctx, 5, "backup_del_all"):
            if not await self._IndPoll. \
                    run(channel=ctx.channel,
                        message=get_translation(
                            "this man {0} trying to delete all backups of '{1}' server. "
                            "Will you let that happen?")
                                .format(ctx.author.mention,
                                        Config.get_selected_server_from_list().server_name),
                        command="backup_del_all",
                        needed_role=Config.get_settings().bot_settings.managing_commands_role_id,
                        need_for_voting=get_half_members_count_with_role(ctx.channel,
                                                                         Config.get_settings().bot_settings
                                                                                 .managing_commands_role_id),
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

    @backup.command(pass_context=True, name="list", aliases=["ls"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def b_list(self, ctx: commands.Context):
        if len(Config.get_server_config().backups) > 0:
            message = get_translation("List of backups for '{0}' server:") \
                          .format(Config.get_selected_server_from_list().server_name) + "\n"
            i = 1
            total_numb = get_number_of_digits(len(Config.get_server_config().backups))
            additional_space = (total_numb - 1) * " "
            for backup in Config.get_server_config().backups:
                first_additional_space = (total_numb - get_number_of_digits(i)) * " "
                message += f"{first_additional_space}[{i}] " + get_translation("Date: ") + \
                           backup.file_creation_date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))
                message += f"\n\t{additional_space}" + get_translation("Backup size: ") + \
                           get_human_readable_size(
                               get_file_size(Config.get_selected_server_from_list().working_directory,
                                             Config.get_backups_settings().name_of_the_backups_folder,
                                             f"{backup.file_name}.zip"))
                if backup.reason is None and backup.initiator is None:
                    message += f"\n\t{additional_space}" + get_translation("Reason: ") + \
                               get_translation("Automatic backup")
                else:
                    message += f"\n\t{additional_space}" + get_translation("Reason: ") + \
                               (backup.reason if backup.reason else get_translation("Not stated"))
                    message += f"\n\t{additional_space}" + get_translation("Initiator: ") + \
                               await get_member_name(self._bot, backup.initiator)
                message += "\n"
                if backup.restored_from:
                    message += "\t" + \
                               get_translation("The world of the server was restored from this backup") + "\n"
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
    async def menu(self, ctx: commands.Context):
        await delete_after_by_msg(ctx.message, without_delay=True)
        emb = Embed(title=get_translation("List of commands via reactions"),
                    color=d_Color.teal())
        for key, value in self._emoji_symbols.items():
            emb.add_field(name=key, value=value)
        add_reactions_to = await ctx.send(embed=emb)
        Config.get_settings().bot_settings.menu_id = add_reactions_to.id
        Config.save_config()
        for emote in self._emoji_symbols.values():
            await add_reactions_to.add_reaction(emote)

    @tasks.loop()
    async def checkups_task(self):
        await server_checkups(self._bot, self._backups_thread, self._IndPoll)

    @checkups_task.before_loop
    async def before_checkups(self):
        await self._bot.wait_until_ready()
        print(get_translation("Starting Minecraft server check-ups"))

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        if payload.message_id == Config.get_settings().bot_settings.menu_id and payload.member.id != self._bot.user.id:
            channel = self._bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)
            await message.remove_reaction(payload.emoji, payload.member)
            if payload.emoji.name in self._emoji_symbols.values():
                BotVars.react_auth = payload.member
                if payload.emoji.name == self._emoji_symbols.get("status"):
                    await bot_status(channel, self._bot, is_reaction=True)
                elif payload.emoji.name == self._emoji_symbols.get("list"):
                    await bot_list(channel, self._bot, is_reaction=True)
                elif payload.emoji.name == self._emoji_symbols.get("backup"):
                    await bot_backup(channel, self._bot, is_reaction=True)
                elif payload.emoji.name == self._emoji_symbols.get("update"):
                    if self.checkups_task.is_running():
                        self.checkups_task.restart()
                    return
                else:
                    if Config.get_settings().bot_settings.managing_commands_role_id is None or \
                            Config.get_settings().bot_settings.managing_commands_role_id \
                            in (e.id for e in payload.member.roles):
                        if payload.emoji.name == self._emoji_symbols.get("start"):
                            await bot_start(channel, self._bot, self._backups_thread, is_reaction=True)
                        elif payload.emoji.name == self._emoji_symbols.get("stop 10"):
                            await bot_stop(channel, command=10, bot=self._bot, poll=self._IndPoll, is_reaction=True)
                        elif payload.emoji.name == self._emoji_symbols.get("restart 10"):
                            await bot_restart(channel, command=10, bot=self._bot, poll=self._IndPoll,
                                              backups_thread=self._backups_thread, is_reaction=True)
                    else:
                        await send_error(channel, self._bot,
                                         commands.MissingRole(Config.get_settings().bot_settings
                                                              .managing_commands_role_id),
                                         is_reaction=True)
