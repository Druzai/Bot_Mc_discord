import socket
from asyncio import Task, CancelledError
from contextlib import contextmanager, suppress, asynccontextmanager
from re import search, findall
from traceback import format_exception
from typing import Optional, Union

from colorama import Style, Fore
from discord import (
    Member, TextChannel, VoiceChannel, Thread as ChannelThread, GroupChannel, Interaction, Client
)
from discord.ext import commands

from cogs.functions.help import get_param_type
from components.constants import URL_REGEX
from components.decorators import MissingAdminPermissions
from components.localization import get_translation
from components.utils import send_interaction, add_quotes, get_author, send_msg, get_role_string, func_name
from config.init_config import Config, BotVars


@asynccontextmanager
async def handle_rcon_error(ctx: Optional[commands.Context], interaction: Interaction = None, is_reaction=False):
    try:
        yield
    except (ConnectionError, socket.error):
        if BotVars.is_server_on:
            await send_interaction(
                interaction,
                add_quotes(get_translation("Couldn't connect to server. Try again.")),
                ctx=ctx,
                is_reaction=is_reaction
            )
        else:
            await send_interaction(
                interaction,
                add_quotes(get_translation("server offline").capitalize()),
                ctx=ctx,
                is_reaction=is_reaction
            )


def _ignore_some_tasks_errors(task: Task):
    with suppress(CancelledError, ConnectionResetError):
        task.result()


class HelpCommandArgument(commands.CheckFailure):
    pass


class BadIPv4Address(commands.BadArgument):
    def __init__(self, ip_address: str):
        self.argument = ip_address
        super().__init__(f"\"{ip_address}\" is not a recognised IPv4 address.")


