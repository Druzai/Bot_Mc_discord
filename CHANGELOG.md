# Changelog

All important changes to this project will be documented in this file.

### [1.4.2 Unreleased](https://github.com/Druzai/Bot_Mc_discord/compare/1.4.1...1.4.2) (2023-xx-xx)

#### Improvements:

* Added backup of several world folders:
    * For example, these servers split world data: PaperMC, Bukkit and Spigot

#### Fixed:

* Fixed checking login string for PaperMC/Bukkit/Spigot servers

#### Breaking changes:

* --

### [1.4.1](https://github.com/Druzai/Bot_Mc_discord/compare/1.4.0...1.4.1) (2023-03-14)

#### Improvements:

* Added handling chat line on Spigot, PaperMC or Bukkit Minecraft server
* Added option to disable login check (whether the player is really logged in)
    * This option was added because when using modded Minecraft (forge, fabric), the player registers with delay and the bot might think that login message is fake
* Added button `List` to server menu that shows list of backups from selected Minecraft server
* Added button `Get an operator` to server menu that gives player an operator in Minecraft
* Updated translation strings for death messages for version `1.19.4`
* Added option to enforce default game mode for selected server instead of hardcoded enforcement
* Updated dependencies

#### Fixed:

* Fixed non-awaited coroutine `backup_force_checking`
* Added handling if an SSL error occurs
* Fixed update of buttons in bot menu
* Added strings `**For admin only!**` to some command descriptions
* Removed requirement for admin role for `associate` command
* Fixed checking if player can't be kicked
* Fixed deletion of backup warn messages if they were called from interaction

## [1.4.0](https://github.com/Druzai/Bot_Mc_discord/compare/1.3.2...1.4.0) (2022-12-03)

#### Main features:

Updated bot to use Discord features such as: dropdown lists, buttons, modals, threads.

Improved bot menu to use Discord features and divided it into server menu and bot menu.
Recommended to generate new menu message(s) instead of editing the old menu message!

Added support for Python 3.11.

#### Improvements:

* **Updated discord.py from `1.7.3` to `2.1.0`**
* Updated other dependencies
* Added `tinyURL` as another link shortening service
* Added support for attachments in webhooks
* Bot can write and reply in threads
* Improved working with webhooks:
    * Bot can fetch given webhook or create a new one if it doesn't find anything
    * More easy setting up a webhook via bot commands
* Added fetching image from links, attachments, stickers and emojis in Discord message and showing its preview in Minecraft chat if server version is `1.16.0` or higher
* Added parameters timeout and `User-Agent` header to requests
* Changed menu for server to using buttons and a dropdown and added menu for bot main features
* Added options to enable/disable `op`
* Added options to enable/disable `obituary` and set custom name for it

#### Fixed:

* Fixed and improved translations and bot responses
* Improved parsing such types as `Union` and `Literal` in `help` command
* Improved kicking players with illegal characters such as space from server
* Improved execution of commands `whitelist add` and `whitelist del` for Minecraft server version lower than `1.7.6`
* Fixed URL regex to include `#` fragment
* Improved parsing death messages for duplicates
* Removed requirement for logging players with secure authorization that players' nicks mustn't contain these characters: `[`,`]`,`<`,`>`
* Added check if some other Minecraft server is running on the same port
* Removed requirement for game chat that player's nick mustn't contain `>` character
* Added handling of unknown OS when starting Minecraft server

#### Changed:

* Created commands:
    * `chat` and its subcommands (obituary, image preview, webhook settings)
    * `rss` and its subcommands (webhook settings)
    * `language select`
    * `menu server` and `menu bot`
    * `status update`
    * `op on/off`
* Changed commands:
    * Moved logic:
        * From `edit` to `chat edit`
        * From `channel chat` to `chat webhook channel`
    * Added alias `remove` to all `del` subcommands
    * Added usage of Discord dropdown lists in commands:
        * `language select`
        * `authorize unban`
        * `backups remove`
        * `backups restore`
* Changed naming:
    * Renamed `Cross-platform chat` to `Game chat` in all bot messages

#### Breaking changes:

* Changed date format for logging in console and in files: `bot.log` and `op.log`
    * From `DD/MM/YYYY` to `YYYY-MM-DD`
* Renamed setting `cross_platform_chat` to `game_chat` and subsetting `enable_cross_platform_chat` to `enable_game_chat`
* Moved setting `default_number_of_times_to_op` to a new setting `op`
* Moved setting `avatar_url_for_death_messages` to a new setting `obituary`

### [1.3.2](https://github.com/Druzai/Bot_Mc_discord/compare/1.3.1...1.3.2) (2022-07-28)

#### Improvements:

