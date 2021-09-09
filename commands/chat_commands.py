from os import chdir
from pathlib import Path
from random import choice, randint

import discord
from discord import Activity, ActivityType
from discord.ext import commands
from vk_api import VkApi

from commands.poll import Poll
from components import decorators
from components.additional_funcs import handle_message_for_chat, server_checkups, send_error, send_msg, add_quotes, \
    parse_params_for_help, send_help_of_command, parse_subcommands_for_help, find_subcommand
from components.localization import get_translation, get_locales, set_locale
from config.init_config import BotVars, Config


def channel_mention(arg: str):
    try:
        return int(arg)
    except ValueError:
        return arg


class ChatCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self._bot: commands.Bot = bot
        self._IndPoll: Poll = Poll(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        print("------")
        print(get_translation("Logged in discord as"))
        print(f"{self._bot.user.name}#{self._bot.user.discriminator}")
        print(get_translation("Discord.py version"), discord.__version__)
        print("------")
        await self._bot.change_presence(activity=Activity(type=ActivityType.watching, name="nsfw"))
        print(get_translation("Bot is ready!"))
        print(get_translation("Starting server check-ups"))
        BotVars.server_checkups_task = self._bot.loop.create_task(server_checkups(self._bot))

    """
    @commands.command(pass_context=True)
    async def debug(self, ctx):
        await send_msg(ctx, "Constants:\nIsServerOn: " + str(IsServerOn) + "\nIsLoading: " + str(IsLoading)
                       + "\nIsStopping: " + str(IsStopping) + "\nIsRestarting: " + str(IsRestarting))
    """

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def chat(self, ctx, channel_id: channel_mention = None):
        if not Config.get_cross_platform_chat_settings().enable_cross_platform_chat:
            await ctx.channel.send(get_translation("Cross-platform chat is disabled in bot config!"))
            return

        channel_set = False
        if channel_id is None:
            Config.get_cross_platform_chat_settings().channel_id = ctx.channel.id
            channel_set = True
        else:
            if isinstance(channel_id, int):
                Config.get_cross_platform_chat_settings().channel_id = channel_id
                channel_set = True
            elif channel_id.startswith("<#"):
                try:
                    Config.get_cross_platform_chat_settings().channel_id = int(channel_id.strip("<#>"))
                    channel_set = True
                except ValueError:
                    pass

        if channel_set:
            Config.save_config()
            await ctx.channel.send(
                get_translation("Channel `{0}` set to minecraft cross-platform chat!")
                    .format((await self._bot.fetch_channel(Config.get_cross_platform_chat_settings().channel_id)).name))
        else:
            await ctx.channel.send(get_translation("You entered wrong argument!"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if not Config.get_cross_platform_chat_settings().enable_cross_platform_chat:
            return

        await handle_message_for_chat(message, self._bot, True)

    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if not Config.get_cross_platform_chat_settings().enable_cross_platform_chat:
            return

        await handle_message_for_chat(after, self._bot, False, on_edit=True, before_message=before)

    @commands.command(pass_context=True, aliases=["lang"])
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    async def language(self, ctx, set_language=""):
        """Get/Select language"""
        if len(set_language) > 0:
            if set_locale(set_language):
                await ctx.send(add_quotes(get_translation("Bot doesn't have this language!\n"
                                                          "Check list pf available languages via {0}language")
                                          .format(Config.get_settings().bot_settings.prefix)))
            else:
                Config.get_settings().bot_settings.language = set_language.lower()
                Config.save_config()
                await ctx.send(add_quotes(get_translation("Language switched successfully!")))

        else:
            await ctx.send(add_quotes(get_translation("Available languages:\n{0}")
                                      .format(", ".join([ln.capitalize() for ln in get_locales()]))))

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, embed_links=True, view_channel=True)
    async def say(self, ctx):
        """Петросян"""
        vk_login, vk_pass = Config.get_settings().bot_settings.vk_login, Config.get_settings().bot_settings.vk_password
        if vk_login is not None and vk_pass is not None:
            if bool(randint(0, 3)):
                _300_answers = [
                    'Ну, держи!',
                    'Ah, shit, here we go again.',
                    'Ты сам напросился...',
                    'Не следовало тебе меня спрашивать...',
                    'Ха-ха-ха-ха.... Извини',
                    '( ͡° ͜ʖ ͡°)',
                    'Ну что пацаны, аниме?',
                    'Ну чё, народ, погнали, на\\*уй! Ё\\*\\*\\*ный в рот!'
                ]
                _300_communities = [
                    -45045130,  # - Хрень, какой-то паблик
                    -45523862,  # - Томат
                    -67580761,  # - КБ
                    -57846937,  # - MDK
                    -12382740,  # - ЁП
                    -45745333,  # - 4ch
                    -76628628,  # - Silvername
                ]
                own_id = choice(_300_communities)
                chdir(Config.get_bot_config_path())
                try:
                    # Тырим с вк фотки)
                    vk_session = VkApi(vk_login, vk_pass)
                    vk_session.auth()
                    vk = vk_session.get_api()
                    photos_count = vk.photos.get(owner_id=own_id, album_id="wall", count=1).get('count')
                    photo_sizes = vk.photos.get(owner_id=own_id,
                                                album_id="wall",
                                                count=1,
                                                offset=randint(0, photos_count) - 1).get('items')[0].get('sizes')
                    max_photo_height = 0
                    photo_url = ""
                    for i in photo_sizes:
                        if i.get('height') > max_photo_height:
                            max_photo_height = i.get('height')
                    for i in photo_sizes:
                        if i.get('height') == max_photo_height:
                            photo_url = i.get('url')
                            break
                    e = discord.Embed(title=choice(_300_answers),
                                      color=discord.Color.from_rgb(randint(0, 255), randint(0, 255), randint(0, 255)))
                    e.set_image(url=photo_url)
                    await ctx.send(embed=e)
                except BaseException:
                    e = discord.Embed(title=get_translation("Vk Error: Something went wrong"),
                                      color=discord.Color.red())
                    file = discord.File(Path(Config.get_inside_path(), "images/sad_dog.jpg"), filename="image.jpg")
                    e.set_image(url="attachment://image.jpg")
                    await ctx.send(embed=e, file=file)
            else:
                await ctx.send(get_translation("I could tell you something, but I'm too lazy. {0}\n"
                                               "Returning to my duties.").format("( ͡° ͜ʖ ͡°)"))
        else:
            e = discord.Embed(title=get_translation("Vk Error: Account details not entered"),
                              color=discord.Color.red())
            file = discord.File(Path(Config.get_inside_path(), "images/sad_dog.jpg"), filename="image.jpg")
            e.set_image(url="attachment://image.jpg")
            await ctx.send(embed=e, file=file)

    async def bot_check(self, ctx):
        # Check if user asks help on each command or subcommand
        tokens = ctx.message.content.split()
        if len(tokens) > 1 and tokens[-1] in Config.get_settings().bot_settings.help_arguments:
            mess_command = tokens[-2].strip(Config.get_settings().bot_settings.prefix)
            if mess_command.lower() == ctx.command.name.lower() or mess_command.lower() in ctx.command.aliases:
                await send_help_of_command(ctx, ctx.command)
            else:
                await ctx.send(add_quotes(get_translation("Bot doesn't have such subcommand!")))
            return False
        return True

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, embed_links=True, view_channel=True)
    @commands.guild_only()
    async def help(self, ctx, *commands: str):
        if len(commands) > 0:
            # Finding command
            command, *subcommands = commands
            for c in self._bot.commands:
                if command.lower() == c.name or command.lower() in c.aliases:
                    if len(subcommands):
                        command = find_subcommand(subcommands, c, -1)
                    else:
                        command = c
                    break
            if isinstance(command, str) or command is None:
                if len(subcommands):
                    await ctx.send(add_quotes(get_translation("Bot doesn't have such subcommand!")))
                else:
                    await ctx.send(add_quotes(get_translation("Bot doesn't have such command!")))
                return

            await send_help_of_command(ctx, command)
        else:
            await ctx.channel.purge(limit=1)
            emb = discord.Embed(title=get_translation("List of all commands, prefix - {0}")
                                .format(Config.get_settings().bot_settings.prefix),
                                color=discord.Color.gold())
            for c in sorted(self._bot.commands, key=lambda i: i.name):
                params, _ = parse_params_for_help(c.clean_params, "")
                subcommands = parse_subcommands_for_help(c)[0]
                emb.add_field(name=f"__`{c.name}" + ("/" if len(c.aliases) > 0 else "") + "/".join(c.aliases) + "`__" +
                                   (" " + " | ".join(subcommands) if len(subcommands) else "") + params,
                              value=add_quotes("\n" + get_translation(f"help_brief_{c.name}")), inline=False)
            emb.set_footer(text=get_translation("Values in [square brackets] are optional.\n"
                                                "Values in <angle brackets> have to be provided by you.\n"
                                                "The | sign means one or the other.\n"  # Add subcommands
                                                "Use {prefix}help command for more info.\n"
                                                "Or {prefix}command {arg_list} for short.")
                           .format(prefix=Config.get_settings().bot_settings.prefix,
                                   arg_list=str(Config.get_settings().bot_settings.help_arguments)))
            await ctx.send(embed=emb)
            # ------------------------------------------------------------------------------

            # emb.add_field(name='status', value='Возвращает статус сервера')
            # emb.add_field(name='list/ls',
            #               value='Возвращает список игроков')
            # emb.add_field(name='start', value='Запускает сервер')
            # emb.add_field(name='stop {10}',
            #               value='Останавливает сервер, {} (сек) сколько идёт отсчёт, без аргументов - убирает таймер')
            # emb.add_field(name='restart {10}',
            #               value='Перезапускает сервер, {} (сек) сколько идёт отсчёт, без аргументов - убирает таймер')
            # emb.add_field(name='op {1} {2}',
            #               value='Даёт op\'ку на {1} ник {2} c комментарием причины, если надо')
            # emb.add_field(name='assoc {1} {2} {3}',
            #               value='Ассоциирует {1} упоминание ника в дискорде по {2} команде (+=/-=) (добавить или удалить) {3} c ником в майнкрафте **для админа**')
            # emb.add_field(name='ops {1} {2}',
            #               value='Даёт инфу о том, какие аккаунты привязаны у вас (при {1} равном "me") '
            #                     'или у всех (при {1} равном "all" **для админа**) и сколько осталось раз op\'нуться. '
            #                     'Показывает не появлявшиеся на сервере аккаунты при {2} равном "missing"')
            # emb.add_field(name='menu', value='Создаёт меню-пульт для удобного управления командами')
            # emb.add_field(name='chat {1}',
            #               value='Сохраняет текущий канал (если без аргументов) или выбранный канал с первого аргумента откуда бот переправляет сообщения в майн')
            # emb.add_field(name='forceload/fl {on/off}',
            #               value='По {on/off} постоянная загрузка сервера, когда он отключен, без аргументов - статус')
            # emb.add_field(name='whitelist/wl {1}',
            #               value='Использует whitelist с сервера майна, аргументы {1} - on, off, add, del, list, reload.  С add и del ещё пишется ник игрока')
            # emb.add_field(name='servers/servs {1}',
            #               value='Использует список серверов в боте, аргументы {1} - select, list, show.  При select ещё пишется номер сервера из list')
            # emb.add_field(name='say', value='"Петросянит" ( ͡° ͜ʖ ͡°)')
            # emb.add_field(name='clear/cls {1}',
            #               value='Если положительное число удаляет {1} сообщений, если отрицательное - удаляет n сообщений до {1} от начала канала')
            # await ctx.send(embed=emb)

    @commands.command(pass_context=True, aliases=["cls"])
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, mention_everyone=True,
                                  embed_links=True, read_message_history=True, view_channel=True)
    @commands.guild_only()
    async def clear(self, ctx, count=1):  # TODO: add arg all to clear all msgs in channel
        message_created_time = ""
        try:
            int(str(count))
        except ValueError:
            await ctx.send(get_translation("{0}, this `{1}` isn't a number!").format(ctx.author.mention, str(count)))
            count = 0
        if count > 0:
            if len(await ctx.channel.history(limit=count).flatten()) < 51:
                await ctx.channel.purge(limit=count + 1, bulk=False)
                return
        elif count < 0:
            message_created_time = (await ctx.channel.history(limit=-count, oldest_first=True).flatten())[-1].created_at
            if len(await ctx.channel.history(limit=51, after=message_created_time, oldest_first=True).flatten()) != 51:
                await ctx.channel.purge(limit=None, after=message_created_time, bulk=False)
                return
        else:
            await send_msg(ctx, get_translation("Nothing's done!"), True)
            return
        if await self._IndPoll.timer(ctx, 5):
            if await self._IndPoll.run(ctx=ctx,
                                       message=get_translation("this man {0} trying to delete some history"
                                                               " of this channel. Will you let that happen?")
                                               .format(ctx.author.mention),
                                       remove_logs_after=5):
                if count < 0:
                    await ctx.channel.purge(limit=None, after=message_created_time, bulk=False)
                else:
                    await ctx.channel.purge(limit=count + 1, bulk=False)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await send_error(ctx, self._bot, error)
