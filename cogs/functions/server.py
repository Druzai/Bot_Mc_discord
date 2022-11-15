import socket
from datetime import datetime, timedelta
from typing import Union, TYPE_CHECKING

from discord import (
    Message, Member, Role, MessageType, TextChannel, VoiceChannel, Thread as ChannelThread, GroupChannel, Interaction,
    Client
)
from discord.ext import commands

from components.backups import BackupsThread, calculate_space_for_current_server, get_average_backup_size
from components.localization import get_translation, check_if_string_in_all_translations
from components.minecraft.connect import get_server_version, connect_rcon, get_server_players
from components.minecraft.server_management import start_server, stop_server
from components.utils import (
    get_member_string, get_time_string, add_quotes, send_msg, send_status, get_last_element_of_async_iterator,
    delete_after_by_msg, get_human_readable_size, get_file_size, get_author
)
from config.init_config import Config, BotVars

if TYPE_CHECKING:
    from cogs.poll_cog import Poll


async def bot_status(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        is_reaction=False
):
    states = ""
    bot_message = ""
    states_info = Config.get_server_config().states
    if states_info.started_info.date is not None and states_info.started_info.user is not None:
        if not states_info.started_info.bot:
            states += get_translation("Server has been started at {0} by member {1}") \
                          .format(states_info.started_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y")),
                                  await get_member_string(bot, states_info.started_info.user)) + "\n"
        else:
            states += get_translation("Server has started at {0}") \
                          .format(states_info.started_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))) + "\n"
    if states_info.stopped_info.date is not None and states_info.stopped_info.user is not None:
        if not states_info.stopped_info.bot:
            states += get_translation("Server has been stopped at {0} by member {1}") \
                          .format(states_info.stopped_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y")),
                                  await get_member_string(bot, states_info.stopped_info.user)) + "\n"
        else:
            states += get_translation("Server has stopped at {0}") \
                          .format(states_info.stopped_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))) + "\n"
    elif states_info.stopped_info.date is not None and states_info.stopped_info.user is None:
        states += get_translation("Server has crashed at {0}") \
                      .format(states_info.stopped_info.date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))) + "\n"
    states = states.strip("\n")
    bot_message += get_translation("Server address: ") + Config.get_settings().bot_settings.ip_address + "\n"
    if BotVars.is_backing_up:
        bot_message += get_translation("Server is backing up") + "\n"
    if BotVars.is_restoring:
        bot_message += get_translation("Server is restoring from backup") + "\n"
    server_info = get_translation(
        "Selected server: {0}"
    ).format(Config.get_selected_server_from_list().server_name) + "\n"
    if Config.get_selected_server_from_list().server_loading_time is not None:
        server_info += get_translation("Average server loading time: {0}") \
                           .format(get_time_string(Config.get_selected_server_from_list().server_loading_time)) + "\n"
    if BotVars.is_server_on and not BotVars.is_stopping:
        try:
            server_version = get_server_version()
            bot_message = get_translation("server online").capitalize() + "\n" + bot_message
            if server_version.minor > 7:
                # Rcon check daytime cycle
                with connect_rcon() as cl_r:
                    time_ticks = int(cl_r.run("time query daytime").split(" ")[-1])
                message = get_translation("Time in Minecraft: ")
                if 450 <= time_ticks <= 11616:
                    message += get_translation("Day")
                elif 11617 <= time_ticks <= 13800:
                    message += get_translation("Sunset")
                elif 13801 <= time_ticks <= 22550:
                    message += get_translation("Night")
                else:
                    message += get_translation("Sunrise")
                message += f", {(6 + time_ticks // 1000) % 24}:{((time_ticks % 1000) * 60 // 1000):02d}\n"
                bot_message += message
            server_info_splits = server_info.split("\n", maxsplit=1)
            server_version_str = get_translation("Server version: {0}").format(server_version.version_string)
            server_info = f"{server_info_splits[0]}\n{server_version_str}\n{server_info_splits[-1]}"
            bot_message += server_info + states
            await send_msg(ctx, add_quotes(bot_message), is_reaction=is_reaction)
        except (ConnectionError, socket.error):
            bot_message += get_translation("Server thinking...") + "\n" + server_info + states
            await send_msg(ctx, add_quotes(bot_message), is_reaction=is_reaction)
            print(get_translation("Server isn't available via RCON"))
    else:
        if BotVars.is_loading:
            bot_message = get_translation("server is loading!").capitalize()[:-1] + "\n" + bot_message
        elif BotVars.is_stopping:
            bot_message = get_translation("server is stopping!").capitalize()[:-1] + "\n" + bot_message
        else:
            bot_message = get_translation("server offline").capitalize() + "\n" + bot_message
        bot_message += server_info + states
        await send_msg(ctx, add_quotes(bot_message), is_reaction=is_reaction)


