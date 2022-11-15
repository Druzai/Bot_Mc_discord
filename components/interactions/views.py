import socket
from contextlib import suppress
from typing import List, Optional, Union, TYPE_CHECKING, Callable, Awaitable, Any

from discord import (
    Message, TextChannel, VoiceChannel, Thread as ChannelThread, GroupChannel, SelectOption,
    Interaction, ButtonStyle, TextStyle
)
from discord.ext import commands
from discord.ui import View, Select, Item, Button, button, Modal, TextInput
from discord.utils import MISSING

from cogs.functions.server import (
    bot_forceload_info, bot_shutdown_info, bot_restart, bot_stop, bot_start, bot_backup, bot_list, bot_status
)
from components.backups import warn_about_auto_backups
from components.constants import DISCORD_SELECT_OPTIONS_MAX_LENGTH, DISCORD_SELECT_FIELD_MAX_LENGTH
from components.decorators import is_admin, is_minecrafter
from components.discord_set_up import create_webhooks
from components.error_handlers import handle_rcon_error, send_error_on_interaction
from components.interactions.utils import send_backup_restore_select, send_backup_remove_select
from components.interactions.views_functions import (
    on_language_select_callback, on_server_select_callback, backup_restore_checking, on_backup_force_callback,
    backup_force_checking
)
from components.localization import get_translation, get_locales, get_current_locale
from components.logs.utils import create_watcher
from components.minecraft.connect import get_server_version, connect_rcon
from components.utils import (
    edit_interaction, add_quotes, send_interaction, shorten_string, get_message_and_channel
)
from config.init_config import Config, BotVars, ServerProperties

if TYPE_CHECKING:
    from cogs.minecraft_cog import MinecraftCommands
    from cogs.chat_cog import ChatCommands