class IPv4Address(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if search(r"^((25[0-5]|(2[0-4]|1\d|[1-9]|)\d)(\.(?!$)|$)){4}$", argument):
            return argument
        raise BadIPv4Address(argument)


class BadURLAddress(commands.BadArgument):
    def __init__(self, url: str):
        self.argument = url
        super().__init__(f"\"{url}\" is not a recognised URL address.")


class URLAddress(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str):
        if search(URL_REGEX, argument):
            return argument
        raise BadURLAddress(argument)


# Handling errors
async def send_error(
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel],
        bot: commands.Bot,
        error: Union[commands.CommandError, commands.CommandInvokeError],
        is_reaction=False
):
    author = get_author(ctx, bot, is_reaction)
    parsed_input = None
    if hasattr(error, "param"):
        error_param_type = get_param_type(error.param)
        error_param_name = error.param.name
    else:
        error_param_type = ""
        error_param_name = ""
    if hasattr(error, "argument") and isinstance(error.argument, str):
        parsed_input = await commands.clean_content(fix_channel_mentions=True).convert(ctx, error.argument)
    if parsed_input is None:
        parsed_input = await commands.clean_content(fix_channel_mentions=True) \
            .convert(ctx, ctx.message.content[ctx.view.previous:ctx.view.index])

    if isinstance(error, commands.MissingRequiredArgument):
        print(get_translation("{0} didn't input the argument '{1}' of type '{2}' in command '{3}'")
              .format(author, error_param_name, error_param_type,
                      f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Required argument '{0}' of type '{1}' is missing!")
                                  .format(error_param_name, error_param_type)),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.TooManyArguments):
        print(get_translation("{0} passed too many arguments to command '{1}'")
              .format(author, f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("You passed too many arguments to this command!")),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.MemberNotFound):
        print(get_translation("{0} passed member mention '{1}' that can't be found").format(author, parsed_input))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Member '{0}' not found!").format(parsed_input)),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.UserNotFound):
        print(get_translation("{0} passed user mention '{1}' that can't be found").format(author, parsed_input))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("User '{0}' not found!").format(parsed_input)),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.RoleNotFound):
        print(get_translation("{0} passed role mention '{1}' that can't be found"))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Role '{0}' not found!").format(parsed_input)),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.ChannelNotReadable):
        print(get_translation("Bot can't read messages in channel '{0}'").format(error.argument))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Bot can't read messages in channel '{0}'")
                                  .format(error.argument) + "!"),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.ChannelNotFound):
        print(get_translation("{0} passed channel mention '{1}' that can't be found").format(author, parsed_input))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Channel '{0}' not found!").format(parsed_input)),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.ThreadNotFound):
        print(get_translation("{0} passed thread mention '{1}' that can't be found").format(author, parsed_input))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Thread '{0}' not found!").format(parsed_input)),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.BadBoolArgument):
        print(get_translation("{0} passed bad bool argument '{1}'").format(author, parsed_input))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Bot couldn't convert bool argument '{0}'!").format(parsed_input)),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.BadLiteralArgument):
        print(get_translation("{0} passed bad literal '{1}'").format(author, parsed_input))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation(
                           "Bot couldn't find argument '{0}' in any of these values: {1}!"
                       ).format(parsed_input, str(error.literals).strip("()"))),
                       is_reaction=is_reaction)
    elif isinstance(error, BadIPv4Address):
        print(get_translation("{0} passed an invalid IPv4 address as argument '{1}'").format(author, parsed_input))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Bot couldn't convert argument '{0}' "
                                                  "to an IPv4 address!").format(parsed_input)),
                       is_reaction=is_reaction)
    elif isinstance(error, BadURLAddress):
        print(get_translation("{0} passed an invalid URL as argument '{1}'").format(author, parsed_input))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Bot couldn't convert argument '{0}' "
                                                  "to a URL!").format(parsed_input)),
                       is_reaction=is_reaction)
    elif isinstance(error, (commands.BadArgument, commands.ArgumentParsingError)):
        conv_args = findall(r"Converting to \".+\" failed for parameter \".+\"\.", "".join(error.args))
        if len(conv_args) > 0:
            conv_args = findall(r"\"([^\"]+)\"", conv_args[0])
        if len(conv_args) > 0:
            print(get_translation("{0} passed parameter '{2}' in string \"{3}\" that bot couldn't "
                                  "convert to type '{1}' in command '{4}'")
                  .format(author, *conv_args, parsed_input,
                          f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
            await send_msg(ctx, f"{author.mention}\n" +
                           add_quotes(get_translation("Bot didn't recognized parameter '{1}'\n"
                                                      "Received: '{2}'\n"
                                                      "Expected: value of type '{0}'"))
                           .format(*conv_args, parsed_input),
                           is_reaction=is_reaction)
        else:
            print(get_translation("{0} passed string \"{1}\" that can't be parsed in command '{2}'")
                  .format(author, parsed_input, f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
            await send_msg(ctx, f"{author.mention}\n" +
                           add_quotes(get_translation("Bot couldn't parse user "
                                                      "string '{0}' in this command!").format(parsed_input)),
                           is_reaction=is_reaction)
    elif isinstance(error, commands.MissingPermissions):
        await send_msg(ctx, f"{author.mention}\n" + add_quotes(await get_missing_permissions_message(error, author)),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.BotMissingPermissions):
        print(get_translation("Bot doesn't have some permissions"))
        missing_perms = [get_translation(perm.replace("_", " ").replace("guild", "server").title())
                         for perm in error.missing_permissions]
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("Bot don't have these permissions to run this command:")
                                  .capitalize() + "\n- " + "\n- ".join(missing_perms)), is_reaction=is_reaction)
    elif isinstance(error, commands.MissingRole):
        await send_msg(ctx, f"{author.mention}\n" + add_quotes(await get_missing_role_message(error, bot, author)),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.CommandNotFound):
        print(get_translation("{0} entered non-existent command").format(author))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("You entered non-existent command!")), is_reaction=is_reaction)
    elif isinstance(error, commands.UserInputError):
        print(get_translation("{0} entered wrong argument(s) of command '{1}'")
              .format(author, f"{Config.get_settings().bot_settings.prefix}{ctx.command}"))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("You entered wrong argument(s) of this command!")),
                       is_reaction=is_reaction)
    elif isinstance(error, commands.DisabledCommand):
        print(get_translation("{0} entered disabled command").format(author))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("You entered disabled command!")), is_reaction=is_reaction)
    elif isinstance(error, commands.NoPrivateMessage):
        print(get_translation("{0} entered a command that only works in the guild").format(author))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("This command only works on server!")), is_reaction=is_reaction)
    elif isinstance(error, commands.CommandOnCooldown):
        cooldown_retry = round(error.retry_after, 1) if error.retry_after < 1 else int(error.retry_after)
        if isinstance(cooldown_retry, float) and cooldown_retry.is_integer():
            cooldown_retry = int(cooldown_retry)
        print(get_translation("{0} triggered a command more than {1} time(s) per {2} sec")
              .format(author, error.cooldown.rate, int(error.cooldown.per)))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(get_translation("You triggered this command more than {0} time(s) per {1} sec.\n"
                                                  "Try again in {2} sec...").format(error.cooldown.rate,
                                                                                    int(error.cooldown.per),
                                                                                    cooldown_retry)),
                       is_reaction=is_reaction)
    elif isinstance(error, HelpCommandArgument):
        pass
    elif isinstance(error, MissingAdminPermissions):
        msg = ""
        if Config.get_settings().bot_settings.admin_role_id is not None:
            msg += await get_missing_role_message(
                commands.MissingRole(Config.get_settings().bot_settings.admin_role_id),
                bot,
                author
            ) + "\n\n"
        msg += await get_missing_permissions_message(commands.MissingPermissions(['administrator']), author)
        await send_msg(ctx, f"{author.mention}\n" + add_quotes(msg), is_reaction=is_reaction)
    else:
        print_unhandled_error(error.original, get_translation("Ignoring exception in command '{0}{1}':")
                              .format(Config.get_settings().bot_settings.prefix, ctx.command))
        await send_msg(ctx, f"{author.mention}\n" +
                       add_quotes(error.original.__class__.__name__ +
                                  (": " + ", ".join([str(a) for a in error.original.args])
                                   if len(error.original.args) > 0 else "")), is_reaction=is_reaction)