async def bot_list(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        is_reaction=False
):
    try:
        info = get_server_players()
        if info.get("current") == 0:
            await send_msg(ctx, add_quotes(get_translation("There are no players on the server")),
                           is_reaction=is_reaction)
        else:
            players_dict = {p: None for p in info.get("players")}
            if Config.get_secure_auth().enable_secure_auth:
                for player in Config.get_auth_users():
                    if player.nick in players_dict.keys() and BotVars.player_logged(player.nick) is not None:
                        non_expired_ips = [ip.expires_on_date for ip in player.ip_addresses
                                           if ip.expires_on_date is not None and datetime.now() < ip.expires_on_date]
                        if len(non_expired_ips) > 0:
                            players_dict[player.nick] = max(non_expired_ips) - \
                                                        timedelta(days=Config.get_secure_auth().days_before_ip_expires)
            else:
                for logged_player, date in BotVars.players_login_dict.items():
                    if logged_player in players_dict.keys():
                        players_dict[logged_player] = date
            players_list = []
            w_from = get_translation("from")
            time_f = get_translation("%H:%M %d/%m/%y")
            for k, v in players_dict.items():
                if v is not None:
                    if v.day == datetime.now().day:
                        players_list.append(f"{k} ({w_from} {v.strftime('%H:%M')})")
                    else:
                        players_list.append(f"{k} ({w_from} {v.strftime(time_f)})")
                else:
                    players_list.append(k)
            await send_msg(ctx, add_quotes(get_translation("Players online: {0} / {1}").format(info.get("current"),
                                                                                               info.get("max")) +
                                           "\n- " + "\n- ".join(players_list)),
                           is_reaction=is_reaction)
    except (ConnectionError, socket.error):
        author = get_author(ctx, bot, is_reaction)
        await send_msg(ctx, f"{author.mention}, " + get_translation("server offline"), is_reaction=is_reaction)


