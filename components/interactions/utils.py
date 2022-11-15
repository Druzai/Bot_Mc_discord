from os import remove
from pathlib import Path
from typing import List, Callable, Awaitable
from typing import Optional, Union, TYPE_CHECKING

from discord import SelectOption, Interaction
from discord.ext import commands
from psutil import disk_usage

from components.backups import (
    BackupsThread, restore_from_zip_archive,
    send_message_of_deleted_backup
)
from components.decorators import is_minecrafter
from components.interactions.data import SelectChoice
from components.interactions.views_functions import on_backups_select_option
from components.localization import get_translation
from components.utils import (
    send_msg, get_member_string, send_interaction, add_quotes, get_author, delete_after_by_msg, get_folder_size,
    get_archive_uncompressed_size, get_human_readable_size, get_half_members_count_with_role
)
from config.init_config import Config, ServerProperties

if TYPE_CHECKING:
    from cogs.poll_cog import Poll


async def send_select_view(
        ctx: Union[commands.Context, Interaction],
        raw_options: List,
        pivot_index: Optional[int],
        make_select_option: Callable[[int, Optional[commands.Bot]], Awaitable[SelectOption]],
        on_callback: Callable[[Optional[Interaction]], Awaitable[SelectChoice]],
        on_interaction_check: Optional[Callable[[Interaction], bool]] = None,
        message: Optional[str] = None,
        min_values: int = 1,
        max_values: int = 1,
        bot: Optional[commands.Bot] = None,
        timeout: Optional[int] = 180.0
):
    from components.interactions.views import SelectView

    view = SelectView(
        raw_options,
        pivot_index,
        make_select_option,
        ctx=ctx if isinstance(ctx, commands.Context) else None,
        min_values=min_values,
        max_values=max_values,
        bot=bot,
        timeout=timeout
    )
    await view.update_view(send=False)

    if on_interaction_check is not None:
        async def interaction_check(interaction: Interaction):
            return on_interaction_check(interaction)

        view.interaction_check = interaction_check

    assert view is not None
    msg = await send_msg(ctx, message, view)

    async def on_timeout():
        view.stop()
        await msg.delete()

    view.on_timeout = on_timeout

    async def callback(interaction: Interaction):
        choice = await on_callback(interaction)
        if choice == SelectChoice.STOP_VIEW:
            view.stop()
            view.on_timeout = lambda: None
        elif choice == SelectChoice.DELETE_SELECT:
            view.stop()
            await msg.delete()

    view.v_select.callback = callback


async def send_backup_remove_select(
        ctx: Union[commands.Context, Interaction],
        bot: commands.Bot,
        IndPoll: 'Poll',
        backups_thread: BackupsThread,
        is_reaction: bool = False
):
    if len(Config.get_server_config().backups) == 0:
        await send_msg(ctx,
                       add_quotes(get_translation("There are no backups for '{0}' server!")
                                  .format(Config.get_selected_server_from_list().server_name)),
                       is_reaction=is_reaction)
        return

    author = get_author(ctx, bot, is_reaction=is_reaction)

    async def on_callback(interaction: Interaction):
        backup_name = interaction.data.get("values", [""])[0]

        for backup in Config.get_server_config().backups:
            if backup.file_name == backup_name:
                selected_backup = backup
                break
        else:
            await send_msg(
                ctx if isinstance(ctx, commands.Context) else interaction,
                add_quotes(get_translation("Bot couldn't find backup by provided date '{0}'")
                           .format(backup_name.strftime(get_translation("%H:%M:%S %d/%m/%Y")))),
                is_reaction=is_reaction
            )
            return SelectChoice.DELETE_SELECT

        if selected_backup.initiator is not None:
            if "backup_remove" in [p.command for p in IndPoll.get_polls().values()]:
                if isinstance(ctx, commands.Context):
                    await delete_after_by_msg(ctx.message, ctx)
                await send_msg(
                    ctx if isinstance(ctx, commands.Context) else interaction,
                    get_translation("{0}, bot already has poll on `backup remove` command!").format(author.mention),
                    is_reaction=True
                )
                return SelectChoice.DELETE_SELECT

            if await IndPoll.timer(ctx, get_author(ctx, bot, is_reaction), 5, "backup_remove"):
                member = await get_member_string(bot, selected_backup.initiator)
                if not await IndPoll.run(
                        channel=ctx.channel,
                        message=get_translation(
                            "this man {0} trying to delete backup dated `{1}` made by {2} of `{3}` "
                            "server. Will you let that happen?"
                        ).format(
                            author.mention,
                            selected_backup.file_creation_date.strftime(get_translation("%H:%M:%S %d/%m/%Y")),
                            member,
                            Config.get_selected_server_from_list().server_name
                        ),
                        command="backup_remove",
                        needed_role=Config.get_settings().bot_settings.managing_commands_role_id,
                        need_for_voting=get_half_members_count_with_role(
                            ctx.channel,
                            Config.get_settings().bot_settings.managing_commands_role_id
                        ),
                        remove_logs_after=5
                ):
                    return SelectChoice.DELETE_SELECT
            else:
                if isinstance(ctx, commands.Context):
                    await delete_after_by_msg(ctx.message, ctx)
                return SelectChoice.DELETE_SELECT

        remove(Path(Config.get_selected_server_from_list().working_directory,
                    Config.get_backups_settings().name_of_the_backups_folder, f"{selected_backup.file_name}.zip"))
        send_message_of_deleted_backup(
            bot,
            f"{author.display_name}#{author.discriminator}",
            selected_backup,
            member_name=await get_member_string(bot, selected_backup.initiator)
        )
        Config.get_server_config().backups.remove(selected_backup)
        Config.save_server_config()
        backups_thread.skip()
        await send_interaction(
            interaction,
            add_quotes(get_translation(
                "Deleted backup dated {0} of '{1}' server"
            ).format(selected_backup.file_creation_date.strftime(get_translation("%H:%M:%S %d/%m/%Y")),
                     Config.get_selected_server_from_list().server_name)),
            ctx=ctx if isinstance(ctx, commands.Context) else None,
            is_reaction=is_reaction
        )
        return SelectChoice.DELETE_SELECT if is_reaction else SelectChoice.STOP_VIEW

    await send_select_view(
        ctx=ctx,
        raw_options=Config.get_server_config().backups,
        pivot_index=None,
        make_select_option=on_backups_select_option,
        on_callback=on_callback,
        on_interaction_check=is_minecrafter,
        message=get_translation("Select backup:"),
        bot=bot,
        timeout=180
    )


