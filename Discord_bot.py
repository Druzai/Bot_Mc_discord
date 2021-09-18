from os import system
from sys import platform, exit, argv
from traceback import print_exc

from discord import Intents, Permissions
from discord.errors import LoginFailure
from discord.ext import commands

from commands.chat_commands import ChatCommands
from commands.minecraft_commands import MinecraftCommands
from commands.poll import Poll
from components.localization import get_translation, RuntimeTextHandler
from config.init_config import Config, BotVars


def _create_pot_lines_for_subcommands(command, find_str: str):
    if not hasattr(command, "commands") or len(command.commands) == 0:
        return

    for subcommand in sorted(command.commands, key=lambda c: c.name):
        RuntimeTextHandler.add_translation(f"{find_str}_{subcommand.name}")
        for arg in sorted(subcommand.clean_params.keys()):
            RuntimeTextHandler.add_translation(f"{find_str}_{subcommand.name}_{arg}")
        _create_pot_lines_for_subcommands(subcommand, f"{find_str}_{subcommand.name}")


def create_pot_lines(bot: commands.Bot):
    if len(argv) > 1 and argv[1] == "-g":
        for command in sorted(bot.commands, key=lambda c: c.name):
            RuntimeTextHandler.add_translation(f"help_brief_{command.name}")
            RuntimeTextHandler.add_translation(f"help_{command.name}")
            for arg in sorted(command.clean_params.keys()):
                RuntimeTextHandler.add_translation(f"help_{command.name}_{arg}")
            _create_pot_lines_for_subcommands(command, f"help_{command.name}")
        for perm in sorted(Permissions.VALID_FLAGS.keys()):
            RuntimeTextHandler.add_translation(perm.replace('_', ' ').replace('guild', 'server').title())
        RuntimeTextHandler.freeze_translation()
        exit(0)


def get_prefix(bot, msg):
    return commands.when_mentioned(bot, msg) + [Config.get_settings().bot_settings.prefix]


def main():
    Config.read_config()
    intents = Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix=get_prefix, intents=intents)
    bot.remove_command('help')
    cog_list = [ChatCommands, MinecraftCommands]
    poll = Poll(bot)
    for command in ["clear", "stop"]:
        poll.add_awaiting_command(command)
    for i in cog_list:
        bot.add_cog(i(bot, poll))
    bot.add_cog(poll)

    create_pot_lines(bot)

    Config.read_server_info()
    print(get_translation("Server info read!"))

    if Config.get_cross_platform_chat_settings().enable_cross_platform_chat:
        BotVars.bot_for_webhooks = bot

    try:
        bot.run(Config.get_settings().bot_settings.token)
    except LoginFailure:
        print(get_translation("Bot/Discord Error: Your token is wrong."))
    except BaseException:
        print(get_translation("Bot/Discord Error: Something went wrong") + " ( ͡° ͜ʖ ͡°)")
        print_exc()
    finally:
        if platform == "linux" or platform == "linux2":
            system("read")
        elif platform == "win32":
            system("pause")
        exit(0)


if __name__ == '__main__':
    main()
