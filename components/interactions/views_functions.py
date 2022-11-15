from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from discord import SelectOption, Interaction
from discord.ext import commands

from components.backups import handle_backups_limit_and_size, warn_about_auto_backups, BackupsThread, create_zip_archive
from components.constants import DISCORD_SELECT_FIELD_MAX_LENGTH
from components.interactions.data import SelectChoice
from components.localization import get_translation, set_locale
from components.utils import (
    send_msg, shorten_string, get_member_string, send_interaction, add_quotes, send_status, get_author,
    delete_after_by_msg
)
from config.init_config import Config, BotVars, ServerProperties


async def on_backups_select_option(i: int, bot: commands.Bot):
    backup = Config.get_server_config().backups[i]

    if backup.reason is None and backup.initiator is None:
        description_str = shorten_string(get_translation("Reason: ") + get_translation("Automatic backup"),
                                         DISCORD_SELECT_FIELD_MAX_LENGTH)
    else:
        if backup.reason:
            description_str = shorten_string(await get_member_string(bot, backup.initiator) + f" ({backup.reason}",
                                             DISCORD_SELECT_FIELD_MAX_LENGTH - 1) + ")"
        else:
            description_str = shorten_string(await get_member_string(bot, backup.initiator),
                                             DISCORD_SELECT_FIELD_MAX_LENGTH)

    return SelectOption(
        label=shorten_string(
            get_translation("Backup from") + " " +
            backup.file_creation_date.strftime(
                get_translation("%H:%M:%S %d/%m/%Y")
            ),
            DISCORD_SELECT_FIELD_MAX_LENGTH
        ),
        value=backup.file_name,
        description=description_str
    )


async def on_server_select_callback(
        interaction: Interaction,
        ctx: Optional[commands.Context] = None,
        is_reaction: bool = False
):
    selected_server = int(interaction.data.get("values", [None])[0])

    if BotVars.is_server_on or BotVars.is_loading or BotVars.is_stopping or BotVars.is_restarting:
        await send_interaction(
            interaction,
            add_quotes(get_translation("You can't change server, while some instance is still running\n"
                                       "Please stop it, before trying again")),
            ctx=ctx,
            is_reaction=True
        )
        return SelectChoice.DO_NOTHING

    if BotVars.watcher_of_log_file is not None:
        BotVars.watcher_of_log_file.stop()
        BotVars.watcher_of_log_file = None
    Config.get_settings().selected_server_number = selected_server + 1
    Config.save_config()
    await send_interaction(
        interaction,
        add_quotes(get_translation("Selected server") + ": " +
                   Config.get_selected_server_from_list().server_name +
                   f" [{str(Config.get_settings().selected_server_number)}]"),
        ctx=ctx,
        is_reaction=is_reaction
    )
    print(get_translation("Selected server") + f" - '{Config.get_selected_server_from_list().server_name}'")
    Config.read_server_info()
    await send_interaction(
        interaction,
        add_quotes(get_translation("Server properties read!")),
        ctx=ctx,
        is_reaction=is_reaction
    )
    print(get_translation("Server info read!"))
    return SelectChoice.STOP_VIEW


async def backup_force_checking(
        ctx: Union[commands.Context, Interaction],
        bot: commands.Bot
) -> bool:
    if not BotVars.is_loading and not BotVars.is_stopping and \
            not BotVars.is_restarting and not BotVars.is_restoring and not BotVars.is_backing_up:
        b_reason = handle_backups_limit_and_size(bot)
        if b_reason:
            await ctx.send(add_quotes(get_translation("Can't create backup because of {0}\n"
                                                      "Delete some backups to proceed!").format(b_reason)))
            return False
        await warn_about_auto_backups(ctx, bot)
        return True
    else:
        await send_status(ctx)
        return False


