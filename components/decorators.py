from discord import DMChannel
from discord.abc import GuildChannel
from discord.ext.commands import NoPrivateMessage, MissingRole, CommandError
from discord.ext.commands.core import check
from discord.utils import get as utils_get

from config.init_config import Config


def has_role_or_default():
    def predicate(ctx):
        config_role = Config.get_settings().bot_settings.role
        if isinstance(ctx.channel, DMChannel):
            return True

        if config_role != "" and utils_get(ctx.author.roles, name=config_role) is None:
            raise MissingRole(config_role)
        return True

    return check(predicate)


class MissingAdminPermissions(CommandError):
    pass


def is_admin(ctx):
    if not isinstance(ctx.channel, GuildChannel):
        raise NoPrivateMessage()

    admin_role = Config.get_settings().bot_settings.admin_role
    role = None if admin_role == "" else utils_get(ctx.author.roles, name=admin_role)
    if role is None and not ctx.author.guild_permissions.administrator:
        raise MissingAdminPermissions()
    return True


def has_admin_role():
    return check(is_admin)
