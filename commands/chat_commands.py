from typing import Union

import discord
from discord import Role, Member, TextChannel, InvalidData, HTTPException, NotFound, Forbidden, DMChannel
from discord.ext import commands, tasks

from commands.poll import Poll
from components import decorators
from components.additional_funcs import (
    handle_message_for_chat, send_error, bot_clear, add_quotes, parse_params_for_help, send_help_of_command,
    parse_subcommands_for_help, find_subcommand, make_underscored_line, create_webhooks, bot_dm_clear,
    delete_after_by_msg, send_msg, HelpCommandArgument
)
from components.localization import get_translation, get_locales, set_locale, get_current_locale
from components.rss_feed_handle import check_on_rss_feed
from config.init_config import Config, BotVars


class ChatCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self._bot: commands.Bot = bot
        self._IndPoll: Poll = bot.get_cog("Poll")

    @commands.Cog.listener()
    async def on_ready(self):
        print("------")
        print(get_translation("Logged in Discord as"))
        print(f"{self._bot.user.name}#{self._bot.user.discriminator}")
        print(get_translation('Version of discord.py') + " - " + discord.__version__)
        print("------")
        create_webhooks()
        if Config.get_rss_feed_settings().enable_rss_feed and not self.rss_feed_task.is_running():
            self.rss_feed_task.start()
        elif self.rss_feed_task.is_running():
            self.rss_feed_task.restart()
        if not self._bot.get_cog("MinecraftCommands").checkups_task.is_running():
            self._bot.get_cog("MinecraftCommands").checkups_task.start()
        else:
            self._bot.get_cog("MinecraftCommands").checkups_task.restart()
        print(get_translation("Bot is ready!"))
        print(get_translation("To stop the bot press Ctrl + C"))

    @commands.group(pass_context=True, aliases=["chn"], invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def channel(self, ctx):
        try:
            channel = self._bot.get_channel(Config.get_cross_platform_chat_settings().channel_id)
            if channel is None:
                channel = await self._bot.fetch_channel(Config.get_cross_platform_chat_settings().channel_id)
            msg = get_translation("Channel {0} set to Minecraft cross-platform chat").format(channel.mention)
        except (InvalidData, HTTPException, NotFound, Forbidden):
            msg = get_translation("Channel for Minecraft cross-platform chat is not found or unreachable!")
        msg += "\n"
        try:
            channel = self._bot.get_channel(Config.get_settings().bot_settings.commands_channel_id)
            if channel is None:
                channel = await self._bot.fetch_channel(Config.get_settings().bot_settings.commands_channel_id)
            msg += get_translation("Channel {0} set as commands' channel for bot").format(channel.mention)
        except (InvalidData, HTTPException, NotFound, Forbidden):
            msg += get_translation("Channel for bot commands is not found or unreachable!")
        await ctx.channel.send(msg)

    @channel.command(pass_context=True, name="chat", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def c_chat(self, ctx, channel: TextChannel = None):
        if not Config.get_cross_platform_chat_settings().enable_cross_platform_chat:
            await ctx.channel.send(get_translation("Cross-platform chat is disabled in bot config!"))
            return

        if channel is None:
            channel = ctx.channel
        Config.get_cross_platform_chat_settings().channel_id = channel.id
        Config.save_config()
        await ctx.channel.send(get_translation("Channel {0} set to Minecraft cross-platform chat")
                               .format(channel.mention))

    @channel.command(pass_context=True, name="commands", ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_role_or_default()
    async def c_commands(self, ctx, channel: TextChannel = None):
        if channel is None:
            channel = ctx.channel
        Config.get_settings().bot_settings.commands_channel_id = channel.id
        Config.save_config()
        await ctx.channel.send(get_translation("Channel {0} set as commands' channel for bot").format(channel.mention))

    @commands.group(pass_context=True, invoke_without_command=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def role(self, ctx):
        role = None
        msg = ""
        if Config.get_settings().bot_settings.managing_commands_role_id is not None:
            role = self._bot.guilds[0].get_role(Config.get_settings().bot_settings.managing_commands_role_id)
            if role is not None:
                msg = get_translation("Role {0} set as role for commands that manage Minecraft server") \
                    .format(role.mention)
        if role is None:
            msg = get_translation("Role for commands that manage Minecraft server not stated")
        msg += "\n"
        role = None

        if Config.get_settings().bot_settings.admin_role_id is not None:
            role = self._bot.guilds[0].get_role(Config.get_settings().bot_settings.admin_role_id)
            if role is not None:
                msg += get_translation("Role {0} set as admin role for bot").format(role.mention)
        if role is None:
            msg += get_translation("Admin role not stated")
        await ctx.channel.send(msg)

    @role.group(pass_context=True, name="command", invoke_without_command=True, ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def r_command(self, ctx, role: Role):
        Config.get_settings().bot_settings.managing_commands_role_id = role.id
        Config.save_config()
        await ctx.channel.send(
            get_translation("Role {0} set as role for commands that manage Minecraft server").format(role.mention))

    @r_command.command(pass_context=True, name="clear")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def r_c_clear(self, ctx):
        Config.get_settings().bot_settings.managing_commands_role_id = None
        Config.save_config()
        await ctx.channel.send(add_quotes(get_translation("Role for commands that manage "
                                                          "Minecraft server has been cleared")))

    @role.group(pass_context=True, name="admin", invoke_without_command=True, ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def r_admin(self, ctx, role: Role):
        Config.get_settings().bot_settings.admin_role_id = role.id
        Config.save_config()
        await ctx.channel.send(get_translation("Role {0} set as admin role for bot").format(role.mention))

    @r_admin.command(pass_context=True, name="clear")
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    @decorators.has_admin_role()
    async def r_a_clear(self, ctx):
        Config.get_settings().bot_settings.admin_role_id = None
        Config.save_config()
        await ctx.channel.send(add_quotes(get_translation("Admin role has been cleared")))

    @commands.group(pass_context=True)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def edit(self, ctx, *, edited_message: str):
        if not Config.get_cross_platform_chat_settings().enable_cross_platform_chat:
            await send_msg(ctx, add_quotes(get_translation("Cross-platform chat is disabled in bot config!")), True)
        elif Config.get_cross_platform_chat_settings().channel_id is None:
            await send_msg(ctx, add_quotes(
                get_translation("Channel for Minecraft cross-platform chat is not found or unreachable!")), True)
        elif ctx.message.reference is not None and ctx.message.reference.resolved.author.discriminator != "0000":
            await send_msg(ctx, add_quotes(get_translation("You can't edit messages from "
                                                           "other members with this command!")), True)
        elif ctx.channel.id == Config.get_cross_platform_chat_settings().channel_id:
            last_message = None
            if ctx.message.reference is not None:
                associated_member_id = [u.user_discord_id for u in Config.get_known_users_list()
                                        if u.user_minecraft_nick == ctx.message.reference.resolved.author.name]
                if len(associated_member_id) > 0 and associated_member_id[0] == ctx.message.author.id:
                    last_message = ctx.message.reference.resolved
                else:
                    await send_msg(ctx,
                                   get_translation("{0}, this nick isn't bound to you, use `{1}associate add` first...")
                                   .format(ctx.author.mention, Config.get_settings().bot_settings.prefix), True)
            else:
                associated_nicks = [u.user_minecraft_nick for u in Config.get_known_users_list()
                                    if u.user_discord_id == ctx.author.id]
                if len(associated_nicks) > 0:
                    async for message in ctx.channel.history(limit=100):
                        if message.author.discriminator == "0000" and message.author.name in associated_nicks:
                            last_message = message
                            break
                    if last_message is None:
                        await send_msg(ctx, add_quotes(
                            get_translation("The bot couldn't find any messages sent by your "
                                            "bound Minecraft accounts in the last 100 messages!")), True)
                else:
                    await send_msg(ctx, get_translation("{0}, you have no bound nicks").format(ctx.author.mention),
                                   True)

            if last_message is not None:
                try:
                    # TODO: In discord.py 2.0 will be added 'message.attachments' to 'webhook.edit_message'
                    BotVars.webhook_chat.edit_message(message_id=last_message.id,
                                                      content=edited_message)
                    await handle_message_for_chat(ctx.message, self._bot, on_edit=True,
                                                  before_message=last_message, edit_command=True)
                except Forbidden:
                    error_msg = get_translation("Can't edit this message, it's not owned "
                                                "by cross-platform chat webhook!")
                    webhook_found = False
                    for i in (await self._bot.guilds[0].webhooks()):
                        if i.id == last_message.author.id:
                            webhook_found = True
                            error_msg += "\n" + get_translation("Owner: ") + f"<@{i.id}>"
                            break
                    if not webhook_found:
                        error_msg += "\n" + get_translation("Owner: ") + last_message.author.name

                    await send_msg(ctx, error_msg, True)
        else:
            await send_msg(ctx, add_quotes(get_translation("You're not in channel for Minecraft cross-platform chat!")),
                           True)
        await delete_after_by_msg(ctx.message)

    @commands.Cog.listener()
    async def on_message(self, message):
        if Config.get_cross_platform_chat_settings().enable_cross_platform_chat and \
                message.channel.id == Config.get_cross_platform_chat_settings().channel_id:
            await handle_message_for_chat(message, self._bot)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if Config.get_cross_platform_chat_settings().enable_cross_platform_chat and \
                payload.channel_id == Config.get_cross_platform_chat_settings().channel_id:
            after_channel = self._bot.get_channel(payload.channel_id)
            if after_channel is None:
                after_channel = await self._bot.fetch_channel(payload.channel_id)
            after_message = await after_channel.fetch_message(payload.message_id)

            if payload.cached_message is not None and after_message.content == payload.cached_message.content and \
                    after_message.attachments == payload.cached_message.attachments:
                return
            await handle_message_for_chat(after_message, self._bot,
                                          on_edit=True, before_message=payload.cached_message)

    @commands.command(pass_context=True, aliases=["lang"], ignore_extra=False)
    @commands.bot_has_permissions(send_messages=True, view_channel=True)
    @commands.guild_only()
    async def language(self, ctx, set_language: str = ""):
        """Get/Select language"""
        if len(set_language) > 0:
            if not set_locale(set_language):
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
    @commands.guild_only()
    async def prefix(self, ctx, *, new_prefix: str = ""):
        if not new_prefix:
            await ctx.send(add_quotes(get_translation("Current prefix - '{0}'.")
                                      .format(Config.get_settings().bot_settings.prefix)))
        else:
            if Config.get_settings().bot_settings.managing_commands_role_id is not None and \
                    Config.get_settings().bot_settings.managing_commands_role_id not in (e.id for e in
                                                                                         ctx.author.roles):
                await send_error(ctx, self._bot,
                                 commands.MissingRole(Config.get_settings().bot_settings.managing_commands_role_id))
                return

            if len(new_prefix.split()) > 1:
                await ctx.send(add_quotes(get_translation("Prefix can't have spaces!")))
            else:
                check = Config.get_settings().bot_settings.prefix == new_prefix
                Config.get_settings().bot_settings.prefix = new_prefix
                Config.save_config()
                await ctx.send(add_quotes(get_translation("Changed prefix to '{0}'.").format(new_prefix) +
                                          (" ( ͡° ͜ʖ ͡°)" if check else "")))

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
            raise HelpCommandArgument()
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
            await delete_after_by_msg(ctx.message, without_delay=True)
            emb = discord.Embed(title=get_translation("List of all commands, prefix - {0}")
                                .format(Config.get_settings().bot_settings.prefix),
                                color=discord.Color.gold())
            for c in sorted(self._bot.commands, key=lambda i: i.name):
                params, _ = parse_params_for_help(c.clean_params, "")
                subcommands = parse_subcommands_for_help(c)[0]
                emb.add_field(name=f"__`{c.name}" + ("/" + "/".join(c.aliases) if len(c.aliases) > 0 else "") + "`__" +
                                   (" " + " | ".join(subcommands) if len(subcommands) else "") +
                                   (" |" if len(subcommands) and len(params) else "") + params,
                              value=add_quotes("\n" + get_translation(f"help_brief_{c.name}")), inline=False)
            emb.set_footer(text=get_translation("Values in [square brackets] are optional.\n"
                                                "Values in <angle brackets> have to be provided by you.\n"
                                                "The | sign means one or the other.\n"
                                                "Use '{prefix}help' command for more info.\n"
                                                "Or '{prefix}command {arg_list}' for short.")
                           .format(prefix=Config.get_settings().bot_settings.prefix,
                                   arg_list=" | ".join(Config.get_settings().bot_settings.help_arguments)))
            await ctx.send(embed=emb)

    @commands.group(pass_context=True, aliases=["cls"], invoke_without_command=True)
    @decorators.bot_has_permissions_with_dm(manage_messages=True, send_messages=True, mention_everyone=True,
                                            add_reactions=True, embed_links=True, read_message_history=True,
                                            view_channel=True)
    @decorators.has_permissions_with_dm(manage_messages=True)
    async def clear(self, ctx, count: int = 1, mentions: commands.Greedy[Union[Member, Role]] = None):
        if not isinstance(ctx.channel, DMChannel):
            await bot_clear(ctx, self._IndPoll, count=count, discord_mentions=mentions)
        else:
            await bot_dm_clear(ctx, self._bot, count=count)

    @clear.command(pass_context=True, name="all")
    @decorators.bot_has_permissions_with_dm(manage_messages=True, send_messages=True, mention_everyone=True,
                                            add_reactions=True, embed_links=True, read_message_history=True,
                                            view_channel=True)
    @decorators.has_permissions_with_dm(manage_messages=True)
    async def c_all(self, ctx, mentions: commands.Greedy[Union[Member, Role]] = None):
        if not isinstance(ctx.channel, DMChannel):
            await bot_clear(ctx, self._IndPoll, subcommand="all", discord_mentions=mentions)
        else:
            await bot_dm_clear(ctx, self._bot, subcommand="all")

    @clear.command(pass_context=True, name="reply", aliases=["to"])
    @decorators.bot_has_permissions_with_dm(manage_messages=True, send_messages=True, mention_everyone=True,
                                            add_reactions=True, embed_links=True, read_message_history=True,
                                            view_channel=True)
    @decorators.has_permissions_with_dm(manage_messages=True)
    async def c_reply(self, ctx, mentions: commands.Greedy[Union[Member, Role]] = None):
        if ctx.message.reference is not None:
            if not isinstance(ctx.channel, DMChannel):
                await bot_clear(ctx, self._IndPoll, subcommand="reply", discord_mentions=mentions)
            else:
                await bot_dm_clear(ctx, self._bot, subcommand="reply")
        else:
            await ctx.send(get_translation("You didn't provide reply in your message!"))

    @tasks.loop()
    async def rss_feed_task(self):
        await check_on_rss_feed()

    @rss_feed_task.before_loop
    async def before_rss_feed(self):
        await self._bot.wait_until_ready()
        print(get_translation("Starting RSS feed check"))

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        await send_error(ctx, self._bot, error)
