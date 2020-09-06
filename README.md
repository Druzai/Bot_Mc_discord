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
* Python 3.5-3.8
____________
Libraries: 
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
### Platforms
* Windows 32/64 bit - tested, working
* Linux (Ubuntu/Debian) - tested, partly working