async def send_backup_restore_select(
        ctx: Union[commands.Context, Interaction],
        bot: commands.Bot,
        backups_thread: BackupsThread,
        is_reaction: bool = False
):
    async def on_callback(interaction: Interaction):
        backup_name = interaction.data.get("values", [""])[0]

        for i in range(len(Config.get_server_config().backups)):
            if Config.get_server_config().backups[i].file_name == backup_name:
                backup_number = i
                break
        else:
            await send_msg(
                ctx if isinstance(ctx, commands.Context) else interaction,
                add_quotes(get_translation("Bot couldn't find backup by provided date '{0}'")
                           .format(backup_name.strftime(get_translation("%H:%M:%S %d/%m/%Y")))),
                is_reaction=is_reaction
            )
            return SelectChoice.DELETE_SELECT

        level_name = ServerProperties().level_name
        free_space = disk_usage(Config.get_selected_server_from_list().working_directory).free
        bc_folder_bytes = get_folder_size(Config.get_selected_server_from_list().working_directory,
                                          level_name)
        uncompressed_size = get_archive_uncompressed_size(
            Config.get_selected_server_from_list().working_directory,
            Config.get_backups_settings().name_of_the_backups_folder,
            f"{backup_name}.zip"
        )
        if free_space + bc_folder_bytes <= uncompressed_size:
            await send_msg(
                ctx if isinstance(ctx, commands.Context) else interaction,
                add_quotes(get_translation("There are not enough space on disk to restore from backup!"
                                           "\nFree - {0}\nRequired at least - {1}"
                                           "\nDelete some backups to proceed!")
                           .format(get_human_readable_size(free_space + bc_folder_bytes),
                                   get_human_readable_size(uncompressed_size))),
                is_reaction=is_reaction
            )
            return SelectChoice.DELETE_SELECT
        await send_interaction(
            interaction,
            add_quotes(get_translation("Starting restore from backup...")),
            ctx=ctx if isinstance(ctx, commands.Context) else None,
            is_reaction=is_reaction
        )
        restore_from_zip_archive(
            backup_name,
            Path(
                Config.get_selected_server_from_list().working_directory,
                Config.get_backups_settings().name_of_the_backups_folder
            ).as_posix(),
            Path(Config.get_selected_server_from_list().working_directory, level_name).as_posix()
        )
        for backup in Config.get_server_config().backups:
            if backup.restored_from:
                backup.restored_from = False
        Config.get_server_config().backups[backup_number].restored_from = True
        Config.save_server_config()
        backups_thread.skip()
        await send_interaction(
            interaction,
            add_quotes(get_translation("Done!")),
            ctx=ctx if isinstance(ctx, commands.Context) else None,
            is_reaction=is_reaction
        )
        return SelectChoice.DELETE_SELECT if is_reaction else SelectChoice.STOP_VIEW

    await send_select_view(
        ctx=ctx,
        raw_options=Config.get_server_config().backups,
        pivot_index=None,
        make_select_option=on_backups_select_option,
        on_callback=on_callback,
        on_interaction_check=is_minecrafter,
        message=get_translation("Select backup:"),
        bot=bot,
        timeout=180
    )
