from os import chdir
from pathlib import Path
from random import choice, randint

import discord
import vk_api
from discord import Activity, ActivityType
from discord.ext import commands

from commands.poll import Poll
from components.additional_funcs import handle_message_for_chat, server_checkups, send_error, send_msg
from components.watcher_handle import create_watcher
from config.init_config import Bot_variables, Config
from decorators import role


class Chat_commands(commands.Cog):
    def __init__(self, bot):
        self._bot = bot
        self._IndPoll = Poll(bot)

    @commands.Cog.listener()
    async def on_ready(self):
        print('------')
        print('Logged in discord as')
        print(f"{self._bot.user.name}#{self._bot.user.discriminator}")
        print("Discord.py version", discord.__version__)
        print('------')
        await self._bot.change_presence(activity=Activity(type=ActivityType.watching, name="nsfw"))
        print("Bot is ready!")
        print("Starting server check-ups")
        Bot_variables.server_checkups_task = self._bot.loop.create_task(server_checkups(self._bot))

    """
    @commands.command(pass_context=True)
    async def debug(self, ctx):
        await send_msg(ctx, "Constants:\nIsServerOn: " + str(IsServerOn) + "\nIsLoading: " + str(IsLoading)
                       + "\nIsStopping: " + str(IsStopping) + "\nIsRestarting: " + str(IsRestarting))
    """

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @role.has_role_or_default()
    async def chat(self, ctx, channel_id=None):
        if not Config.get_cross_platform_chat_settings().enable_cross_platform_chat:
            await ctx.channel.send("Cross platform chat is disabled in bot config!")
            return

        channel_set = False
        if channel_id is None:
            Config.get_cross_platform_chat_settings().channel_id = ctx.channel.id
            channel_set = True
        else:
            if channel_id.startswith("<#"):
                try:
                    Config.get_cross_platform_chat_settings().channel_id = int(channel_id.strip("<#>"))
                    channel_set = True
                except ValueError:
                    pass
            else:
                try:
                    Config.get_cross_platform_chat_settings().channel_id = int(channel_id)
                    channel_set = True
                except ValueError:
                    pass

        if channel_set:
            Config.save_config()
            await ctx.channel.send(
                "Channel `" +
                (await self._bot.fetch_channel(Config.get_cross_platform_chat_settings().channel_id)).name +
                "` set to minecraft cross platform chat!")
            if Bot_variables.watcher_of_log_file is None:
                Bot_variables.watcher_of_log_file = create_watcher()
                Bot_variables.watcher_of_log_file.start()
        else:
            await ctx.channel.send("You entered wrong argument!")

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
                    vk_session = vk_api.VkApi(vk_login, vk_pass)
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
                    e = discord.Embed(title="Ошибка vk:  Что-то пошло не так",
                                      color=discord.Color.red())
                    file = discord.File(Path(Config.get_inside_path(), "images/sad_dog.jpg"), filename="image.jpg")
                    e.set_image(url="attachment://image.jpg")
                    await ctx.send(embed=e, file=file)
            else:
                await ctx.send("Я бы мог рассказать что-то, но мне лень. ( ͡° ͜ʖ ͡°)\nReturning to my duties.")
        else:
            e = discord.Embed(title="Ошибка vk:  Не введены данные аккаунта",
                              color=discord.Color.red())
            file = discord.File(Path(Config.get_inside_path(), "images/sad_dog.jpg"), filename="image.jpg")
            e.set_image(url="attachment://image.jpg")
            await ctx.send(embed=e, file=file)

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, embed_links=True, view_channel=True)
    @commands.guild_only()
    async def help(self, ctx):
        await ctx.channel.purge(limit=1)
        emb = discord.Embed(title=f'Список всех команд (через {Config.get_settings().bot_settings.prefix})',
                            color=discord.Color.gold())
        emb.add_field(name='status', value='Возвращает статус сервера')
        emb.add_field(name='list/ls',
                      value='Возвращает список игроков')
        emb.add_field(name='start', value='Запускает сервер')
        emb.add_field(name='stop {10}',
                      value='Останавливает сервер, {} (сек) сколько идёт отсчёт, без аргументов - убирает таймер')
        emb.add_field(name='restart {10}',
                      value='Перезапускает сервер, {} (сек) сколько идёт отсчёт, без аргументов - убирает таймер')
        emb.add_field(name='op {1} {2} {3}',
                      value='Даёт op\'ку на {1} ник по {2} коду {3} c комментарием причины, если надо')
        emb.add_field(name='assoc {1} {2} {3}',
                      value='Ассоциирует {1} упоминание ника в дискорде по {2} команде (+=/-=) (добавить или удалить) {3} c ником в майнкрафте **для админа**')
        emb.add_field(name='codes {1}', value='Даёт коды на {1} ник в лс')
        emb.add_field(name='menu', value='Создаёт меню-пульт для удобного управления командами')
        emb.add_field(name='chat {1}',
                      value='Сохраняет текущий канал (если без аргументов) или выбранный канал с первого аргумента откуда бот переправляет сообщения в майн')
        emb.add_field(name='forceload/fl {on/off}',
                      value='По {on/off} постоянная загрузка сервера, когда он отключен, без аргументов - статус')
        emb.add_field(name='whitelist/wl {1}',
                      value='Использует whitelist с сервера майна, аргументы {1} - on, off, add, del, list, reload.  С add и del ещё пишется ник игрока')
        emb.add_field(name='servers/servs {1}',
                      value='Использует список серверов в боте, аргументы {1} - select, list, show.  При select ещё пишется номер сервера из list')
        emb.add_field(name='say', value='"Петросянит" ( ͡° ͜ʖ ͡°)')
        emb.add_field(name='clear/cls {1}',
                      value='Если положительное число удаляет {1} сообщений, если отрицательное - удаляет n сообщений до {1} от начала канала')
        await ctx.send(embed=emb)

    @commands.command(pass_context=True, aliases=["cls"])
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, mention_everyone=True,
                                  embed_links=True, read_message_history=True, view_channel=True)
    @commands.guild_only()
    async def clear(self, ctx, count=1):  # TODO: add arg all to clear all msgs in channel
        message_created_time = ""
        try:
            int(str(count))
        except ValueError:
            await ctx.send("Ты дебик? Чё ты там написал? Как мне это понимать? А? '" + str(count) + "' Убейся там!")
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
            await send_msg(ctx, "Nothing's done!", True)
            return
        if await self._IndPoll.timer(ctx, 5):
            if await self._IndPoll.run(ctx=ctx, remove_logs_after=5):
                if count < 0:
                    await ctx.channel.purge(limit=None, after=message_created_time, bulk=False)
                else:
                    await ctx.channel.purge(limit=count + 1, bulk=False)

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await send_error(ctx, self._bot, error)
