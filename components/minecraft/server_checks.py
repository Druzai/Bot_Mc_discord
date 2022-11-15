import socket
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from discord import (
    Activity, ActivityType, ChannelType
)
from discord.ext import commands
from discord.utils import get as utils_get

from components.backups import BackupsThread
from components.error_handlers import _ignore_some_tasks_errors
from components.localization import get_translation
from components.minecraft.connect import get_server_players, get_server_version
from components.minecraft.server_management import stop_server, start_server
from components.utils import get_list_of_processes, get_time_string, send_msg, add_quotes
from components.logs.utils import create_watcher
from config.init_config import Config, BotVars

if TYPE_CHECKING:
    from cogs.poll_cog import Poll


async def server_checkups(bot: commands.Bot, backups_thread: BackupsThread, poll: 'Poll'):
    java_processes = get_list_of_processes()
    try:
        info = get_server_players()
        if len(java_processes) == 0:
            raise ConnectionError()
        if info.get("current") != 0:
            to_save = False
            BotVars.players_login_dict = {k: v for k, v in BotVars.players_login_dict.items()
                                          if k in info.get("players")}
            for player in info.get("players"):
                if player not in [i.player_minecraft_nick for i in Config.get_server_config().seen_players]:
                    Config.add_to_seen_players_list(player)
                    to_save = True
                BotVars.add_player_login(player)
            if to_save:
                Config.save_server_config()
            if BotVars.is_auto_backup_disable:
                BotVars.is_auto_backup_disable = False
        if not BotVars.is_server_on:
            BotVars.is_server_on = True
        if Config.get_game_chat_settings().enable_game_chat or \
                Config.get_secure_auth().enable_secure_auth:
            if BotVars.watcher_of_log_file is None:
                BotVars.watcher_of_log_file = create_watcher(BotVars.watcher_of_log_file, get_server_version())
            BotVars.watcher_of_log_file.start()
        if not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting:
            task = bot.loop.create_task(bot.change_presence(
                activity=Activity(type=ActivityType.playing,
                                  name=Config.get_settings().bot_settings.gaming_status +
                                       ", " + str(info.get("current")) + get_translation(" player(s) online"))
            ))
            task.add_done_callback(_ignore_some_tasks_errors)
            if Config.get_settings().bot_settings.auto_shutdown:
                if info.get("current") == 0 and BotVars.auto_shutdown_start_date is None:
                    BotVars.auto_shutdown_start_date = \
                        datetime.now() + timedelta(seconds=Config.get_timeouts_settings().calc_before_shutdown)
                elif info.get("current") != 0 and BotVars.auto_shutdown_start_date is not None:
                    BotVars.auto_shutdown_start_date = None
                elif info.get("current") == 0 and BotVars.auto_shutdown_start_date <= datetime.now():
                    channel = bot.guilds[0].get_channel(Config.get_settings().bot_settings.commands_channel_id)
                    if channel is None:
                        channel = utils_get(bot.guilds[0].channels, type=ChannelType.text)
                    print(get_translation("Bot detected: Server is idle for {0} "
                                          "without players! Stopping server now!")
                          .format(get_time_string(Config.get_timeouts_settings().calc_before_shutdown)))
                    await send_msg(ctx=channel,
                                   msg=add_quotes(get_translation(
                                       "Bot detected: Server is idle for "
                                       "{0} without players!\n"
                                       "Time: {1}\n"
                                       "Shutting down server now!"
                                   ).format(get_time_string(Config.get_timeouts_settings().calc_before_shutdown),
                                            datetime.now().strftime(get_translation("%H:%M:%S %d/%m/%Y")))),
                                   is_reaction=True)
                    await stop_server(ctx=channel, bot=bot, poll=poll, shut_up=True)
    except (ConnectionError, socket.error):
        if len(java_processes) == 0:
            if BotVars.is_server_on:
                BotVars.is_server_on = False
                print(get_translation("Server unexpectedly stopped!"))
                Config.get_server_config().states.stopped_info.set_state_info(None, datetime.now())
                Config.save_server_config()
            if BotVars.watcher_of_log_file is not None and BotVars.watcher_of_log_file.is_running():
                BotVars.watcher_of_log_file.stop()
        if not BotVars.is_loading and not BotVars.is_stopping and not BotVars.is_restarting:
            task = bot.loop.create_task(
                bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                      name=Config.get_settings().bot_settings.idle_status +
                                                           (" 🤔" if len(java_processes) != 0 else ""))))
            task.add_done_callback(_ignore_some_tasks_errors)
        if Config.get_settings().bot_settings.forceload and not BotVars.is_stopping \
                and not BotVars.is_loading and not BotVars.is_restarting:
            channel = bot.guilds[0].get_channel(Config.get_settings().bot_settings.commands_channel_id)
            if channel is None:
                channel = utils_get(bot.guilds[0].channels, type=ChannelType.text)
            print(get_translation("Bot detected: Server offline! Starting up server again!"))
            await send_msg(ctx=channel,
                           msg=add_quotes(get_translation(
                               "Bot detected: Server offline!\n"
                               "Time: {0}\n"
                               "Starting up server again!"
                           ).format(datetime.now().strftime(get_translation("%H:%M:%S %d/%m/%Y")))),
                           is_reaction=True)
            await start_server(ctx=channel, bot=bot, backups_thread=backups_thread, shut_up=True)
    if Config.get_secure_auth().enable_secure_auth:
        check_if_ips_expired()


def check_if_ips_expired():
    removed = False
    remove_empty_nicks = []
    remove_old_ips = {}
    for user in Config.get_auth_users():
        if len(user.ip_addresses) == 0:
            remove_empty_nicks.append(user)
            continue
        for ip in user.ip_addresses:
            if ip.expires_on_date is not None and (datetime.now() - ip.expires_on_date).days >= \
                    Config.get_secure_auth().days_before_ip_will_be_deleted:
                if remove_old_ips.get(user.nick, None) is None:
                    remove_old_ips[user.nick] = []
                remove_old_ips[user.nick].append(ip)
    if len(remove_empty_nicks) > 0:
        for user in remove_empty_nicks:
            Config.get_auth_users().remove(user)
        removed = True
    if len(remove_old_ips.keys()) > 0:
        for i in range(len(Config.get_auth_users())):
            if remove_old_ips.get(Config.get_auth_users()[i].nick, None) is None:
                continue
            for address in remove_old_ips[Config.get_auth_users()[i].nick]:
                Config.get_auth_users()[i].ip_addresses.remove(address)
        removed = True
    if removed:
        Config.save_auth_users()
