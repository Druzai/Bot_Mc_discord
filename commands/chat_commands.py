from os import chdir
from pathlib import Path
from random import choice, randint
from typing import Union

import discord
from discord import Activity, ActivityType, Role, Member
from discord.ext import commands, tasks
from vk_api import VkApi

from commands.poll import Poll
from components import decorators
from components.additional_funcs import handle_message_for_chat, send_error, bot_clear, add_quotes, \
    parse_params_for_help, send_help_of_command, parse_subcommands_for_help, find_subcommand, make_underscored_line, \
    create_webhooks
from components.localization import get_translation, get_locales, set_locale, get_current_locale
from components.rss_feed_handle import *


def channel_mention(arg: str):
    try:
        return int(arg)
    except ValueError:
        return arg


class ChatCommands(commands.Cog):
    def __init__(self, bot: commands.Bot, poll: Poll):
        self._bot: commands.Bot = bot
        self._IndPoll: Poll = poll

    @commands.Cog.listener()
    async def on_ready(self):
        print("------")
        print(get_translation("Logged in discord as"))
        print(f"{self._bot.user.name}#{self._bot.user.discriminator}")
        print(get_translation("Discord.py version"), discord.__version__)
        print("------")
        await self._bot.change_presence(activity=Activity(type=ActivityType.watching, name="nsfw"))
        create_webhooks()
        if Config.get_rss_feed_settings().enable_rss_feed:
            self.rss_feed_task.start()
        print(get_translation("Bot is ready!"))

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
    async def language(self, ctx, set_language: str = ""):
        """Get/Select language"""
        if len(set_language) > 0:
            if set_locale(set_language):
                await ctx.send(add_quotes(get_translation("Bot doesn't have this language!\n"
                                                          "Check list of available languages via {0}language")
                                          .format(Config.get_settings().bot_settings.prefix)))
            else:
                Config.get_settings().bot_settings.language = set_language.lower()
                Config.save_config()
                await ctx.send(add_quotes(get_translation("Language switched successfully!")))

        else:
            langs = []
            for lang in get_locales():
                lang_code = lang.capitalize()
                if get_current_locale() == lang:
                    lang_code = make_underscored_line(lang_code)
                langs.append(f"{lang_code} ({get_translation(lang)})")
            await ctx.send(add_quotes(get_translation("Available languages:") + "\n- " + "\n- ".join(langs)))

    @commands.command(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    async def prefix(self, ctx, *, new_prefix: str = ""):
        if not new_prefix:
            await ctx.send(add_quotes(get_translation("Current prefix - '{0}'.")
                                      .format(Config.get_settings().bot_settings.prefix)))
        else:
            if Config.get_settings().bot_settings.role != "" and \
                    Config.get_settings().bot_settings.role not in (e.name for e in ctx.author.roles):
                await send_error(ctx, self._bot,
                                 commands.MissingRole(Config.get_settings().bot_settings.role))
                return

            if len(new_prefix.split()) > 1:
                await ctx.send(add_quotes(get_translation("Prefix can't have spaces!")))
            else:
                check = Config.get_settings().bot_settings.prefix == new_prefix
                Config.get_settings().bot_settings.prefix = new_prefix
                Config.save_config()
                await ctx.send(add_quotes(get_translation("Changed prefix to '{0}'.").format(new_prefix) +
                                          (" ( ͡° ͜ʖ ͡°)" if check else "")))

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
                    max_photo_width = 0
                    photo_url = None
                    for i in photo_sizes:
                        if i['height'] > max_photo_height:
                            max_photo_height = i['height']
                        if i['width'] > max_photo_width:
                            max_photo_width = i['width']
                    for i in photo_sizes:
                        if i['height'] == max_photo_height and i['width'] == max_photo_width:
                            photo_url = i['url']
                            break
                    if photo_url is None:
                        for i in photo_sizes:
                            if i['height'] == max_photo_height:
                                photo_url = i['url']
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
            command, *subcommands = tokens
            command = command.strip(Config.get_settings().bot_settings.prefix)
            subcommands.pop()
            for c in self._bot.commands:
                if command.lower() == c.name or command.lower() in c.aliases:
                    if len(subcommands):
                        command = find_subcommand(subcommands, c, -1)
                    else:
                        command = c
                    break
            if command == ctx.command:
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
                                                "The | sign means one or the other.\n"
                                                "Use {prefix}help command for more info.\n"
                                                "Or {prefix}command {arg_list} for short.")
                           .format(prefix=Config.get_settings().bot_settings.prefix,
                                   arg_list=str(Config.get_settings().bot_settings.help_arguments)))
            await ctx.send(embed=emb)

    @commands.group(pass_context=True, aliases=["cls"], invoke_without_command=True)
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, mention_everyone=True, add_reactions=True,
                                  embed_links=True, read_message_history=True, view_channel=True)
    @commands.guild_only()
    async def clear(self, ctx, count: int = 1, mentions: commands.Greedy[Union[Member, Role]] = None):
        await bot_clear(ctx, self._IndPoll, count=count, discord_mentions=mentions)

    @clear.command(pass_context=True, name="all")
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, mention_everyone=True, add_reactions=True,
                                  embed_links=True, read_message_history=True, view_channel=True)
    @commands.guild_only()
    async def c_all(self, ctx, mentions: commands.Greedy[Union[Member, Role]] = None):
        await bot_clear(ctx, self._IndPoll, subcommand="all", discord_mentions=mentions)

    @clear.command(pass_context=True, name="reply")
    @commands.bot_has_permissions(manage_messages=True, send_messages=True, mention_everyone=True, add_reactions=True,
                                  embed_links=True, read_message_history=True, view_channel=True)
    @commands.guild_only()
    async def c_reply(self, ctx, mentions: commands.Greedy[Union[Member, Role]] = None):
        if ctx.message.reference is not None:
            await bot_clear(ctx, self._IndPoll, subcommand="reply", discord_mentions=mentions)
        else:
            await ctx.send(get_translation("You didn't provide reply in your message!"))

    @tasks.loop()
    async def rss_feed_task(self):
        await check_on_rss_feed()

    @rss_feed_task.before_loop
    async def before_rss_feed(self):
        await self._bot.wait_until_ready()
        print(get_translation("Starting rss feed check"))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await send_error(ctx, self._bot, error)
