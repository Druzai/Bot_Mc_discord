from os import SEEK_END, stat
from pathlib import Path
from queue import Queue
from re import search, split, sub
from sys import exc_info
from threading import Thread
from time import sleep
from traceback import format_exc
from typing import Optional

from colorama import Fore, Style

from components.constants import MASS_REGEX_DEATH_MESSAGES, REGEX_DEATH_MESSAGES, DEATH_MESSAGES
from components.localization import get_translation
from components.logs.data import LogMessage, MessageType
from components.minecraft.connect import ServerVersion
from config.init_config import Config, BotVars


class WatchThread(Thread):
    def __init__(self, watch_file: Path, queue: Queue, server_version: ServerVersion):
        super().__init__()
        self.name = "WatchThread"
        self.daemon = True
        self._running = True
        self._cached_stamp: Optional[int] = None
        self._last_line: Optional[str] = None
        self._filename: Path = watch_file
        self._refresh_delay_secs = Config.get_server_watcher().refresh_delay_of_console_log
        self._queue: Queue[LogMessage] = queue
        self._server_version = server_version

    # Look for changes
    def look(self):
        stamp = stat(self._filename).st_mtime
        if stamp != self._cached_stamp:
            self._cached_stamp = stamp
            self._last_line = _check_log_file(
                file=self._filename,
                last_line=self._last_line,
                queue=self._queue,
                server_version=self._server_version
            )

    # Keep watching in a loop
    def run(self):
        while self._running:
            try:
                sleep(self._refresh_delay_secs)
                self.look()
            except FileNotFoundError:
                print(get_translation("Watcher Error: File '{0}' wasn't found!").format(self._filename.as_posix()))
            except UnicodeDecodeError:
                print(get_translation("Watcher Error: Can't decode strings from file '{0}'"
                                      ", check that Minecraft server saves it in utf-8 encoding!\n"
                                      "(Ensure you have '-Dfile.encoding=UTF-8' as one of the arguments "
                                      "to start the server in start script)").format(self._filename.as_posix()))
            except BaseException:
                exc = format_exc().rstrip("\n")
                print(get_translation("Log Watcher Unhandled Error: {0}").format(exc_info()[0]) +
                      f"\n{Style.DIM}{Fore.RED}{exc}{Style.RESET_ALL}")

    def join(self, timeout=0.5):
        self._running = False
        sleep(max(timeout, 0.5))


def _check_log_file(
        file: Path,
        server_version: ServerVersion,
        queue: Queue,
        last_line: Optional[str] = None
):
    if not Config.get_game_chat_settings().enable_game_chat and \
            not Config.get_secure_auth().enable_secure_auth:
        return None, None

    last_lines = _get_last_n_lines(file, Config.get_server_watcher().number_of_lines_to_check_in_console_log, last_line)
    if len(last_lines) == 0:
        return last_line

    date_line = r"^\[(?:\d{2}\w{3}\d{4} )?\d+:\d+:\d+(\.\d+)?]" if server_version.minor > 6 \
        else r"^\d+-\d+-\d+ \d+:\d+:\d+"
    info_line = r"\[Server thread/INFO][^\*<>]*:" if server_version.minor > 6 else r"\[INFO]"

    if last_line is None:
        last_lines = last_lines[-min(50, Config.get_server_watcher().number_of_lines_to_check_in_console_log):]
    last_lines = [sub(r"§[\dabcdefklmnor]", "", line) for line in last_lines]
    last_death_mob_id = ""

    for line in last_lines:
        if not search(rf"{date_line} {info_line}", line) or \
                search(rf"{date_line} {info_line}(?: \[Not Secure])? \* ", line):
            continue

        if server_version.minor < 17 or (server_version.minor == 17 and server_version.patch < 1):
            nick_regex = r".+"
        else:
            nick_regex = r"[^>]+"
        match = search(
            rf"{date_line} {info_line}(?: \[Not Secure])? <(?P<nick>{nick_regex})> (?P<message>.+)",
            line
        )
        if match is not None:
            player_nick = match.group("nick")
            player_message = match.group("message")

            queue.put(LogMessage(MessageType.PlayerMessage, player_nick=player_nick, player_message=player_message))
            continue

        if Config.get_secure_auth().enable_secure_auth or BotVars.webhook_chat is not None:
            logged_out_nick, reason = check_if_player_logged_out(line, info_line)

            if logged_out_nick is not None and reason is not None:
                queue.put(LogMessage(MessageType.PlayerLogout, player_nick=logged_out_nick, player_reason=reason))
                continue

            logged_in_nick, ip_address = check_if_player_logged_in(line, info_line)

            if logged_in_nick is not None and ip_address is not None:
                queue.put(LogMessage(MessageType.PlayerLogin, player_nick=logged_in_nick, player_ip=ip_address))
                continue

        if BotVars.webhook_chat is not None and search(f"{info_line} {MASS_REGEX_DEATH_MESSAGES}", line):
            for regex in range(len(REGEX_DEATH_MESSAGES)):
                message_match = search(f"{info_line} {REGEX_DEATH_MESSAGES[regex]}", line)
                if message_match:
                    id_match = search(
                        r"\['[^']+'/(?P<id>\d+), l='[^']+', x=-?\d+\.\d+, y=-?\d+\.\d+, z=-?\d+\.\d+]",
                        line
                    )
                    if id_match is not None:
                        if last_death_mob_id == id_match.group("id"):
                            break
                        last_death_mob_id = id_match.group("id")

                    queue.put(LogMessage(
                        MessageType.DeathMessage,
                        message_groups=[g.strip() for g in message_match.groups()],
                        death_message_regex=DEATH_MESSAGES[regex]
                    ))
                    break
            continue

    queue.put(LogMessage(MessageType.MessageBlockEnd))

    for line in reversed(last_lines):
        if search(date_line, line):
            return line


def check_if_player_logged_out(line: str, INFO_line: str):
    nick = None
    reason = None
    match = search(rf"{INFO_line} (?P<nick>.+) lost connection:", line)
    if match:
        nick = match.group("nick").strip()
        reason = split(r"lost connection:", line, maxsplit=1)[-1].strip()
        valid = nick in [p.player_minecraft_nick for p in Config.get_server_config().seen_players]
        if not valid:
            nick = None
            reason = None
    return nick, reason


def check_if_player_logged_in(line: str, INFO_line: str):
    nick = None
    ip_address = None
    match = search(
        rf"{INFO_line} (?P<nick>.+)\[/(?P<ip>\d+\.\d+\.\d+\.\d+):\d+] logged in with entity id \d+ at",
        line
    )
    if match:
        nick = match.group("nick").strip()
        ip_address = match.group("ip").strip()
    return nick, ip_address


def _get_last_n_lines(file: Path, number_of_lines: int, last_line: Optional[str]):
    list_of_lines = []
    with open(file, 'rb') as read_obj:
        read_obj.seek(-2, SEEK_END)
        buffer = bytearray()
        pointer_location = read_obj.tell()
        while pointer_location >= 0:
            read_obj.seek(pointer_location)
            pointer_location = pointer_location - 1
            new_byte = read_obj.read(1)
            if new_byte == b'\n':
                decoded_line = buffer[::-1].decode().strip()
                if decoded_line == last_line:
                    return list(reversed(list_of_lines))
                list_of_lines.append(decoded_line)
                if len(list_of_lines) == number_of_lines:
                    return list(reversed(list_of_lines))
                buffer = bytearray()
            else:
                buffer.extend(new_byte)
        if len(buffer) > 0:
            list_of_lines.append(buffer[::-1].decode().strip())
    return list(reversed(list_of_lines))
