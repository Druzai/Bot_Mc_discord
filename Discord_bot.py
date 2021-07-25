from os import system
from sys import platform, exit
from traceback import print_exc

from discord import Intents
from discord.errors import LoginFailure
from discord.ext import commands

from commands.chat_commands import Chat_commands
from commands.minecraft_commands import Minecraft_commands
from commands.poll import Poll
from components.rss_feed_handle import create_feed_webhook, check_on_rss_feed
from config.init_config import Config, Bot_variables


# TODO: features
#  Make rus/eng localization and get it from dict from file or so and setup *.spec file!
#  Continuously rewrite code in classes
#  Check process status when bot starts and instantly checking process? maybe checking latest.log would help
#  Remove opcodes, assoc already does that, replace with counters, save it in StartStopStates.json
#  Доделать пересыльный чат: экранизацию посмотреть
#  Сделать отправку об выключении/перезагрузке через tellraw тоже
#  https://github.com/MyTheValentinus/minecraftTellrawGenerator
#  Сделать ограничения на использование комманд в дме и на серве
#  Поработать над упоминаниями на майн и из майна, Regex @\.+ | в процессе + id-to-nicks.json
#  Переработать конфиг в классы и сделать сохранение в yaml
#  Мб добавить вывод игрок подкл, откл и причина
# [23:53:40] [Server thread/INFO]: jokobaba lost connection: Timed out
# [23:53:40] [Server thread/INFO]: jokobaba left the game
# [23:53:55] [Server thread/INFO]: jokobaba joined the game
# [23:55:07] [Server thread/INFO]: Dedicated407 has completed the challenge [Cover Me in Debris]

# TODO: wait for discord.py 2.0.0, (move to python 3.9 or 3.10)
#  to rewrite webhooks
#  + add webhook creating/modifying (channel_id in https://discord.com/developers/docs/resources/webhook#modify-webhook)
#  replace reactions with buttons in menu and poll
#  https://github.com/Rapptz/discord.py/blob/master/examples/views/persistent.py
#  maybe add slash commands via separate `Slash` Cog


def main():
    Config.read_config()
    intents = Intents.default()
    intents.members = True
    bot = commands.Bot(command_prefix=commands.when_mentioned_or(Config.get_prefix()),
                       description="Server bot",
                       intents=intents)
    bot.remove_command('help')
    cog_list = [Chat_commands, Minecraft_commands, Poll]
    for i in cog_list:
        bot.add_cog(i(bot))

    Config.read_server_info()
    print("Server info read!")

    if Config.get_webhook_rss():
        create_feed_webhook()
        bot.loop.create_task(check_on_rss_feed())

    if Config.get_webhook_chat():
        Bot_variables.bot_for_webhooks = bot

    try:
        bot.run(Config.get_token())
    except LoginFailure:
        print("Bot/Discord Error: Your token is wrong.")
    except BaseException:
        print("Bot/Discord Error: Something wrong :)")
        print_exc()
    finally:
        if platform == "linux" or platform == "linux2":
            system("read")
        elif platform == "win32":
            system("pause")
        exit(0)


if __name__ == '__main__':
    main()
