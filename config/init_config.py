import datetime as dt
import sys
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from glob import glob
from hashlib import md5
from json import load, JSONDecodeError, dump
from locale import getdefaultlocale
from os import mkdir, getcwd, environ
from os.path import isfile, isdir, join as path_join
from pathlib import Path
from random import randint, choice
from re import search, findall
from secrets import choice as sec_choice
from string import ascii_letters, digits
from struct import unpack
from typing import List, Optional, TYPE_CHECKING, Set, Union, Dict, Iterable

from colorama import Style
from cryptography.fernet import InvalidToken
from discord import SyncWebhook, Member
from discord.ext.commands import Bot
from discord.utils import MISSING
from jsons import load as sload, DeserializationError
from omegaconf import OmegaConf as Conf
from psutil import Process
from requests import Session

from components.constants import CODE_LETTERS, URL_REGEX, WINDOW_AVERAGE_LENGTH
from components.localization import get_translation, get_locales, set_locale
from config.crypt_wrapper import encrypt_string, decrypt_string

if TYPE_CHECKING:
    from components.additional_funcs import ServerVersion, IPv4Address
    from components.watcher_handle import Watcher


class BotVars:
    react_auth: Member = None  # Represents author that added reaction
    is_server_on: bool = False
    is_loading: bool = False
    is_stopping: bool = False
    is_restarting: bool = False
    is_doing_op: bool = False
    is_voting: bool = False
    is_backing_up: bool = False
    is_restoring: bool = False
    is_auto_backup_disable: bool = False
    op_deop_list: List = []  # List of nicks of players to op and then to deop
    auto_shutdown_start_date: Optional[datetime] = None
    players_login_dict: dict = {}  # Dict of logged nicks and datetime of their login
    java_processes: List[Process] = []
    watcher_of_log_file: Optional['Watcher'] = None
    session_for_other_requests: Optional[Session] = None
    webhook_chat: Optional[SyncWebhook] = None
    wh_session_chat: Optional[Session] = None
    webhook_rss: Optional[SyncWebhook] = None
    wh_session_rss: Optional[Session] = None
    bot_for_webhooks: Bot = None

    @classmethod
    def add_player_login(cls, nick: str):
        if cls.player_logged(nick) is None:
            cls.players_login_dict[nick] = datetime.now()

    @classmethod
    def remove_player_login(cls, nick: str):
        with suppress(KeyError):
            del cls.players_login_dict[nick]

    @classmethod
    def player_logged(cls, nick: str) -> Optional[datetime]:
        return cls.players_login_dict.get(nick, None)


class OS(Enum):
    Windows = auto()
    Linux = auto()
    MacOS = auto()
    Unknown = auto()

    @staticmethod
    def resolve_os():
        if sys.platform == "linux" or sys.platform == "linux2":
            return OS.Linux
        elif sys.platform == "win32":
            return OS.Windows
        elif sys.platform == "darwin":
            return OS.MacOS
        else:
            return OS.Unknown


class WindowedAverage:
    def __init__(self, size: int):
        self._size = size
        self._data = []

    @property
    def average(self):
        return int(sum(self._data) / len(self._data)) if len(self._data) > 0 else 0

    def add(self, value: int):
        self._data.append(value)
        if len(self._data) > self._size:
            value = self.average
            self._data.pop(-1)
            old_value = max(self._data, key=lambda x: abs(value - x))
            self._data[self._data.index(old_value)] = value

    def add_all(self, values: Iterable[int]):
        for value in values:
            self.add(value)

    def dump_list(self):
        return self._data


class UserAgent:
    _header: str = None

    @classmethod
    def _get_os(cls):
        if Config.get_os() == OS.Windows:
            return "Windows NT 10.0; Win64; x64"
        elif Config.get_os() == OS.MacOS:
            separator = choice([".", "_"])
            version = choice([
                separator.join(["10", str(randint(13, 15)), str(randint(0, 10))]),
                f"{randint(11, 13)}{separator}0"
            ])
            return f"Macintosh; Intel Mac OS X {version}"
        else:
            return choice(["X11; Linux", "X11; OpenBSD", "X11; Ubuntu; Linux"]) + \
                choice([" i386", " i686", " amd64", " x86_64"])

    @classmethod
    def _set_header(cls):
        if randint(0, 1):
            # Chrome
            version = f"{randint(105, 131)}.{randint(0, 99)}.{randint(0, 9999)}.{randint(0, 999)}"
            cls._header = f"Mozilla/5.0 ({cls._get_os()}) AppleWebKit/537.36 " \
                          f"(KHTML, like Gecko) Chrome/{version} Safari/537.36"
        else:
            # Firefox
            version = f"{randint(102, 132)}.0"
            cls._header = f"Mozilla/5.0 ({cls._get_os()}; rv:{version}) Gecko/20100101 Firefox/{version}"

    @classmethod
    def get_header(cls):
        if cls._header is None:
            cls._set_header()
        return cls._header

    @classmethod
    def clear_header(cls):
        cls._header = None


@dataclass
class Image_preview:
    enable_image_preview: Optional[bool] = None
    max_width: Optional[int] = None
    max_height: Optional[int] = None


@dataclass
class Obituary:
    enable_obituary: Optional[bool] = None
    name_for_death_messages: Optional[str] = None
    avatar_url_for_death_messages: Optional[str] = None

    @property
    def get_webhook_name_for_death_messages(self):
        if self.name_for_death_messages is not None:
            return self.name_for_death_messages
        return get_translation("☠ Obituary ☠")


@dataclass
class Game_chat:
    enable_game_chat: Optional[bool] = None
    webhook_url: Optional[str] = None
    obituary: Obituary = field(default_factory=Obituary)
    max_words_in_mention: Optional[int] = None
    max_wrong_symbols_in_mention_from_right: Optional[int] = None
    image_preview: Image_preview = field(default_factory=Image_preview)


@dataclass
class Ip_address_of_user:
    ip_address: str = ""
    authorized: bool = False
    expires_on_stamp: Optional[int] = None
    login_attempts: Optional[int] = None
    code = ""
    _code_expires_on_stamp = None

    @property
    def expires_on_date(self):
        if self.expires_on_stamp is not None:
            return datetime.fromtimestamp(self.expires_on_stamp)
        else:
            return None

    @expires_on_date.setter
    def expires_on_date(self, date: Optional[datetime]):
        self.expires_on_stamp = int(date.timestamp()) if date is not None else None

    @property
    def code_expires_on_date(self):
        if self._code_expires_on_stamp is not None:
            return datetime.fromtimestamp(self._code_expires_on_stamp)
        else:
            return None

    @code_expires_on_date.setter
    def code_expires_on_date(self, date: Optional[datetime]):
        self._code_expires_on_stamp = int(date.timestamp()) if date is not None else None


@dataclass
class Auth_user:
    nick: str = ""
    ip_addresses: List[Ip_address_of_user] = field(default_factory=list)


@dataclass
class Auth_users_list:
    auth_users: List[Auth_user] = field(default_factory=list)


@dataclass
class Secure_authorization:
    enable_secure_auth: Optional[bool] = None
    enable_login_check: Optional[bool] = None
    max_login_attempts: int = -1
    days_before_ip_expires: int = -1
    days_before_ip_will_be_deleted: int = -1
    code_length: int = -1
    mins_before_code_expires: int = -1


@dataclass
class Server_watcher:
    refresh_delay_of_console_log: float = -1.0
    number_of_lines_to_check_in_console_log: int = 0
    secure_auth: Secure_authorization = field(default_factory=Secure_authorization)
    game_chat: Game_chat = field(default_factory=Game_chat)


@dataclass
class Rss_feed:
    enable_rss_feed: Optional[bool] = None
    webhook_url: Optional[str] = None
    rss_url: Optional[str] = None
    rss_download_delay: int = -1
    rss_last_date: Optional[str] = None
    rss_spoof_user_agent: Optional[bool] = None


@dataclass
class Timeouts:
    await_seconds_when_connecting_via_rcon: float = -1.0
    await_seconds_in_check_ups: int = -1
    await_seconds_before_shutdown: int = -1
    await_seconds_when_opped: int = -1
    await_seconds_before_message_deletion: int = -1

    @property
    def calc_before_shutdown(self):
        return round(self.await_seconds_before_shutdown / self.await_seconds_in_check_ups) \
            * self.await_seconds_in_check_ups


@dataclass
class Backups:
    automatic_backup: Optional[bool] = None
    period_of_automatic_backups: Optional[int] = None
    name_of_the_backups_folder: str = ""
    size_limit_for_server: Optional[str] = ""
    max_backups_limit_for_server: Optional[int] = -1
    compression_method: Optional[str] = None

    @property
    def size_limit(self):
        if self.size_limit_for_server is None:
            return None
        else:
            if self.size_limit_for_server[-2:].upper() == "MB":
                return int(self.size_limit_for_server[:-2]) * 1048576
            elif self.size_limit_for_server[-2:].upper() == "GB":
                return int(self.size_limit_for_server[:-2]) * 1073741824
            elif self.size_limit_for_server[-2:].upper() == "TB":
                return int(self.size_limit_for_server[:-2]) * 1099511627776

    @property
    def supported_compression_methods(self):
        return ["STORED", "DEFLATED", "BZIP2", "LZMA"]


@dataclass
class Menu:
    ask_about_server_menu: bool = True
    server_menu_message_id: Optional[int] = None
    server_menu_channel_id: Optional[int] = None
    ask_about_bot_menu: bool = True
    bot_menu_message_id: Optional[int] = None
    bot_menu_channel_id: Optional[int] = None


@dataclass
class Op:
    enable_op: bool = False
    default_number_of_times_to_op: int = -1


@dataclass
class Proxy_opts:
    enable_rss_proxy: Optional[bool] = None
    enable_proxy_for_other_requests: Optional[bool] = None


@dataclass
class Proxy:
    enable_proxy: Optional[bool] = None
    proxy_url: Optional[str] = None
    enable_proxy_credentials: Optional[bool] = None
    proxy_login: Optional[str] = None
    proxy_password: Optional[str] = None
    proxy_opts: Proxy_opts = field(default_factory=Proxy_opts)


@dataclass
class Bot_settings:
    language: Optional[str] = None
    _token = None
    token_encrypted: Optional[str] = None

    @property
    def token(self):
        return self._token

    @token.setter
    def token(self, token_decrypted):
        self._token = token_decrypted
        self.token_encrypted = encrypt_string(token_decrypted)

    proxy: Proxy = field(default_factory=Proxy)
    prefix: str = ""
    help_arguments: List[str] = field(default_factory=list)
    gaming_status: str = ""
    idle_status: str = ""
    managing_commands_role_id: Optional[int] = None
    admin_role_id: Optional[int] = None
    ip_address: str = ""
    local_address: str = ""
    log_bot_messages: bool = None
    deletion_messages_limit_without_poll: int = -1
    menu: Menu = field(default_factory=Menu)
    commands_channel_id: Optional[int] = None
    forceload: bool = False
    auto_shutdown: bool = False
    op: Op = field(default_factory=Op)
    server_watcher: Server_watcher = field(default_factory=Server_watcher)
    rss_feed: Rss_feed = field(default_factory=Rss_feed)
    backups: Backups = field(default_factory=Backups)
    timeouts: Timeouts = field(default_factory=Timeouts)

    def __post_init__(self):
        if self.token_encrypted:
            with suppress(InvalidToken):
                self._token = decrypt_string(self.token_encrypted)


@dataclass
class Server_settings:
    server_name: str = ""
    working_directory: str = ""
    start_file_name: str = ""
    server_avg_loading_times: List[int] = field(default_factory=list)
    enforce_offline_mode: bool = False
    enforce_default_gamemode: bool = False

    @property
    def avg_loading_time(self):
        if len(self.server_avg_loading_times) > 0:
            wa = WindowedAverage(WINDOW_AVERAGE_LENGTH)
            wa.add_all(self.server_avg_loading_times)
            return wa.average
        else:
            return None

    @avg_loading_time.setter
    def avg_loading_time(self, value: int):
        wa = WindowedAverage(WINDOW_AVERAGE_LENGTH)
        wa.add_all(self.server_avg_loading_times)
        wa.add(value)
        self.server_avg_loading_times = wa.dump_list()
        del wa


