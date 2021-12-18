<p align="center">
   <img src="images/bot.ico">
</p>

<h1 align="center">
   Bot for Minecraft Server in discord
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
    * Secure authorization
        * **Can't guarantee tight security when nickname has spaces** (bot can't kick these players because of minecraft
          server)
        * Has options to ban and unban IP-address regardless of whether secure authorization is enabled or not
    * Autoload if the minecraft server crashes
    * Auto backup at specified intervals and forced backup by member
        * Auto deleting backup(s) if backup's limit or space exceeded
    * Make yourself an operator for limited amount of time if your discord account has association with minecraft nick
* Changing minecraft servers on the go while server is down
* Setting an optional role. If set then the bot commands for managing the minecraft server will require this role from
  the member
* Setting an optional admin role. If set then commands that interacts with minecraft server commands will execute if
  member has admin role. Otherwise, member must have `Administrator` permission.
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

Note: some commands will require optional role or/and admin role if you set them in bot config.

To enable cross-platform chat you need to enter in bot setup channel id (or use `chat` command) and webhook url!
And to enable rss feed you also need webhook url!

[How to create webhook and get its url.](https://github.com/Akizo96/de.isekaidev.discord.wbbBridge/wiki/How-to-get-Webhook-ID-&-Token)

For minecraft server lower than version `1.7.2` cross-platform chat currently work only from minecraft to discord,
because these minecraft servers don't have a `tellraw` command!

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
    * Run server 1 or 2 times to accept eula and generate server.properties
    * Enable query and rcon in `server.properties` (unnecessary, bot can enable it if file `server.properties` exists)

### Required bot permissions

* Enable the `Server Members Intent` and the `Presence Intent` in section `Privileged Gateway Intents` on the Bot tab of
  your bot's page on the [Discord developer's portal](https://discord.com/developers/applications).

## Build

### Lib installation

Type in command prompt, you must have [requirements.txt](requirements.txt) in root folder of the project.

```
pip install -r requirements.txt
```

### Build with pyinstaller

Firstly, you have to install pyinstaller via `pip install pyinstaller==4.0`.

Type in command prompt `make` in root directory of the project to build it.

Executable file will be in `/build_dist`.

## Run

**Important! If you running minecraft server between versions  `1.7.2` and `1.18` to avoid critical security
vulnerability `Log4Shell` do instructions stated in
this [link](https://www.minecraft.net/en-us/article/important-message--security-vulnerability-java-edition)!**

For minecraft server lower than version `1.17` for cross-platform chat to work properly you have to have
argument `-Dfile.encoding=UTF-8` when you're executing `*.bat` or `*.sh` script (necessary for Windows).

### Windows

Just start bot executable file.

For the bot to properly start the minecraft server you have to have `*.bat` (in bot setting you can set name for this
script) in your root minecraft server directory! Example of file:

```batch
@echo off
rem min_ram, max_ram - consists how many min and max GB you're allocating for server on start up
rem your_jar_file - jar file that starts up your server. It can be for vanilla: standard server.jar or for modded server: spigot.jar, forge.jar
rem java_parameters - parameters for minecraft server
SET min_ram=1
SET max_ram=3
SET your_jar_file=server.jar
SET java_parameters=
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
# your_jar_file - jar file that starts up your server. It can be for vanilla: standard server.jar or for modded server: spigot.jar, forge.jar
# java_parameters - parameters for minecraft server
min_ram='1G'
max_ram='3G'
your_jar_file='server.jar'
java_parameters=''
java -Xms${min_ram} -Xmx${max_ram} ${java_parameters} -Dfile.encoding=UTF-8 -jar ${your_jar_file} nogui
```

For server process bot will start virtual terminal session via `screen` command. You can connect to it
via `screen -r %your_session_name%`. Server name you can find in list of virtual sessions - `screen -ls`.

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

* Windows 7 or higher (64 bit)
* Linux (Debian-based) (64 bit)