class TemplateSelectView(View):
    def __init__(
            self,
            options_raw: List,
            namespace: str = "template_select_view",
            name: str = "TemplateSelectView",
            ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, None] = None,
            raw_content: Optional[str] = None,
            message_id: Optional[int] = None,
            channel_id: Optional[int] = None,
            message: Optional[Message] = None,
            min_values: int = 1,
            max_values: int = 1,
            start_row: int = 0,
            is_reaction: bool = False,
            timeout: Optional[float] = None
    ):
        super().__init__(timeout=timeout)
        self.namespace = namespace
        self.name = name
        self.ctx = ctx
        self.message_id = message_id
        self.channel_id = channel_id
        self.message = message
        self.raw_content = raw_content
        self.select_page: int = -1
        self.options_list_raw = options_raw
        self.options_list_length = len(options_raw)
        if start_row > 3:
            raise RuntimeError("'start_row' more than 3!")
        self.is_reaction = is_reaction
        self.controls_removed = False

        # Creating Select and buttons

        self.v_select = Select(
            custom_id=f"{namespace}:select",
            min_values=min_values,
            max_values=max_values,
            row=start_row
        )
        self.v_select.callback = self.v_select_callback
        self.add_item(self.v_select)

        self.v_start = Button(
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_start",
            emoji="⏮",
            row=start_row + 1
        )
        self.v_start.callback = self.v_start_callback
        self.add_item(self.v_start)

        self.v_left = Button(
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_left",
            emoji="◀",
            row=start_row + 1
        )
        self.v_left.callback = self.v_left_callback
        self.add_item(self.v_left)

        self.v_page = Button(
            label="N / N",
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_page",
            disabled=True,
            row=start_row + 1
        )
        self.add_item(self.v_page)

        self.v_right = Button(
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_right",
            emoji="▶",
            row=start_row + 1
        )
        self.v_right.callback = self.v_right_callback
        self.add_item(self.v_right)

        self.v_end = Button(
            style=ButtonStyle.secondary,
            custom_id=f"{namespace}:select_end",
            emoji="⏭",
            row=start_row + 1
        )
        self.v_end.callback = self.v_end_callback
        self.add_item(self.v_end)

    async def update_view(
            self,
            send: bool = True,
            update_content: bool = False,
            check_if_content_is_different: bool = False
    ):
        await self.update_view_components()
        await self.update_select_options()
        if self.options_list_length > DISCORD_SELECT_OPTIONS_MAX_LENGTH:
            last_page = self.get_last_page()
            if self.select_page == 0:
                self.v_left.disabled = True
                self.v_start.disabled = True
                self.v_right.disabled = False
                self.v_end.disabled = False
            elif self.select_page == last_page:
                self.v_left.disabled = False
                self.v_start.disabled = False
                self.v_right.disabled = True
                self.v_end.disabled = True
            else:
                self.v_left.disabled = False
                self.v_start.disabled = False
                self.v_right.disabled = False
                self.v_end.disabled = False
            self.v_page.label = f"{self.select_page + 1} / {last_page + 1}"
            if last_page == 1:
                self.v_start.disabled = True
                self.v_end.disabled = True
        else:
            if not self.controls_removed:
                for c in [self.v_left, self.v_start, self.v_page, self.v_right, self.v_end]:
                    self.remove_item(c)
                self.controls_removed = True
        if not send:
            return

        if self.message is None and self.message_id is not None:
            self.message, channel = await get_message_and_channel(
                BotVars.bot_for_webhooks,
                self.message_id,
                self.channel_id
            )
            if channel is not None:
                self.channel_id = channel.id
        if self.message is not None:
            if check_if_content_is_different and self.message.clean_content == get_translation(self.raw_content):
                update_content = False
            self.message = await self.message.edit(
                view=self,
                content=(get_translation(self.raw_content)
                         if self.raw_content is not None and update_content else MISSING)
            )
        await self.do_after_sending_message()

    async def update_select_options(self, page: Optional[int] = None):
        if page is None:
            self.v_select.options = [SelectOption(label="Not implemented!")]
        else:
            self.v_select.options = [SelectOption(label="Not implemented!")]

    async def update_view_components(self):
        pass

    async def do_after_sending_message(self):
        pass

    def get_indexes(self, current_pos: int):
        start_index = current_pos // DISCORD_SELECT_OPTIONS_MAX_LENGTH
        if start_index > 0 and start_index > self.get_last_page():
            start_index -= 1
        self.select_page = start_index
        stop_index = start_index * DISCORD_SELECT_OPTIONS_MAX_LENGTH + 25
        if stop_index > self.options_list_length:
            stop_index = self.options_list_length
        start_index *= DISCORD_SELECT_OPTIONS_MAX_LENGTH

        return start_index, stop_index

    def set_by_page(self, page: int):
        last_page = self.get_last_page()
        if page <= 0:
            self.select_page = 0
        elif page >= last_page:
            self.select_page = last_page
        else:
            self.select_page = page
        stop_index = self.select_page * DISCORD_SELECT_OPTIONS_MAX_LENGTH + 25
        if stop_index > self.options_list_length:
            stop_index = self.options_list_length
        start_index = self.select_page * DISCORD_SELECT_OPTIONS_MAX_LENGTH

        return start_index, stop_index

    def get_last_page(self):
        if self.options_list_length % DISCORD_SELECT_OPTIONS_MAX_LENGTH == 0:
            return (self.options_list_length // DISCORD_SELECT_OPTIONS_MAX_LENGTH) - 1
        return self.options_list_length // DISCORD_SELECT_OPTIONS_MAX_LENGTH

    async def interaction_check_select(self, interaction: Interaction, /) -> bool:
        return True

    async def on_error(self, interaction: Interaction, error: Exception, item: Item[Any], /) -> None:
        await send_error_on_interaction(self.name, interaction, self.ctx, error, self.is_reaction)

    async def v_select_callback(self, interaction: Interaction):
        pass

    async def v_start_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await self.update_select_options(0)
            self.v_start.disabled = True
            self.v_left.disabled = True
            self.v_right.disabled = False
            self.v_end.disabled = False
            self.v_page.label = f"{1} / {self.get_last_page() + 1}"
            await edit_interaction(interaction, self, self.message_id)

    async def v_left_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await self.update_select_options(self.select_page - 1)
            last_page = self.get_last_page()
            self.v_start.disabled = self.select_page == 0 if last_page > 1 else True
            self.v_left.disabled = self.select_page == 0
            self.v_right.disabled = False
            self.v_end.disabled = last_page == 1
            self.v_page.label = f"{self.select_page + 1} / {last_page + 1}"
            await edit_interaction(interaction, self, self.message_id)

    async def v_right_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await self.update_select_options(self.select_page + 1)
            last_page = self.get_last_page()
            self.v_start.disabled = last_page == 1
            self.v_left.disabled = False
            self.v_right.disabled = self.select_page == last_page
            self.v_end.disabled = self.select_page == last_page if last_page > 1 else True
            self.v_page.label = f"{self.select_page + 1} / {last_page + 1}"
            await edit_interaction(interaction, self, self.message_id)

    async def v_end_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await self.update_select_options(self.get_last_page())
            self.v_start.disabled = False
            self.v_left.disabled = False
            self.v_right.disabled = True
            self.v_end.disabled = True
            self.v_page.label = "{0} / {0}".format(self.get_last_page() + 1)
            await edit_interaction(interaction, self, self.message_id)


class SelectView(TemplateSelectView):
    def __init__(
            self,
            options_raw: List,
            pivot_index: Optional[int],
            make_select_option: Callable[[int, Optional[commands.Bot]], Awaitable[SelectOption]],
            ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, None] = None,
            bot: Optional[commands.Bot] = None,
            namespace: str = "select_view",
            name: str = "SelectView",
            min_values: int = 1,
            max_values: int = 1,
            timeout: Optional[float] = 180.0
    ):
        super().__init__(
            options_raw=options_raw,
            ctx=ctx,
            namespace=namespace,
            name=name,
            min_values=min_values,
            max_values=max_values,
            timeout=timeout
        )
        self.pivot_index = pivot_index if pivot_index is not None else 0  # Starts from 0 to len(options_raw) - 1
        self.make_select_option = make_select_option
        self.bot = bot

    async def update_select_options(self, page: Optional[int] = None):
        if page is None:
            indexes = self.get_indexes(self.pivot_index)
        else:
            indexes = self.set_by_page(page)
        self.v_select.options = [
            await self.make_select_option(i, self.bot) for i in range(*indexes)
        ]


