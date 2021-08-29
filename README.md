<p align="center">
   <img src="images/bot.ico">
</p>

<h1 align="center">
   Bot for minecraft server in discord
</h1>

### Commands
* `help` - list all commands (currently in russian)
* `status` - return status of the server
* `list/ls` - return list of the players on server
* `start` - start server
* `stop {10}` - stop server, {} (sec) countdown, without args - remove timer
* `restart {10}` - restart server, {} (sec) countdown, without args - remove timer
* `op {1} {3}` - give op to {1} player {3} with reason comment, if needed, after set time deop that player
* `assoc {1} {2} {3}` - Associates {1} mentioning a nickname in discord on {2} command (+=/-=) (add or remove) {3} with a nickname in minecraft **for admin**
* `ops {1} {2}` - Sends info about which accounts you have linked (if {1} set to `me`) or everyone has linked (if {1} set to `all` **for admin**) and how many times are left to op. Shows not appeared accounts on server if {2} set to `missing`
* `menu` - creates menu-panel (embed) for easy command management
* `chat {1}` - saves current channel (if no arguments are given) or selected channel from {1} argument from which the bot forwards messages to the minecraft chat
* `forceload/fl {on/off}` - by {`on` / `off`} constant loading of the server when it is shut down, if no arguments - return status
* `whitelist/wl {1}` - uses whitelist from minecraft server, {1} arguments are `on`, `off`, `add`, `del`, `list`, `reload`. If you use `add` or `del`, the player's nickname is also must be written
* `servers/servs {1}` - uses a list of servers stored in the bot, arguments {1} - `select`, `list`, `show`. With `select`, the server number from the `list` is also must be written
* `say` - return embed with random picture from VK
* `clear/cls {1}` - If positive number it deletes {1} messages, if negative number - deletes n messages up to {1} from the beginning of the channel

Note: these commands will require custom role if you set it in bot configuration file:
`start`, `stop`, `restart`, `menu`, `forceload`, `whitelist`, `servers`, `op`, `ops`, `chat`.
<!---->
Also, to enable cross-platform chat you need to enter in bot setup channel id (or use `chat` command) and webhook url!
[How to create webhook and get url](https://github.com/Akizo96/de.isekaidev.discord.wbbBridge/wiki/How-to-get-Webhook-ID-&-Token).
<!---->
For cross-platform chat to work properly you have to have argument `-Dfile.encoding=UTF-8` when you're executing `***.bat` or `***.sh` script.
### Requirements
* [Python 3.5-3.8](https://www.python.org/downloads/)
* For Linux required [screen](https://linuxize.com/post/how-to-use-linux-screen/) command
* Minecraft server not lower than version 1.0.0
#### Required Bot Permissions
* Enable the `Server Members Intent` in section `Privileged Gateway Intents` on the Bot tab of your bot's page on the Discord developer's portal.
____________
> Libraries for Python: 
* [discord](https://github.com/Rapptz/discord.py) - main lib to run bot
* [vk_api](https://github.com/python273/vk_api) - lib for connecting & using VK to download and post photos from selected communities
* [cryptography](https://github.com/pyca/cryptography) - lib for encrypting necessary data to config file
* [mcipc](https://github.com/conqp/mcipc) - lib for easy using query and rcon to connect to minecraft server
* [pyinstaller](https://github.com/pyinstaller/pyinstaller) - lib to build project to executable file, you can use another one if you can't for some reason, but my makefile works only with this library
* [psutil](https://github.com/giampaolo/psutil) - lib to check minecraft process and stop it if needed
* [feedparser](https://github.com/kurtmckee/feedparser) - lib to parse RSS feed files
* [jsons](https://github.com/ramonhagenaars/jsons) - lib to serialize class from dictionary
* [omegaconf](https://github.com/omry/omegaconf) - lib to deserialize and serialize class to yaml file 
### Installation
Type in command prompt, you must have [requirements.txt](requirements.txt) in root folder of the project.
```
pip install -r requirements.txt
```
### Build
Type in command prompt in root directory of the project to build it.

* Windows
```
pyinstaller -F --icon=images/bot.ico --add-data "images\sad_dog.jpg;images" --distpath=./ Discord_bot.py
```

* Linux
```
pyinstaller -F --add-data "images/sad_dog.jpg:images" --distpath=./ Discord_bot.py
```
Or using [make utility](https://www.gnu.org/software/make/) type "make" in root directory.
### Run
* Windows

You have to start bot file from folder located in your root minecraft server directory! Example:
```
%your_minecraft_server_dir%\%bot_folder%\bot_executable_file
```
And for the bot to properly work you have to have `***.bat` (in bot setting you can set name for this script) in your root minecraft server directory! Example of file:
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

You have to execute bot file using terminal from folder located in your root minecraft server directory with screen command! Example:
```
screen -dmS %your_session_name% %your_minecraft_server_dir%\%bot_folder%\bot_executable_file
```
And for the bot to properly work you have to have `***.sh` (in bot setting you can set name for this script) in your root minecraft server directory! Example of file:
```shell
# ask_int - consists how many GB you're allocating for server on start up
# your_jar_file - jar file that starts up your server. It can be for vanilla: standart server.jar or for modded server: spigot.jar, forge.jar
# java_parameters - parameters for minecraft server
ask_int='3G'
your_jar_file='server.jar'
java_parameters='-d64 -server -XX:+AggressiveOpts' # ... and so on :)
java -Xmx${ask_int} -Xms${ask_int} ${java_parameters} -Dfile.encoding=UTF-8 -jar ${your_jar_file} nogui
```
### Tested Platforms
* Windows 7 or higher (32/64 bit)
* Linux (Ubuntu/Debian/CentOS)
