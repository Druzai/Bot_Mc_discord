# Bot_Mc_discord
### Commands
* `%help` - list all commands (currently in russian)
* `%status` - return status of the server
* `%list` - return list of the players on server
* `%start` - start server
* `%stop {10}` - stop server, {} (sec) countdown, 0 - remove timer
* `%restart {10}` - restart server, {} (sec) countdown, 0 - remove timer
* `%op {1} {2} {3}` - Give op to {1} player using {2} code {3} with reason comment, if needed, after setted time deop that player
* `%menu` - Create menu-panel (embed) for easy command management
* `%forceload/fl {on/off}` - By {on / off} constant loading of the server when it is shutted down, if no arguments - return status
* `%say` - return embed with random picture from VK
* `%clear {1}` - Delete {1} messages
### Requirements
* [Python 3.5-3.8](https://www.python.org/downloads/)
* [Java RE](https://www.java.com/en/download/)
* For Linux required [screen](https://linuxize.com/post/how-to-use-linux-screen/) command
____________
> Libraries for Python: 
* [discord](https://github.com/Rapptz/discord.py) - main lib to run bot
* [vk_api](https://github.com/python273/vk_api) - lib for connecting & using VK to download and post photoes from selected communities
* [cryptography](https://github.com/pyca/cryptography) - lib for encrypting nessesary data to config file
* [mcipc](https://github.com/conqp/mcipc) - lib for easy using query and rcon to connect to minecraft server
* [pyinstaller](https://github.com/pyinstaller/pyinstaller) - lib to build project to executable file, you can use another one if you can't for some reason
### Installation
Type in command promt, you must have [requirements.txt](requirements.txt) in root folder of the project
```
pip install -r requirements.txt
```
### Build
Type in command promt in root directory of the project to build it
```
pyinstaller -F --icon=bot.ico Discord_bot.py
```
### Run
* Windows


You have to start bot file from folder located in your root minecraft server directory! Example:
```
%your_minecraft_server_dir%\%bot_folder%\bot_executable_file
```
And for the bot to properly work you have to have Start_bot.bat in your root minecraft server directory! Example:
```
rem ask_int - consists how many GB you're allocating for server on start up
rem your_jar_file - jar file that starts up your server. It can be for vanilla: standart server.jar or for modded server: spigot.jar, forge.jar
@echo off
SET ask_int=3
SET your_jar_file=server.jar
chcp 1251
cls
color 3
echo Starting server...
echo RAM maximum set to %ask_int%Gb
title Minecraft Server Console (%ask_int%Gb RAM)
echo java -Xmx%ask_int%G -Xms%ask_int%G -jar %your_jar_file% nogui
java -Xmx%ask_int%G -Xms%ask_int%G -jar %your_jar_file% nogui
exit /b
```
* Linux


You have execute bot file using terminal from folder located in your root minecraft server directory with screen command! Example:
```
screen -dmS %your_session_name% %your_minecraft_server_dir%\%bot_folder%\bot_executable_file
```
And for the bot to properly work you have to have Start_bot.sh in your root minecraft server directory!
```
# ask_int - consists how many GB you're allocating for server on start up
# your_jar_file - jar file that starts up your server. It can be for vanilla: standart server.jar or for modded server: spigot.jar, forge.jar
ask_int='3G'
your_jar_file='server.jar'
java -Xmx$ask_int -Xms$ask_int -jar $your_jar_file nogui
```
### Tested Platforms
* Windows 32/64 bit
* Linux (Ubuntu/Debian/CentOS)
