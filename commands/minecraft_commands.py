import socket
from asyncio import sleep as asleep
from contextlib import suppress
from datetime import datetime
from os import remove
from pathlib import Path
from random import randint
from re import search
from sys import argv
from typing import TYPE_CHECKING, Literal, Optional

from discord import DMChannel, Member, SelectOption, Interaction
from discord.ext import commands, tasks

from components import decorators
from components.additional_funcs import (
    server_checkups, send_status, get_server_players, add_quotes, bot_status, bot_list, bot_start, bot_stop,
    bot_restart, connect_rcon, make_underscored_line, get_human_readable_size, get_file_size, BackupsThread,
    send_message_of_deleted_backup, bot_backup, delete_after_by_msg, get_half_members_count_with_role,
    warn_about_auto_backups, get_bot_display_name, get_server_version, DISCORD_SYMBOLS_IN_MESSAGE_LIMIT,
    get_number_of_digits, bot_associate, bot_associate_info, get_time_string, bot_shutdown_info, bot_forceload_info,
    get_member_string, handle_rcon_error, IPv4Address, handle_unhandled_error_in_task,
    check_if_string_in_all_translations, build_nickname_tellraw_for_bot, send_select_view, shorten_string, SelectChoice,
    send_interaction, DISCORD_SELECT_FIELD_MAX_LENGTH, MenuServerView, on_server_select_callback, MenuBotView,
    get_message_and_channel, backup_force_checking, on_backup_force_callback, backup_restore_checking,
    send_backup_restore_select, send_backup_remove_select, check_if_obituary_webhook
)
from components.localization import get_translation
from components.watcher_handle import create_watcher
from config.init_config import BotVars, Config, ServerProperties

if TYPE_CHECKING:
    from commands.poll import Poll


class MinecraftCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self._bot: commands.Bot = bot
        self._IndPoll: Optional['Poll'] = bot.get_cog("Poll")
        if self._IndPoll is None:
            raise RuntimeError("Cog 'Poll' not found!")
        self.backups_thread = BackupsThread(self._bot)
        if Config.get_menu_settings().server_menu_message_id is not None:
            self.menu_server_view: Optional[MenuServerView] = MenuServerView(self._bot, self)
        else:
            self.menu_server_view: Optional[MenuServerView] = None
        if Config.get_menu_settings().bot_menu_message_id is not None:
            self.menu_bot_view: Optional[MenuBotView] = MenuBotView(self._bot, self)
        else:
            self.menu_bot_view: Optional[MenuBotView] = None
        if len(argv) == 1:
            self.backups_thread.start()
            self.checkups_task.change_interval(seconds=Config.get_timeouts_settings().await_seconds_in_check_ups)

    @commands.group(pass_context=True, invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    async def status(self, ctx: commands.Context):
        """Shows server status"""
        await bot_status(ctx, self._bot)

    @status.command(pass_context=True, name="update")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def s_update(self, ctx: commands.Context):
        self.checkups_task.restart()
        await ctx.send(add_quotes(get_translation("Updated bot status!")))

    @commands.command(pass_context=True, aliases=["ls"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    async def list(self, ctx: commands.Context):
        """Shows list of players"""
        await bot_list(ctx, self._bot)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def start(self, ctx: commands.Context):
        """Start server"""
        await bot_start(ctx, self._bot, self.backups_thread)

    @commands.command(pass_context=True, ignore_extra=False)
    @commands.bot_has_permissions(
        manage_messages=True, send_messages=True, mention_everyone=True, add_reactions=True, embed_links=True,
        view_channel=True
    )
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def stop(self, ctx: commands.Context, timeout: int = 0):
        """Stop server"""
        await bot_stop(ctx, timeout, self._bot, self._IndPoll)

    @commands.command(pass_context=True, ignore_extra=False)
    @commands.bot_has_permissions(
        manage_messages=True, send_messages=True, mention_everyone=True, add_reactions=True, embed_links=True,
        view_channel=True
    )
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def restart(self, ctx: commands.Context, timeout: int = 0):
        """Restart server"""
        await bot_restart(ctx, timeout, self._bot, self._IndPoll, self.backups_thread)

    @commands.group(pass_context=True, invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def op(self, ctx: commands.Context, minecraft_nick: str, *, reasons: str = ""):
        if not Config.get_op_settings().enable_op:
            await ctx.send(f"{ctx.author.mention}, " +
                           get_translation("Getting an operator to Minecraft players is disabled") + "!")
            return

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
            Config.append_to_op_log(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " || " + get_translation("Opped ") +
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
                        bot_tellraw = build_nickname_tellraw_for_bot(server_version, bot_display_name)
                        bot_tellraw[-1]["text"] += bot_message
                        cl_r.tellraw("@a", bot_tellraw)
                    cl_r.mkop(minecraft_nick)
                Config.decrease_number_to_op_for_player(minecraft_nick)
                Config.save_server_config()
            except (ConnectionError, socket.error):
                await ctx.send(get_translation("{0}, server isn't working (at least I've tried), try again later...")
                               .format(ctx.author.mention))
                return
            is_special_bot_speech = randint(0, 3) == 1
            if is_special_bot_speech and await_time_op > 0:
                line_to_op = get_translation(
                    "So {0}, I gave you an operator, but I'm not going to pretend like "
                    "I did it to win favors upstairs. "
                    "I'll come in {1}, take away operator from everyone and we're even. "
                    "I don't give a shit why you want this operator and mind my own business. "
                    "If you want it, well, you must have your reasons..."
                ).format(ctx.author.mention, get_time_string(await_time_op))
            else:
                line_to_op = add_quotes(get_translation(
                    "Now {0} is an operator!"
                ).format(f"{ctx.author.display_name}#{ctx.author.discriminator}"))
            await ctx.send(line_to_op)
            if await_time_op > 0:
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
                            bot_message = f"{minecraft_nick}, "
                            if len(to_delete_ops) > 1:
                                bot_message += get_translation(
                                    "the operator will be taken away from {0} players now."
                                ).format(len(to_delete_ops))
                            else:
                                bot_message += get_translation("the operator will be taken away from you.")
                            if server_version.minor < 7:
                                cl_r.say(bot_message)
                            else:
                                bot_tellraw = build_nickname_tellraw_for_bot(server_version, bot_display_name)
                                bot_tellraw[-1]["text"] += bot_message
                                cl_r.tellraw("@a", bot_tellraw)
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
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " || " + get_translation("Deopped all") + " " +
                    (str(get_translation("|| Note: ") +
                         get_translation("from {0} people in belated list operator was taken away")
                         .format(len(BotVars.op_deop_list))) if len(BotVars.op_deop_list) > 1 else ""))
                if is_special_bot_speech:
                    line_to_deop = get_translation(
                        "Well, {0}, your time is over..."
                    ).format(ctx.author.mention) + \
                                   (" " + get_translation("and not only yours...") if len(to_delete_ops) > 1 else "") \
                                   + "\n" + get_translation("As they say \"Cheeki breeki i v damké!\"")
                else:
                    line_to_deop = add_quotes(get_translation(
                        "The operator was taken away from {0}"
                    ).format(f"{ctx.author.display_name}#{ctx.author.discriminator}") +
                                              (" " + get_translation(
                                                  "and {0} player(s)"
                                              ).format(len(to_delete_ops)) if len(to_delete_ops) > 1 else "") + ".")
                await ctx.send(line_to_deop)
                BotVars.op_deop_list.clear()
            else:
                await ctx.send(get_translation("{0}, you have no time limit, but you are all doomed...")
                               .format(ctx.author.mention))

            if len(BotVars.op_deop_list) == 0:
                BotVars.is_doing_op = False
        else:
            await send_status(ctx)

    @op.command(pass_context=True, name="on")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_admin_role()
    @commands.guild_only()
    async def o_on(self, ctx: commands.Context):
        if not Config.get_op_settings().enable_op:
            Config.get_op_settings().enable_op = True
            Config.save_config()
        await ctx.send(add_quotes(get_translation("Getting an operator to Minecraft players is enabled")))

    @op.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_admin_role()
    @commands.guild_only()
    async def o_off(self, ctx: commands.Context):
        if Config.get_op_settings().enable_op:
            Config.get_op_settings().enable_op = False
            Config.save_config()
        await ctx.send(add_quotes(get_translation("Getting an operator to Minecraft players is disabled")))

    @op.command(pass_context=True, name="history", aliases=["hist"], ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def o_history(self, ctx: commands.Context, messages_from_end: int = 0):
        if messages_from_end < 0:
            await ctx.send(add_quotes(get_translation("Wrong 1-st argument used!") + "\n" +
                                      get_translation("Integer must be above {0}!").format(0)))
            return
        log = Config.get_op_log() if messages_from_end < 1 else Config.get_op_log()[-messages_from_end:]
        if "".join(log) == "":
            await ctx.send(add_quotes(get_translation("There is no history of giving an operator to players yet...")))
            return
        log = [lg for lg in log if not check_if_string_in_all_translations(translate_text="Deopped all",
                                                                           match_text=lg.split("||")[1].strip())]
        for line in range(len(log)):
            arr = log[line].split("||")
            for format_line in ["%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"]:  # Date compatibility
                with suppress(ValueError):
                    date = datetime.strptime(arr[0].strip(), format_line).strftime(get_translation("%H:%M %d/%m/%Y"))
                    break
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
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def o_info(self, ctx: commands.Context, for_who: Literal['me', 'everyone'], show: Literal['seen', 'all']):
        """Get info about ops"""
        message = await bot_associate_info(ctx, for_me=for_who == "me", show=show)
        await ctx.send(message)

    @op.command(pass_context=True, name="timeout", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_admin_role()
    @commands.guild_only()
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
    @decorators.has_admin_role()
    @commands.guild_only()
    async def associate(self, ctx: commands.Context, for_who: Literal['me', 'everyone']):
        """Associates discord user with nick in Minecraft"""
        message = await bot_associate_info(ctx, for_me=for_who == "me")
        await ctx.send(message)

    @associate.command(pass_context=True, name="add")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_admin_role()
    @commands.guild_only()
    async def a_add(self, ctx: commands.Context, discord_mention: Member, *, minecraft_nick: str):
        await bot_associate(ctx, self._bot, discord_mention, "add", minecraft_nick)

    @associate.command(pass_context=True, name="remove", aliases=["del"], ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_admin_role()
    @commands.guild_only()
    async def a_remove(self, ctx: commands.Context, discord_mention: Member, *, minecraft_nick: str):
        await bot_associate(ctx, self._bot, discord_mention, "remove", minecraft_nick)

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
    @decorators.has_admin_role()
    @commands.guild_only()
    async def a_on(self, ctx: commands.Context):
        if not Config.get_secure_auth().enable_secure_auth:
            Config.get_secure_auth().enable_secure_auth = True
            Config.save_config()
        with suppress(ConnectionError, socket.error):
            if BotVars.watcher_of_log_file is None:
                BotVars.watcher_of_log_file = create_watcher(BotVars.watcher_of_log_file, get_server_version())
            BotVars.watcher_of_log_file.start()
        await ctx.send(add_quotes(get_translation("Secure authorization on")))

    @authorize.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_admin_role()
    @commands.guild_only()
    async def a_off(self, ctx: commands.Context):
        if Config.get_secure_auth().enable_secure_auth:
            Config.get_secure_auth().enable_secure_auth = False
            Config.save_config()
        if not Config.get_game_chat_settings().enable_game_chat and \
                BotVars.watcher_of_log_file is not None:
            BotVars.watcher_of_log_file.stop()
        await ctx.send(add_quotes(get_translation("Secure authorization off")))

    @authorize.command(pass_context=True, name="login", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
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
                                               message=get_translation(
                                                   "this man {0} trying to login as `{1}`. "
                                                   "Bot requesting create link {0} -> {1}. "
                                                   "Will you let that happen?"
                                               ).format(ctx.author.mention, nick),
                                               command=f"auth login {nick}",
                                               needed_role=Config.get_settings().bot_settings.admin_role_id,
                                               need_for_voting=1,
                                               timeout=Config.get_secure_auth().mins_before_code_expires * 60,
                                               admin_needed=True,
                                               remove_logs_after=5):
                    return
                if check_if_obituary_webhook(nick):
                    await ctx.send(get_translation("{0}, you don't have permission to control fates! "
                                                   "Not in this life at least...").format(ctx.author.mention))
                    return
                # Associate member with this nick
                Config.add_to_known_users_list(nick, ctx.author.id)
                Config.save_config()
            Config.update_ip_address(nick, ip_info.ip_address, whitelist=True)
            Config.save_auth_users()
            await ctx.send(get_translation("{0}, bot gave access to the nick `{1}` with IP-address `{2}`!")
                           .format(ctx.author.mention, nick, ip_info.ip_address))
            banned_ips = Config.get_list_of_banned_ips_and_reasons(get_server_version())
            if ip_info.ip_address in [e["ip"] for e in banned_ips]:
                async with handle_rcon_error(ctx):
                    with connect_rcon() as cl_r:
                        cl_r.run(f"pardon-ip {ip_info.ip_address}")
                    await ctx.send(add_quotes(get_translation("Unbanned IP-address {0}!").format(ip_info.ip_address)))
        else:
            await ctx.send(add_quotes(get_translation("Your code for this nick is wrong. Try again.")))

    @authorize.command(pass_context=True, name="banlist")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
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
    @decorators.has_minecrafter_role_or_default()
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
    @decorators.has_admin_role()
    @commands.guild_only()
    async def a_unban(self, ctx: commands.Context, ip: IPv4Address = None):
        async with handle_rcon_error(ctx):
            banned_ips = Config.get_list_of_banned_ips_and_reasons(get_server_version())
            if len(banned_ips) == 0:
                await ctx.send(add_quotes(get_translation("There are no banned IP-addresses!")))
                return

            async def on_callback(interaction: Optional[Interaction]):
                set_ip = interaction.data.get("values", [None])[0] if interaction is not None else ip

                if set_ip is None:
                    await send_interaction(
                        interaction,
                        add_quotes(get_translation("You provided wrong IP-address in chosen option! Try again")),
                        ctx=ctx,
                        is_reaction=True
                    )
                    return SelectChoice.DO_NOTHING

                async with handle_rcon_error(ctx):
                    with connect_rcon() as cl_r:
                        cl_r.run(f"pardon-ip {set_ip}")
                    await send_interaction(
                        interaction,
                        add_quotes(get_translation("Unbanned IP-address {0}!").format(set_ip)),
                        ctx=ctx
                    )
                return SelectChoice.STOP_VIEW

            if ip is not None:
                await on_callback(None)
                return

            async def on_select_option(i: int, _):
                return SelectOption(
                    label=shorten_string(banned_ips[i]["ip"], DISCORD_SELECT_FIELD_MAX_LENGTH),
                    value=shorten_string(banned_ips[i]["ip"], DISCORD_SELECT_FIELD_MAX_LENGTH),
                    description=(shorten_string(get_translation("Reason: ") + banned_ips[i]["reason"],
                                                DISCORD_SELECT_FIELD_MAX_LENGTH)
                                 if banned_ips[i]["reason"] is not None else None)
                )

            await send_select_view(
                ctx=ctx,
                raw_options=banned_ips,
                pivot_index=None,
                make_select_option=on_select_option,
                on_callback=on_callback,
                on_interaction_check=decorators.is_admin,
                message=get_translation("Select from the list of banned IP-addresses:"),
                timeout=180
            )

    @authorize.group(pass_context=True, name="revoke", invoke_without_command=True, ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
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
            server_version = None
            kicked_nicks = []
            reason = get_translation("One of the sessions for this nick has been ended")
            with suppress(ConnectionError, socket.error):
                with connect_rcon() as cl_r:
                    for player in available_players_to_kick:
                        response = cl_r.kick(
                            player if get_server_version().minor < 14 else f"'{player}'",
                            reason
                        )
                        if not search(reason, response):
                            if server_version is None:
                                server_version = get_server_version()
                            if server_version.minor > 2:
                                cl_r.run(f"ban-ip {ip} {reason}")
                            else:
                                cl_r.run(f"ban-ip {ip}")
                            cl_r.run(f"pardon-ip {ip}")
                        kicked_nicks.append(player)
            await ctx.send(f"{ctx.author.mention}\n" + add_quotes(get_translation("These nicks bound this IP-address "
                                                                                  "were kicked from Minecraft server:")
                                                                  + "\n- " + "\n- ".join(kicked_nicks)))

    @a_revoke.command(pass_context=True, name="all")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_admin_role()
    @commands.guild_only()
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
            server_version = None
            kicked_nicks = []
            reason = get_translation("All sessions for this nick have been ended")
            with suppress(ConnectionError, socket.error):
                with connect_rcon() as cl_r:
                    for player in available_players_to_kick:
                        response = cl_r.kick(
                            player if get_server_version().minor < 14 else f"'{player}'",
                            reason
                        )
                        if not search(reason, response):
                            if server_version is None:
                                server_version = get_server_version()
                            for ip in Config.get_known_user_ips(player):
                                if server_version.minor > 2:
                                    cl_r.run(f"ban-ip {ip} {reason}")
                                else:
                                    cl_r.run(f"ban-ip {ip}")
                                cl_r.run(f"pardon-ip {ip}")
                        kicked_nicks.append(player)
            await ctx.send(f"{ctx.author.mention}\n" +
                           add_quotes(get_translation("These nicks were kicked from Minecraft server:")
                                      + "\n- " + "\n- ".join(kicked_nicks)))

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
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def s_s_on(self, ctx: commands.Context):
        if not Config.get_settings().bot_settings.auto_shutdown:
            Config.get_settings().bot_settings.auto_shutdown = True
            Config.save_config()
        await ctx.send(add_quotes(bot_shutdown_info(with_timeout=True)))

    @s_shutdown.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def s_s_off(self, ctx: commands.Context):
        if Config.get_settings().bot_settings.auto_shutdown:
            Config.get_settings().bot_settings.auto_shutdown = False
            Config.save_config()
        await ctx.send(add_quotes(bot_shutdown_info()))

    @s_shutdown.command(pass_context=True, name="timeout", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
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
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def s_f_on(self, ctx: commands.Context):
        if not Config.get_settings().bot_settings.forceload:
            Config.get_settings().bot_settings.forceload = True
            Config.save_config()
        await ctx.send(add_quotes(bot_forceload_info()))

    @s_forceload.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def s_f_off(self, ctx: commands.Context):
        if Config.get_settings().bot_settings.forceload:
            Config.get_settings().bot_settings.forceload = False
            Config.save_config()
        await ctx.send(add_quotes(bot_forceload_info()))

    @commands.group(pass_context=True, aliases=["wl"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def whitelist(self, ctx: commands.Context):
        if ServerProperties().white_list:
            await ctx.send(add_quotes(get_translation("The server only allows players from the list of allowed nicks")))
        else:
            await ctx.send(add_quotes(get_translation("The server allows players regardless of their nick")))

    @whitelist.command(pass_context=True, name="add", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def w_add(self, ctx: commands.Context, *, minecraft_nick: str):
        async with handle_rcon_error(ctx):
            version = get_server_version()
            with connect_rcon() as cl_r:
                added = False
                server_properties = ServerProperties()
                if " " not in minecraft_nick and \
                        (not any(map(str.isupper, minecraft_nick)) or server_properties.online_mode):
                    response = cl_r.run("whitelist add", minecraft_nick).strip()
                    match = search(r"^Added\s(?P<nick>\S+)", response)
                    if match is not None:
                        if match.group("nick") == minecraft_nick:
                            added = True
                        else:
                            if Config.check_entry_in_whitelist(version, match.group("nick"), remove_entry=True):
                                cl_r.run("whitelist reload")

                if not server_properties.online_mode and not added:
                    Config.save_to_whitelist(version, minecraft_nick)
                    cl_r.run("whitelist reload")
                    added = True

                if added:
                    await ctx.send(add_quotes(get_translation("Added {0} to the list of allowed nicks")
                                              .format(minecraft_nick)))
                else:
                    await ctx.send(add_quotes(get_translation("Nick wasn't added to the list of allowed nicks")))

    @whitelist.command(pass_context=True, name="remove", aliases=["del"], ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def w_remove(self, ctx: commands.Context, *, minecraft_nick: str):
        async with handle_rcon_error(ctx):
            version = get_server_version()
            with connect_rcon() as cl_r:
                removed = False
                if " " not in minecraft_nick:
                    response = cl_r.run("whitelist remove", minecraft_nick).strip()
                    match = search(r"^Removed\s(?P<nick>\S+)", response)
                    if match is not None:
                        if match.group("nick") == minecraft_nick:
                            removed = True

                if not removed:
                    if Config.check_entry_in_whitelist(version, minecraft_nick, remove_entry=True):
                        cl_r.run("whitelist reload")
                        removed = True

                if removed:
                    await ctx.send(add_quotes(get_translation("Removed {0} from the list of allowed nicks")
                                              .format(minecraft_nick)))
                else:
                    await ctx.send(add_quotes(get_translation("Nick wasn't found in the list of allowed nicks")))

    @whitelist.command(pass_context=True, name="list", aliases=["ls"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
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
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def w_on(self, ctx: commands.Context):
        async with handle_rcon_error(ctx):
            with connect_rcon() as cl_r:
                cl_r.run("whitelist on")
                await ctx.send(add_quotes(get_translation("The server is forbidden to let players not "
                                                          "from the list of allowed nicknames")))

    @whitelist.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def w_off(self, ctx: commands.Context):
        async with handle_rcon_error(ctx):
            with connect_rcon() as cl_r:
                cl_r.run("whitelist off")
                await ctx.send(add_quotes(get_translation("The server is allowed to let any players regardless "
                                                          "of the list of allowed nicknames")))

    @whitelist.command(pass_context=True, name="reload")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def w_reload(self, ctx: commands.Context):
        async with handle_rcon_error(ctx):
            with connect_rcon() as cl_r:
                cl_r.run("whitelist reload")
                await ctx.send(add_quotes(get_translation("Reloaded the list of allowed nicks")))

    @commands.group(pass_context=True, aliases=["serv"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def server(self, ctx: commands.Context):
        await ctx.send(add_quotes(get_translation("Selected server") + ": " +
                                  Config.get_selected_server_from_list().server_name +
                                  f" [{str(Config.get_settings().selected_server_number)}]"))

    @server.command(pass_context=True, name="select")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def s_select(self, ctx: commands.Context):
        async def on_callback(interaction: Interaction):
            result = await on_server_select_callback(interaction, ctx=ctx)
            if self.menu_server_view is not None:
                await self.menu_server_view.update_view()
            return result

        servers_list = Config.get_settings().servers_list

        async def on_select_option(i: int, _):
            return SelectOption(
                label=shorten_string(servers_list[i].server_name, DISCORD_SELECT_FIELD_MAX_LENGTH),
                value=str(i),
                default=i + 1 == Config.get_settings().selected_server_number
            )

        await send_select_view(
            ctx=ctx,
            raw_options=servers_list,
            pivot_index=Config.get_settings().selected_server_number,
            make_select_option=on_select_option,
            on_callback=on_callback,
            on_interaction_check=decorators.is_minecrafter,
            message=get_translation("Select Minecraft server:"),
            timeout=180
        )

    @server.command(pass_context=True, name="list", aliases=["ls"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
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
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def b_on(self, ctx: commands.Context):
        if not Config.get_backups_settings().automatic_backup:
            Config.get_backups_settings().automatic_backup = True
            Config.save_config()
        await warn_about_auto_backups(ctx, self._bot)
        await ctx.send(add_quotes(get_translation("Automatic backups enabled")))

    @backup.command(pass_context=True, name="off")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def b_off(self, ctx: commands.Context):
        if Config.get_backups_settings().automatic_backup:
            Config.get_backups_settings().automatic_backup = False
            Config.save_config()
        await ctx.send(add_quotes(get_translation("Automatic backups disabled")))

    @backup.command(pass_context=True, name="period", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
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
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
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
    @commands.cooldown(rate=1, per=15)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def b_force(self, ctx: commands.Context, *, reason: str = None):
        if backup_force_checking(ctx, self._bot):
            await on_backup_force_callback(ctx, self._bot, self.backups_thread, reason)

    @backup.command(pass_context=True, name="restore")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def b_restore(self, ctx: commands.Context):
        if not (await backup_restore_checking(ctx)):
            return

        await send_backup_restore_select(ctx, self._bot, self.backups_thread)

    @backup.group(pass_context=True, name="remove", aliases=["del"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def b_remove(self, ctx: commands.Context):
        await send_backup_remove_select(ctx, self._bot, self._IndPoll, self.backups_thread)

    @b_remove.command(pass_context=True, name="all")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def b_r_all(self, ctx: commands.Context):
        if len(Config.get_server_config().backups) == 0:
            await ctx.send(add_quotes(get_translation("There are no backups for '{0}' server!")
                                      .format(Config.get_selected_server_from_list().server_name)))
            return

        if "backup_remove_all" in [p.command for p in self._IndPoll.get_polls().values()]:
            await delete_after_by_msg(ctx.message)
            await ctx.send(get_translation("{0}, bot already has poll on `backup remove all` command!")
                           .format(ctx.author.mention),
                           delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
            return

        if await self._IndPoll.timer(ctx, ctx.author, 5, "backup_remove_all"):
            if not await self._IndPoll.run(
                    channel=ctx.channel,
                    message=get_translation(
                        "this man {0} trying to delete all backups of `{1}` server. "
                        "Will you let that happen?"
                    ).format(ctx.author.mention,
                             Config.get_selected_server_from_list().server_name),
                    command="backup_remove_all",
                    needed_role=Config.get_settings().bot_settings.managing_commands_role_id,
                    need_for_voting=get_half_members_count_with_role(
                        ctx.channel,
                        Config.get_settings().bot_settings.managing_commands_role_id
                    ),
                    remove_logs_after=5
            ):
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
                               await get_member_string(self._bot, backup.initiator)
                message += "\n"
                if backup.restored_from:
                    message += "\t" + \
                               get_translation("The world of the server was restored from this backup") + "\n"
                i += 1
            await ctx.send(add_quotes(message))
        else:
            await ctx.send(add_quotes(get_translation("There are no backups for '{0}' server!")
                                      .format(Config.get_selected_server_from_list().server_name)))

    @commands.group(pass_context=True, invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def menu(self, ctx: commands.Context):
        msg = ""
        message = None
        channel = None
        if self.menu_server_view is not None:
            message, channel = await get_message_and_channel(
                self._bot,
                self.menu_server_view.message_id,
                self.menu_server_view.channel_id
            )
        if message is not None and channel is not None:
            msg += get_translation("Server menu was found in {0}\nLink - {1}").format(
                channel.mention, f"<{message.jump_url}>"
            ) + "\n\n"
        else:
            msg += get_translation("Server menu wasn't found!") + "\n"

        message = None
        channel = None
        if self.menu_bot_view is not None:
            message, channel = await get_message_and_channel(
                self._bot,
                self.menu_bot_view.message_id,
                self.menu_bot_view.channel_id
            )
        if message is not None and channel is not None:
            msg += get_translation("Bot menu was found in {0}\nLink - {1}").format(
                channel.mention, f"<{message.jump_url}>"
            )
        else:
            msg += get_translation("Bot menu wasn't found!")
        await ctx.send(msg)

    @menu.command(pass_context=True, name="server", aliases=["serv"])
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def m_server(self, ctx: commands.Context):
        await delete_after_by_msg(ctx.message, without_delay=True)
        for v in self._bot.persistent_views:
            if isinstance(v, MenuServerView):
                v.stop()
        self.menu_server_view = MenuServerView(self._bot, self)
        await self.menu_server_view.update_view(send=False)
        menu_msg = await ctx.send(get_translation("List of commands for interacting with Minecraft server via buttons"
                                                  " and dropdown for selecting server"),
                                  view=self.menu_server_view)
        Config.get_menu_settings().server_menu_message_id = menu_msg.id
        self.menu_server_view.message_id = menu_msg.id
        Config.get_menu_settings().server_menu_channel_id = menu_msg.channel.id
        self.menu_server_view.channel_id = menu_msg.channel.id
        Config.save_config()

    @menu.command(pass_context=True, name="bot")
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, view_channel=True)
    @decorators.has_minecrafter_role_or_default()
    @commands.guild_only()
    async def m_bot(self, ctx: commands.Context):
        await delete_after_by_msg(ctx.message, without_delay=True)
        for v in self._bot.persistent_views:
            if isinstance(v, MenuBotView):
                v.stop()
        self.menu_bot_view = MenuBotView(self._bot, self)
        await self.menu_bot_view.update_view(send=False)
        menu_msg = await ctx.send(get_translation("List of bot features for interaction via buttons"
                                                  " and dropdown for selecting bot language"),
                                  view=self.menu_bot_view)
        Config.get_menu_settings().bot_menu_message_id = menu_msg.id
        self.menu_bot_view.message_id = menu_msg.id
        Config.get_menu_settings().bot_menu_channel_id = menu_msg.channel.id
        self.menu_bot_view.channel_id = menu_msg.channel.id
        Config.save_config()

    @tasks.loop()
    async def checkups_task(self):
        with handle_unhandled_error_in_task():
            await server_checkups(self._bot, self.backups_thread, self._IndPoll)

    @checkups_task.before_loop
    async def before_checkups(self):
        await self._bot.wait_until_ready()
        print(get_translation("Starting Minecraft server check-ups"))
