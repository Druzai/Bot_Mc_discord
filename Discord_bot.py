from os import system
from sys import platform

from discord.errors import LoginFailure
from discord.ext import commands

from commands.bot_commands import Main_commands
from commands.poll import Poll
from config.init_config import Config


# TODO: features
#  Make rus/eng localization and get it from dict from file or so


def main():
    Config.read_config()
    bot = commands.Bot(command_prefix='%', description="Server bot")
    bot.remove_command('help')
    cog_list = [Main_commands, Poll]
    for i in cog_list:
        bot.add_cog(i(bot))

    try:
        bot.run(Config.get_token())
    except LoginFailure:
        print("Bot/Discord Error: Your token is wrong.")
    except BaseException:
        print("Bot/Discord Error: Something wrong :)")


if __name__ == '__main__':
    main()
    if platform == "linux" or platform == "linux2":
        system("read")
    elif platform == "win32":
        system("pause")
