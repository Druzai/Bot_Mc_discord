<p align="center">
   <img src="images/bot.ico">
</p>

<h1 align="center">
   Bot for Minecraft Server in Discord
</h1>

[![Build with pyinstaller and release](https://github.com/Druzai/Bot_Mc_discord/actions/workflows/pyinstaller_build.yml/badge.svg?branch=master)](https://github.com/Druzai/Bot_Mc_discord/actions/workflows/pyinstaller_build.yml)

## Main features

> **Warning**
>
> **This bot designed to work only on 1 Discord server!**

* Managing Minecraft server via Discord bot:
    * Start the server
    * Stop the server
    * Restart the server
    * Get info about players on the server
    * Work with server whitelist
    * Secure authorization
        * Has options to ban and unban IP-address regardless of whether secure authorization is enabled or not
    * Autoload if the Minecraft server crashes
    * Auto stop if the Minecraft server online during certain period of time without players
    * Auto backup at specified intervals and forced backup by member
        * Auto deleting backup(s) if backup's limit or space exceeded
        * **If there are files in backups directory that not in server config, they will be deleted! And vice versa!**
    * Make yourself an operator for limited amount of time if your Discord account has association with Minecraft nick
        * **Bot can't do it when nick has spaces!** (this applies to servers from `1.0.0` to `1.19.0`!)
* Changing Minecraft servers on the go while server is down
* Creating menus for quick bot and Minecraft server managing
    * Creating a server menu with buttons and a dropdown to quickly execute common commands
    * Creating a bot menu with buttons and a dropdown to quickly toggle bot features
* Setting an optional role in Discord. If set then the bot commands for managing the Minecraft server will require this
  role from the member
* Setting an optional admin role in Discord. If set then commands that interacts with Minecraft server commands will
  execute if member has admin role. Otherwise, member must have `Administrator` permission.
* Creating optional game chat between Discord text channel and Minecraft server via bot and webhook
    * Supported mentions in Discord and Minecraft
        * Also, for better recognition you can create list of associations between Discord member and Minecraft nick
    * Supported edited messages from Discord and editing messages from Minecraft
        * Message should start with single `*` or with `*` and space if edited message should start with `**`
    * Supported Discord reply in message
    * Supported url links (shortens via `clck.ru` or `tinyURL` if link longer than 256 symbols)
    * Supported stickers in message
    * Supported attached files to message in Discord
    * Half supported emojis
        * Custom emojis are converted to text with their own text name and hyperlink to img of emoji if applicable
        * Minecraft players can send custom emojis typing `:emoji_name:` (finds first full match, then if nothing is
          found trying to find case-insensitive name)
        * Most of the standard unicode emojis are not processed by the vanilla Minecraft server
    * Logging of death messages from Minecraft
        * If you set custom image link in bot config and getting standard avatar in webhook message then your image link
          is invalid!
        * If the same death message is repeated in the Minecraft log, bot will group it and send it to Discord with the
          modifier `(xN)`, where `N` is the number of these messages
        * Works in versions `1.4.6` and higher
            * From version `1.4.6` server started logging players deaths
            * From version `1.15.0` server started logging villagers' deaths
            * From version `1.17.1` server started logging named mobs' deaths
    * Showing low quality preview of an image in Minecraft chat (max - 160 pixels in width)
        * Can fetch image from links, attachments, stickers and emojis in Discord message
            * Shows emoji if there is only one emoji in the message
        * Supported image opacity
        * Works in versions `1.16.0` and higher
    * Some features may not work in versions lower than `1.7.2`!
* Setting up optional rss feed. Bot will send new items from feed to Discord text channel via webhook

**How bot converts mentions from Minecraft chat to Discord for game chat:**

| Minecraft               | Discord                  |
|-------------------------|--------------------------|
| `@a`                    | `@Minecrafters`          |
| `@all`                  | `@Minecrafters`          |
| `@e`                    | `@everyone`              |
| `@everyone`             | `@everyone`              |
| `@p`                    | `@here`                  |
| `@here`                 | `@here`                  |
| `@AnyRoleOrUserMention` | `@SameRoleOrUserMention` |

`@Minecrafters` - an optional role in Discord for managing the Minecraft server. If not stated then bot will
mention `@everyone`.

> **Warning**
>
> Mentions from Minecraft mustn't contain `@` in them!

## Commands

If you want to see help on all bot's commands use `help` command when bot is running.

> **Note**
>
> Some commands will require an optional role or/and an admin role if you set them in bot config.

## Languages

Supported 2 languages:

* English
* Russian

## Requirements

* [Python 3.8-3.10](https://www.python.org/downloads/)
* For Linux and macOS
    * Required installed screen command [(Linux)](https://linuxize.com/post/how-to-use-linux-screen/)
      [(macOS)](https://brewinstall.org/install-screen-mac-osx/)
* Minecraft server not lower than version `1.0.0`
    * Run server 1 or 2 times to accept `eula` and generate `server.properties`

Bot can automatically enable `query` and `rcon` in `server.properties` if file exists, but you can enable and enter them
manually if you want.

### Required bot intents

* Enable the `Server Members Intent`, the `Presence Intent` and the `Message Content Intent` in
  section `Privileged Gateway Intents` on the Bot tab of your bot's page on
  the [Discord developer's portal](https://discord.com/developers/applications).

## Build

### Lib installation

Type in command prompt, you must have [requirements.txt](requirements.txt) in root folder of the project.

```
pip install -r requirements.txt
```

For macOS you have to update certificates by running script `/Applications/Python 3.XX/Install Certificates.command`

### Build with pyinstaller

Firstly, you have to install pyinstaller via `pip install pyinstaller==5.6.2`.

Type in command prompt `make` in root directory of the project to build it.

Executable file will be in `%project_root_dir%/build_dist`.

## Run

> **Warning**
>
> **If you're running Minecraft server between versions `1.7.2` and `1.18.0` to avoid critical security
vulnerability `Log4Shell` do instructions stated in
this [article](https://www.minecraft.net/en-us/article/important-message--security-vulnerability-java-edition)!**
>
> **Or check if your modded server already has a patch for it!**

For Minecraft server lower than version `1.17.0` for game chat to work properly you have to have
argument `-Dfile.encoding=UTF-8` when you're executing `*.bat`, `*.cmd`, shortcut, `*.sh` or `*.command` script (
necessary for Windows).

### Windows

Just start bot executable file.

For the bot to properly start the Minecraft server you have to have `*.bat` or `*.cmd` script (in bot setting you can
set name for this script) in your root Minecraft server directory! Example of file:

```batch
@echo off
rem min_ram, max_ram - consists how many min and max GB you're allocating for server on start up
rem your_jar_file - jar file that starts up your server. It can be for vanilla: standard server.jar or for modded server: spigot.jar, forge.jar
rem java_parameters - parameters for Minecraft server
set min_ram=1
set max_ram=3
set your_jar_file=server.jar
set java_parameters=
chcp 65001
cls
title Minecraft Server Console (%max_ram%Gb RAM)
echo java -Xms%min_ram%G -Xmx%max_ram%G %java_parameters% -jar %your_jar_file% nogui
java -Xms%min_ram%G -Xmx%max_ram%G %java_parameters% -Dfile.encoding=UTF-8 -jar %your_jar_file% nogui
exit /b
```

Also, if you don't want the server console to pop up in front of other windows at startup, you'll need to create
shortcut by doing these steps:

- Create a shortcut to the `*.bat` or `*.cmd` file. To do so, right click on the file, click `Create Shortcut`
- Right click on the shortcut and choose `Properties`
- In the `Run`: drop down, choose `Minimized`
- Click `OK`

After creating shortcut you can specify it as start file for bot instead of script in config setup.

### Linux

On the desktop version of Linux just start bot executable file.

On the server version of Linux you have to start bot executable file using terminal with screen command! Example:

```
screen -dmS %your_session_name% %path_to_bot%/bot_executable_file
```

For the bot to properly start the Minecraft server you have to have `*.sh` script (in bot setting you can set name for
this script) in your root Minecraft server directory! Example of file:

```shell
# min_ram, max_ram - consists how many min and max GB you're allocating for server on start up
# your_jar_file - jar file that starts up your server. It can be for vanilla: standard server.jar or for modded server: spigot.jar, forge.jar
# java_parameters - parameters for Minecraft server
min_ram='1G'
max_ram='3G'
your_jar_file='server.jar'
java_parameters=''
exec java -Xms${min_ram} -Xmx${max_ram} ${java_parameters} -Dfile.encoding=UTF-8 -jar ${your_jar_file} nogui
```

For server process bot will start a virtual terminal session via `screen` command. You can connect to it
via `screen -r %your_session_name%`. You can find server name in list of virtual sessions - `screen -ls`.

### macOS

On macOS you should start bot executable file from terminal `%path_to_bot%/bot_executable_file`. Because if you just
double click on executable file, current working directory will be set as your home directory (`~`) and bot couldn't
find config and key.

For the bot to properly start the Minecraft server you have to have `*.command` or `*.sh` script (in bot setting you can
set name for this script) in your root Minecraft server directory! Example of file can be seen above in [Linux](#linux)
section.

For server process bot will start a virtual terminal session via `screen` command. You can connect to it
via `screen -r %your_session_name%`. You can find server name in list of virtual sessions - `screen -ls`.

## Localization

For adding or updating/fixing translations:

* If you want to add translations, you need to generate `*.pot` file running
  script [generate_pot.py](locales/generate_pot.py) (**without admin privilege!**) after you added translations
  in `*.py` files. Otherwise, if you only want to fix translations, then skip this step.
* Then you need to update existing `*.po` file yourself for required language or create new one in this
  path: `%project_root_dir%/locales/%language_code%/LC_MESSAGES/lang.po`.
* For translations to be updated you also need generate updated `*.mo` file running
  script [generate_mo.py](locales/generate_mo.py).

On Linux or macOS you may need to install `gettext`:

* Linux: `sudo apt install gettext`
* macOS: `brew install gettext`

## Tested platforms

* Windows 7 or higher (64 bit)
  * For Windows 7 you have to use executable file built with Python 3.8! (It has the string `p3.8` in its name)
* Linux (Debian-based) (64 bit)
* macOS 11 or higher (64 bit)
