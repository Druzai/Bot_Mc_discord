# Changelog

All important changes to this project will be documented in this file.

### [1.2.4 Unreleased](https://github.com/Druzai/Bot_Mc_discord/compare/1.2.3...1.2.4) (2022-xx-xx)

#### Improvements:

* **Important!** Added saving all data on the server to disk before backing up
* Added handling `.cmd` script and shortcut to `.bat` or `.cmd` script as start file on Windows
* Added editing messages from Minecraft in Discord channel and edit webhook messages from Discord ([#27](https://github.com/Druzai/Bot_Mc_discord/issues/27))

#### Fixed:

* Fixed mentions from Minecraft to Discord ([#25](https://github.com/Druzai/Bot_Mc_discord/issues/25))
* Bot created a poll if you were initiator of stopping the server and only your accounts were logged in ([#24](https://github.com/Druzai/Bot_Mc_discord/issues/24))
* Added resetting gamemode in `op` command
* Disabled deleting user message in cross-platform chat when server is down or there are no players on it
* Fixed slow bot response when sending a message from synchronous function
* Added additional spaces when there are more than 9 items in list to display in command output
* Reduced 'backup force' command cooldown to 15 seconds
* Changed commands:
  * Renamed `servers` to `server` and alias `servs` to `serv`
  * Moved logic from `servers show` to `server`
  * Added alias `associate` to `assoc`
  * Added alias `ls` to all `list` subcommands

#### Breaking changes:

* Changed `specific_command_role_id` to `managing_commands_role_id` in bot's configuration file

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

## [0.4.0](https://github.com/Druzai/Bot_Mc_discord/compare/0.2.1...0.4.0) (2021-08-30)

### Stable release with huge changes

* Added cross-platform chat, RRS feed, moved all bot configs to yaml file
* Improved op and codes commands