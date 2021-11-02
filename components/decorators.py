from discord import DMChannel, Permissions
from discord.abc import GuildChannel
from discord.ext.commands import NoPrivateMessage, MissingRole, CommandError, BotMissingPermissions
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


def bot_has_permissions_with_dm(**perms):
    invalid = set(perms) - set(Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError('Invalid permission(s): %s' % (', '.join(invalid)))

    def predicate(ctx):
        guild = ctx.guild
        me = guild.me if guild is not None else ctx.bot.user
        permissions: Permissions = ctx.channel.permissions_for(me)

        if isinstance(ctx.channel, DMChannel):
            perms["manage_messages"] = False

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise BotMissingPermissions(missing)

    return check(predicate)