@dataclass
class User:
    user_minecraft_nick: str = ""
    user_discord_id: int = -1


@dataclass
class Settings:
    bot_settings: Bot_settings = field(default_factory=Bot_settings)
    force_create_server_properties_and_eula: bool = None
    ask_to_change_servers_list: bool = True
    selected_server_number: int = 1
    servers_list: List[Server_settings] = field(default_factory=list)
    known_users: List[User] = field(default_factory=list)


@dataclass
class State_info:
    user: Optional[int] = None
    bot: bool = False
    date_stamp: Optional[int] = None

    def set_state_info(self, user: Optional[int], date: datetime, bot: bool = False):
        self.user, self.bot, self.date_stamp = user, bot, int(date.timestamp())

    @property
    def date(self):
        if self.date_stamp is not None:
            return datetime.fromtimestamp(self.date_stamp)
        else:
            return None


@dataclass
class States:
    started_info: State_info = field(default_factory=State_info)
    stopped_info: State_info = field(default_factory=State_info)


@dataclass
class Player:
    player_minecraft_nick: str = ""
    number_of_times_to_op: int = -1


@dataclass
class Backup_info:
    file_name: str = ""
    reason: Optional[str] = None
    restored_from: bool = False
    initiator: Optional[int] = None

    @property
    def file_creation_date(self):
        return datetime.strptime(self.file_name, "%d-%m-%Y-%H-%M-%S")


@dataclass
class Server_config:
    states: States = field(default_factory=States)
    backups: List[Backup_info] = field(default_factory=list)
    seen_players: List[Player] = field(default_factory=list)
    query_port = 0
    rcon_port = 0
    rcon_password = ""


class Properties:
    filepath: Path
    properties: dict

    def __init__(self, filepath: Path, create_if_not_exists: bool = False):
        self.filepath = filepath
        self.properties = {}
        if filepath.exists():
            with open(filepath, "r", encoding="utf8") as f:
                for line in f.readlines():
                    if line.startswith("#") or len(line) == 0 or line.find("=") == -1:
                        continue
                    ctx = iter(reversed(line.split("=", maxsplit=1)))
                    self.properties[next(ctx)] = next(ctx, "").strip()
        elif not create_if_not_exists:
            raise FileNotFoundError(get_translation("File '{0}' doesn't exist!").format(filepath.as_posix()))

    def save(self):
        with open(self.filepath, "w", encoding="utf8") as f:
            f.writelines([f"{k}={v}\n" for k, v in self.properties.items()])

    def __getitem__(self, key: str):
        return self.properties.get(key, None)

    def __setitem__(self, key: str, value):
        self.properties[key] = value

    def __delitem__(self, key):
        with suppress(KeyError):
            del self.properties[key]

    def __contains__(self, item):
        return item in self.properties

    def __iter__(self):
        return iter(self.properties)

    def __len__(self):
        return len(self.properties)

    def __repr__(self):
        return repr(self.properties)

    @staticmethod
    def _parse_from_parameter(value: Optional[str], is_bool=False, is_int=False):
        if value is None or value == "":
            return value
        else:
            if is_bool:
                if value.lower() == "true":
                    return True
                elif value.lower() == "false":
                    return False
                else:
                    return
            elif is_int:
                try:
                    return int(value)
                except ValueError:
                    return None
            else:
                return value

    @staticmethod
    def _parse_to_parameter(value: Union[str, int, bool, None]):
        if value is None:
            return ""
        else:
            if isinstance(value, bool):
                return str(value).lower()
            elif isinstance(value, int):
                return str(value)
            elif isinstance(value, str):
                return value
            else:
                raise ValueError(f"Wrong passed value {value!r}!")


class Eula(Properties):
    def __init__(self, filepath: Optional[Path] = None, create_if_not_exists: bool = False):
        if filepath is None:
            filepath = Path(Config.get_selected_server_from_list().working_directory, "eula.txt")
        super().__init__(filepath, create_if_not_exists)

    @property
    def eula(self) -> bool:
        return self._parse_from_parameter(self["eula"], is_bool=True)

    @eula.setter
    def eula(self, value: bool):
        self["eula"] = self._parse_to_parameter(value)


class ServerProperties(Properties):
    def __init__(self, filepath: Optional[Path] = None, create_if_not_exists: bool = False):
        if filepath is None:
            filepath = Path(Config.get_selected_server_from_list().working_directory, "server.properties")
        super().__init__(filepath, create_if_not_exists)

    @property
    def enable_query(self) -> bool:
        return self._parse_from_parameter(self["enable-query"], is_bool=True)

    @enable_query.setter
    def enable_query(self, value: bool):
        self["enable-query"] = self._parse_to_parameter(value)

    @property
    def query_port(self) -> int:
        return self._parse_from_parameter(self["query.port"], is_int=True)

    @query_port.setter
    def query_port(self, value: int):
        self["query.port"] = self._parse_to_parameter(value)

    @property
    def enable_rcon(self) -> bool:
        return self._parse_from_parameter(self["enable-rcon"], is_bool=True)

    @enable_rcon.setter
    def enable_rcon(self, value: bool):
        self["enable-rcon"] = self._parse_to_parameter(value)

    @property
    def rcon_port(self) -> int:
        return self._parse_from_parameter(self["rcon.port"], is_int=True)

    @rcon_port.setter
    def rcon_port(self, value: int):
        self["rcon.port"] = self._parse_to_parameter(value)

    @property
    def rcon_password(self) -> str:
        return self._parse_from_parameter(self["rcon.password"])

    @rcon_password.setter
    def rcon_password(self, value: str):
        self["rcon.password"] = self._parse_to_parameter(value)

    @property
    def force_gamemode(self) -> bool:
        return self._parse_from_parameter(self["force-gamemode"], is_bool=True)

    @force_gamemode.setter
    def force_gamemode(self, value: bool):
        self["force-gamemode"] = self._parse_to_parameter(value)

    @property
    def online_mode(self) -> bool:
        return self._parse_from_parameter(self["online-mode"], is_bool=True)

    @online_mode.setter
    def online_mode(self, value: bool):
        self["online-mode"] = self._parse_to_parameter(value)

    @property
    def enforce_secure_profile(self) -> bool:
        return self._parse_from_parameter(self["enforce-secure-profile"], is_bool=True)

    @enforce_secure_profile.setter
    def enforce_secure_profile(self, value: bool):
        self["enforce-secure-profile"] = self._parse_to_parameter(value)

    @property
    def level_name(self) -> str:
        return self._parse_from_parameter(self["level-name"])

    @level_name.setter
    def level_name(self, value: str):
        self["level-name"] = self._parse_to_parameter(value)

    @property
    def white_list(self) -> bool:
        return self._parse_from_parameter(self["white-list"], is_bool=True)

    @white_list.setter
    def white_list(self, value: bool):
        self["white-list"] = self._parse_to_parameter(value)

    @property
    def log_ips(self) -> bool:
        return self._parse_from_parameter(self["log-ips"], is_bool=True)

    @log_ips.setter
    def log_ips(self, value: bool):
        self["log-ips"] = self._parse_to_parameter(value)