async def bot_start(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        backups_thread,
        is_reaction=False
):
    if not BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and \
            not BotVars.is_backing_up and not BotVars.is_restoring:
        await start_server(ctx, bot=bot, backups_thread=backups_thread, is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_stop(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        command,
        bot: Union[commands.Bot, Client],
        poll: 'Poll',
        is_reaction=False
):
    if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and \
            not BotVars.is_backing_up and not BotVars.is_restoring:
        if BotVars.is_doing_op:
            await send_msg(ctx, add_quotes(get_translation("Some player(s) still have an operator, waiting for them")),
                           is_reaction=is_reaction)
            return
        if Config.get_settings().bot_settings.forceload:
            Config.get_settings().bot_settings.forceload = False
            Config.save_config()
        await stop_server(ctx, bot, poll, command, is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_restart(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        command,
        bot: Union[commands.Bot, Client],
        poll: 'Poll',
        backups_thread: BackupsThread,
        is_reaction=False
):
    if BotVars.is_server_on and not BotVars.is_stopping and not BotVars.is_loading and \
            not BotVars.is_backing_up and not BotVars.is_restoring:
        if BotVars.is_doing_op:
            await send_msg(ctx, add_quotes(get_translation("Some player(s) still have an operator, waiting for them")),
                           is_reaction=is_reaction)
            return
        BotVars.is_restarting = True
        print(get_translation("Restarting server"))
        await stop_server(ctx, bot, poll, command, True, is_reaction=is_reaction)
        await start_server(ctx, bot, backups_thread, is_reaction=is_reaction)
    else:
        await send_status(ctx, is_reaction=is_reaction)


async def bot_clear(
        ctx: commands.Context,
        poll: 'Poll',
        subcommand: str = None,
        count: int = None,
        discord_mentions=None
):
    message_created = None
    mentions = set()
    if discord_mentions is not None:
        for mention in discord_mentions:
            if isinstance(mention, Member):
                mentions.add(mention)
            elif isinstance(mention, Role):
                mentions.update(mention.members)
    if len(mentions):
        check_condition = lambda m: m.author in mentions and m.id not in poll.get_polls().keys()
    elif len(mentions) == 0 and not len(ctx.message.channel_mentions):
        check_condition = lambda m: m.id not in poll.get_polls().keys()
    else:
        await ctx.send(get_translation("You should mention ONLY members or roles of this server!"))
        return
    delete_limit = Config.get_settings().bot_settings.deletion_messages_limit_without_poll + 1

    if subcommand is None:
        if count > 0:
            lim = count if count < delete_limit else delete_limit + 1
            if delete_limit == 0 or len([m async for m in ctx.channel.history(limit=lim)]) <= delete_limit:
                await ctx.message.delete()
                await clear_with_big_limit(ctx, count=count, check_condition=check_condition)
                return
        elif count < 0:
            message_created = await get_last_element_of_async_iterator(
                ctx.channel.history(limit=-count, oldest_first=True)
            )
            if delete_limit == 0 or len([m async for m in ctx.channel.history(limit=delete_limit + 1,
                                                                              after=message_created,
                                                                              oldest_first=True)]) <= delete_limit:
                await ctx.message.delete()
                await clear_with_none_limit(ctx, check_condition=check_condition, after_message=message_created)
                return
        else:
            await send_msg(ctx, get_translation("Nothing's done!"), is_reaction=True)
            return
    elif subcommand == "all":
        if delete_limit == 0 or len([m async for m in ctx.channel.history(limit=delete_limit + 1)]) <= delete_limit:
            await ctx.message.delete()
            await clear_with_none_limit(ctx, check_condition=check_condition)
            return
    elif subcommand == "reply":
        message_created = ctx.message.reference.resolved
        if delete_limit == 0 or len([m async for m in ctx.channel.history(limit=delete_limit + 1,
                                                                          after=message_created,
                                                                          oldest_first=True)]) <= delete_limit:
            await ctx.message.delete()
            await clear_with_none_limit(ctx, check_condition=check_condition, after_message=message_created)
            return
    if await poll.timer(ctx, ctx.author, 5, "clear"):
        if ctx.channel in [p.channel for p in poll.get_polls().values() if p.command == "clear"]:
            await delete_after_by_msg(ctx.message)
            await ctx.send(get_translation("{0}, bot already has poll on `clear` command for this channel!")
                           .format(ctx.author.mention),
                           delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
            return
        if await poll.run(channel=ctx.channel,
                          message=get_translation(
                              "this man {0} trying to delete some history of this channel. Will you let that happen?"
                          ).format(ctx.author.mention),
                          command="clear",
                          remove_logs_after=5):
            if subcommand == "all" or subcommand == "reply" or count < 0:
                await ctx.message.delete()
                await clear_with_none_limit(ctx, check_condition=check_condition, after_message=message_created)
            else:
                await ctx.message.delete()
                await clear_with_big_limit(ctx, count=count, check_condition=check_condition)
    else:
        await delete_after_by_msg(ctx.message)


async def clear_with_big_limit(ctx: commands.Context, count: int, check_condition):
    last_undeleted_message = None
    ranges_to_delete = [100 for _ in range(count // 100)] + [count % 100]
    ranges_to_delete_length = len(ranges_to_delete)
    for i in range(ranges_to_delete_length):
        if ranges_to_delete_length > i + 1:
            last_undeleted_message = await get_last_element_of_async_iterator(
                ctx.channel.history(limit=ranges_to_delete[i], before=last_undeleted_message)
            )
        await ctx.channel.purge(limit=ranges_to_delete[i], check=check_condition, before=last_undeleted_message)


async def clear_with_none_limit(ctx: commands.Context, check_condition, after_message: Message = None):
    last_undeleted_message = None
    while True:
        limited_messages = [m async for m in ctx.channel.history(before=last_undeleted_message)]
        await ctx.channel.purge(check=check_condition, before=last_undeleted_message, after=after_message)
        if (after_message is not None and after_message in limited_messages) or len(limited_messages) == 0:
            return
        last_undeleted_message = limited_messages[-1]


async def bot_dm_clear(ctx: commands.Context, bot: commands.Bot, subcommand: str = None, count: int = None):
    message_created = None
    if count is not None:
        count += 1
    if subcommand is None:
        if count < 0:
            message_created = await get_last_element_of_async_iterator(
                ctx.channel.history(limit=-count, oldest_first=True)
            )
        elif count == 0:
            await send_msg(ctx, get_translation("Nothing's done!"), is_reaction=True)
            return
    elif subcommand == "reply":
        message_created = ctx.message.reference.resolved

    async for msg in ctx.channel.history(limit=count, after=message_created):
        if msg.author == bot.user and msg.type == MessageType.default:
            await msg.delete()


async def bot_backup(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        is_reaction=False
):
    bot_message = (get_translation("Automatic backups enabled") if Config.get_backups_settings()
                   .automatic_backup else get_translation("Automatic backups disabled")) + "\n"
    bot_message += get_translation("Automatic backups period set to {0} min").format(Config.get_backups_settings()
                                                                                     .period_of_automatic_backups)
    if Config.get_backups_settings().max_backups_limit_for_server is not None:
        bot_message += "\n" + get_translation("Max backups' count limit for server - {0}") \
            .format(Config.get_backups_settings().max_backups_limit_for_server)
    if Config.get_backups_settings().size_limit is not None:
        bot_message += "\n" + get_translation("Max backups' size limit for server - {0}") \
            .format(get_human_readable_size(Config.get_backups_settings().size_limit))
    bot_message += "\n" + get_translation("Current compression method - {0}").format(Config.get_backups_settings()
                                                                                     .compression_method) + "\n\n"

    bc_free_bytes, bc_used_bytes = calculate_space_for_current_server()
    bot_message += get_translation(
        "Backups folder info for '{0}' server:"
    ).format(Config.get_selected_server_from_list().server_name) + "\n" + \
                   get_translation("Used - {0}").format(get_human_readable_size(bc_used_bytes)) + "\n" + \
                   get_translation("Free - {0}").format(get_human_readable_size(bc_free_bytes))
    average_backup_size = get_average_backup_size()
    max_backups = None
    if average_backup_size != 0:
        max_backups = bc_free_bytes // average_backup_size
    if Config.get_backups_settings().max_backups_limit_for_server is not None:
        if max_backups is None or (max_backups + len(Config.get_server_config().backups)) > Config \
                .get_backups_settings().max_backups_limit_for_server:
            max_backups = Config.get_backups_settings().max_backups_limit_for_server - \
                          len(Config.get_server_config().backups)
    bot_message += "\n" + get_translation("Stored backups count - {0}").format(len(Config.get_server_config().backups))
    bot_message += "\n" + get_translation("Approximate remaining backups count - {0}") \
        .format(max_backups if max_backups is not None else "∞")

    if len(Config.get_server_config().backups) > 0:
        backup = Config.get_server_config().backups[-1]
        bot_message += "\n\n" + get_translation("Last backup: ") + \
                       backup.file_creation_date.strftime(get_translation("%H:%M:%S %d/%m/%Y"))
        bot_message += "\n" + get_translation("Backup size: ") + \
                       get_human_readable_size(get_file_size(Config.get_selected_server_from_list().working_directory,
                                                             Config.get_backups_settings().name_of_the_backups_folder,
                                                             f"{backup.file_name}.zip"))
        if backup.reason is None and backup.initiator is None:
            bot_message += "\n" + get_translation("Reason: ") + get_translation("Automatic backup")
        else:
            bot_message += "\n" + get_translation("Reason: ") + \
                           (backup.reason if backup.reason else get_translation("Not stated"))
            bot_message += "\n" + get_translation("Initiator: ") + await get_member_string(bot, backup.initiator)
        if backup.restored_from:
            bot_message += "\n" + get_translation("The world of the server was restored from this backup")
    await send_msg(ctx, add_quotes(bot_message), is_reaction=is_reaction)


async def bot_associate(
        ctx: commands.Context,
        bot: commands.Bot,
        discord_mention: Member,
        assoc_command: str,
        minecraft_nick: str
):
    need_to_save = False

    if "☠ " in minecraft_nick and \
            check_if_string_in_all_translations(translate_text="☠ Obituary ☠", match_text=minecraft_nick):
        await ctx.send(get_translation("{0}, you don't have permission to control fates! "
                                       "Not in this life at least...").format(discord_mention.mention))
        return

    if assoc_command == "add":
        if minecraft_nick in [u.user_minecraft_nick for u in Config.get_known_users_list()]:
            associated_member = [u.user_discord_id for u in Config.get_known_users_list()
                                 if u.user_minecraft_nick == minecraft_nick][0]
            associated_member = await bot.guilds[0].fetch_member(associated_member)
            await ctx.send(get_translation("This nick is already associated with member {0}.")
                           .format(associated_member.mention))
        else:
            need_to_save = True
            Config.add_to_known_users_list(minecraft_nick, discord_mention.id)
            await ctx.send(get_translation("Now {0} associates with nick `{1}` in Minecraft.")
                           .format(discord_mention.mention, minecraft_nick))
    elif assoc_command == "remove":
        if minecraft_nick in [u.user_minecraft_nick for u in Config.get_known_users_list()] and \
                discord_mention.id in [u.user_discord_id for u in Config.get_known_users_list()]:
            need_to_save = True
            Config.remove_from_known_users_list(minecraft_nick, discord_mention.id)
            await ctx.send(get_translation("Now link {0} -> `{1}` do not exist!")
                           .format(discord_mention.mention, minecraft_nick))
        else:
            await ctx.send(get_translation("Bot don't have `mention to nick` link already!"))
    if need_to_save:
        Config.save_config()


async def bot_associate_info(ctx: commands.Context, for_me: bool, show: str = None):
    if show is not None:
        message = get_translation("{0}, bot has this data on nicks and number of remaining uses:") \
                      .format(ctx.author.mention) + "\n```"
    else:
        message = get_translation("{0}, bot has this data on nicks:").format(ctx.author.mention) + "\n```"

    if for_me:
        if ctx.author.id not in [u.user_discord_id for u in Config.get_known_users_list()]:
            return get_translation("{0}, you have no bound nicks").format(ctx.author.mention)

        user_nicks = [u.user_minecraft_nick for u in Config.get_known_users_list()
                      if u.user_discord_id == ctx.author.id]
        user_players_data = {}

        if show is not None:
            for m_nick in user_nicks:
                for p in Config.get_seen_players_list():
                    if p.player_minecraft_nick == m_nick:
                        user_players_data.update({p.player_minecraft_nick: p.number_of_times_to_op})
                        user_nicks.remove(m_nick)
        if show is None or show == "all":
            user_players_data.update({n: -1 for n in user_nicks})

        for k, v in user_players_data.items():
            if show is not None:
                message += f"- {k}: {str(v) if v >= 0 else get_translation('not seen on server')}\n"
            else:
                message += f"- {k}\n"
    else:
        users_to_nicks = {}
        for user in Config.get_known_users_list():
            if users_to_nicks.get(user.user_discord_id, None) is None:
                users_to_nicks.update({user.user_discord_id: []})
            users_to_nicks[user.user_discord_id].append(user.user_minecraft_nick)

        if show is not None:
            for user_id in users_to_nicks.keys():
                for p in Config.get_seen_players_list():
                    if p.player_minecraft_nick in users_to_nicks[user_id]:
                        users_to_nicks[user_id].remove(p.player_minecraft_nick)
                        users_to_nicks[user_id].append({p.player_minecraft_nick: p.number_of_times_to_op})

        for k, v in users_to_nicks.items():
            if not len(v) or (show is not None and show == "seen" and all([isinstance(i, str) for i in v])):
                continue
            member = await ctx.guild.fetch_member(k)
            message += f"{member.display_name}#{member.discriminator}:\n"
            for item in v:
                if show is None:
                    message += f"- {item}\n"
                elif show == "all" and isinstance(item, str):
                    message += f"- {item}: " + get_translation("not seen on server") + "\n"
                elif isinstance(item, dict):
                    message += f"- {list(item.items())[0][0]}: {str(list(item.items())[0][1])}\n"

    if message[-3:] == "```":
        message += "-----"
    message += "```"
    return message


def bot_shutdown_info(with_timeout=False, only_timeout=False):
    msg = get_translation("Task: ") + "\"" + get_translation("Shutdown of Minecraft server when idle") + "\""
    if not only_timeout:
        msg += "\n" + get_translation("State: ")
        if Config.get_settings().bot_settings.auto_shutdown:
            msg += get_translation("Active")
        else:
            msg += get_translation("Disabled")
    if with_timeout:
        msg += "\n" + get_translation("Timeout: {0} sec") \
            .format(Config.get_timeouts_settings().await_seconds_before_shutdown)
        if Config.get_timeouts_settings().calc_before_shutdown > 59 or \
                Config.get_timeouts_settings().await_seconds_before_shutdown % \
                Config.get_timeouts_settings().await_seconds_in_check_ups != 0:
            msg += " (" + (f"~ " if Config.get_timeouts_settings().await_seconds_before_shutdown %
                                    Config.get_timeouts_settings().await_seconds_in_check_ups != 0 else "") + \
                   f"{get_time_string(Config.get_timeouts_settings().calc_before_shutdown)})"
        if Config.get_timeouts_settings().calc_before_shutdown == 0:
            msg += "\n" + get_translation("Server will be stopped immediately.").rstrip(".")
    return msg


def bot_forceload_info():
    msg = get_translation("Task: ") + "\"" + get_translation("Autoload if server crashes") + \
          "\"\n" + get_translation("State: ")
    if Config.get_settings().bot_settings.forceload:
        msg += get_translation("Active")
    else:
        msg += get_translation("Disabled")
    return msg
