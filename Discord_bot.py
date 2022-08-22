from asyncio import run
from sys import platform, exit, argv
from threading import enumerate as threads
from traceback import format_exc
from typing import Union

from colorama import Fore, Style
from discord import Intents, Permissions
from discord.errors import LoginFailure
from discord.ext import commands
from sshkeyboard import listen_keyboard, stop_listening
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from commands.chat_commands import ChatCommands
from commands.minecraft_commands import MinecraftCommands
from commands.poll import Poll
from components.additional_funcs import setup_print_handlers
from components.localization import get_translation, RuntimeTextHandler
from config.init_config import Config, BotVars

if platform == "win32":
    from colorama import init

VERSION = "1.3.2"


def _create_pot_lines_for_subcommands(command: Union[commands.Command, commands.Group], find_str: str):
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
            RuntimeTextHandler.add_translation(perm.replace("_", " ").replace("guild", "server").title())
        RuntimeTextHandler.freeze_translation()
        exit(0)


def get_prefix(bot, msg):
    return commands.when_mentioned(bot, msg) + [Config.get_settings().bot_settings.prefix]


def main():
    if len(argv) == 1 or (len(argv) > 1 and argv[1] not in ["-v", "--version", "-g"]):
        Config.init_with_system_language()
    if platform == "win32":
        init()
    if len(argv) > 1 and argv[1] not in ["-h", "--help", "-v", "--version", "-g", "-cs"]:
        print(get_translation("Bot doesn't have this command line argument!"))
        exit(0)
    if len(argv) > 1 and (argv[1] == "-h" or argv[1] == "--help"):
        print(get_translation("bot_help"))
        exit(0)
    if len(argv) > 1 and (argv[1] == "-v" or argv[1] == "--version"):
        print(VERSION)
        exit(0)
    try:
        if len(argv) == 1 or (len(argv) > 1 and argv[1] == "-cs"):
            Config.read_config(change_servers=(len(argv) > 1 and argv[1] == "-cs"))
            setup_print_handlers()
        bot = commands.Bot(command_prefix=get_prefix, intents=Intents.all(), help_command=None)

        async def add_cogs(bot: commands.Bot):
            for i in [Poll, ChatCommands, MinecraftCommands]:
                await bot.add_cog(i(bot))
            return bot

        bot = run(add_cogs(bot))
        create_pot_lines(bot)
        print(get_translation("Bot started!"))
        BotVars.bot_for_webhooks = bot
        Config.read_server_info()
        print(get_translation("Server info read!"))
        bot.run(Config.get_settings().bot_settings.token)
    except LoginFailure:
        print(get_translation("Bot/Discord Error: Your token is wrong"))
    except (RuntimeError, FileNotFoundError) as e:
        print(get_translation("Bot Error: {0}").format("".join(e.args)))
    except (ScannerError, ParserError) as e:
        print(get_translation("Bot Error: {0}").format(e.problem.capitalize()) +
              f"\n{Fore.RED}{e.problem_mark}{Style.RESET_ALL}")
    except (SystemExit, KeyboardInterrupt):
        pass
    except BaseException:
        exc = format_exc().rstrip("\n")
        print(get_translation("Bot/Discord Error: Something went wrong ( ͡° ͜ʖ ͡°)") +
              f"\n{Fore.RED}{exc}{Style.RESET_ALL}")
    finally:
        if len(argv) == 1 or (len(argv) > 1 and argv[1] == "-cs"):
            if BotVars.watcher_of_log_file is not None and BotVars.watcher_of_log_file.is_running():
                BotVars.watcher_of_log_file.stop()
            for thread in threads():
                if thread.name != "MainThread":
                    thread.join()
            print(get_translation("Press any key to continue..."))
            listen_keyboard(on_press=lambda _: stop_listening())
            print(get_translation("Bot is stopping..."))
        exit(0)


if __name__ == '__main__':
    main()
