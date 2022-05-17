<p align="center">
   <img src="images/bot.ico">
</p>

<h1 align="center">
   Bot for Minecraft Server in Discord
</h1>

[![Build with pyinstaller and release](https://github.com/Druzai/Bot_Mc_discord/actions/workflows/pyinstaller_build.yml/badge.svg?branch=master)](https://github.com/Druzai/Bot_Mc_discord/actions/workflows/pyinstaller_build.yml)

## Main features

**Attention! This bot designed to work only on 1 Discord server!**

* Managing Minecraft server via Discord bot:
    * Start the server
    * Stop the server
    * Restart the server
    * Get info about players on the server
    * Work with server whitelist
    * Secure authorization
        * **Can't guarantee security when nick has spaces!** (bot can't kick these players because of Minecraft server)
        * Players' nicks mustn't contain these characters: `[`,`]`,`<`,`>`
        * Has options to ban and unban IP-address regardless of whether secure authorization is enabled or not
    * Autoload if the Minecraft server crashes
    * Auto stop if the Minecraft server online during certain period of time without players
    * Auto backup at specified intervals and forced backup by member
        * Auto deleting backup(s) if backup's limit or space exceeded
    * Make yourself an operator for limited amount of time if your Discord account has association with Minecraft nick
        * **Bot can't do it when nick has spaces!**
* Changing Minecraft servers on the go while server is down
* Setting an optional role in Discord. If set then the bot commands for managing the Minecraft server will require this
  role from the member
* Setting an optional admin role in Discord. If set then commands that interacts with Minecraft server commands will
  execute if member has admin role. Otherwise, member must have `Administrator` permission.
* Creating optional cross-platform chat between Discord text channel and Minecraft server via bot and webhook
    * Supported mentions in Discord and Minecraft
        * Also for better recognition you can create list of associations between Discord member and Minecraft nick
    * Supported edited messages from Discord and editing messages from Minecraft
        * Message should start with single `*` or with `*` and space if edited message should start with `**`
    * Supported Discord reply in message
    * Supported url links (shortens if link longer than 256 symbols)
    * Supported attached files to message in Discord
    * Half supported emojis
        * Custom emojis are converted to text with their own text name and hyperlink to img of emoji if applicable
        * Minecraft players can send custom emojis typing `:emoji_name:` (finds first full match, then if nothing is
          found trying to find case-insensitive name)
        * Most of the standard unicode emojis are not processed by the vanilla Minecraft server
    * Logging of death messages from Minecraft
        * If you set custom image link in bot config and getting standard avatar in webhook message then your image link
          is invalid!
    * Some features may not work in versions lower than `1.7.2`!
* Setting up optional rss feed. Bot will send new items of feed to Discord text channel via webhook

**How bot converts mentions from Minecraft chat to Discord for cross-platform chat:**

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

Note: Mentions from Minecraft mustn't contain `@` in them!

## Commands

If you want to see help on all bot's commands use `help` command when bot is running.

Note: some commands will require optional role or/and admin role if you set them in bot config.

To enable cross-platform chat you need to enter in bot setup channel id (or use `chat` command) and webhook url!

And to enable rss feed you also need webhook url!

[How to create webhook and get its url.](https://github.com/Akizo96/de.isekaidev.discord.wbbBridge/wiki/How-to-get-Webhook-ID-&-Token)

**For backups: remember that if there are files in backups directory that not in server config, they will be deleted!
And vice versa!**

## Languages

Supported 2 languages:

* English
* Russian

## Requirements

* [Python 3.8-3.10](https://www.python.org/downloads/)
* For Linux
    * Required installed [screen](https://linuxize.com/post/how-to-use-linux-screen/) command
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

### Build with pyinstaller

Firstly, you have to install pyinstaller via `pip install pyinstaller==5.0`.

Type in command prompt `make` in root directory of the project to build it.

Executable file will be in `%project_root_dir%/build_dist`.

## Run

**Important! If you running Minecraft server between versions `1.7.2` and `1.18` to avoid critical security
vulnerability `Log4Shell` do instructions stated in
this [article](https://www.minecraft.net/en-us/article/important-message--security-vulnerability-java-edition)!**

For Minecraft server lower than version `1.17` for cross-platform chat to work properly you have to have
argument `-Dfile.encoding=UTF-8` when you're executing `*.bat`, `*.cmd`, shortcut or `*.sh` script (necessary for
Windows).

### Windows

Just start bot executable file.

For the bot to properly start the Minecraft server you have to have `*.bat` or `*.cmd` (in bot setting you can set name
for this script) in your root Minecraft server directory! Example of file:

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

For the bot to properly start the Minecraft server you have to have `*.sh` (in bot setting you can set name for this
script) in your root Minecraft server directory! Example of file:

```shell
# min_ram, max_ram - consists how many min and max GB you're allocating for server on start up
# your_jar_file - jar file that starts up your server. It can be for vanilla: standard server.jar or for modded server: spigot.jar, forge.jar
# java_parameters - parameters for Minecraft server
min_ram='1G'
max_ram='3G'
your_jar_file='server.jar'
java_parameters=''
java -Xms${min_ram} -Xmx${max_ram} ${java_parameters} -Dfile.encoding=UTF-8 -jar ${your_jar_file} nogui
```

For server process bot will start a virtual terminal session via `screen` command. You can connect to it
via `screen -r %your_session_name%`. Server name you can find in list of virtual sessions - `screen -ls`.

## Localization

For adding or updating/fixing translations:

* If you want to add translations, you need to generate `*.pot` file running
  script [generate_pot.py](locales/generate_pot.py) (**without admin privilege!**) after you added translations
  in `*.py` files. Otherwise, if you only want to fix translations, then skip this step.
* Then you need to update existing `*.po` file yourself for required language or create new one in this
  path: `%project_root_dir%/locales/%language_code%/LC_MESSAGES/lang.po`.
* For translations to be updated you also need generate updated `*.mo` file running
  script [generate_mo.py](locales/generate_mo.py).

## Tested platforms

* Windows 7 or higher (64 bit)
* Linux (Debian-based) (64 bit)