class MenuServerView(TemplateSelectView):
    def __init__(self, bot: commands.Bot, commands_cog: 'MinecraftCommands'):
        super().__init__(
            options_raw=Config.get_settings().servers_list,
            raw_content="List of commands for interacting with Minecraft server via buttons"
                        " and dropdown for selecting server",
            namespace="menu_server_view",
            name="MenuServerView",
            message_id=Config.get_menu_settings().server_menu_message_id,
            channel_id=Config.get_menu_settings().server_menu_channel_id,
            start_row=3,
            is_reaction=True
        )
        self.bot = bot
        self.commands_cog = commands_cog

    async def update_select_options(self, page: Optional[int] = None):
        if page is None:
            indexes = self.get_indexes(Config.get_settings().selected_server_number)
        else:
            indexes = self.set_by_page(page)
        self.v_select.options = [
            SelectOption(
                label=shorten_string(Config.get_settings().servers_list[i].server_name,
                                     DISCORD_SELECT_FIELD_MAX_LENGTH),
                value=str(i),
                default=i + 1 == Config.get_settings().selected_server_number
            ) for i in range(*indexes)
        ]

    async def do_after_sending_message(self):
        if self.channel_id is not None and Config.get_menu_settings().server_menu_channel_id is None:
            Config.get_menu_settings().server_menu_channel_id = self.channel_id
            Config.save_config()

    async def interaction_check_select(self, interaction: Interaction, /) -> bool:
        return is_minecrafter(interaction)

    @button(label="status", style=ButtonStyle.secondary, custom_id="menu_server_view:status", emoji="⚠", row=0)
    async def c_status(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        await bot_status(interaction, interaction.client, is_reaction=True)

    @button(label="list", style=ButtonStyle.secondary, custom_id="menu_server_view:list", emoji="📋", row=0)
    async def c_list(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        await bot_list(interaction, interaction.client, is_reaction=True)

    @button(label="backup", style=ButtonStyle.secondary, custom_id="menu_server_view:backup", emoji="📇", row=0)
    async def c_backup(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        await bot_backup(interaction, interaction.client, is_reaction=True)

    @button(label="update", style=ButtonStyle.secondary, custom_id="menu_server_view:update", emoji="📶", row=0)
    async def c_update(self, interaction: Interaction, button: Button):
        self.commands_cog.checkups_task.restart()
        await send_interaction(interaction, get_translation("Updated bot status!"), is_reaction=True)

    @button(label="start", style=ButtonStyle.secondary, custom_id="menu_server_view:start", emoji="⏯", row=1)
    async def c_start(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        if await self.interaction_check_select(interaction):
            await bot_start(
                interaction,
                interaction.client,
                self.commands_cog.backups_thread,
                is_reaction=True
            )

    @button(label="stop 10", style=ButtonStyle.secondary, custom_id="menu_server_view:stop_10", emoji="⏹", row=1)
    async def c_stop(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        if await self.interaction_check_select(interaction):
            await bot_stop(
                interaction,
                command=10,
                bot=interaction.client,
                poll=self.commands_cog._IndPoll,
                is_reaction=True
            )

    @button(label="restart 10", style=ButtonStyle.secondary, custom_id="menu_server_view:restart_10", emoji="🔄", row=1)
    async def c_restart(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        if await self.interaction_check_select(interaction):
            await bot_restart(
                interaction,
                command=10,
                bot=interaction.client,
                poll=self.commands_cog._IndPoll,
                backups_thread=self.commands_cog.backups_thread,
                is_reaction=True
            )

    @button(
        label="backup force",
        style=ButtonStyle.secondary,
        custom_id="menu_server_view:backup_force",
        emoji="💽",
        row=2
    )
    async def c_b_force(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        if await self.interaction_check_select(interaction):
            backup_reason_modal = Modal(title=get_translation("Backup reason"))
            reason = TextInput(
                label=get_translation("What is the reason for creating this backup?"),
                style=TextStyle.long,
                placeholder=get_translation("Type here... (you can leave this blank)"),
                required=False,
                max_length=300,
            )
            backup_reason_modal.add_item(reason)

            async def on_submit(interaction: Interaction):
                if await backup_force_checking(interaction, self.bot):
                    await on_backup_force_callback(
                        interaction,
                        self.bot,
                        self.commands_cog.backups_thread,
                        reason=reason.value if len(reason.value) > 0 else None,
                        is_reaction=True
                    )

            async def on_error(interaction: Interaction, error: Exception) -> None:
                await send_error_on_interaction("BackupReasonModal", interaction, None, error, True)

            backup_reason_modal.on_submit = on_submit
            backup_reason_modal.on_error = on_error
            await interaction.response.send_modal(backup_reason_modal)

    @button(
        label="backup restore",
        style=ButtonStyle.secondary,
        custom_id="menu_server_view:backup_restore",
        emoji="♻",
        row=2
    )
    async def c_b_restore(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        if await self.interaction_check_select(interaction):
            if not (await backup_restore_checking(interaction, is_reaction=True)):
                return

            await send_backup_restore_select(interaction, self.bot, self.commands_cog.backups_thread, is_reaction=True)

    @button(
        label="backup remove",
        style=ButtonStyle.secondary,
        custom_id="menu_server_view:backup_remove",
        emoji="🗑",
        row=2
    )
    async def c_b_remove(self, interaction: Interaction, button: Button):
        BotVars.react_auth = interaction.user
        if await self.interaction_check_select(interaction):
            await send_backup_remove_select(
                interaction,
                self.bot,
                self.commands_cog._IndPoll,
                self.commands_cog.backups_thread,
                is_reaction=True
            )

    async def v_select_callback(self, interaction: Interaction):
        if await self.interaction_check_select(interaction):
            await on_server_select_callback(interaction, is_reaction=True)
            await self.update_view()


class MenuBotView(TemplateSelectView):
    def __init__(self, bot: commands.Bot, commands_cog: 'MinecraftCommands'):
        super().__init__(
            options_raw=get_locales(),
            raw_content="List of bot features for interaction via buttons"
                        " and dropdown for selecting bot language",
            namespace="menu_bot_view",
            name="MenuBotView",
            message_id=Config.get_menu_settings().bot_menu_message_id,
            channel_id=Config.get_menu_settings().bot_menu_channel_id,
            start_row=3,
            is_reaction=True
        )
        self.bot = bot
        self.commands_cog = commands_cog
        self.chat_cog: Optional['ChatCommands'] = None

    async def update_select_options(self, page: Optional[int] = None):
        pivot = [i for i in range(self.options_list_length) if get_current_locale() == self.options_list_raw[i]][0]
        if page is None:
            indexes = self.get_indexes(pivot)
        else:
            indexes = self.set_by_page(page)
        self.v_select.options = [
            SelectOption(
                label=shorten_string(self.options_list_raw[i].capitalize(), DISCORD_SELECT_FIELD_MAX_LENGTH),
                value=shorten_string(self.options_list_raw[i], DISCORD_SELECT_FIELD_MAX_LENGTH),
                description=shorten_string(get_translation(self.options_list_raw[i]),
                                           DISCORD_SELECT_FIELD_MAX_LENGTH),
                default=pivot == i,
                emoji="🌐" if pivot == i else None
            ) for i in range(*indexes)
        ]

    async def update_view_components(self):
        if self.chat_cog is None:
            self.chat_cog = self.bot.get_cog("ChatCommands")
            if self.chat_cog is None:
                raise RuntimeError("Cog 'ChatCommands' not found!")

        self.b_auth.style = ButtonStyle.green if Config.get_secure_auth().enable_secure_auth else ButtonStyle.red
        self.b_auth.emoji = "🔒" if Config.get_secure_auth().enable_secure_auth else "🔑"
        self.b_auth.label = get_translation("Authorization")

        self.b_a_backup.style = ButtonStyle.green if Config.get_backups_settings().automatic_backup else ButtonStyle.red
        self.b_a_backup.label = get_translation("Auto backup")

        self.b_whitelist.style = ButtonStyle.green if ServerProperties().white_list else ButtonStyle.red
        self.b_whitelist.label = get_translation("White list")

        self.b_forceload.style = ButtonStyle.green if Config.get_settings().bot_settings.forceload else ButtonStyle.red
        self.b_forceload.emoji = "♾" if Config.get_settings().bot_settings.forceload else "🇽"
        self.b_forceload.label = get_translation("Forceload")

        self.b_a_shutdown.style = ButtonStyle.green \
            if Config.get_settings().bot_settings.auto_shutdown else ButtonStyle.red
        self.b_a_shutdown.emoji = "🌜" if Config.get_settings().bot_settings.auto_shutdown else "🌕"
        self.b_a_shutdown.label = get_translation("Auto shutdown")

        self.b_chat.style = ButtonStyle.green \
            if Config.get_game_chat_settings().enable_game_chat else ButtonStyle.red
        self.b_chat.label = get_translation("Game chat")

        self.b_c_p_images.style = ButtonStyle.green \
            if Config.get_game_chat_settings().image_preview.enable_image_preview else ButtonStyle.red
        self.b_c_p_images.label = get_translation("Image preview")

        self.b_rss_news.style = ButtonStyle.green if Config.get_rss_feed_settings().enable_rss_feed else ButtonStyle.red
        self.b_rss_news.emoji = "🔔" if Config.get_rss_feed_settings().enable_rss_feed else "🔕"
        self.b_rss_news.label = get_translation("RSS feed")

    async def do_after_sending_message(self):
        if self.channel_id is not None and Config.get_menu_settings().bot_menu_channel_id is None:
            Config.get_menu_settings().bot_menu_channel_id = self.channel_id
            Config.save_config()

    @button(custom_id="menu_bot_view:authorize", row=0)
    async def b_auth(self, interaction: Interaction, button: Button):
        if is_admin(interaction):
            Config.get_secure_auth().enable_secure_auth = not Config.get_secure_auth().enable_secure_auth
            Config.save_config()
            button.emoji = "🔑" if button.style == ButtonStyle.green else "🔒"
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_secure_auth().enable_secure_auth:
                with suppress(ConnectionError, socket.error):
                    if BotVars.watcher_of_log_file is None:
                        BotVars.watcher_of_log_file = create_watcher(BotVars.watcher_of_log_file, get_server_version())
                    BotVars.watcher_of_log_file.start()
                msg = add_quotes(get_translation("Secure authorization on"))
            else:
                if not Config.get_game_chat_settings().enable_game_chat and \
                        BotVars.watcher_of_log_file is not None:
                    BotVars.watcher_of_log_file.stop()
                msg = add_quotes(get_translation("Secure authorization off"))
            await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:auto_backup", emoji="💾", row=0)
    async def b_a_backup(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            Config.get_backups_settings().automatic_backup = not Config.get_backups_settings().automatic_backup
            Config.save_config()
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_backups_settings().automatic_backup:
                await warn_about_auto_backups(interaction, self.bot, is_reaction=True)
                msg = add_quotes(get_translation("Automatic backups enabled"))
            else:
                msg = add_quotes(get_translation("Automatic backups disabled"))
            await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:whitelist", emoji="🗒️", row=0)
    async def b_whitelist(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            async with handle_rcon_error(None, interaction, is_reaction=True):
                msg = None
                with connect_rcon() as cl_r:
                    if ServerProperties().white_list:
                        cl_r.run("whitelist off")
                        msg = add_quotes(get_translation("The server is allowed to let any players regardless "
                                                         "of the list of allowed nicknames"))
                    else:
                        cl_r.run("whitelist on")
                        msg = add_quotes(get_translation("The server is forbidden to let players not "
                                                         "from the list of allowed nicknames"))

                button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
                await edit_interaction(interaction, self, self.message_id)
                if msg is not None:
                    await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:forceload", row=1)
    async def b_forceload(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            Config.get_settings().bot_settings.forceload = not Config.get_settings().bot_settings.forceload
            Config.save_config()
            button.emoji = "🇽" if button.style == ButtonStyle.green else "♾"
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            await send_interaction(interaction, add_quotes(bot_forceload_info()), is_reaction=True)

    @button(custom_id="menu_bot_view:auto_shutdown", row=1)
    async def b_a_shutdown(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            Config.get_settings().bot_settings.auto_shutdown = not Config.get_settings().bot_settings.auto_shutdown
            Config.save_config()
            button.emoji = "🌕" if button.style == ButtonStyle.green else "🌜"
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            await send_interaction(
                interaction,
                add_quotes(bot_shutdown_info(with_timeout=Config.get_settings().bot_settings.auto_shutdown)),
                is_reaction=True
            )

    @button(custom_id="menu_bot_view:chat", emoji="💬", row=2)
    async def b_chat(self, interaction: Interaction, button: Button):
        if is_admin(interaction):
            Config.get_game_chat_settings().enable_game_chat = \
                not Config.get_game_chat_settings().enable_game_chat
            Config.save_config()
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_game_chat_settings().enable_game_chat:
                BotVars.webhook_chat = None
                await create_webhooks(self.bot)
                with suppress(ConnectionError, socket.error):
                    if BotVars.watcher_of_log_file is None:
                        BotVars.watcher_of_log_file = create_watcher(BotVars.watcher_of_log_file, get_server_version())
                    BotVars.watcher_of_log_file.start()
                msg = get_translation("Game chat enabled") + "!"
            else:
                if not Config.get_secure_auth().enable_secure_auth and BotVars.watcher_of_log_file is not None:
                    BotVars.watcher_of_log_file.stop()
                msg = get_translation("Game chat disabled") + "!"
            await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:chat_preview_images", emoji="🖼", row=2)
    async def b_c_p_images(self, interaction: Interaction, button: Button):
        if is_minecrafter(interaction):
            Config.get_game_chat_settings().image_preview.enable_image_preview = \
                not Config.get_game_chat_settings().image_preview.enable_image_preview
            Config.save_config()
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_game_chat_settings().image_preview.enable_image_preview:
                msg = get_translation("Image preview enabled") + "!"
            else:
                msg = get_translation("Image preview disabled") + "!"
            await send_interaction(interaction, msg, is_reaction=True)

    @button(custom_id="menu_bot_view:rss_news", row=2)
    async def b_rss_news(self, interaction: Interaction, button: Button):
        if is_admin(interaction):
            Config.get_rss_feed_settings().enable_rss_feed = not Config.get_rss_feed_settings().enable_rss_feed
            Config.save_config()
            button.emoji = "🔕" if button.style == ButtonStyle.green else "🔔"
            button.style = ButtonStyle.red if button.style == ButtonStyle.green else ButtonStyle.green
            await edit_interaction(interaction, self, self.message_id)
            if Config.get_rss_feed_settings().enable_rss_feed:
                BotVars.webhook_rss = None
                await create_webhooks(self.bot)
                if self.chat_cog.rss_feed_task.is_running():
                    self.chat_cog.rss_feed_task.restart()
                else:
                    self.chat_cog.rss_feed_task.start()
                msg = get_translation("RSS enabled") + "!"
            else:
                if self.chat_cog.rss_feed_task.is_running():
                    self.chat_cog.rss_feed_task.stop()
                msg = get_translation("RSS disabled") + "!"
            await send_interaction(interaction, msg, is_reaction=True)

    async def v_select_callback(self, interaction: Interaction):
        await on_language_select_callback(interaction, None, is_reaction=True)
        await self.update_view(update_content=True)
        if self.commands_cog.menu_server_view is not None:
            await self.commands_cog.menu_server_view.update_view(update_content=True)
