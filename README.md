<p align="center">
   <img src="images/bot.ico">
</p>

<h1 align="center">
   Bot for minecraft server in discord
</h1>

[![Build with pyinstaller and release](https://github.com/Druzai/Bot_Mc_discord/actions/workflows/pyinstaller_build.yml/badge.svg?branch=master)](https://github.com/Druzai/Bot_Mc_discord/actions/workflows/pyinstaller_build.yml)

### Commands

If you want to see help on all bot's commands use `help` command when bot is running.

Note: these commands will require custom role if you set it in bot configuration file:
`start`, `stop`, `restart`, `menu`, `forceload`, `whitelist`, `servers`, `op`, `ops`, `chat`.

Also, to enable cross-platform chat you need to enter in bot setup channel id (or use `chat` command) and webhook url!
[How to create webhook and get url](https://github.com/Akizo96/de.isekaidev.discord.wbbBridge/wiki/How-to-get-Webhook-ID-&-Token).

For cross-platform chat to work properly you have to have argument `-Dfile.encoding=UTF-8` when you're
executing `***.bat` or `***.sh` script (necessary for windows).

### Languages

Supported 2 languages:

* English
* Russian

### Requirements

* [Python 3.5-3.8](https://www.python.org/downloads/)
* For Linux required [screen](https://linuxize.com/post/how-to-use-linux-screen/) command
* Minecraft server not lower than version 1.0.0

#### Required Bot Permissions

* Enable the `Server Members Intent` in section `Privileged Gateway Intents` on the Bot tab of your bot's page on the
  Discord developer's portal.

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

### Lib installation

Type in command prompt, you must have [requirements.txt](requirements.txt) in root folder of the project.

```
pip install -r requirements.txt
```

### Build

Firstly, you have to install pyinstaller via `pip install pyinstaller==4.0`.

Type in command prompt `make` in root directory of the project to build it.

Executable file will be in `/build_dist`

### Run

* Windows

You have to start bot file from folder located in your root minecraft server directory! Example:

```
%your_minecraft_server_dir%\%bot_folder%\bot_executable_file
```

And for the bot to properly work you have to have `***.bat` (in bot setting you can set name for this script) in your
root minecraft server directory! Example of file:

```batch
rem ask_int - consists how many GB you're allocating for server on start up
rem your_jar_file - jar file that starts up your server. It can be for vanilla: standart server.jar or for modded server: spigot.jar, forge.jar
rem java_parameters - parameters for minecraft server
@echo off
SET ask_int=3
SET your_jar_file=server.jar
SET java_parameters=-d64 -server -XX:+AggressiveOpts
rem ... and so on :)
chcp 65001
cls
title Minecraft Server Console (%ask_int%Gb RAM)
echo java -Xmx%ask_int%G -Xms%ask_int%G %java_parameters% -jar %your_jar_file% nogui
java -Xmx%ask_int%G -Xms%ask_int%G %java_parameters% -Dfile.encoding=UTF-8 -jar %your_jar_file% nogui
exit /b
```

* Linux

You have to execute bot file using terminal from folder located in your root minecraft server directory with screen
command! Example:

```
screen -dmS %your_session_name% %your_minecraft_server_dir%\%bot_folder%\bot_executable_file
```

And for the bot to properly work you have to have `***.sh` (in bot setting you can set name for this script) in your
root minecraft server directory! Example of file:

```shell
# ask_int - consists how many GB you're allocating for server on start up
# your_jar_file - jar file that starts up your server. It can be for vanilla: standart server.jar or for modded server: spigot.jar, forge.jar
# java_parameters - parameters for minecraft server
ask_int='3G'
your_jar_file='server.jar'
java_parameters='-d64 -server -XX:+AggressiveOpts' # ... and so on :)
java -Xmx${ask_int} -Xms${ask_int} ${java_parameters} -Dfile.encoding=UTF-8 -jar ${your_jar_file} nogui
```

### Localization

If you want to fix or add translations, you need to generate `*.pot` file running
script [generate_pot.py](locales/generate_pot.py).

After you need yourself update existing `*.po` file for required language or create new one in this
path: `/locales/%language_code%/LC_MESSAGES/lang.po`.

For translations to be updated you also need generate updated `*.mo` file running
script [generate_mo.py](locales/generate_mo.py).

### Tested Platforms

* Windows 7 or higher (32/64 bit)
* Linux (Ubuntu/Debian/CentOS)
