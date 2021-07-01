from discord.ext import commands
from mcipc.rcon import Client as Client_r
from re import split, search, findall

from components.additional_funcs import get_author_and_mention, send_msg, delete_after_by_msg_id
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
        if message.author == self._bot.user or message.content.startswith(Config.get_prefix()) or str(
                message.author.discriminator) == "0000" or len(message.content) == 0 or \
                message.channel.id != int(Config.get_discord_channel_id_for_crossplatform_chat()):
            return

        _, author_mention = get_author_and_mention(message, self._bot, False)
        delete_user_message = True

        if not Config.get_discord_channel_id_for_crossplatform_chat() or not Config.get_webhook_info():
            await send_msg(message.channel, f"{author_mention}, this chat couldn't work! Crossplatform chat disabled!",
                           True)
        elif not Bot_variables.IsServerOn:
            await send_msg(message.channel, f"{author_mention}, server offline!", True)
        elif Bot_variables.IsRestarting:
            await send_msg(message.channel, f"{author_mention}, server is restarting!", True)
        elif Bot_variables.IsStopping and Bot_variables.watcher_of_log_file is None:
            await send_msg(message.channel, f"{author_mention}, server is stopping!", True)
        elif Bot_variables.IsLoading:
            await send_msg(message.channel, f"{author_mention}, server is loading!", True)
        else:
            # handle custom emojis
            if search(r"<:\w+:\d+>", message.content.strip()):
                temp_split = split(r"<:\w+:\d+>", message.content.strip())
                temp_arr = list(findall(r"<:\w+:\d+>", message.content.strip()))
                i = 1
                for emoji in temp_arr:
                    temp_split.insert(i, findall(r"\w+", emoji)[0])
                    i += 2
                result_msg = "".join(temp_split)
            else:
                result_msg = message.content.strip()

            with Client_r(Config.get_local_address(), Bot_variables.port_rcon, timeout=1) as cl_r:
                cl_r.login(Bot_variables.rcon_pass)
                answ = cl_r.tellraw("@a",
                                    ["", {"text": "<"}, {"text": message.author.display_name, "color": "dark_gray"},
                                     {"text": f"> {result_msg}"}])
            if answ == '':
                delete_user_message = False
            else:
                await send_msg(message.channel, f"{author_mention}, {answ.lower()}!", True)

        if delete_user_message:
            await delete_after_by_msg_id(message, message.id)
