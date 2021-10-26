<p align="center">
   <img src="images/bot.ico">
</p>

<h1 align="center">
   Bot for minecraft server in discord
</h1>

[![Build with pyinstaller and release](https://github.com/Druzai/Bot_Mc_discord/actions/workflows/pyinstaller_build.yml/badge.svg?branch=master)](https://github.com/Druzai/Bot_Mc_discord/actions/workflows/pyinstaller_build.yml)

## Main features

**Attention! This bot designed to work only on 1 discord server!**

* Managing minecraft server via discord bot:
    * Start the server
    * Stop the server
    * Restart the server
    * Get info about players on the server
    * Work with server whitelist
    * Autoload if the minecraft server crashes
    * Auto backup at specified intervals and forced backup by member
        * Auto deleting backup(s) if backup's limit or space exceeded
    * Make yourself an operator for limited amount of time if your discord account has association with minecraft nick
* Changing minecraft servers on the go while server is down
* Setting an optional role. If set then the bot commands for managing the minecraft server will require this role from
  the member
* Creating optional cross-platform chat between discord text channel and minecraft server via bot and webhook
    * Supported mentions in discord and minecraft (also for better recognition you can create list of associations
      between discord member and minecraft nick)
    * Supported discord reply in message
    * Supported url links (shortens if link longer than 256 symbols)
    * Supported attached files to message in discord
    * Half supported emojis
        * Custom emojis are converted to text with their own text name
        * Most of the standard unicode emojis are not processed by the vanilla minecraft server
* Setting up optional rss feed. Bot will send new items of feed to discord text channel via webhook

## Commands

If you want to see help on all bot's commands use `help` command when bot is running.

Note: these commands will require custom optional role if you set it in bot config:
`start`, `stop`, `restart`, `menu`, `forceload`, `whitelist`, `servers`, `op`, `ops`, `backup`, `chat`.

To enable cross-platform chat you need to enter in bot setup channel id (or use `chat` command) and webhook url!
And to enable rss feed you also need webhook url!

[How to create webhook and get its url.](https://github.com/Akizo96/de.isekaidev.discord.wbbBridge/wiki/How-to-get-Webhook-ID-&-Token)

For minecraft server version lower than `1.17.*` for cross-platform chat to work properly you have to have
argument `-Dfile.encoding=UTF-8` when you're executing `*.bat` or `*.sh` script (necessary for Windows).

For minecraft server version lower than `1.7.*` cross-platform chat currently work only from minecraft to discord!

Known problem that in `1.7.*` symbol `\n` doesn't render properly. This problem lies in the client.

**For backups: remember that if there are files in backups dir that not in server config, they will be deleted! And vice
versa!**

## Languages

Supported 2 languages:

* English
* Russian

## Requirements

* [Python 3.8-3.9](https://www.python.org/downloads/)
* For Linux required [screen](https://linuxize.com/post/how-to-use-linux-screen/) command
* Minecraft server not lower than version `1.0.0`
    * Run server 2 times to accept eula and generate server.properties
    * Enable query and rcon in `server.properties` (unnecessary, bot can enable it if file `server.properties` exists)

### Required bot permissions

* Enable the `Server Members Intent` and the `Presence Intent` in section `Privileged Gateway Intents` on the Bot tab of
  your bot's page on the [Discord developer's portal](https://discord.com/developers/applications).

____________
> Libraries for Python:

* [discord](https://github.com/Rapptz/discord.py) - main lib to run bot
* [vk_api](https://github.com/python273/vk_api) - lib for connecting & using VK to download and post photos from
  selected communities
* [cryptography](https://github.com/pyca/cryptography) - lib for encrypting necessary data to config file
* [mcipc](https://github.com/conqp/mcipc) - lib for easy using query and rcon to connect to minecraft server
* [pyinstaller](https://github.com/pyinstaller/pyinstaller) - lib to build project to executable file, you can use
  another one if you can't for some reason, but my makefile works only with this library
* [psutil](https://github.com/giampaolo/psutil) - lib to check minecraft process and stop it if needed
* [feedparser](https://github.com/kurtmckee/feedparser) - lib to parse RSS feed files
* [jsons](https://github.com/ramonhagenaars/jsons) - lib to serialize class from dictionary
* [omegaconf](https://github.com/omry/omegaconf) - lib to deserialize and serialize class to yaml file
* [colorama](https://github.com/tartley/colorama) - lib to make ANSI escape character sequences work under Windows

## Lib installation

Type in command prompt, you must have [requirements.txt](requirements.txt) in root folder of the project.

```
pip install -r requirements.txt
```

## Build

Firstly, you have to install pyinstaller via `pip install pyinstaller==4.0`.

Type in command prompt `make` in root directory of the project to build it.

Executable file will be in `/build_dist`.

## Run

### Windows

Just start bot executable file.

For the bot to properly start the minecraft server you have to have `*.bat` (in bot setting you can set name for this
script) in your root minecraft server directory! Example of file:

```batch
rem min_ram, max_ram - consists how many min and max GB you're allocating for server on start up
rem your_jar_file - jar file that starts up your server. It can be for vanilla: standart server.jar or for modded server: spigot.jar, forge.jar
rem java_parameters - parameters for minecraft server
@echo off
SET min_ram=1
SET max_ram=3
SET your_jar_file=server.jar
SET java_parameters=-d64 -server -XX:+AggressiveOpts
rem                                                  ... and so on :)
chcp 65001
cls
title Minecraft Server Console (%max_ram%Gb RAM)
echo java -Xms%min_ram%G -Xmx%max_ram%G %java_parameters% -jar %your_jar_file% nogui
java -Xms%min_ram%G -Xmx%max_ram%G %java_parameters% -Dfile.encoding=UTF-8 -jar %your_jar_file% nogui
exit /b
```

### Linux

On the desktop version of linux just start bot executable file.

On the server version of linux you have to start bot executable file using terminal with screen command! Example:

```
screen -dmS %your_session_name% %path_to_bot%/bot_executable_file
```

For the bot to properly start the minecraft server you have to have `*.sh` (in bot setting you can set name for this
script) in your root minecraft server directory! Example of file:

```shell
# min_ram, max_ram - consists how many min and max GB you're allocating for server on start up
# your_jar_file - jar file that starts up your server. It can be for vanilla: standart server.jar or for modded server: spigot.jar, forge.jar
# java_parameters - parameters for minecraft server
min_ram='1G'
max_ram='3G'
your_jar_file='server.jar'
java_parameters='-d64 -server -XX:+AggressiveOpts' # ... and so on :)
java -Xms${min_ram} -Xmx${max_ram} ${java_parameters} -Dfile.encoding=UTF-8 -jar ${your_jar_file} nogui
```

For server process bot will start virtual terminal session via `screen` command. You can connect to it
via `screen -r %server_name%`. Server name you can find in list of virtual sessions - `screen -ls`.

## Localization

For adding or updating/fixing translations:

* If you want to add translations, you need to generate `*.pot` file running
  script [generate_pot.py](locales/generate_pot.py) after you added them. Otherwise, if you want to fix them, then skip
  this step.
* Then you need to update existing `*.po` file yourself for required language or create new one in this
  path: `/locales/%language_code%/LC_MESSAGES/lang.po`.
* For translations to be updated you also need generate updated `*.mo` file running
  script [generate_mo.py](locales/generate_mo.py).

## Tested platforms

* Windows 7 or higher (32/64 bit)
* Linux (Ubuntu/Debian/CentOS)
