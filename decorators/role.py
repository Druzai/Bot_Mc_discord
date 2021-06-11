from discord.abc import GuildChannel
from discord.ext.commands import NoPrivateMessage, MissingRole
from discord.ext.commands.core import check
from discord.utils import get as utils_get

from config.init_config import Config


def has_role_if_given_in_config():
    def predicate(ctx):
        config_role = Config.get_role()
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
