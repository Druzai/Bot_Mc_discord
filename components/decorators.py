from discord.abc import GuildChannel
from discord.ext.commands import NoPrivateMessage, MissingRole
from discord.ext.commands.core import check
from discord.utils import get as utils_get

from config.init_config import Config


# from functools import wraps
# import inspect


def has_role_or_default():
    def predicate(ctx):
        config_role = Config.get_settings().bot_settings.role
        if config_role == "":
            return True
        if not isinstance(ctx.channel, GuildChannel):
            raise NoPrivateMessage()

        if isinstance(config_role, int):
            role = utils_get(ctx.author.roles, id=config_role)
        else:
            role = utils_get(ctx.author.roles, name=config_role)
        if role is None:
            raise MissingRole(config_role)
        return True

    return check(predicate)


# def check_before_invocation(func):
#     @wraps(func)
#     async def predicate(ctx, *args, **kwargs):
#         if "-h" in ctx.message.content:
#             str_help = f"{Config.get_settings().bot_settings.prefix}{ctx.command.name}"
#             for key, par in ctx.command.clean_params.items():
#                 if par.annotation != inspect._empty:
#                     str_help += f" [{key}]: {par.annotation.__name__}"
#                 else:
#                     str_help += f" <{key}>: {type(par.default).__name__}"
#             await ctx.send(str_help)
#
#             await ctx.send(trnslt())
#         else:
#             return await func(ctx, *args, **kwargs)
#
#     return predicate
