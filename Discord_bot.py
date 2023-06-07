from asyncio import run
from logging import ERROR, Formatter
from sys import exit, argv
from threading import enumerate as threads
from traceback import format_exc

from colorama import Fore, Style
from discord import Intents
from discord.errors import LoginFailure
from discord.ext import commands
from sshkeyboard import listen_keyboard, stop_listening
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from commands.chat_commands import ChatCommands
from commands.minecraft_commands import MinecraftCommands
from commands.poll import Poll
from components.additional_funcs import setup_print_handlers
from components.localization import get_translation
from config.init_config import Config, BotVars, OS

if Config.get_os() == OS.Windows:
    from colorama import init

VERSION = "1.4.4a"


def get_prefix(bot, msg):
    return commands.when_mentioned(bot, msg) + [Config.get_settings().bot_settings.prefix]


def build_bot(create_pot_lines=False) -> commands.Bot:
    bot = commands.Bot(command_prefix=get_prefix, intents=Intents.all(), help_command=None)

    async def add_cogs(bot: commands.Bot):
        for i in [Poll, MinecraftCommands, ChatCommands]:
            await bot.add_cog(i(bot, create_pot_lines))
        return bot

    bot = run(add_cogs(bot))
    return bot


def main():
    if len(argv) == 1 or (len(argv) > 1 and argv[1] not in ["-v", "--version"]):
        Config.init_with_system_language()
    if Config.get_os() == OS.Windows:
        init()
    if len(argv) > 1 and argv[1] not in ["-h", "--help", "-v", "--version", "-cs"]:
        print(get_translation("Bot doesn't have this command line argument!"))
        exit(0)
    if len(argv) > 1 and (argv[1] == "-h" or argv[1] == "--help"):
        print(get_translation("bot_help"))
        exit(0)
    if len(argv) > 1 and (argv[1] == "-v" or argv[1] == "--version"):
        print(VERSION)
        exit(0)
    if Config.get_os() == OS.MacOS:
        Config.setup_ca_file()
    try:
        if len(argv) == 1 or (len(argv) > 1 and argv[1] == "-cs"):
            Config.read_config(change_servers=(len(argv) > 1 and argv[1] == "-cs"))
            setup_print_handlers()

        bot = build_bot()
        print(get_translation("Bot started!"))
        BotVars.bot_for_webhooks = bot
        Config.read_server_info()
        print(get_translation("Server info read!"))
        bot.run(
            Config.get_settings().bot_settings.token,
            log_level=ERROR,
            log_formatter=Formatter("[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{")
        )
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
