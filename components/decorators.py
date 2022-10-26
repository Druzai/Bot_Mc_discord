from typing import Any, Union

from discord import DMChannel, Permissions
from discord.ext.commands import NoPrivateMessage, MissingRole, CommandError, BotMissingPermissions, MissingPermissions
from discord.ext.commands._types import BotT, Check
from discord.ext.commands.context import Context
from discord.ext.commands.core import check
from discord.interactions import Interaction
from discord.utils import get as utils_get

from config.init_config import Config


def is_minecrafter(ctx: Union[Context[BotT], Interaction]) -> bool:
    if isinstance(ctx, Context):
        if isinstance(ctx.channel, DMChannel):
            return True

        if ctx.guild is None:
            raise NoPrivateMessage()

    config_role_id = Config.get_settings().bot_settings.managing_commands_role_id
    if config_role_id is None:
        return True

    author_roles = ctx.author.roles if isinstance(ctx, Context) else ctx.user.roles
    if utils_get(author_roles, id=config_role_id) is None:
        raise MissingRole(config_role_id)
    return True


def has_role_or_default() -> Check[Any]:
    return check(is_minecrafter)


class MissingAdminPermissions(CommandError):
    pass


def is_admin(ctx: Union[Context[BotT], Interaction]) -> bool:
    if isinstance(ctx, Context) and ctx.guild is None:
        raise NoPrivateMessage()

    admin_role_id = Config.get_settings().bot_settings.admin_role_id
    author = ctx.author if isinstance(ctx, Context) else ctx.user
    role = None if admin_role_id is None else utils_get(author.roles, id=admin_role_id)
    if role is None and not author.guild_permissions.administrator:
        raise MissingAdminPermissions()
    return True


def has_admin_role() -> Check[Any]:
    return check(is_admin)


def has_permissions_with_dm(**perms) -> Check[Any]:
    invalid = set(perms) - set(Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    def predicate(ctx: Context[BotT]) -> bool:
        permissions = ctx.permissions

        if isinstance(ctx.channel, DMChannel):
            perms["manage_messages"] = False

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise MissingPermissions(missing)

    return check(predicate)


def bot_has_permissions_with_dm(**perms) -> Check[Any]:
    invalid = set(perms) - set(Permissions.VALID_FLAGS)
    if invalid:
        raise TypeError(f"Invalid permission(s): {', '.join(invalid)}")

    def predicate(ctx: Context[BotT]) -> bool:
        permissions = ctx.bot_permissions

        if isinstance(ctx.channel, DMChannel):
            perms["manage_messages"] = False

        missing = [perm for perm, value in perms.items() if getattr(permissions, perm) != value]

        if not missing:
            return True

        raise BotMissingPermissions(missing)

    return check(predicate)
