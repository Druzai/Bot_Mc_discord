from typing import Union

from discord import Permissions
from discord.ext import commands

from Discord_bot import build_bot
from components.localization import RuntimeTextHandler


def _create_pot_lines_for_subcommands(command: Union[commands.Command, commands.Group], find_str: str):
    if not hasattr(command, "commands") or len(command.commands) == 0:
        return

    for subcommand in sorted(command.commands, key=lambda c: c.name):
        RuntimeTextHandler.add_translation(f"{find_str}_{subcommand.name}")
        for arg in sorted(subcommand.clean_params.keys()):
            RuntimeTextHandler.add_translation(f"{find_str}_{subcommand.name}_{arg}")
        _create_pot_lines_for_subcommands(subcommand, f"{find_str}_{subcommand.name}")


def create_pot_lines(bot: commands.Bot):
    for command in sorted(bot.commands, key=lambda c: c.name):
        RuntimeTextHandler.add_translation(f"help_brief_{command.name}")
        RuntimeTextHandler.add_translation(f"help_{command.name}")
        for arg in sorted(command.clean_params.keys()):
            RuntimeTextHandler.add_translation(f"help_{command.name}_{arg}")
        _create_pot_lines_for_subcommands(command, f"help_{command.name}")
    for perm in sorted(Permissions.VALID_FLAGS.keys()):
        RuntimeTextHandler.add_translation(perm.replace("_", " ").replace("guild", "server").title())
    RuntimeTextHandler.freeze_translation()


if __name__ == '__main__':
    create_pot_lines(build_bot(create_pot_lines=True))
