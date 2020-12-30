# Bot_Mc_discord
### Commands
* `%help` - list all commands (currently in russian)
* `%status` - return status of the server
* `%list` - return list of the players on server
* `%start` - start server
* `%stop {10}` - stop server, {} (sec) countdown, 0 - remove timer
* `%restart {10}` - restart server, {} (sec) countdown, 0 - remove timer
* `%op {1} {2} {3}` - give op to {1} player using {2} code {3} with reason comment, if needed, after setted time deop that player
* `%assoc {1} {2} {3}` - Associates {1} mentioning a nickname in discord on {2} command (+=/-=) (add or remove) {3} with a nickname in minecraft **for admin**
* `%codes {1}` - Sends dm with codes for {1} nickname in discord
* `%menu` - create menu-panel (embed) for easy command management
* `%forceload/fl {on/off}` - by {`on` / `off`} constant loading of the server when it is shutted down, if no arguments - return status
* `%whitelist/wl {1}` - uses whitelist from minecraft server, {1} arguments are `on`, `off`, `add`, `del`, `list`, `reload`. If you use `add` or `del`, the player's nickname is also must be written
* `server {1}` - uses a list of servers stored in the bot, arguments {1} - `select`, `list`, `show`. With `select`, the server number from the `list` is also must be written
* `%say` - return embed with random picture from VK
* `%clear {1}` - If positive number it deletes {1} messages, if negative number - deletes n messages up to {1} from the beginging of the channel
### Requirements
* [Python 3.5-3.8](https://www.python.org/downloads/)
* [Java RE](https://www.java.com/en/download/)
* For Linux required [screen](https://linuxize.com/post/how-to-use-linux-screen/) command
* You must enable query and rcon, its ports & rcon password in server.properties!
____________
> Libraries for Python: 
* [discord](https://github.com/Rapptz/discord.py) - main lib to run bot
* [vk_api](https://github.com/python273/vk_api) - lib for connecting & using VK to download and post photoes from selected communities
* [cryptography](https://github.com/pyca/cryptography) - lib for encrypting nessesary data to config file
* [mcipc](https://github.com/conqp/mcipc) - lib for easy using query and rcon to connect to minecraft server
* [pyinstaller](https://github.com/pyinstaller/pyinstaller) - lib to build project to executable file, you can use another one if you can't for some reason, but my makefile works only with this library
### Installation
Type in command promt, you must have [requirements.txt](requirements.txt) in root folder of the project
```
pip install -r requirements.txt
```
### Build
Type in command promt in root directory of the project to build it
```
pyinstaller -F --icon=bot.ico --distpath=./ Discord_bot.py
```
Or using [make utility](https://www.gnu.org/software/make/) type "make" in root directory
### Run
Note: for using almost all commands you have to have role "Майнкрафтер"
* Windows


You have to start bot file from folder located in your root minecraft server directory! Example:
```
%your_minecraft_server_dir%\%bot_folder%\bot_executable_file
```
And for the bot to properly work you have to have ***.bat (in bot setting you can set name for this script) in your root minecraft server directory! Example of file:
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
And for the bot to properly work you have to have ***.sh (in bot setting you can set name for this script) in your root minecraft server directory! Example of file:
```
# ask_int - consists how many GB you're allocating for server on start up
# your_jar_file - jar file that starts up your server. It can be for vanilla: standart server.jar or for modded server: spigot.jar, forge.jar
ask_int='3G'
your_jar_file='server.jar'
java -Xmx$ask_int -Xms$ask_int -jar $your_jar_file nogui
```
### Tested Platforms
* Windows 7 or higher (32/64 bit)
* Linux (Ubuntu/Debian/CentOS)