* Added check if last backup datetime is older than datetime of stopped server
* Added check if world folder doesn't exist or is empty
* Added option to enforce offline mode for selected server
* Added support for `macOS`
* Updated dependencies

#### Fixed:

* Fixed parsing `ops.json`
* Fixed checking for players in `handle_message_for_chat`
* Fixed regex for finding unsecured player's messages in log file for version `1.19.1`

### [1.3.1](https://github.com/Druzai/Bot_Mc_discord/compare/1.3.0...1.3.1) (2022-06-07)

#### Improvements:

* Added parsing for animated emojis in cross-platform chat
* Improved finding emoji name
* Added printing reason of ban in command `auth banlist`
* Added new translation strings for death messages for version `1.19` and updated the old ones
* Added printing info if bot couldn't archive some files into a backup
* Added printing timestamp when bot catches exception in internal task
* Added handling of stickers in message for cross-platform chat from Discord to Minecraft

#### Fixed:

* Fixed changing `pygettext.py` on Windows to set default encoding to `UTF-8` if file can't be edited without admin privilege
* Fixed `\n` processing in command `auth ban` for Minecraft servers below version `1.7.6`
* Added suppression if exception `AccessDenied` is raised
* Made parameter `count` in `clear` command not required when only roles are specified
* Changed to edit poll message instead of sending a new one
* Fixed choosing `say` instead of `tellraw` when sending `Backup completed!` to Minecraft chat

## [1.3.0](https://github.com/Druzai/Bot_Mc_discord/compare/1.2.3...1.3.0) (2022-05-01)

#### Improvements:

* **Added saving all data on the server to disk before making a backup**
* **Added support of cross-platform chat and server-related commands for Minecraft versions `1.0.0` - `1.6.4`**
* Added handling `*.cmd` script and shortcut to `*.bat` or `*.cmd` script as start file on Windows
* Added editing messages from Minecraft in Discord channel and edit webhook messages from Discord via command `edit` ([#27](https://github.com/Druzai/Bot_Mc_discord/issues/27))
* Added check for edited messages whether they are stored in cache or not
* Added timeout to stop server when no players found during long period of time ([#29](https://github.com/Druzai/Bot_Mc_discord/issues/29))
* Added fast-login feature if user is in associations ([#26](https://github.com/Druzai/Bot_Mc_discord/issues/26))
* Optimized getting list of java processes
* Added printing server version and server status when it's loading/stopping in `status` command
* Added ability to send Discord emojis from Minecraft chat
* Added check if cryptography key is wrong or bot can't decrypt a token
* Added handling of more granular errors for bot and improved handling of the old ones
* Added sending death messages from Minecraft in Discord

#### Fixed:

* Fixed mentions from Minecraft to Discord ([#25](https://github.com/Druzai/Bot_Mc_discord/issues/25))
* Bot created a poll if you were initiator of stopping the server and only your accounts were logged in ([#24](https://github.com/Druzai/Bot_Mc_discord/issues/24))
* Added resetting gamemode in `op` command
* Disabled deleting user message in cross-platform chat when server is down or there are no players on it
* Fixed slow bot response when sending a message from synchronous function
* Added additional spaces when there are more than 9 items in list to display in command output
* Reduced `backup force` command cooldown to 15 seconds
* Fixed and rewrote many translations
* Added support of servers' version lower than `1.7.6` for `whitelist` and `op` command
* Added support of deletion of some nicks for `whitelist` command
* Better handling on versions lower than `1.7.6` for files: `banned-ips.txt`, `ops.txt` and `white-list.txt`
* Fixed handling long tellraw objects and improved their building
* Speeded up deletion of messages in `clear` command

#### Changes in bot commands

* Created commands:
    * `associate add` and `associate del`
    * `edit`
* Changed commands:
    * Renamed `servers` to `server` and alias `servs` to `serv`
    * Moved logic:
        * From `servers show` to `server`
        * From `ops history` to `op history`
        * From `ops` to `op info`
        * From `forceload` to `schedule forceload`
    * Added alias `associate` to `assoc`
    * Added alias `authorize` to `auth`
    * Added alias `ls` to all `list` subcommands
    * Added alias `to` to `reply` subcommand of `clear`

#### Breaking changes:

* Changed `specific_command_role_id` to `managing_commands_role_id` in bot's configuration file
* Changed in file `server_config.yml` (**save forced world backups before starting the new bot's version cause bot will delete them!**):
    * Field `initiator` in category `backups` from `Optional[str]` to `Optional[int]`
    * Field `user` in category `states` from `Optional[str]` to `Optional[int]`

### [1.2.3](https://github.com/Druzai/Bot_Mc_discord/compare/1.2.2...1.2.3) (2021-12-19)

### Added information about `Log4Shell` exploit in README

#### Improvements:

* Updated mcipc from `1.4.0` to `1.5.4`
* Updated cryptography from `3.3.2` to `3.4.8`
* Added more extended printing of exceptions in bot commands
* Added handling very long messages from Discord in cross-platform chat

### [1.2.2](https://github.com/Druzai/Bot_Mc_discord/compare/1.2.1...1.2.2) (2021-12-02)

#### Improvements:

* Improved awaiting user input before bot get stopped
* Added print of help when bot is started with argument `-h` or `--help`
* Bot now can save unhandled exceptions to log file
* Improved RSS feed parser for checking published date

#### Fixed:

* Fixed getting bot's current working directory
* Fixed executing command `clear all`

### [1.2.1](https://github.com/Druzai/Bot_Mc_discord/compare/1.2.0...1.2.1) (2021-11-16)

### Updated some dependencies

#### Fixed:

* Changed `enable_auth_security` to `enable_secure_auth` in bot's configuration file

## [1.2.0](https://github.com/Druzai/Bot_Mc_discord/compare/1.1.4...1.2.0) (2021-11-15)

#### Improvements:

* **Added secure authorization in Minecraft** ([#22](https://github.com/Druzai/Bot_Mc_discord/issues/22))
* Added ability to delete only bot's messages in DM

#### Fixed:

* Fixed wrong parsed `\n` by Minecraft client `1.7.*`

#### Breaking changes:

* Deleted `vk_api` and `say` command
* In server's configuration file changed a way to store datetime object, to get update status dates just start/stop server
* In bot's configuration file:
    * Moved setting `cross_platform_chat` and subsettings: `enable_cross_platform_chat`, `channel_id`, `webhook_url` in new setting `server_watcher`
    * Moved subsettings: `refresh_delay_of_console_log`, `number_of_lines_to_check_in_console_log` in new setting `server_watcher`

### [1.1.4](https://github.com/Druzai/Bot_Mc_discord/compare/1.1.3...1.1.4) (2021-10-26)

#### Improvements:

* Added administrator role
* Added compatibility with old Minecraft versions

#### Fixed:

* Printing servers' list
* Showing replies from Discord

### [1.1.3](https://github.com/Druzai/Bot_Mc_discord/compare/1.1.2...1.1.3) (2021-10-17)

### Hotfix

Fixed cross-platform chat on Linux

### [1.1.2](https://github.com/Druzai/Bot_Mc_discord/compare/1.1.1...1.1.2) (2021-10-17)

#### Improvements:

* Added short mentions from Minecraft for `@everyone` and `@here`, `@a` and `@p` accordingly
* Added subcommand `ops history/hist`
* Added optional logging to file
* Extended mention handling from Minecraft chat

#### Fixed:

* Fixed small errors
* Fixed printing of ANSI escape sequences on Windows

### [1.1.1](https://github.com/Druzai/Bot_Mc_discord/compare/1.1.0...1.1.1) (2021-10-01)

### Hotfix

Fixed stop/restart in menu

## [1.1.0](https://github.com/Druzai/Bot_Mc_discord/compare/1.0.1...1.1.0) (2021-09-27)

#### Improvements:

* **Added auto and forced backups** ([#20](https://github.com/Druzai/Bot_Mc_discord/issues/20) [#21](https://github.com/Druzai/Bot_Mc_discord/issues/21))
* Added more thorough checking for polls
* Added subcommands sorting in help description

#### Fixed:

* Fixed detection in command clear, when passing a positive number and member mention
* Fixed small bugs

### [1.0.1](https://github.com/Druzai/Bot_Mc_discord/compare/1.0.0...1.0.1) (2021-09-16)

#### Improvements:

* Added missing translations for permissions
* Added printing full names of languages when list of bot's languages is returned
* Misc fixes

## [1.0.0](https://github.com/Druzai/Bot_Mc_discord/compare/0.4.0...1.0.0) (2021-09-15)

## Major version, at last

#### Improvements:

* Added localization for English and Russian
* Improved help command
    * Refactored help command
    * Added help about each command and subcommand
* Improved clear command
    * Clear to reply
    * Clear only mentioned members
* Added prefix command
* Fixed bugs and improved text strings

#### Breaking changes:

* Section in config.yaml `awaiting_times` is now `timeouts`, so if you have configured config just replace this key with
  a new one
* Changed file extension of config files from `.yaml` to `.yml`

### [0.4.0](https://github.com/Druzai/Bot_Mc_discord/compare/0.2.1...0.4.0) (2021-08-30)

### Stable release with huge changes

* Added cross-platform chat, RRS feed, moved all bot configs to yaml file
* Improved op and codes commands