def print_unhandled_error(error, error_title: str):
    exc = "".join(format_exception(type(error), error, error.__traceback__)).rstrip("\n")
    print(f"{error_title}\n{Fore.RED}{exc}{Style.RESET_ALL}")


async def get_missing_role_message(
        error: commands.MissingRole,
        bot: Union[commands.Bot, Client],
        author: Member,
        interaction=False
):
    if isinstance(error.missing_role, int):
        role = await get_role_string(bot, error.missing_role)
    else:
        role = error.missing_role
    if interaction:
        print(get_translation("{0} don't have role '{1}' to use interaction").format(author, role))
        return get_translation("You don't have role '{0}' to use this interaction!").format(role)
    print(get_translation("{0} don't have role '{1}' to run command").format(author, role))
    return get_translation("You don't have role '{0}' to run this command!").format(role)


async def get_missing_permissions_message(
        error: commands.MissingPermissions,
        author: Member,
        interaction=False
):
    missing_perms = [get_translation(perm.replace("_", " ").replace("guild", "server").title())
                     for perm in error.missing_permissions]
    if interaction:
        print(get_translation("{0} don't have some permissions to use interaction").format(author))
        return get_translation("You don't have these permissions to use this interaction:").capitalize() + \
               "\n- " + "\n- ".join(missing_perms)
    print(get_translation("{0} don't have some permissions to run command").format(author))
    return get_translation("You don't have these permissions to run this command:").capitalize() + \
           "\n- " + "\n- ".join(missing_perms)


async def send_error_on_interaction(
        view_name: str,
        interaction: Interaction,
        ctx: Union[commands.Context, TextChannel, VoiceChannel, ChannelThread, GroupChannel, None],
        error: Union[commands.CommandError, Exception],
        is_reaction=False
):
    author = interaction.user

    if isinstance(error, commands.MissingPermissions):
        await send_interaction(
            interaction,
            f"{author.mention}\n" + add_quotes(await get_missing_permissions_message(error, author, interaction=True)),
            ephemeral=True,
            ctx=ctx,
            is_reaction=is_reaction
        )
    elif isinstance(error, commands.MissingRole):
        await send_interaction(
            interaction,
            f"{author.mention}\n" +
            add_quotes(await get_missing_role_message(error, interaction.client, author, interaction=True)),
            ephemeral=True,
            ctx=ctx,
            is_reaction=is_reaction
        )
    elif isinstance(error, MissingAdminPermissions):
        msg = ""
        if Config.get_settings().bot_settings.admin_role_id is not None:
            msg += await get_missing_role_message(
                commands.MissingRole(Config.get_settings().bot_settings.admin_role_id),
                interaction.client,
                author,
                interaction=True
            ) + "\n\n"
        msg += await get_missing_permissions_message(
            commands.MissingPermissions(['administrator']),
            author,
            interaction=True
        )
        await send_interaction(
            interaction,
            f"{author.mention}\n" + add_quotes(msg),
            ephemeral=True,
            ctx=ctx,
            is_reaction=is_reaction
        )
    else:
        await send_interaction(
            interaction,
            f"{author.mention}\n" + get_translation("This interaction failed! Try again!") + \
            add_quotes(error.__class__.__name__ +
                       (": " + ", ".join([str(a) for a in error.args]) if len(error.args) > 0 else "")),
            ctx=ctx,
            is_reaction=is_reaction
        )
        if isinstance(ctx, commands.Context):
            ignore_message = get_translation("Ignoring exception in view '{0}' created by command '{1}':") \
                .format(view_name, str(ctx.command))
        else:
            ignore_message = get_translation("Ignoring exception in view '{0}':").format(view_name)
        print_unhandled_error(error, ignore_message)


@contextmanager
def handle_unhandled_error_in_task(func_number: int = 2):
    try:
        yield
    except (KeyboardInterrupt, CancelledError):
        pass
    except BaseException as error:
        print_unhandled_error(error, get_translation("Ignoring exception in internal background task '{0}':")
                              .format(func_name(func_number=func_number + 1)))


@contextmanager
def handle_unhandled_error_in_events(func_number: int = 2):
    try:
        yield
    except KeyboardInterrupt:
        pass
    except BaseException as error:
        print_unhandled_error(error, get_translation("Ignoring exception in internal event '{0}':")
                              .format(func_name(func_number=func_number + 1)))