async def on_backup_force_callback(
        ctx: Union[commands.Context, Interaction],
        bot: commands.Bot,
        backups_thread: BackupsThread,
        reason: Optional[str] = None,
        is_reaction: bool = False
):
    author = get_author(ctx, bot, is_reaction=is_reaction)
    print(get_translation("Starting backup triggered by {0}").format(f"{author.display_name}#{author.discriminator}"))
    msg = await send_msg(ctx, add_quotes(get_translation("Starting backup...")))
    file_name = datetime.now().strftime("%d-%m-%Y-%H-%M-%S")
    list_obj = None
    level_name = ServerProperties().level_name
    try:
        for obj in create_zip_archive(bot, file_name,
                                      Path(Config.get_selected_server_from_list().working_directory,
                                           Config.get_backups_settings().name_of_the_backups_folder).as_posix(),
                                      Path(Config.get_selected_server_from_list().working_directory,
                                           level_name).as_posix(),
                                      Config.get_backups_settings().compression_method, forced=True,
                                      user=author):
            if isinstance(obj, str):
                if msg is not None:
                    await msg.edit(content=obj)
                else:
                    msg = await send_msg(ctx, obj)
            elif isinstance(obj, list):
                list_obj = obj
        Config.add_backup_info(file_name=file_name, reason=reason, initiator=author.id)
        Config.save_server_config()
        backups_thread.skip()
        if is_reaction:
            await delete_after_by_msg(msg, ctx)
        print(get_translation("Backup completed!"))
        if isinstance(list_obj, list):
            await send_msg(ctx, add_quotes(get_translation("Bot couldn't archive some files to this backup!")),
                           is_reaction=is_reaction)
            print(get_translation("Bot couldn't archive some files to this backup, they located in path '{0}'")
                  .format(Path(Config.get_selected_server_from_list().working_directory,
                               ServerProperties().level_name).as_posix()))
            print(get_translation("List of these files:"))
            print(", ".join(list_obj))
    except FileNotFoundError:
        exception_reason = add_quotes(get_translation("Backup cancelled!") + "\n" +
                                      get_translation("The world folder '{0}' doesn't exist or is empty!")
                                      .format(level_name))
        if msg is not None:
            await msg.edit(content=exception_reason)
            await delete_after_by_msg(msg, ctx)
        else:
            await send_msg(ctx, exception_reason, is_reaction=is_reaction)
        print(get_translation("The world folder in path '{0}' doesn't exist or is empty!")
              .format(Path(Config.get_selected_server_from_list().working_directory, level_name).as_posix()))
        print(get_translation("Backup cancelled!"))


async def backup_restore_checking(ctx: Union[commands.Context, Interaction], is_reaction: bool = False) -> bool:
    if len(Config.get_server_config().backups) == 0:
        await send_msg(ctx,
                       add_quotes(get_translation("There are no backups for '{0}' server!")
                                  .format(Config.get_selected_server_from_list().server_name)),
                       is_reaction=is_reaction)
        return False

    if not BotVars.is_server_on and not BotVars.is_loading and not BotVars.is_stopping and \
            not BotVars.is_restarting and not BotVars.is_backing_up and not BotVars.is_restoring:
        return True
    else:
        await send_status(ctx, is_reaction=is_reaction)
        return False


async def on_language_select_callback(
        interaction: Optional[Interaction],
        set_language: Optional[str],
        ctx: Optional[commands.Context] = None,
        is_reaction: bool = False
):
    new_language = interaction.data.get("values", [None])[0] if interaction is not None else set_language

    if not set_locale(new_language):
        msg = add_quotes(get_translation("Bot doesn't have this language!\n"
                                         "Check list of available languages via {0}language")
                         .format(Config.get_settings().bot_settings.prefix))
        await send_interaction(interaction, msg, ctx=ctx, is_reaction=is_reaction)
        return SelectChoice.DO_NOTHING
    else:
        Config.get_settings().bot_settings.language = new_language.lower()
        Config.save_config()
        await send_interaction(
            interaction,
            add_quotes(get_translation("Language switched successfully!")),
            ctx=ctx,
            is_reaction=is_reaction
        )
        return SelectChoice.STOP_VIEW
