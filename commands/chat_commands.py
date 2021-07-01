from discord.ext import commands

from components.additional_funcs import handle_message_for_chat
from components.watcher_handle import create_watcher
from config.init_config import Bot_variables, Config
from decorators import role


class Chat_commands(commands.Cog):
    def __init__(self, bot):
        self._bot = bot

    @commands.command(pass_context=True)
    @role.has_role_or_default()
    async def chat(self, ctx, channel_id=None):
        channel_setted = False
        if channel_id is None:
            Config.set_discord_channel_id_for_crossplatform_chat(str(ctx.channel.id))
            channel_setted = True
        else:
            if channel_id.startswith("<#"):
                try:
                    Config.set_discord_channel_id_for_crossplatform_chat(str(int(channel_id.strip("<#>"))))
                    channel_setted = True
                except ValueError:
                    pass
            else:
                try:
                    Config.set_discord_channel_id_for_crossplatform_chat(str(int(channel_id)))
                    channel_setted = True
                except ValueError:
                    pass

        if channel_setted:
            await ctx.channel.send(
                f"Channel `{(await self._bot.fetch_channel(Config.get_discord_channel_id_for_crossplatform_chat())).name}` set to minecraft crossplatform chat!")
            if Bot_variables.watcher_of_log_file is None:
                Bot_variables.watcher_of_log_file = create_watcher()
                Bot_variables.watcher_of_log_file.start()
        else:
            await ctx.channel.send("You entered wrong argument!")

    @commands.Cog.listener()
    async def on_message(self, message):
        await handle_message_for_chat(message, self._bot, True)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        await handle_message_for_chat(after, self._bot, False, on_edit=True, before_message=before)