class Config:
    _current_bot_path: str = getcwd()
    _config_name = "bot_config.yml"
    _settings_instance: Settings = Settings()
    _auth_users_name = "auth_users.yml"
    _auth_users_instance: Auth_users_list = Auth_users_list()
    _server_config_name = "server_config.yml"
    _server_config_instance: Server_config = Server_config()
    _op_log_name = "op.log"
    _bot_log_name = "bot.log"
    _need_to_rewrite = False
    _system_lang = None
    _os = OS.resolve_os()

    @classmethod
    def read_config(cls, change_servers=False):
        file_exists = False
        if isfile(cls._config_name):
            cls._settings_instance = cls._load_from_yaml(Path(cls._current_bot_path, cls._config_name), Settings)
            file_exists = True
        if change_servers:
            cls._settings_instance.ask_to_change_servers_list = True
        cls._setup_config(file_exists)
        cls.read_auth_users()

    @classmethod
    def save_config(cls):
        cls._save_to_yaml(cls._settings_instance, Path(cls._current_bot_path, cls._config_name))

    @classmethod
    def get_inside_path(cls):
        """
        Get bot current path for accessing files that added via pyinstaller --add-data

        Return
        ----------
        bot_path: str
            bot pyinstaller path if there is one
        """
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            return sys._MEIPASS
        else:
            return cls._current_bot_path

    @classmethod
    def setup_ca_file(cls):
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            environ['SSL_CERT_FILE'] = path_join(sys._MEIPASS, 'lib', 'cert.pem')

    @classmethod
    def init_with_system_language(cls):
        lang = getdefaultlocale()[0].split('_')[0].lower()
        cls._system_lang = set_locale(lang, set_eng_if_error=True)

    @classmethod
    def get_os(cls):
        return cls._os

    @classmethod
    def get_bot_config_path(cls) -> str:
        return cls._current_bot_path

    @classmethod
    def get_settings(cls) -> Settings:
        return cls._settings_instance

    @classmethod
    def get_server_watcher(cls) -> Server_watcher:
        return cls._settings_instance.bot_settings.server_watcher

    @classmethod
    def get_secure_auth(cls) -> Secure_authorization:
        return cls._settings_instance.bot_settings.server_watcher.secure_auth

    @classmethod
    def get_auth_users(cls) -> List[Auth_user]:
        return cls._auth_users_instance.auth_users

    @classmethod
    def read_auth_users(cls):
        fpath = Path(cls._current_bot_path, cls._auth_users_name)
        if fpath.is_file():
            cls._auth_users_instance = cls._load_from_yaml(fpath, Auth_users_list)
        else:
            cls._auth_users_instance = Auth_users_list()

    @classmethod
    def save_auth_users(cls):
        cls._save_to_yaml(cls._auth_users_instance, Path(cls._current_bot_path, cls._auth_users_name))

    @classmethod
    def add_ip_address(cls, user_nick: str, ip_address: str, is_login_attempt: bool = False):
        for i in range(len(cls.get_auth_users())):
            if cls.get_auth_users()[i].nick == user_nick:
                ip_addr = Ip_address_of_user(ip_address=ip_address)
                if is_login_attempt:
                    ip_addr.login_attempts = 1
                    while True:
                        ip_addr.code = "".join(sec_choice(CODE_LETTERS)
                                               for _ in range(cls.get_secure_auth().code_length))
                        if ip_addr.code not in [a.code for a in cls.get_auth_users()[i].ip_addresses]:
                            break
                    ip_addr.code_expires_on_date = \
                        datetime.now() + dt.timedelta(minutes=cls.get_secure_auth().mins_before_code_expires)
                else:
                    ip_addr.expires_on_date = datetime.now() + \
                                              dt.timedelta(days=cls.get_secure_auth().days_before_ip_expires)
                cls.get_auth_users()[i].ip_addresses.append(ip_addr)
                if is_login_attempt:
                    return ip_addr.login_attempts, ip_addr.code
                else:
                    return None

    @classmethod
    def update_ip_address(cls, user_nick: str, ip_address: str, whitelist: bool = False):
        is_login_attempt = False
        for i in range(len(cls.get_auth_users())):
            if cls.get_auth_users()[i].nick == user_nick:
                for j in range(len(cls.get_auth_users()[i].ip_addresses)):
                    if cls.get_auth_users()[i].ip_addresses[j].ip_address == ip_address:
                        if not whitelist:
                            if cls.get_auth_users()[i].ip_addresses[j].login_attempts is None:
                                if cls.get_auth_users()[i].ip_addresses[j].expires_on_date is None or \
                                        cls.get_auth_users()[i].ip_addresses[j].expires_on_date < datetime.now():
                                    is_login_attempt = True
                            else:
                                is_login_attempt = True

                        if is_login_attempt:
                            if cls.get_auth_users()[i].ip_addresses[j].login_attempts is None:
                                cls.get_auth_users()[i].ip_addresses[j].login_attempts = 0
                            cls.get_auth_users()[i].ip_addresses[j].login_attempts += 1
                            while True:
                                code = "".join(sec_choice(CODE_LETTERS)
                                               for _ in range(cls.get_secure_auth().code_length))
                                if code not in [a.code for a in cls.get_auth_users()[i].ip_addresses]:
                                    break
                            cls.get_auth_users()[i].ip_addresses[j].code = code
                            cls.get_auth_users()[i].ip_addresses[j].code_expires_on_date = \
                                datetime.now() + \
                                dt.timedelta(minutes=cls.get_secure_auth().mins_before_code_expires)
                            cls.get_auth_users()[i].ip_addresses[j].expires_on_date = None
                            return cls.get_auth_users()[i].ip_addresses[j].login_attempts, \
                                cls.get_auth_users()[i].ip_addresses[j].code
                        else:
                            cls.get_auth_users()[i].ip_addresses[j].expires_on_date = \
                                datetime.now() + dt.timedelta(days=cls.get_secure_auth().days_before_ip_expires)
                            cls.get_auth_users()[i].ip_addresses[j].authorized = True
                            cls.get_auth_users()[i].ip_addresses[j].login_attempts = None
                            cls.get_auth_users()[i].ip_addresses[j].code = None
                            cls.get_auth_users()[i].ip_addresses[j].code_expires_on_date = None
                            return None, None

    @classmethod
    def remove_ip_address(cls, ip_address: Union[str, 'IPv4Address'], user_nicks: Optional[List[str]] = None):
        ip_info_to_delete = None
        for i in range(len(cls.get_auth_users())):
            if user_nicks is None or cls.get_auth_users()[i].nick in user_nicks:
                for j in range(len(cls.get_auth_users()[i].ip_addresses)):
                    if cls.get_auth_users()[i].ip_addresses[j].ip_address == ip_address:
                        ip_info_to_delete = cls.get_auth_users()[i].ip_addresses[j]
                        break
                if ip_info_to_delete is not None:
                    cls.get_auth_users()[i].ip_addresses.remove(ip_info_to_delete)
                    ip_info_to_delete = None
                    if user_nicks is not None and len(user_nicks) == 1:
                        break

    @classmethod
    def get_users_ip_address_info(cls, user_nick: str, ip_address: str = None,
                                  code: str = None) -> Optional[Ip_address_of_user]:
        if ip_address is None and code is None:
            return None
        for user in cls.get_auth_users():
            if user.nick == user_nick:
                for ip_info in user.ip_addresses:
                    if ip_address is not None and ip_info.ip_address == ip_address:
                        return ip_info
                    if code is not None and ip_info.code == code:
                        return ip_info

    @classmethod
    def get_known_user_ips(cls, nick: Optional[str] = None) -> Set[str]:
        ip_set = set()
        for user in cls.get_auth_users():
            if nick is not None and user.nick != nick:
                continue
            for ip in user.ip_addresses:
                ip_set.add(ip.ip_address)
            if user.nick == nick:
                break
        return ip_set

    @classmethod
    def get_user_nicks(cls, ip_address: str = None, nick: str = None, authorized: bool = False):
        nicks_dict = {}
        for user in cls.get_auth_users():
            nicks_dict[user.nick] = []
            for ip in user.ip_addresses:
                if ip_address is not None and ip.ip_address != ip_address:
                    continue
                if (ip.expires_on_date is None or ip.expires_on_date < datetime.now() or
                    ip.login_attempts is not None) and not ip.authorized:
                    if not authorized or (nick is not None and user.nick == nick):
                        nicks_dict[user.nick].append([ip.ip_address, get_translation("Not allowed")])
                elif (ip.expires_on_date is None or ip.expires_on_date < datetime.now() or
                      ip.login_attempts is not None) and ip.authorized:
                    nicks_dict[user.nick].append([ip.ip_address, get_translation("Session expired")])
                else:
                    nicks_dict[user.nick].append([ip.ip_address, get_translation("Access granted")])
                if ip.ip_address == ip_address:
                    break
            if len(nicks_dict[user.nick]) == 0:
                nicks_dict.pop(user.nick)
        return nicks_dict

    @classmethod
    def add_auth_user(cls, user_nick: str):
        cls.get_auth_users().append(Auth_user(nick=user_nick))

    @classmethod
    def remove_auth_user(cls, user_nick: str):
        cls.get_auth_users().remove([i for i in cls.get_auth_users() if i.nick == user_nick][0])

    @classmethod
    def get_game_chat_settings(cls) -> Game_chat:
        return cls._settings_instance.bot_settings.server_watcher.game_chat

    @classmethod
    def get_obituary_settings(cls) -> Obituary:
        return cls._settings_instance.bot_settings.server_watcher.game_chat.obituary

    @classmethod
    def get_image_preview_settings(cls) -> Image_preview:
        return cls._settings_instance.bot_settings.server_watcher.game_chat.image_preview

    @classmethod
    def get_rss_feed_settings(cls) -> Rss_feed:
        return cls._settings_instance.bot_settings.rss_feed

    @classmethod
    def get_timeouts_settings(cls) -> Timeouts:
        return cls._settings_instance.bot_settings.timeouts

    @classmethod
    def get_backups_settings(cls) -> Backups:
        return cls._settings_instance.bot_settings.backups

    @classmethod
    def get_menu_settings(cls) -> Menu:
        return cls._settings_instance.bot_settings.menu

    @classmethod
    def get_op_settings(cls) -> Op:
        return cls._settings_instance.bot_settings.op

    @classmethod
    def get_selected_server_from_list(cls) -> Server_settings:
        return cls._settings_instance.servers_list[cls._settings_instance.selected_server_number - 1]

    @classmethod
    def get_known_users_list(cls) -> List[User]:
        return cls._settings_instance.known_users

    @classmethod
    def add_to_known_users_list(cls, user_minecraft_nick: str, user_discord_id: int):
        cls._settings_instance.known_users.append(User(user_minecraft_nick, user_discord_id))

    @classmethod
    def remove_from_known_users_list(cls, user_minecraft_nick: str, user_discord_id: int):
        cls._settings_instance.known_users.remove(User(user_minecraft_nick, user_discord_id))

    @classmethod
    def get_seen_players_list(cls) -> List[Player]:
        return cls._server_config_instance.seen_players

    @classmethod
    def add_to_seen_players_list(cls, player_minecraft_nick: str):
        cls._server_config_instance.seen_players.append(
            Player(player_minecraft_nick, cls.get_op_settings().default_number_of_times_to_op)
        )

    @classmethod
    def decrease_number_to_op_for_player(cls, player_minecraft_nick: str):
        for p in range(len(cls._server_config_instance.seen_players)):
            if cls._server_config_instance.seen_players[p].player_minecraft_nick == player_minecraft_nick:
                cls._server_config_instance.seen_players[p].number_of_times_to_op -= 1

    @classmethod
    def add_backup_info(cls, file_name: str, reason: str = None, initiator: int = None):
        cls._server_config_instance.backups.append(Backup_info(file_name=file_name, reason=reason, initiator=initiator))

    @classmethod
    def read_server_config(cls):
        fpath = Path(cls.get_selected_server_from_list().working_directory, cls._server_config_name)
        if fpath.is_file():
            cls._server_config_instance = cls._load_from_yaml(fpath, Server_config)
        else:
            cls._server_config_instance = Server_config()

    @classmethod
    def save_server_config(cls):
        cls._save_to_yaml(cls._server_config_instance,
                          Path(cls.get_selected_server_from_list().working_directory, cls._server_config_name))

    @classmethod
    def get_server_config(cls):
        return cls._server_config_instance

    @classmethod
    def read_server_info(cls):
        # Ensure that server folder exists
        if not Path(cls.get_selected_server_from_list().working_directory).exists():
            raise RuntimeError(get_translation("Directory {0} doesn't exist!")
                               .format(cls.get_selected_server_from_list().working_directory))
        cls.read_server_config()
        # Ensure we have backups folder
        backups_folder = Path(cls.get_selected_server_from_list().working_directory,
                              cls.get_backups_settings().name_of_the_backups_folder)
        if not backups_folder.exists():
            mkdir(backups_folder)
        # Remove nonexistent backups from server config
        list_to_remove = []
        for backup in cls.get_server_config().backups:
            if not Path(cls.get_selected_server_from_list().working_directory,
                        cls.get_backups_settings().name_of_the_backups_folder,
                        f"{backup.file_name}.zip").is_file():
                list_to_remove.append(backup)
        if len(list_to_remove) > 0:
            print(get_translation("There are some mismatched backups entries in '{0}':")
                  .format(Path(cls.get_selected_server_from_list().working_directory,
                               cls._server_config_name).as_posix()))
        for bc in list_to_remove:
            cls.get_server_config().backups.remove(bc)
            print(get_translation("Deleted backup entry named '{0}'").format(bc.file_name))
        if len(list_to_remove) > 0:
            cls.save_server_config()
        # Check if last backup is older than time of stopped server
        if len(cls.get_server_config().backups) > 0:
            if cls.get_server_config().states.stopped_info.date is not None:
                BotVars.is_auto_backup_disable = cls.get_server_config().states.stopped_info.date < \
                                                 max([b.file_creation_date for b in cls.get_server_config().backups])
            else:
                BotVars.is_auto_backup_disable = True
        if cls.get_settings().force_create_server_properties_and_eula:
            # Check eula.txt
            filepath = Path(cls.get_selected_server_from_list().working_directory, "eula.txt")
            if not filepath.exists():
                print(get_translation("File '{0}' doesn't exist!").format(filepath.as_posix()))
                print(get_translation("Bot will create a new one!"))
            eula_txt = Eula(filepath, create_if_not_exists=True)
            # Check eula parameters
            changed_parameters = []
            if not eula_txt.eula:
                eula_txt.eula = True
                changed_parameters.append("eula=true")
            if len(changed_parameters) > 0:
                eula_txt.save()
                print("------")
                print(get_translation("Note: In '{0}' bot set these parameters:").format(filepath.as_posix()))
                for line in changed_parameters:
                    print(line)
                print("------")
        # Check server.properties
        filepath = Path(cls.get_selected_server_from_list().working_directory, "server.properties")
        if not filepath.exists():
            if not cls.get_settings().force_create_server_properties_and_eula:
                raise FileNotFoundError(get_translation(
                    "File '{0}' doesn't exist! Run Minecraft server manually to create one and accept EULA!"
                ).format(filepath.as_posix()))
            print(get_translation("File '{0}' doesn't exist!").format(filepath.as_posix()))
            print(get_translation("Bot will create a new one!"))
        server_properties = ServerProperties(
            filepath,
            create_if_not_exists=cls.get_settings().force_create_server_properties_and_eula
        )
        if not cls.get_settings().force_create_server_properties_and_eula and len(server_properties) == 0:
            raise RuntimeError(get_translation(
                "File '{0}' doesn't have any parameters! Accept EULA and "
                "run Minecraft server manually to fill it with parameters!"
            ).format(filepath.as_posix()))
        # Check server parameters
        changed_parameters = []
        if cls.get_selected_server_from_list().enforce_offline_mode:
            if server_properties.online_mode or server_properties.online_mode is None:
                server_properties.online_mode = False
                changed_parameters.append("online-mode=false")
            if server_properties.enforce_secure_profile or (server_properties.enforce_secure_profile is None and
                                                            cls.get_settings().force_create_server_properties_and_eula):
                server_properties.enforce_secure_profile = False
                changed_parameters.append("enforce-secure-profile=false")
        if cls.get_selected_server_from_list().enforce_default_gamemode and not server_properties.force_gamemode:
            server_properties.force_gamemode = True
            changed_parameters.append("force-gamemode=true")
        # Ensure we have IPs shown if secure auth enabled otherwise message
        if cls.get_secure_auth().enable_secure_auth and server_properties.log_ips is False:
            server_properties.log_ips = True
            changed_parameters.append("log-ips=true")
            changed_parameters.append(get_translation("Note: Bot set property \"log-ips\" to true "
                                                      "because otherwise secure authorization won't work."))
        if not server_properties.enable_query:
            server_properties.enable_query = True
            changed_parameters.append("enable-query=true")
        if server_properties.query_port is None or server_properties.query_port == "":
            server_properties.query_port = 25565
            changed_parameters.append(f"query.port={server_properties.query_port}")
        if not server_properties.enable_rcon:
            server_properties.enable_rcon = True
            changed_parameters.append("enable-rcon=true")
        if server_properties.rcon_port is None or server_properties.rcon_port == "":
            server_properties.rcon_port = 25575
            changed_parameters.append(f"rcon.port={server_properties.rcon_port}")
        if server_properties.rcon_password is None or server_properties.rcon_password == "":
            server_properties.rcon_password = "".join(sec_choice(ascii_letters + digits) for _ in range(20))
            changed_parameters.append(f"rcon.password={server_properties.rcon_password}")
            changed_parameters.append(get_translation("Reminder: For better security "
                                                      "you have to change this password for a more secure one."))
        if len(changed_parameters) > 0:
            server_properties.save()
            print("------")
            print(get_translation("Note: In '{0}' bot set these parameters:").format(filepath.as_posix()))
            for line in changed_parameters:
                print(line)
            print("------")

        cls.get_server_config().query_port = server_properties.query_port
        cls.get_server_config().rcon_port = server_properties.rcon_port
        cls.get_server_config().rcon_password = server_properties.rcon_password

    @staticmethod
    def get_offline_uuid(username: str):
        data = bytearray(md5(("OfflinePlayer:" + username).encode()).digest())
        data[6] &= 0x0f  # clear version
        data[6] |= 0x30  # set to version 3
        data[8] &= 0x3f  # clear variant
        data[8] |= 0x80  # set to IETF variant
        uuid = data.hex()
        return "-".join((uuid[:8], uuid[8:12], uuid[12:16], uuid[16:20], uuid[20:]))

    @classmethod
    def save_to_whitelist(cls, version: 'ServerVersion', username: str):
        if cls.check_entry_in_whitelist(version, username):
            return

        if version.minor < 7 or (version.minor == 7 and version.patch < 6):
            filepath = Path(Config.get_selected_server_from_list().working_directory + "/white-list.txt")
            if filepath.exists():
                with open(filepath, "a", encoding="utf8") as f:
                    f.write(username + "\n")
            else:
                with open(filepath, "w", encoding="utf8") as f:
                    f.write(username + "\n")
        else:
            entry = dict(uuid=Config.get_offline_uuid(username), name=username)
            whitelist = [entry]
            filepath = Path(Config.get_selected_server_from_list().working_directory + "/whitelist.json")
            if filepath.exists():
                with suppress(JSONDecodeError):
                    with open(filepath, "r", encoding="utf8") as f:
                        whitelist = load(f)
                    whitelist.append(entry)
            with open(filepath, "w", encoding="utf8") as f:
                dump(whitelist, f, indent=2)

    @classmethod
    def check_entry_in_whitelist(cls, version: 'ServerVersion', username: str, remove_entry: bool = False) -> bool:
        is_entry_deleted = False
        if version.minor < 7 or (version.minor == 7 and version.patch < 6):
            filepath = Path(Config.get_selected_server_from_list().working_directory + "/white-list.txt")
            if filepath.exists():
                with open(filepath, "r", encoding="utf8") as f:
                    whitelist = [ln.strip() for ln in f.readlines()]
                if not remove_entry:
                    return username in whitelist
                with suppress(ValueError):
                    whitelist.remove(username)
                    is_entry_deleted = True
                if is_entry_deleted:
                    with open(filepath, "w", encoding="utf8") as f:
                        f.writelines(whitelist)
        else:
            filepath = Path(Config.get_selected_server_from_list().working_directory + "/whitelist.json")
            if filepath.exists():
                with suppress(JSONDecodeError):
                    with open(filepath, "r", encoding="utf8") as f:
                        whitelist = load(f)
                    if not remove_entry:
                        return username in [e["name"] for e in whitelist]
                for entry in range(len(whitelist)):
                    if whitelist[entry]["name"] == username:
                        whitelist.remove(whitelist[entry])
                        is_entry_deleted = True
                if is_entry_deleted:
                    with open(filepath, "w", encoding="utf8") as f:
                        dump(whitelist, f, indent=2)
        return is_entry_deleted

    @classmethod
    def get_list_of_ops(cls, version: 'ServerVersion') -> List[str]:
        ops_list = []
        if version.minor < 7 or (version.minor == 7 and version.patch < 6):
            filepath = Path(cls.get_selected_server_from_list().working_directory + "/ops.txt")
            if filepath.is_file():
                with open(filepath, "r", encoding="utf8") as f:
                    ops_list = [ln.strip() for ln in f.readlines()]
        else:
            filepath = Path(cls.get_selected_server_from_list().working_directory + "/ops.json")
            if filepath.is_file():
                with open(filepath, "r", encoding="utf8") as f:
                    json_ops = load(f)
                ops_list = [d["name"] for d in json_ops if d.get("name", None) is not None]
        return ops_list

    @classmethod
    def get_list_of_banned_ips_and_reasons(cls, version: 'ServerVersion') -> List[Dict[str, Optional[str]]]:
        ban_list = []
        if version.minor < 7 or (version.minor == 7 and version.patch < 6):
            filepath = Path(Config.get_selected_server_from_list().working_directory + "/banned-ips.txt")
            if filepath.is_file():
                with open(filepath, "r", encoding="utf8") as f:
                    if version.minor < 3:
                        ban_list = [{"ip": e.strip(), "reason": None} for e in f.readlines()]
                    else:
                        for line in f.readlines():
                            if not line.startswith("#") and len(line) > 0 and "|" in line:
                                try:
                                    ip, *_, reason = line.split("|")
                                    reason = reason.strip()
                                    if len(reason) == 0:
                                        reason = None
                                except ValueError:
                                    ip = line.split("|")[0]
                                    reason = None
                                ban_list.append({"ip": ip.strip(), "reason": reason})
        else:
            filepath = Path(Config.get_selected_server_from_list().working_directory + "/banned-ips.json")
            if filepath.is_file():
                with suppress(JSONDecodeError):
                    with open(filepath, "r", encoding="utf8") as f:
                        ban_list = load(f)
                    ban_list = [{"ip": e["ip"], "reason": e["reason"] if len(e["reason"]) > 0 else None}
                                for e in ban_list]
        return ban_list

    @classmethod
    def append_to_op_log(cls, message_line: str):
        with open(Path(cls.get_bot_config_path() + f'/{cls._op_log_name}'), 'a', encoding='utf8') as f:
            f.write(f"{message_line}\n")

    @classmethod
    def get_op_log(cls):
        try:
            with open(Path(cls.get_bot_config_path() + f'/{cls._op_log_name}'), 'r', encoding='utf8') as f:
                return f.readlines()
        except FileNotFoundError:
            return []

    @classmethod
    def get_bot_log_name(cls):
        return cls._bot_log_name

    @classmethod
    def get_proxy_url(cls):
        if (Config.get_settings().bot_settings.proxy.enable_proxy
                and Config.get_settings().bot_settings.proxy.proxy_url is not None
                and len(Config.get_settings().bot_settings.proxy.proxy_url) > 0):
            return Config.get_settings().bot_settings.proxy.proxy_url
        return

    @classmethod
    def get_proxy_credentials(cls):
        auth_login = Config.get_settings().bot_settings.proxy.proxy_login
        auth_password = Config.get_settings().bot_settings.proxy.proxy_password
        if (Config.get_settings().bot_settings.proxy.enable_proxy_credentials and auth_login is not None
                and auth_password is not None and len(auth_login) > 0 and len(auth_password) > 0):
            return auth_login, auth_password
        return

    @classmethod
    def get_enable_rss_proxy(cls):
        return (Config.get_settings().bot_settings.proxy.enable_proxy and
                Config.get_proxy_url() is not None and
                Config.get_settings().bot_settings.proxy.proxy_opts.enable_rss_proxy)

    @classmethod
    def get_proxy_dict(cls):
        proxies = {}
        proxy_url = Config.get_proxy_url()
        if not Config.get_settings().bot_settings.proxy.enable_proxy or proxy_url is None:
            return

        proxy_credentials = Config.get_proxy_credentials()
        if not proxy_url.startswith("http://") and not proxy_url.startswith("https://"):
            print(get_translation("Bot Error: {0}").format(
                get_translation("Proxy type isn't HTTP or HTTPS. Bot will use webhooks and requests without proxy!"))
            )
            return

        if proxy_credentials is not None:
            proxy_type = findall(r"https?://", proxy_url)[0]
            proxy_url = (f"{proxy_type}{proxy_credentials[0]}:{proxy_credentials[1]}@" + proxy_url.lstrip(proxy_type))
        proxies["http"] = proxy_url
        proxies["https"] = proxy_url
        return proxies

    @classmethod
    def get_proxy_session_for_other_requests(cls):
        session = Session()
        session.headers["User-Agent"] = UserAgent.get_header()
        if not Config.get_settings().bot_settings.proxy.enable_proxy or Config.get_proxy_url() is None or \
                not Config.get_settings().bot_settings.proxy.proxy_opts.enable_proxy_for_other_requests:
            return session
        proxies = cls.get_proxy_dict()
        if proxies is not None:
            session.proxies = proxies
        return session

    @classmethod
    def get_webhook_proxy_session(cls):
        proxies = cls.get_proxy_dict()
        if proxies is None:
            return MISSING
        session = Session()
        session.proxies = proxies
        return session

    @classmethod
    def _load_from_yaml(cls, filepath: Path, baseclass):
        class_object = Conf.to_object(Conf.load(filepath))
        if isinstance(Settings(), baseclass):
            if class_object.get("servers_list", None) is not None \
                    and isinstance(class_object.get("servers_list"), list):
                for i in range(len(class_object["servers_list"])):
                    # Migrate from 'server_loading_time' to 'server_avg_loading_times'
                    if class_object["servers_list"][i].get("server_loading_time", None) is not None:
                        wa = WindowedAverage(WINDOW_AVERAGE_LENGTH)
                        if class_object["servers_list"][i].get("server_avg_loading_times", None) is not None \
                                and isinstance(class_object["servers_list"][i]["server_avg_loading_times"], list):
                            wa.add_all(class_object["servers_list"][i]["server_avg_loading_times"])
                        wa.add(class_object["servers_list"][i]["server_loading_time"])
                        class_object["servers_list"][i]["server_avg_loading_times"] = wa.dump_list()
                        del wa
                        del class_object["servers_list"][i]["server_loading_time"]
        try:
            return sload(json_obj=class_object, cls=baseclass)
        except DeserializationError as e:
            print(get_translation("Bot Error: {0}").format(
                get_translation("Couldn't parse config file in path '{0}' - '{1}'").format(filepath.as_posix(), e)
            ))
            print(get_translation("Note: You can stop bot and fix config file manually."))
            print(get_translation("Setting up a new config..."))
            return baseclass()

    @classmethod
    def _save_to_yaml(cls, class_instance, filepath: Path):
        Conf.save(config=Conf.structured(class_instance), f=filepath)

    @staticmethod
    def _ask_for_data(
            message: str,
            match_str: Optional[str] = None,
            try_int=False,
            int_high_or_equal_than: Optional[int] = None,
            int_low_or_equal_than: Optional[int] = None,
            try_float=False,
            float_high_or_equal_than: Optional[float] = None,
            float_low_or_equal_than: Optional[float] = None,
            try_link=False
    ):
        while True:
            answer = str(input(message)).strip()
            if answer != "":
                if match_str is not None:
                    if match_str.lower() == "y" and answer.lower() not in ["y", "n"]:
                        continue
                    else:
                        return answer.lower() == match_str
                if try_link:
                    if search(rf"^{URL_REGEX}", answer):
                        return answer
                    else:
                        continue
                if try_int or int_high_or_equal_than is not None or int_low_or_equal_than is not None:
                    try:
                        if int_high_or_equal_than is not None and int(answer) < int_high_or_equal_than:
                            print(get_translation("Your number lower than {0}!").format(int_high_or_equal_than))
                            continue
                        if int_low_or_equal_than is not None and int(answer) > int_low_or_equal_than:
                            print(get_translation("Your number higher than {0}!").format(int_low_or_equal_than))
                            continue
                        return int(answer)
                    except ValueError:
                        print(get_translation("Your string doesn't contain an integer!"))
                        continue
                if try_float or float_high_or_equal_than is not None or float_low_or_equal_than is not None:
                    try:
                        if float_high_or_equal_than is not None and float(answer) < float_high_or_equal_than:
                            print(get_translation("Your number lower than {0}!").format(float_high_or_equal_than))
                            continue
                        if float_low_or_equal_than is not None and float(answer) > float_low_or_equal_than:
                            print(get_translation("Your number higher than {0}!").format(float_low_or_equal_than))
                            continue
                        return float(answer)
                    except ValueError:
                        print(get_translation("Your string doesn't contain a fractional number!"))
                        continue
                return answer

    @classmethod
    def _setup_config(cls, file_exists=False):
        cls._setup_language()

        if not file_exists:
            print(get_translation("File '{0}' wasn't found! Setting up a new one!").format(cls._config_name))
        else:
            print(get_translation("File '{0}' was found!").format(cls._config_name))

        cls._setup_token()
        cls._setup_proxy()
        cls._setup_prefix()
        cls._setup_help_arguments()
        cls._setup_roles()
        cls._setup_bot_statuses()
        cls._setup_ip_address()
        cls._setup_local_address()
        cls._setup_log_bot_messages()
        cls._print_tasks_info()
        cls._setup_clear_delete_limit_without_poll()
        cls._setup_menu()
        cls._setup_commands_channel_id()
        cls._setup_op()
        cls._setup_server_watcher()
        cls._setup_rss_feed()
        cls._setup_timeouts()
        cls._setup_servers()
        cls._setup_backups()

        if cls._need_to_rewrite:
            cls._need_to_rewrite = False
            cls.save_config()
            print(get_translation("Config saved!"))
        print(get_translation("Config read!"))

    @classmethod
    def _setup_language(cls):
        if cls._settings_instance.bot_settings.language is None or \
                not set_locale(cls._settings_instance.bot_settings.language):
            if cls._settings_instance.bot_settings.language is not None and \
                    not set_locale(cls._settings_instance.bot_settings.language):
                print(get_translation("Language setting in bot config is wrong! Setting up language again..."))

            cls._need_to_rewrite = True
            if not cls._system_lang:
                print("Bot doesn't have your system language. So bot selected English.")
            else:
                print(get_translation("Bot selected language based on your system language."))
            cls._settings_instance.bot_settings.language = cls._system_lang if cls._system_lang else "en"

            if cls._ask_for_data(get_translation("Do you want to change it?") + " Y/n\n> ", "y"):
                while True:
                    lang = cls._ask_for_data(get_translation("Enter one of these two-letter language codes: ") +
                                             "\n- " + "\n- ".join([f"{ln.capitalize()} ({get_translation(ln)})"
                                                                   for ln in get_locales()]) + "\n> ").lower()
                    if set_locale(lang):
                        cls._settings_instance.bot_settings.language = lang
                        print(get_translation("This language selected!"))
                        break
                    else:
                        print(get_translation("Bot doesn't have such language. Try again."))

    @classmethod
    def _setup_token(cls):
        if cls._settings_instance.bot_settings.token is None:
            cls._need_to_rewrite = True
            if cls._settings_instance.bot_settings.token_encrypted is not None:
                print(get_translation("Bot couldn't decrypt Discord token with key from file '{0}'!")
                      .format(Path(Config._current_bot_path, "key").as_posix()))
            cls._settings_instance.bot_settings.token = \
                cls._ask_for_data(get_translation("Discord token not founded. Enter it") + "\n> ")

    @classmethod
    def _setup_proxy(cls):
        if cls._settings_instance.bot_settings.proxy.enable_proxy is None:
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.proxy.enable_proxy = cls._ask_for_data(
                get_translation("Enable using proxy?") + " Y/n\n> ", "y"
            )
        if cls._settings_instance.bot_settings.proxy.enable_proxy:
            if cls._settings_instance.bot_settings.proxy.proxy_url is None:
                cls._need_to_rewrite = True
                cls._settings_instance.bot_settings.proxy.proxy_url = cls._ask_for_data(
                    get_translation("Enter proxy URL (Example - http://{ip_address}:{port})") + "\n> ",
                    try_link=True
                )

            if cls._settings_instance.bot_settings.proxy.enable_proxy_credentials is None:
                cls._settings_instance.bot_settings.proxy.enable_proxy_credentials = cls._ask_for_data(
                    get_translation("Enable using proxy credentials?") + " Y/n\n> ", "y"
                )
            if cls._settings_instance.bot_settings.proxy.enable_proxy_credentials:
                if cls._settings_instance.bot_settings.proxy.proxy_login is None:
                    cls._need_to_rewrite = True
                    cls._settings_instance.bot_settings.proxy.proxy_login = \
                        cls._ask_for_data(get_translation("Enter proxy login") + "\n> ")
                if cls._settings_instance.bot_settings.proxy.proxy_password is None:
                    cls._need_to_rewrite = True
                    cls._settings_instance.bot_settings.proxy.proxy_password = \
                        cls._ask_for_data(get_translation("Enter proxy password") + "\n> ")

            if cls._settings_instance.bot_settings.proxy.proxy_opts.enable_rss_proxy is None:
                cls._need_to_rewrite = True
                cls._settings_instance.bot_settings.proxy.proxy_opts.enable_rss_proxy = cls._ask_for_data(
                    get_translation("Enable using proxy for RSS?") + " Y/n\n> ", "y"
                )
            if cls._settings_instance.bot_settings.proxy.proxy_opts.enable_proxy_for_other_requests is None:
                cls._need_to_rewrite = True
                cls._settings_instance.bot_settings.proxy.proxy_opts.enable_proxy_for_other_requests = \
                    cls._ask_for_data(
                        get_translation(
                            "Enable using proxy for other requests?\n"
                            "(Such as checking links/images from channel associated with game chat feature,"
                            " checking Minecraft snapshot version, getting shortened links and etc.)"
                        ) + "\nY/n\n> ", "y"
                    )

        if cls._settings_instance.bot_settings.proxy.enable_proxy and cls.get_proxy_url() is not None:
            print(get_translation("Bot using proxy URL '{0}'.").format(cls.get_proxy_url()))
            if cls.get_proxy_credentials() is not None:
                print(get_translation("Proxy: login '{0}', password '{1}'.").format(*cls.get_proxy_credentials()))
        else:
            print(get_translation("Bot isn't using any proxy."))

    @classmethod
    def _setup_prefix(cls):
        if cls._settings_instance.bot_settings.prefix == "":
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.prefix = cls._ask_for_data(get_translation("Enter bot prefix") + "\n> ")
        print(get_translation("Bot prefix set to '{0}'.").format(cls._settings_instance.bot_settings.prefix))

    @classmethod
    def _setup_help_arguments(cls):
        if cls._settings_instance.bot_settings.help_arguments is None or \
                len(cls._settings_instance.bot_settings.help_arguments) == 0:
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.help_arguments.extend(["-h", "--help", "?"])
            print(get_translation("Default help arguments for each command are {0}.")
                  .format(str(cls._settings_instance.bot_settings.help_arguments).strip("[]")))
            if cls._ask_for_data(get_translation("Would you like to add something else?") + " Y/n\n> ", "y"):
                new_help_args = cls._ask_for_data(get_translation("Enter new arguments comma separated") + "\n> ")
                new_help_args = [i.strip() for i in new_help_args.split(",")]
                cls._settings_instance.bot_settings.help_arguments.extend(new_help_args)
                print(get_translation("Arguments added!"))
        print(get_translation("Help arguments for each command set to {0}.")
              .format(str(cls._settings_instance.bot_settings.help_arguments).strip("[]")))

    @classmethod
    def _setup_roles(cls):
        if cls._settings_instance.bot_settings.managing_commands_role_id is not None:
            print(get_translation("Role for commands that manage Minecraft server is set."))
        else:
            print(get_translation("Role for commands that manage Minecraft server doesn't stated. "
                                  "You can set it via command {0}.")
                  .format(f"{Config.get_settings().bot_settings.prefix}role command <role>"))
        if cls._settings_instance.bot_settings.admin_role_id:
            print(get_translation("Admin role for bot is set."))
        else:
            print(get_translation("Admin role for bot doesn't stated. You can set it via command {0}. "
                                  "Bot will check if member has 'Administrator' permission.")
                  .format(f"{Config.get_settings().bot_settings.prefix}role admin <role>"))

    @classmethod
    def _setup_ip_address(cls):
        if cls._settings_instance.bot_settings.ip_address == "":
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.ip_address = \
                cls._ask_for_data(get_translation("Enter server's real IP-address or DNS-name") + "\n> ")
        print(get_translation("Server's real IP-address or DNS-name is '{0}'.")
              .format(cls._settings_instance.bot_settings.ip_address))

    @classmethod
    def _setup_local_address(cls):
        if cls._settings_instance.bot_settings.local_address == "":
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.local_address = \
                cls._ask_for_data(get_translation("Enter server's local address (default - 'localhost')") + "\n> ")

    @classmethod
    def _setup_log_bot_messages(cls):
        if cls._settings_instance.bot_settings.log_bot_messages is None:
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.log_bot_messages = \
                cls._ask_for_data(get_translation("Do you want bot to log messages to '{0}' file?")
                                  .format(cls._bot_log_name) + " Y/n\n> ", "y")

    @classmethod
    def _setup_clear_delete_limit_without_poll(cls):
        if cls._settings_instance.bot_settings.deletion_messages_limit_without_poll < 0 or \
                cls._settings_instance.bot_settings.deletion_messages_limit_without_poll > 1000000:
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.deletion_messages_limit_without_poll = \
                cls._ask_for_data(get_translation("Set limit for deletion messages "
                                                  "without poll (0 - for disable poll) (int)") + "\n> ",
                                  try_int=True, int_high_or_equal_than=0, int_low_or_equal_than=1000000)

    @classmethod
    def _setup_menu(cls):
        # Server menu
        may_shut_up = False
        if cls.get_menu_settings().ask_about_server_menu and \
                (cls.get_menu_settings().server_menu_message_id is None or
                 cls.get_menu_settings().server_menu_message_id < 1):
            if cls._ask_for_data(
                    get_translation("Server menu message id not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                cls._need_to_rewrite = True
                cls.get_menu_settings().server_menu_message_id = \
                    cls._ask_for_data(get_translation("Enter server menu message id") + "\n> ", try_int=True,
                                      int_high_or_equal_than=1)
            else:
                may_shut_up = True
                print(get_translation("Server menu via buttons won't work. To make it work type "
                                      "'{0}menu server' to create new server menu and its message id with channel id.")
                      .format(cls._settings_instance.bot_settings.prefix))
        if cls.get_menu_settings().ask_about_server_menu and \
                cls.get_menu_settings().server_menu_message_id is not None and \
                (cls.get_menu_settings().server_menu_channel_id is None or
                 cls.get_menu_settings().server_menu_channel_id < 1):
            if cls._ask_for_data(
                    get_translation("Server menu channel id not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                cls._need_to_rewrite = True
                cls.get_menu_settings().server_menu_channel_id = \
                    cls._ask_for_data(get_translation("Enter server menu channel id") + "\n> ", try_int=True,
                                      int_high_or_equal_than=1)
            else:
                may_shut_up = True
                print(get_translation("Bot will try to find channel and message "
                                      "by going through all channels in Discord server."))
        if may_shut_up:
            cls._need_to_rewrite = True
            cls.get_menu_settings().ask_about_server_menu = \
                not cls._ask_for_data(get_translation("Do you want the bot to never ask you about server menu setup?") +
                                      " Y/n\n> ", "y")
        # Bot menu
        may_shut_up = False
        if cls.get_menu_settings().ask_about_bot_menu and \
                (cls.get_menu_settings().bot_menu_message_id is None or
                 cls.get_menu_settings().bot_menu_message_id < 1):
            if cls._ask_for_data(
                    get_translation("Bot menu message id not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                cls._need_to_rewrite = True
                cls.get_menu_settings().bot_menu_message_id = \
                    cls._ask_for_data(get_translation("Enter bot menu message id") + "\n> ", try_int=True,
                                      int_high_or_equal_than=1)
            else:
                may_shut_up = True
                print(get_translation("Bot menu via buttons won't work. To make it work type "
                                      "'{0}menu bot' to create new bot menu and its message id with channel id.")
                      .format(cls._settings_instance.bot_settings.prefix))
        if cls.get_menu_settings().ask_about_bot_menu and \
                cls.get_menu_settings().bot_menu_message_id is not None and \
                (cls.get_menu_settings().bot_menu_channel_id is None or
                 cls.get_menu_settings().bot_menu_channel_id < 1):
            if cls._ask_for_data(
                    get_translation("Bot menu channel id not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                cls._need_to_rewrite = True
                cls.get_menu_settings().bot_menu_channel_id = \
                    cls._ask_for_data(get_translation("Enter bot menu channel id") + "\n> ", try_int=True,
                                      int_high_or_equal_than=1)
            else:
                may_shut_up = True
                print(get_translation("Bot will try to find channel and message "
                                      "by going through all channels in Discord server."))
        if may_shut_up:
            cls._need_to_rewrite = True
            cls.get_menu_settings().ask_about_bot_menu = \
                not cls._ask_for_data(get_translation("Do you want the bot to never ask you about bot menu setup?") +
                                      " Y/n\n> ", "y")

    @classmethod
    def _setup_commands_channel_id(cls):
        if cls._settings_instance.bot_settings.commands_channel_id is None or \
                cls._settings_instance.bot_settings.commands_channel_id < 1:
            if cls._ask_for_data(
                    get_translation("Commands' channel id not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                cls._need_to_rewrite = True
                cls._settings_instance.bot_settings.commands_channel_id = \
                    cls._ask_for_data(get_translation("Enter commands' channel id") + "\n> ",
                                      try_int=True, int_high_or_equal_than=1)
            else:
                print(get_translation("Bot will send some push events to the channel it can post to."
                                      " To make it work right type '{0}channel commands' to create a link.")
                      .format(cls._settings_instance.bot_settings.prefix))

    @classmethod
    def _setup_bot_statuses(cls):
        # Gaming status
        if cls._settings_instance.bot_settings.gaming_status == "":
            cls._settings_instance.bot_settings.gaming_status = cls._ask_for_data(
                get_translation("Set gaming status") + "\n> ")
        # Idle status
        if cls._settings_instance.bot_settings.idle_status == "":
            cls._settings_instance.bot_settings.idle_status = cls._ask_for_data(
                get_translation("Set idle status") + "\n> ")

    @classmethod
    def _setup_op(cls):
        if cls.get_op_settings().enable_op:
            print(get_translation("Getting an operator to Minecraft players is enabled") + ".")
        else:
            print(get_translation("Getting an operator to Minecraft players is disabled") + ".")

        if cls.get_op_settings().default_number_of_times_to_op < 1 or \
                cls.get_op_settings().default_number_of_times_to_op > 1000:
            cls.get_op_settings().default_number_of_times_to_op = \
                cls._ask_for_data(get_translation("Set default number of times to give an operator "
                                                  "for every player (int):") + "\n> ",
                                  try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=1000)

    @classmethod
    def _print_tasks_info(cls):
        msg = f"{get_translation('Task: ')}'{get_translation('Autoload if server crashes')}'." \
              f"\n{get_translation('State: ')}"
        if cls.get_settings().bot_settings.forceload:
            msg += get_translation("Active")
        else:
            msg += get_translation("Disabled")
        print(f"{msg}.")
        msg = f"{get_translation('Task: ')}'{get_translation('Shutdown of Minecraft server when idle')}'." \
              f"\n{get_translation('State: ')}"
        if cls.get_settings().bot_settings.auto_shutdown:
            msg += get_translation("Active")
        else:
            msg += get_translation("Disabled")
        print(f"{msg}.")

    @classmethod
    def _setup_timeouts(cls):
        # Timeout between check-ups func
        if cls.get_timeouts_settings().await_seconds_in_check_ups < 5 or \
                cls.get_timeouts_settings().await_seconds_in_check_ups > 60:
            cls._need_to_rewrite = True
            print(get_translation("Timeout between check-ups 'Server on/off' set below 5. Change this option."))
            print(get_translation("Note: If your machine has processor with frequency 2-2.5 GHz, "
                                  "you have to set this option at least to '8' seconds "
                                  "or higher for the bot to work properly."))
            cls.get_timeouts_settings().await_seconds_in_check_ups = \
                cls._ask_for_data(
                    get_translation("Set timeout between check-ups 'Server on/off' (in seconds, int)") + "\n> ",
                    try_int=True, int_high_or_equal_than=5, int_low_or_equal_than=60
                )
        print(get_translation("Timeout between check-ups 'Server on/off' set to {0} sec.")
              .format(cls.get_timeouts_settings().await_seconds_in_check_ups))

        # Timeout for shutdown when no players found during a long period of time
        if cls.get_timeouts_settings().await_seconds_before_shutdown < 0 or \
                cls.get_timeouts_settings().await_seconds_before_shutdown > 86400:
            cls._need_to_rewrite = True
            print(get_translation("Timeout for shutdown the Minecraft server when no players found "
                                  "during a long period of time set below 0. Change this option."))
            cls.get_timeouts_settings().await_seconds_before_shutdown = \
                cls._ask_for_data(get_translation("Set timeout for shutdown the Minecraft server when "
                                                  "no players found during a long period of time (0 "
                                                  "- for instant shutdown) (in seconds, int)") + "\n> ",
                                  try_int=True, int_high_or_equal_than=0, int_low_or_equal_than=86400)
        print(get_translation("Timeout for shutdown the Minecraft server when no players found during "
                              "a long period of time set to {0} sec.")
              .format(cls.get_timeouts_settings().await_seconds_before_shutdown))
        if cls.get_timeouts_settings().await_seconds_before_shutdown == 0:
            print(get_translation("Server will be stopped immediately."))

        # Timeout for op
        if cls.get_timeouts_settings().await_seconds_when_opped < 0 or \
                cls.get_timeouts_settings().await_seconds_when_opped > 1440:
            cls._need_to_rewrite = True
            print(get_translation("Timeout for being operator in Minecraft set below 0. Change this option."))
            cls.get_timeouts_settings().await_seconds_when_opped = \
                cls._ask_for_data(get_translation("Set timeout for being operator in Minecraft "
                                                  "(0 - for unlimited timeout) (in seconds, int)") + "\n> ",
                                  try_int=True, int_high_or_equal_than=0, int_low_or_equal_than=1440)
        print(get_translation("Timeout for being operator in Minecraft set to {0} sec.")
              .format(cls.get_timeouts_settings().await_seconds_when_opped))
        if cls.get_timeouts_settings().await_seconds_when_opped == 0:
            print(get_translation("Limitation doesn't exist, padawan."))

        # Timeout to sleep while bot pinging server for info
        if cls.get_timeouts_settings().await_seconds_when_connecting_via_rcon < 0.5 or \
                cls.get_timeouts_settings().await_seconds_when_connecting_via_rcon > 7.0:
            cls._need_to_rewrite = True
            print(get_translation("Timeout while bot pinging server for info set below 0. Change this option."))
            cls.get_timeouts_settings().await_seconds_when_connecting_via_rcon = \
                cls._ask_for_data(get_translation(
                    "Set timeout while bot pinging server for info (in seconds, float)") + "\n> ",
                                  try_float=True, float_high_or_equal_than=0.5, float_low_or_equal_than=7.0)
        print(get_translation("Timeout while bot pinging server for info set to {0} sec.")
              .format(cls.get_timeouts_settings().await_seconds_when_connecting_via_rcon))

        # Timeout before message deletion
        if cls.get_timeouts_settings().await_seconds_before_message_deletion < 1 or \
                cls.get_timeouts_settings().await_seconds_before_message_deletion > 120:
            cls._need_to_rewrite = True
            print(get_translation(
                "Timeout before message deletion is set below 1. Change this option."))
            cls.get_timeouts_settings().await_seconds_before_message_deletion = \
                cls._ask_for_data(get_translation("Set timeout before message deletion (in seconds, int)") + "\n> ",
                                  try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=120)
        print(get_translation("Timeout before message deletion is set to {0} sec.")
              .format(cls.get_timeouts_settings().await_seconds_before_message_deletion))

    @classmethod
    def _setup_servers(cls):
        if cls._settings_instance.force_create_server_properties_and_eula is None:
            cls._need_to_rewrite = True
            cls._settings_instance.force_create_server_properties_and_eula = cls._ask_for_data(
                get_translation("Do you want the bot to create files 'server.properties' and 'eula.txt' "
                                "if they don't exist or empty? (EULA will always be accepted)") + " Y/n\n> ",
                "y"
            )
        if not 0 < cls._settings_instance.selected_server_number <= len(cls._settings_instance.servers_list):
            cls._settings_instance.selected_server_number = 1
            print(get_translation("Selected Minecraft server number is out of range! Bot set it to '1'."))
            cls._need_to_rewrite = True
        if not cls._settings_instance.ask_to_change_servers_list:
            print(get_translation("Selected Minecraft server dir set to path '{0}' also known as '{1}'.")
                  .format(cls.get_selected_server_from_list().working_directory,
                          cls.get_selected_server_from_list().server_name))
            return

        cls._need_to_rewrite = True
        if len(cls._settings_instance.servers_list) > 0:
            print(get_translation("There is/are {0} server(s) in bot config")
                  .format(len(cls._settings_instance.servers_list)))
        new_servers_number = cls._ask_for_data(get_translation("How much servers you intend to keep?") + "\n> ",
                                               try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=100)
        if new_servers_number >= len(cls._settings_instance.servers_list):
            for i in range(len(cls._settings_instance.servers_list)):
                cls._settings_instance.servers_list[i] = \
                    cls._change_server_settings(cls._settings_instance.servers_list[i])
            for _ in range(new_servers_number - len(cls._settings_instance.servers_list)):
                cls._settings_instance.servers_list.append(cls._change_server_settings())
        else:
            for server in cls._settings_instance.servers_list.copy():
                changed_server = cls._change_server_settings(server)
                if changed_server is not None:
                    old_server_pos = [s for s in range(len(cls._settings_instance.servers_list))
                                      if cls._settings_instance.servers_list[s] == server][0]
                    cls._settings_instance.servers_list[old_server_pos] = changed_server
                elif cls._ask_for_data(get_translation("Would you like to delete this server '{0}'?").format(
                        server.server_name
                ) + " Y/n\n> ", "y"):
                    cls._settings_instance.servers_list.remove(server)

        cls._settings_instance.ask_to_change_servers_list = False
        print(get_translation("Selected Minecraft server dir set to path '{0}' also known as '{1}'.")
              .format(cls.get_selected_server_from_list().working_directory,
                      cls.get_selected_server_from_list().server_name))

    @classmethod
    def _change_server_settings(cls, server: Server_settings = None):
        changing_settings = False
        if server is not None:
            if not cls._ask_for_data(
                    get_translation("Would you like to change this server '{0}'?").format(server.server_name) +
                    " Y/n\n> ", "y"):
                return server
            changing_settings = True
        else:
            print(get_translation("Configuring new server settings..."))

        if not changing_settings:
            server = Server_settings()
            server.server_name = cls._ask_for_data(get_translation("Enter server name") + "\n> ")
            server.working_directory = cls._get_server_working_directory()
            server.start_file_name = cls._get_server_start_file_name(server.working_directory)
            server.enforce_offline_mode = cls._ask_for_data(
                get_translation("Do you want the bot to set server properties "
                                "to offline mode (without Internet access)?") + " Y/n\n> ",
                "y"
            )
            server.enforce_default_gamemode = cls._ask_for_data(
                get_translation(
                    "Do you want the bot to set server property 'force-gamemode' to 'true'? Y/n"
                    " (forces players to join in the default game mode. Default is survival)\n"
                    "Note: It's better to enable this option if you're using a temporary operator via bot commands"
                ) + " \n> ",
                "y"
            )
        else:
            if cls._ask_for_data(
                    get_translation("Change server name '{0}'?").format(server.server_name) + " Y/n\n> ", "y"):
                server.server_name = cls._ask_for_data(get_translation("Enter server name") + "\n> ")
            if cls._ask_for_data(
                    get_translation("Change server working directory '{0}'?").format(server.working_directory) +
                    " Y/n\n> ", "y"):
                server.working_directory = cls._get_server_working_directory()
            if cls._ask_for_data(
                    get_translation("Change server start file name '{0}'?").format(server.start_file_name) +
                    " Y/n\n> ", "y"):
                server.start_file_name = cls._get_server_start_file_name(server.working_directory)
            if cls._ask_for_data(get_translation("Change server's enforce offline mode?") + " Y/n\n> ", "y"):
                server.enforce_offline_mode = cls._ask_for_data(
                    get_translation("Do you want the bot to set server properties "
                                    "to offline mode (without Internet access)?") + " Y/n\n> ",
                    "y"
                )
            if cls._ask_for_data(get_translation("Change server's enforce default game mode?") + " Y/n\n> ", "y"):
                server.enforce_default_gamemode = cls._ask_for_data(
                    get_translation(
                        "Do you want the bot to set server property 'force-gamemode' to 'true'? Y/n"
                        " (forces players to join in the default game mode. Default is survival)\n"
                        "Note: It's better to enable this option if you're using a temporary operator via bot commands"
                    ) + " \n> ",
                    "y"
                )
        return server

    @classmethod
    def _get_server_working_directory(cls):
        while True:
            working_directory = cls._ask_for_data(
                get_translation("Enter server working directory (full path)") + "\n> ")
            if isdir(working_directory):
                if len(glob(Path(working_directory + "/*.jar").as_posix())) > 0:
                    return working_directory
                else:
                    print(get_translation("There are no '*.jar' files in this working directory."))
            else:
                print(get_translation("This working directory is wrong."))

    @classmethod
    def _get_server_start_file_name(cls, working_directory: str):
        file_extensions = []
        existing_files = []
        if cls.get_os() == OS.Linux:
            file_extensions.append(".sh")
            print(get_translation(
                "Bot detected your operating system is Linux.\n"
                "Bot will search for '*.sh' file.\n"
                "You need to enter file name {0}without{1} file extension!"
            ).format(Style.BRIGHT, Style.RESET_ALL))
        elif cls.get_os() == OS.Windows:
            file_extensions.extend([".bat", ".cmd", ".lnk", ".bat.lnk", ".cmd.lnk"])
            print(get_translation(
                "Bot detected your operating system is Windows.\n"
                "Bot will search for '*.bat' file, '*.cmd' file or shortcut.\n"
                "You need to enter file name {0}without{1} file extension!"
            ).format(Style.BRIGHT, Style.RESET_ALL))
        elif cls.get_os() == OS.MacOS:
            file_extensions.extend([".command", ".sh"])
            print(get_translation(
                "Bot detected your operating system is macOS.\n"
                "Bot will search for '*.command' or '*.sh' file.\n"
                "You need to enter file name {0}without{1} file extension!"
            ).format(Style.BRIGHT, Style.RESET_ALL))
        else:
            file_extensions.append(None)
            print(get_translation(
                "Bot couldn't detect your operating system.\n"
                "You need to enter file name {0}with{1} file extension!"
            ).format(Style.BRIGHT, Style.RESET_ALL))
        while True:
            start_file_name = cls._ask_for_data(get_translation("Enter server start file name") + "\n> ")
            is_link_file = False
            for ext in file_extensions:
                start_file_name_with_ext = start_file_name + (ext if ext is not None else '')
                start_file_path = Path(working_directory, start_file_name_with_ext)
                if start_file_path.is_file():
                    if len(start_file_name_with_ext.split(".")) == 1 or \
                            start_file_name_with_ext.split(".")[-1].lower() == "lnk":
                        is_link_file = True
                        start_file_target = cls.read_link_target(start_file_path)
                        if not Path(start_file_target).is_file():
                            print(get_translation("Target of this start file shortcut '{0}' doesn't exists.")
                                  .format(start_file_name_with_ext))
                            continue
                        elif len(start_file_target.split(".")) == 1 or \
                                start_file_target.split(".")[-1] not in ["bat", "cmd"]:
                            print(get_translation("Target of this start file shortcut '{0}' "
                                                  "isn't '*.bat' file or '*.cmd' file.")
                                  .format(start_file_name_with_ext))
                            continue
                    existing_files.append(start_file_name_with_ext)
            if len(existing_files) == 0:
                if is_link_file:
                    continue
                print(get_translation("This start file doesn't exist."))
            elif len(existing_files) > 1:
                print(get_translation("Bot found several files that match search conditions:") +
                      "\n- " + "\n- ".join(existing_files))
                while True:
                    chosen_file_name = input(get_translation("Type the chosen one") + "\n> ").strip()
                    if chosen_file_name in existing_files:
                        return chosen_file_name
            else:
                return existing_files.pop()

    @staticmethod
    def read_link_target(path: Path):
        # Taken from
        # http://stackoverflow.com/a/28952464/1119602
        # https://gist.github.com/Winand/997ed38269e899eb561991a0c663fa49
        with open(path, "rb") as stream:
            content = stream.read()
        # skip first 20 bytes (HeaderSize and LinkCLSID)
        # read the LinkFlags structure (4 bytes)
        lflags = unpack("I", content[0x14:0x18])[0]
        position = 0x18
        # if the HasLinkTargetIDList bit is set then skip the stored IDList
        # structure and header
        if (lflags & 0x01) == 1:
            position = unpack("H", content[0x4C:0x4E])[0] + 0x4E
        last_pos = position
        position += 0x04
        # get how long the file information is (LinkInfoSize)
        length = unpack("I", content[last_pos:position])[0]
        # skip 12 bytes (LinkInfoHeaderSize, LinkInfoFlags and VolumeIDOffset)
        position += 0x0C
        # go to the LocalBasePath position
        lbpos = unpack("I", content[position:position + 0x04])[0]
        position = last_pos + lbpos
        # read the string at the given position of the determined length
        size = (length + last_pos) - position - 0x02
        content = content[position:position + size].split(b"\x00", 1)
        return content[-1].decode("utf-16" if len(content) > 1 else getdefaultlocale()[1])

    @classmethod
    def _setup_server_watcher(cls):
        if cls.get_server_watcher().refresh_delay_of_console_log < 0.5 or \
                cls.get_server_watcher().refresh_delay_of_console_log > 10.0:
            print(get_translation("Watcher's delay to refresh doesn't set."))
            print(get_translation("Note: If your machine has processor with frequency 2-2.5 GHz, "
                                  "you have to set this option from '0.5' to '0.9' second "
                                  "for the bot to work properly."))
            cls.get_server_watcher().refresh_delay_of_console_log = \
                cls._ask_for_data(get_translation("Set delay to refresh (in seconds, float)") + "\n> ",
                                  try_float=True, float_high_or_equal_than=0.5, float_low_or_equal_than=10.0)

        if cls.get_server_watcher().number_of_lines_to_check_in_console_log < 1 or \
                cls.get_server_watcher().number_of_lines_to_check_in_console_log > 100:
            print(get_translation("Watcher's number of lines to check in server log doesn't set."))
            cls.get_server_watcher().number_of_lines_to_check_in_console_log = \
                cls._ask_for_data(get_translation("Set number of lines to check") + "\n> ",
                                  try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=100)

        # Game chat
        if cls.get_game_chat_settings().enable_game_chat is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Would you like to enable game chat?") + " Y/n\n> ", "y"):
                cls.get_game_chat_settings().enable_game_chat = True
                print(get_translation("Game chat enabled") + ".")

                if cls.get_game_chat_settings().webhook_url is None:
                    if cls._ask_for_data(get_translation("Webhook URL for game chat not found. "
                                                         "Would you like to enter it?") + " Y/n\n> ", "y"):
                        cls.get_game_chat_settings().webhook_url = \
                            cls._ask_for_data(get_translation("Enter webhook URL for game chat") + "\n> ",
                                              try_link=True)
                    else:
                        print(get_translation(
                            "Bot will fetch disowned webhook or create a new one! "
                            "You can change it via '{0}{1}'."
                        ).format(Config.get_settings().bot_settings.prefix, "chat webhook"))
                if cls.get_obituary_settings().avatar_url_for_death_messages is None:
                    if cls._ask_for_data(get_translation("Avatar URL for death messages chat not found. "
                                                         "Would you like to enter it?") + " Y/n\n> ", "y"):
                        cls.get_obituary_settings().avatar_url_for_death_messages = \
                            cls._ask_for_data(get_translation("Enter URL for avatar image") + "\n> ", try_link=True)
                    else:
                        print(get_translation("Avatar URL for death messages would be taken from bot's avatar."))
            else:
                cls.get_game_chat_settings().enable_game_chat = False
                print(get_translation("Game chat disabled") + ".")
        else:
            if cls.get_game_chat_settings().enable_game_chat:
                print(get_translation("Game chat enabled") + ".")
            else:
                print(get_translation("Game chat disabled") + ".")

        if cls.get_game_chat_settings().max_words_in_mention is None or \
                cls.get_game_chat_settings().max_words_in_mention < 1 or \
                cls.get_game_chat_settings().max_words_in_mention > 20:
            cls._need_to_rewrite = True
            cls.get_game_chat_settings().max_words_in_mention = \
                cls._ask_for_data(
                    get_translation("Enter how many words in mention from Minecraft chat bot can parse "
                                    "(0 - handle only mentions with one word) (default - 5, int)") + "\n> ",
                    try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=20)
        if cls.get_game_chat_settings().max_wrong_symbols_in_mention_from_right is None or \
                cls.get_game_chat_settings().max_wrong_symbols_in_mention_from_right < 1 or \
                cls.get_game_chat_settings().max_wrong_symbols_in_mention_from_right > 20:
            cls._need_to_rewrite = True
            cls.get_game_chat_settings().max_wrong_symbols_in_mention_from_right = \
                cls._ask_for_data(
                    get_translation("Enter how many characters from right side of mention "
                                    "bot can remove to find similar mention in Discord"
                                    " (0 - don't try to find similar ones) (default - 5, int)") + "\n> ",
                    try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=20)

        # Images preview
        if cls.get_image_preview_settings().enable_image_preview is None and \
                not cls.get_game_chat_settings().enable_game_chat:
            cls.get_image_preview_settings().enable_image_preview = False
            cls.get_image_preview_settings().max_width = 160
            cls.get_image_preview_settings().max_height = 30
        elif cls.get_image_preview_settings().enable_image_preview is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Would you like to enable image preview in game chat?") +
                                 " Y/n\n> ", "y"):
                cls.get_image_preview_settings().enable_image_preview = True
                print(get_translation("Image preview enabled") + ".")
            else:
                cls.get_image_preview_settings().enable_image_preview = False
                print(get_translation("Image preview disabled") + ".")

        if cls.get_image_preview_settings().max_width is None or \
                cls.get_image_preview_settings().max_width < 1 or \
                cls.get_image_preview_settings().max_width > 160:
            cls._need_to_rewrite = True
            cls.get_image_preview_settings().max_width = \
                cls._ask_for_data(
                    get_translation("Enter the maximum image width that will be displayed in game chat"
                                    " (default - 160 pixels, int)") + "\n> ",
                    try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=160)

        if cls.get_image_preview_settings().max_height is None or \
                cls.get_image_preview_settings().max_height < 1 or \
                cls.get_image_preview_settings().max_height > 36:
            cls._need_to_rewrite = True
            cls.get_image_preview_settings().max_height = \
                cls._ask_for_data(
                    get_translation("Enter the maximum image height that will be displayed in game chat"
                                    " (default - 30 pixels, int)") + "\n> ",
                    try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=36)

        # Obituary
        if cls.get_obituary_settings().enable_obituary is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Would you like to enable obituary?") + " Y/n\n> ", "y"):
                cls.get_obituary_settings().enable_obituary = True
                print(get_translation("Obituary enabled") + ".")

                if cls.get_obituary_settings().name_for_death_messages is None:
                    if cls._ask_for_data(get_translation("Webhook name for death messages not found. "
                                                         "Would you like to enter it?") + " Y/n\n> ", "y"):
                        cls.get_obituary_settings().name_for_death_messages = \
                            cls._ask_for_data(get_translation("Enter webhook name for death messages") + "\n> ")
                    else:
                        print(get_translation(
                            "Bot will use default name for death messages! "
                            "You can change it via '{0}{1}'."
                        ).format(Config.get_settings().bot_settings.prefix, "chat obituary name"))

                if cls.get_obituary_settings().avatar_url_for_death_messages is None:
                    if cls._ask_for_data(get_translation("Avatar URL for death messages not found. "
                                                         "Would you like to enter it?") + " Y/n\n> ", "y"):
                        cls.get_obituary_settings().avatar_url_for_death_messages = \
                            cls._ask_for_data(get_translation("Enter avatar URL for death messages") + "\n> ",
                                              try_link=True)
                    else:
                        print(get_translation(
                            "Bot will use default webhook's avatar for death messages! "
                            "You can change it via '{0}{1}'."
                        ).format(Config.get_settings().bot_settings.prefix, "chat obituary avatar"))
            else:
                cls.get_obituary_settings().enable_obituary = False
                print(get_translation("Obituary disabled") + ".")

        # Secure auth
        if cls.get_secure_auth().enable_secure_auth is None:
            cls._need_to_rewrite = True
            cls.get_secure_auth().enable_secure_auth = \
                cls._ask_for_data(get_translation("Would you like to enable authorization security?") + " Y/n\n> ", "y")
        if cls.get_secure_auth().enable_login_check is None:
            cls._need_to_rewrite = True
            cls.get_secure_auth().enable_login_check = \
                cls._ask_for_data(
                    get_translation(
                        "Would you like to enable login check? Y/n"
                        " (bot will ping the server to check if the player is really logged in)\n"
                        "Note: It's better to disable this option if you're using a modded server (forge, fabric)!"
                    ) + "\n> ",
                    "y"
                )
        if cls.get_secure_auth().max_login_attempts < 1 or cls.get_secure_auth().max_login_attempts > 100:
            cls._need_to_rewrite = True
            cls.get_secure_auth().max_login_attempts = \
                cls._ask_for_data(get_translation("Enter how many attempts bot will accept connection from "
                                                  "a certain IP-address before it bans this IP") + "\n> ",
                                  try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=100)
        if cls.get_secure_auth().days_before_ip_expires < 1 or cls.get_secure_auth().days_before_ip_expires > 90:
            cls._need_to_rewrite = True
            cls.get_secure_auth().days_before_ip_expires = \
                cls._ask_for_data(
                    get_translation("Enter how many days IP-address will be valid before it expires (int)") +
                    "\n> ", try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=90
                )
        if cls.get_secure_auth().days_before_ip_will_be_deleted < cls.get_secure_auth().days_before_ip_expires or \
                cls.get_secure_auth().days_before_ip_will_be_deleted > 356:
            cls._need_to_rewrite = True
            cls.get_secure_auth().days_before_ip_will_be_deleted = \
                cls._ask_for_data(
                    get_translation("Enter in how many days expired IP-address will be deleted (int)") + "\n> ",
                    try_int=True, int_high_or_equal_than=cls.get_secure_auth().days_before_ip_expires,
                    int_low_or_equal_than=356
                )
        if cls.get_secure_auth().code_length < 1 or \
                cls.get_secure_auth().code_length > 60:
            cls._need_to_rewrite = True
            cls.get_secure_auth().code_length = \
                cls._ask_for_data(
                    get_translation("Enter how many characters the code should consist of (default - 6, int)") + "\n> ",
                    try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=60
                )
        if cls.get_secure_auth().mins_before_code_expires < 1 or cls.get_secure_auth().mins_before_code_expires > 30:
            cls._need_to_rewrite = True
            cls.get_secure_auth().mins_before_code_expires = \
                cls._ask_for_data(get_translation("Enter how many minutes code will be valid before it expires (int)") +
                                  "\n> ", try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=30)

        if cls.get_secure_auth().enable_secure_auth:
            print(get_translation("Secure authorization enabled."))
        else:
            print(get_translation("Secure authorization disabled."))

    @classmethod
    def _setup_rss_feed(cls):
        if cls.get_rss_feed_settings().enable_rss_feed is None:
            cls._need_to_rewrite = True
            cls.get_rss_feed_settings().enable_rss_feed = cls._ask_for_data(
                get_translation("Would you like to enable RSS?") + " Y/n\n> ", "y"
            )

        if cls.get_rss_feed_settings().enable_rss_feed:
            if cls.get_rss_feed_settings().webhook_url is None:
                if cls._ask_for_data(get_translation("Webhook URL for RSS not found. Would you like to enter it?") +
                                     " Y/n\n> ", "y"):
                    cls._need_to_rewrite = True
                    cls.get_rss_feed_settings().webhook_url = \
                        cls._ask_for_data(get_translation("Enter webhook URL for RSS") + "\n> ", try_link=True)
                else:
                    print(get_translation(
                        "Bot will fetch disowned webhook or create a new one! "
                        "You can change it via '{0}{1}'."
                    ).format(Config.get_settings().bot_settings.prefix, "rss webhook"))

            if cls.get_rss_feed_settings().rss_url is None:
                if cls._ask_for_data(
                        get_translation("URL of RSS feed not found. Would you like to enter it?") + " Y/n\n> ",
                        "y"):
                    cls._need_to_rewrite = True
                    cls.get_rss_feed_settings().rss_url = \
                        cls._ask_for_data(get_translation("Enter URL of RSS feed") + "\n> ", try_link=True)
                else:
                    print(get_translation("RSS wouldn't work. Enter URL of RSS feed to bot config!"))

            if cls.get_rss_feed_settings().rss_download_delay < 1 or \
                    cls.get_rss_feed_settings().rss_download_delay > 604800:
                cls._need_to_rewrite = True
                print(get_translation("Scan interval for RSS feed not set") + ".")
                cls.get_rss_feed_settings().rss_download_delay = \
                    cls._ask_for_data(get_translation("Enter scan interval for RSS feed (in seconds, int)") +
                                      "\n> ", try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=604800)

            if cls.get_rss_feed_settings().rss_last_date is None:
                cls._need_to_rewrite = True
                cls.get_rss_feed_settings().rss_last_date = \
                    datetime.now().replace(microsecond=0).isoformat()

            if cls.get_rss_feed_settings().rss_spoof_user_agent is None:
                cls._need_to_rewrite = True
                cls.get_rss_feed_settings().rss_spoof_user_agent = cls._ask_for_data(
                    get_translation("Enable using spoofed user agent (Chrome or Firefox) instead of default one"
                                    " (indicating the sender is a bot) for RSS feed check requests?") + " Y/n\n> ",
                    "y"
                )

        if cls.get_rss_feed_settings().enable_rss_feed:
            print(get_translation("RSS enabled") + ".")
        else:
            print(get_translation("RSS disabled") + ".")

    @classmethod
    def _setup_backups(cls):
        if cls.get_backups_settings().automatic_backup is None:
            cls._need_to_rewrite = True
            cls.get_backups_settings().automatic_backup = \
                cls._ask_for_data(get_translation("Automatic backup isn't set. Would you like to enable them?") +
                                  " Y/n\n> ", "y")
        if cls.get_backups_settings().period_of_automatic_backups is None or \
                cls.get_backups_settings().period_of_automatic_backups < 1 or \
                cls.get_backups_settings().period_of_automatic_backups > 1440:
            cls._need_to_rewrite = True
            cls.get_backups_settings().period_of_automatic_backups = \
                cls._ask_for_data(get_translation("Set period of automatic backups (in minutes, int)") + "\n> ",
                                  try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=1440)
        if not cls.get_backups_settings().name_of_the_backups_folder:
            cls._need_to_rewrite = True
            cls.get_backups_settings().name_of_the_backups_folder = \
                cls._ask_for_data(get_translation("Enter name of the backups folder for each Minecraft server") +
                                  "\n> ")
        if cls.get_backups_settings().max_backups_limit_for_server is not None and \
                (cls.get_backups_settings().max_backups_limit_for_server < 1 or
                 cls.get_backups_settings().max_backups_limit_for_server > 100):
            cls._need_to_rewrite = True
            if cls._ask_for_data(
                    get_translation("The maximum backups' count limit for server not found. Would you like to set it?")
                    + " Y/n\n> ", "y"):
                cls.get_backups_settings().max_backups_limit_for_server = \
                    cls._ask_for_data(get_translation("Set maximum backups' count limit for server (int)") + "\n> ",
                                      try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=100)
            else:
                cls.get_backups_settings().max_backups_limit_for_server = None
        if cls.get_backups_settings().size_limit_for_server is not None and \
                len(cls.get_backups_settings().size_limit_for_server) > 0 and \
                cls.get_backups_settings().size_limit_for_server[-2:].upper() not in ["MB", "GB", "TB"]:
            cls.get_backups_settings().size_limit_for_server = ""
        if cls.get_backups_settings().size_limit_for_server == "":
            cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Backups' size limit for server not found. Would you like to set it?")
                                 + " Y/n\n> ", "y"):
                while True:
                    unit_of_bytes = cls._ask_for_data(get_translation("Enter in what unit of measure "
                                                                      "you will set the limit") +
                                                      " (MB, GB, TB)" + "\n> ").strip()
                    if unit_of_bytes.upper() not in ["MB", "GB", "TB"]:
                        print(get_translation("You have entered the wrong unit of measure!"))
                    else:
                        break
                size = cls._ask_for_data(
                    get_translation("Backups' size limit for server in {0} (int)").format(unit_of_bytes) + "\n> ",
                    try_int=True, int_high_or_equal_than=1, int_low_or_equal_than=100000)
                cls.get_backups_settings().size_limit_for_server = f"{size}{unit_of_bytes}"
            else:
                cls.get_backups_settings().size_limit_for_server = None
        if cls.get_backups_settings().compression_method is None:
            cls._need_to_rewrite = True
            cls.get_backups_settings().compression_method = \
                cls.get_backups_settings().supported_compression_methods[1]

        print(get_translation("Name of the backups folder in which bot will store them - '{0}'.")
              .format(cls.get_backups_settings().name_of_the_backups_folder))
