from os import system
from sys import platform, exit, argv
from threading import enumerate as threads
from traceback import format_exc

from colorama import Fore, Style
from discord import Intents, Permissions
from discord.errors import LoginFailure
from discord.ext import commands
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from commands.chat_commands import ChatCommands
from commands.minecraft_commands import MinecraftCommands
from commands.poll import Poll
from components.additional_funcs import Print_file_handler
from components.localization import get_translation, RuntimeTextHandler
from config.init_config import Config, BotVars

if platform == "win32":
    from colorama import init

VERSION = "1.1.4"


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
    if platform == "win32":
        init(autoreset=True)
    if len(argv) > 1 and argv[1] not in ["-v", "--version", "-g"]:
        print("Bot doesn't have this command line argument!")
        exit(0)
    if len(argv) > 1 and (argv[1] == "-v" or argv[1] == "--version"):
        print(VERSION)
        exit(0)
    try:
        if len(argv) == 1:
            Config.read_config()
        bot = commands.Bot(command_prefix=get_prefix, intents=Intents.all())
        bot.remove_command('help')
        cog_list = [ChatCommands, MinecraftCommands]
        poll = Poll(bot)
        for command in ["clear", "stop", "backup_del", "backup_del_all"]:
            poll.add_awaiting_command(command)
        for i in cog_list:
            bot.add_cog(i(bot, poll))
        bot.add_cog(poll)

        create_pot_lines(bot)

        if Config.get_cross_platform_chat_settings().enable_cross_platform_chat:
            BotVars.bot_for_webhooks = bot

        Print_file_handler()
        Config.read_server_info()
        print(get_translation("Server info read!"))
        bot.run(Config.get_settings().bot_settings.token)
    except LoginFailure:
        print(get_translation("Bot/Discord Error: Your token is wrong"))
    except RuntimeError as e:
        print(get_translation("Bot Error: {0}").format("".join(e.args)))
    except (ScannerError, ParserError) as e:
        print(get_translation("Bot Error: {0}").format(e.problem.capitalize()) +
              f"\n{Style.DIM}{Fore.RED}{e.problem_mark}{Style.RESET_ALL}")
    except SystemExit:
        pass
    except BaseException:
        exc = format_exc().rstrip("\n")
        print(get_translation("Bot/Discord Error: Something went wrong") + " ( ͡° ͜ʖ ͡°)" +
              f"\n{Style.DIM}{Fore.RED}{exc}{Style.RESET_ALL}")
    finally:
        if len(argv) == 1:
            for thread in threads():
                if thread.getName() == "BackupsThread":
                    thread.join()
            if platform == "linux" or platform == "linux2":
                system("read")
            elif platform == "win32":
                system("pause")
        exit(0)


if __name__ == '__main__':
    main()
