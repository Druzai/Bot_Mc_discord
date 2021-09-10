from os import system
from sys import platform, exit, argv
from traceback import print_exc

from discord import Intents
from discord.errors import LoginFailure
from discord.ext import commands

from commands.chat_commands import ChatCommands
from commands.minecraft_commands import MinecraftCommands
from commands.poll import Poll
from components.localization import get_translation, RuntimeTextHandler
from components.rss_feed_handle import create_feed_webhook, check_on_rss_feed
from config.init_config import Config, BotVars


# TODO: features
#  Continuously rewrite code in classes
#  Сделать отправку об выключении/перезагрузке через tellraw тоже
#  https://github.com/MyTheValentinus/minecraftTellrawGenerator
#  Мб добавить команду смены префикса команд...
#  При обратном отсчёте использовать tellraw или title в stop_server
#  Сделать список из гуи дискорда для %servs select и комманда для музыки из майнкрафта
#  Мб добавить вывод игрок подкл, откл и причина
# [23:53:40] [Server thread/INFO]: jokobaba lost connection: Timed out
# [23:53:40] [Server thread/INFO]: jokobaba left the game
# [23:53:55] [Server thread/INFO]: jokobaba joined the game
# [23:55:07] [Server thread/INFO]: Dedicated407 has completed the challenge [Cover Me in Debris]

# TODO: wait for discord.py 2.0.0 (archived), (move to python 3.9 or 3.10)
#  to rewrite webhooks
#  + add webhook creating/modifying (channel_id in https://discord.com/developers/docs/resources/webhook#modify-webhook)
#  replace reactions with buttons in menu and poll
#  https://github.com/Rapptz/discord.py/blob/master/examples/views/persistent.py
#  maybe add slash commands via separate `Slash` Cog

def _create_pot_lines_for_subcommands(command, find_str: str):
    if not hasattr(command, "all_commands") or len(command.all_commands) == 0:
        return

    for subcommand in command.all_commands.values():
        RuntimeTextHandler.add_translation(f"{find_str}_{subcommand.name}")
        for arg in subcommand.clean_params.keys():
            RuntimeTextHandler.add_translation(f"{find_str}_{subcommand.name}_{arg}")
        _create_pot_lines_for_subcommands(subcommand, f"{find_str}_{subcommand.name}")


def create_pot_lines(bot: commands.Bot):
    if len(argv) > 1 and argv[1] == "-g":
        for command in bot.commands:
            RuntimeTextHandler.add_translation(f"help_brief_{command.name}")
            RuntimeTextHandler.add_translation(f"help_{command.name}")
            for arg in command.clean_params.keys():
                RuntimeTextHandler.add_translation(f"help_{command.name}_{arg}")
            _create_pot_lines_for_subcommands(command, f"help_{command.name}")
        RuntimeTextHandler.freeze_translation()
        exit(0)


def main():
    Config.read_config()
    intents = Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix=commands.when_mentioned_or(Config.get_settings().bot_settings.prefix),
                       intents=intents)
    bot.remove_command('help')
    cog_list = [ChatCommands, MinecraftCommands, Poll]
    for i in cog_list:
        bot.add_cog(i(bot))

    create_pot_lines(bot)

    Config.read_server_info()
    print(get_translation("Server info read!"))

    if Config.get_rss_feed_settings().enable_rss_feed:
        create_feed_webhook()
        bot.loop.create_task(check_on_rss_feed())

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
