import datetime as dt
import sys
from ast import literal_eval
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from glob import glob
from json import load
from locale import getdefaultlocale
from os import mkdir, listdir, remove, getcwd
from os.path import isfile, isdir
from pathlib import Path
from secrets import choice as sec_choice
from shutil import rmtree
from string import ascii_letters, digits
from typing import List, Optional, TYPE_CHECKING, Set

from discord import Webhook, Member
from discord.ext.commands import Bot
from jsons import load as sload, DeserializationError
from omegaconf import OmegaConf as Conf

from components.localization import get_translation, get_locales, set_locale
from config.crypt_wrapper import *

if TYPE_CHECKING:
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
    port_query: int = None
    port_rcon: int = None
    rcon_pass: str = None
    watcher_of_log_file: 'Watcher' = None
    watcher_last_line: str = None
    webhook_chat: Webhook = None
    webhook_rss: Webhook = None
    bot_for_webhooks: Bot = None


CODE_LETTERS = "WERTYUPASFGHKZXCVBNM23456789$%&+="


@dataclass
class Cross_platform_chat:
    enable_cross_platform_chat: Optional[bool] = None
    channel_id: Optional[int] = None
    webhook_url: Optional[str] = None
    max_words_in_mention: Optional[int] = None
    max_wrong_symbols_in_mention_from_right: Optional[int] = None


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
    logged = False


@dataclass
class Auth_users_list:
    auth_users: List[Auth_user] = field(default_factory=list)


@dataclass
class Secure_authorization:
    enable_secure_auth: Optional[bool] = None
    max_login_attempts: int = -1
    days_before_ip_expires: int = -1
    days_before_ip_will_be_deleted: int = -1
    code_length: int = -1
    mins_before_code_expires: int = -1


@dataclass
class Server_watcher:
    refresh_delay_of_console_log: float = -1.0
    number_of_lines_to_check_in_console_log: int = 0
    secure_auth: Secure_authorization = Secure_authorization()
    cross_platform_chat: Cross_platform_chat = Cross_platform_chat()


@dataclass
class Rss_feed:
    enable_rss_feed: Optional[bool] = None
    webhook_url: Optional[str] = None
    rss_url: Optional[str] = None
    rss_download_delay: int = -1
    rss_last_date: Optional[str] = None


@dataclass
class Timeouts:
    await_seconds_when_connecting_via_rcon: float = -1.0
    await_seconds_in_check_ups: int = -1
    await_seconds_when_opped: int = -1
    await_seconds_before_message_deletion: int = -1


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
                return int(self.size_limit_for_server[:-2]) * 1024 * 1024
            elif self.size_limit_for_server[-2:].upper() == "GB":
                return int(self.size_limit_for_server[:-2]) * 1024 * 1024 * 1024
            elif self.size_limit_for_server[-2:].upper() == "TB":
                return int(self.size_limit_for_server[:-2]) * 1024 * 1024 * 1024 * 1024

    @property
    def supported_compression_methods(self):
        return ["STORED", "DEFLATED", "BZIP2", "LZMA"]


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

    prefix: str = ""
    help_arguments: List[str] = field(default_factory=list)
    gaming_status: str = ""
    idle_status: str = ""
    specific_command_role_id: Optional[int] = None
    admin_role_id: Optional[int] = None
    ip_address: str = ""
    local_address: str = ""
    log_bot_messages: bool = None
    deletion_messages_limit_without_poll: int = -1
    menu_id: Optional[int] = None
    commands_channel_id: Optional[int] = None
    forceload: bool = False
    default_number_of_times_to_op: int = -1
    server_watcher: Server_watcher = Server_watcher()
    rss_feed: Rss_feed = Rss_feed()
    backups: Backups = Backups()
    timeouts: Timeouts = Timeouts()

    def __post_init__(self):
        if self.token_encrypted:
            self._token = decrypt_string(self.token_encrypted)


@dataclass
class Server_settings:
    server_name: str = ""
    working_directory: str = ""
    start_file_name: str = ""
    server_loading_time: Optional[int] = None


@dataclass
class User:
    user_minecraft_nick: str = ""
    user_discord_id: int = -1


@dataclass
class Settings:
    bot_settings: Bot_settings = Bot_settings()
    ask_to_change_servers_list: bool = True
    selected_server_number: int = 1
    servers_list: List[Server_settings] = field(default_factory=list)
    known_users: List[User] = field(default_factory=list)


@dataclass
class State_info:
    user: Optional[str] = None
    date_stamp: Optional[int] = None

    def set_state_info(self, user: str, date: datetime):
        self.user, self.date_stamp = user, int(date.timestamp())

    @property
    def date(self):
        if self.date_stamp is not None:
            return datetime.fromtimestamp(self.date_stamp)
        else:
            return None


@dataclass
class States:
    started_info: State_info = State_info()
    stopped_info: State_info = State_info()


@dataclass
class Player:
    player_minecraft_nick: str = ""
    number_of_times_to_op: int = -1


@dataclass
class Backup_info:
    file_name: str = ""
    reason: Optional[str] = None
    restored_from: bool = False
    initiator: Optional[str] = None

    @property
    def file_creation_date(self):
        return datetime.strptime(self.file_name, "%d-%m-%Y-%H-%M-%S")


@dataclass
class Server_config:
    states: States = States()
    backups: List[Backup_info] = field(default_factory=list)
    seen_players: List[Player] = field(default_factory=list)


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

    @classmethod
    def read_config(cls):
        file_exists = False
        if isfile(cls._config_name):
            cls._settings_instance = cls._load_from_yaml(Path(cls._current_bot_path, cls._config_name), Settings)
            file_exists = True
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
        if getattr(sys, 'frozen', False):
            return sys._MEIPASS
        elif __file__:
            return cls._current_bot_path

    @classmethod
    def init_with_system_language(cls):
        lang = getdefaultlocale()[0].split('_')[0].lower()
        cls._system_lang = set_locale(lang, set_eng_if_error=True)

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
    def remove_ip_address(cls, ip_address: str, user_nicks: Optional[List[str]] = None):
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
    def set_user_logged(cls, nick: str, logged: bool):
        for i in range(len(cls.get_auth_users())):
            if cls.get_auth_users()[i].nick == nick:
                cls.get_auth_users()[i].logged = logged

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
    def get_cross_platform_chat_settings(cls) -> Cross_platform_chat:
        return cls._settings_instance.bot_settings.server_watcher.cross_platform_chat

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
            Player(player_minecraft_nick, cls._settings_instance.bot_settings.default_number_of_times_to_op))

    @classmethod
    def decrease_number_to_op_for_player(cls, player_minecraft_nick: str):
        for p in range(len(cls._server_config_instance.seen_players)):
            if cls._server_config_instance.seen_players[p].player_minecraft_nick == player_minecraft_nick:
                cls._server_config_instance.seen_players[p].number_of_times_to_op -= 1

    @classmethod
    def add_backup_info(cls, file_name: str, reason: str = None, initiator: str = None):
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
        cls.read_server_config()
        # Ensure we have backups folder
        with suppress(FileExistsError):
            mkdir(Path(cls.get_selected_server_from_list().working_directory,
                       cls.get_backups_settings().name_of_the_backups_folder))
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
        # Remove nonexistent backups from server's backups folder
        print(get_translation("Starting checking backups folder '{0}' for nonexistent files and folder by using '{1}'")
              .format(Path(cls.get_selected_server_from_list().working_directory,
                           cls.get_backups_settings().name_of_the_backups_folder).as_posix(), cls._server_config_name))
        list_of_backups_names = [b.file_name for b in cls.get_server_config().backups]
        for backup in listdir(Path(cls.get_selected_server_from_list().working_directory,
                                   cls.get_backups_settings().name_of_the_backups_folder)):
            file_path = Path(cls.get_selected_server_from_list().working_directory,
                             cls.get_backups_settings().name_of_the_backups_folder, backup)
            if file_path.is_file():
                if backup.rsplit(".", 1)[0] not in list_of_backups_names:
                    remove(Path(cls.get_selected_server_from_list().working_directory,
                                cls.get_backups_settings().name_of_the_backups_folder, backup))
                    print(get_translation("Deleted file in path '{0}'").format(file_path.as_posix()))
            else:
                rmtree(file_path, ignore_errors=True)
                print(get_translation("Deleted folder in path '{0}'").format(file_path.as_posix()))
        print(get_translation("Done!"))

        filepath = Path(cls.get_selected_server_from_list().working_directory, "server.properties")
        if not filepath.exists():
            raise RuntimeError(get_translation("File '{0}' doesn't exist! "
                                               "Run Minecraft server manually to create one and accept eula!")
                               .format(filepath.as_posix()))
        BotVars.port_query = None
        BotVars.port_rcon = None
        BotVars.rcon_pass = None
        with open(filepath, "r", encoding="utf8") as f:
            lines = f.readlines()
            if len(lines) < 3:
                raise RuntimeError(get_translation("File '{0}' doesn't have any parameters! Accept eula and "
                                                   "run Minecraft server manually to fill it with parameters!")
                                   .format(filepath.as_posix()))
            for i in lines:
                if i.find("enable-query") >= 0:
                    enable_query = literal_eval(i.split("=")[1].capitalize())
                if i.find("enable-rcon") >= 0:
                    enable_rcon = literal_eval(i.split("=")[1].capitalize())
                if i.find("query.port") >= 0:
                    BotVars.port_query = int(i.split("=")[1])
                if i.find("rcon.port") >= 0:
                    BotVars.port_rcon = int(i.split("=")[1])
                if i.find("rcon.password") >= 0:
                    BotVars.rcon_pass = i.split("=")[1].strip()
        if not enable_query or not enable_rcon or not BotVars.rcon_pass:
            changed_parameters = []
            rewritten_rcon_pass = False
            if not enable_query:
                changed_parameters.append("enable-query=true")
            if not enable_rcon:
                changed_parameters.append("enable-rcon=true")
            if not BotVars.rcon_pass:
                BotVars.rcon_pass = "".join(sec_choice(ascii_letters + digits) for _ in range(20))
                changed_parameters.append(f"rcon.password={BotVars.rcon_pass}")
                changed_parameters.append(get_translation("Reminder: For better security "
                                                          "you have to change this password for a more secure one."))
            with open(filepath, "r", encoding="utf8") as f:
                properties_file = f.readlines()
            for i in range(len(properties_file)):
                if "enable-query" in properties_file[i] or "enable-rcon" in properties_file[i]:
                    properties_file[i] = f"{properties_file[i].split('=')[0]}=true\n"
                if "rcon.password" in properties_file[i]:
                    rewritten_rcon_pass = True
                    properties_file[i] = f"rcon.password={BotVars.rcon_pass}\n"
            if BotVars.port_query is None:
                BotVars.port_query = 25565
                properties_file.append(f"query.port={BotVars.port_query}\n")
                changed_parameters.append(f"query.port={BotVars.port_query}")
            if BotVars.port_rcon is None:
                BotVars.port_rcon = 25575
                properties_file.append(f"rcon.port={BotVars.port_rcon}\n")
                changed_parameters.append(f"rcon.port={BotVars.port_rcon}")
            if not rewritten_rcon_pass:
                properties_file.append(f"rcon.password={BotVars.rcon_pass}\n")
            with open(filepath, "w", encoding="utf8") as f:
                f.writelines(properties_file)
            print("------")
            print(get_translation("Note: In '{0}' bot set these parameters:").format(filepath.as_posix()))
            for line in changed_parameters:
                print(line)
            print("------")

    @classmethod
    def get_ops_json(cls):
        return load(open(Path(cls.get_selected_server_from_list().working_directory + '/ops.json'), 'r'))

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
    def _load_from_yaml(cls, filepath: Path, baseclass):
        try:
            return sload(json_obj=Conf.to_object(Conf.load(filepath)), cls=baseclass)
        except DeserializationError:
            return baseclass()

    @classmethod
    def _save_to_yaml(cls, class_instance, filepath: Path):
        Conf.save(config=Conf.structured(class_instance), f=filepath)

    @staticmethod
    def _ask_for_data(message: str, match_str: Optional[str] = None, try_int=False, int_high_than: Optional[int] = None,
                      int_low_than: Optional[int] = None, try_float=False,
                      float_high_than: Optional[float] = None, float_low_than: Optional[float] = None):
        while True:
            answer = str(input(message))
            if answer != "":
                if match_str is not None and answer.lower() != match_str:
                    return False
                if try_int or int_high_than is not None or int_low_than is not None:
                    try:
                        if int_high_than is not None and int(answer) < int_high_than:
                            print(get_translation("Your number lower than {0}!").format(int_high_than))
                            continue
                        if int_low_than is not None and int(answer) > int_low_than:
                            print(get_translation("Your number higher than {0}!").format(int_low_than))
                            continue
                        return int(answer)
                    except ValueError:
                        print(get_translation("Your string doesn't contain an integer!"))
                        continue
                if try_float or float_high_than is not None or float_low_than is not None:
                    try:
                        if float_high_than is not None and float(answer) < float_high_than:
                            print(get_translation("Your number lower than {0}!").format(float_high_than))
                            continue
                        if float_low_than is not None and float(answer) > float_low_than:
                            print(get_translation("Your number higher than {0}!").format(float_low_than))
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
        cls._setup_prefix()
        cls._setup_help_arguments()
        cls._setup_roles()
        cls._setup_bot_statuses()
        cls._setup_ip_address()
        cls._setup_local_address()
        cls._setup_log_bot_messages()
        cls._setup_clear_delete_limit_without_poll()
        cls._setup_menu_id()
        cls._setup_commands_channel_id()
        cls._setup_default_number_of_times_to_op()
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
                                                                   for ln in get_locales()]) + "\n> ")
                    output = set_locale(lang)
                    if not output:
                        cls._settings_instance.bot_settings.language = lang.lower()
                        print(get_translation("This language selected!"))
                        break
                    else:
                        print(get_translation("Bot doesn't have such language. Try again."))

    @classmethod
    def _setup_token(cls):
        if cls._settings_instance.bot_settings.token is None:
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.token = \
                cls._ask_for_data(get_translation("Token not founded. Enter token") + "\n> ")

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
        if cls._settings_instance.bot_settings.specific_command_role_id is not None:
            print(get_translation("Role for specific commands is set."))
        else:
            print(get_translation("Role for specific commands doesn't stated. "
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
        if cls._settings_instance.bot_settings.deletion_messages_limit_without_poll < 0:
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.deletion_messages_limit_without_poll = \
                cls._ask_for_data(get_translation("Set limit for deletion messages "
                                                  "without poll (0 - for disable poll) (int)") + "\n> ",
                                  try_int=True, int_high_than=0)

    @classmethod
    def _setup_menu_id(cls):
        if cls._settings_instance.bot_settings.menu_id is None:
            if cls._ask_for_data(
                    get_translation("Menu message id not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                cls._need_to_rewrite = True
                cls._settings_instance.bot_settings.menu_id = \
                    cls._ask_for_data(get_translation("Enter menu message id") + "\n> ",
                                      try_int=True, int_high_than=0)
            else:
                print(get_translation("Menu via reactions wouldn't work. To make it work type "
                                      "'{0}menu' to create new menu and its id.").format(
                    cls._settings_instance.bot_settings.prefix))

    @classmethod
    def _setup_commands_channel_id(cls):
        if cls._settings_instance.bot_settings.commands_channel_id is None:
            if cls._ask_for_data(
                    get_translation("Commands' channel id not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                cls._need_to_rewrite = True
                cls._settings_instance.bot_settings.commands_channel_id = \
                    cls._ask_for_data(get_translation("Enter commands' channel id") + "\n> ",
                                      try_int=True, int_high_than=0)
            else:
                print(get_translation("Bot send some push events to the channel it can post. To make it work rigth type"
                                      " '{0}channel commands' to create a link.")
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
    def _setup_default_number_of_times_to_op(cls):
        if cls._settings_instance.bot_settings.default_number_of_times_to_op < 1:
            cls._settings_instance.bot_settings.default_number_of_times_to_op = \
                cls._ask_for_data(
                    get_translation("Set default number of times to op for every player (int):") + "\n> ")

    @classmethod
    def _setup_timeouts(cls):
        # Timeout between check-ups func
        if cls.get_timeouts_settings().await_seconds_in_check_ups < 1:
            cls._need_to_rewrite = True
            print(get_translation("Timeout between check-ups 'Server on/off' set below 1. Change this option."))
            print(get_translation("Note: If your machine has processor with frequency 2-2.5 GHz, "
                                  "you have to set this option at least to '2' seconds "
                                  "or higher for the bot to work properly."))
            cls.get_timeouts_settings().await_seconds_in_check_ups = \
                cls._ask_for_data(
                    get_translation("Set timeout between check-ups 'Server on/off' (in seconds, int)") + "\n> ",
                    try_int=True, int_high_than=1)
        print(get_translation("Timeout between check-ups 'Server on/off' set to {0} sec.")
              .format(str(cls.get_timeouts_settings().await_seconds_in_check_ups)))

        # Timeout for op
        if cls.get_timeouts_settings().await_seconds_when_opped < 0:
            cls._need_to_rewrite = True
            print(get_translation("Timeout for op set below 0. Change this option."))
            cls.get_timeouts_settings().await_seconds_when_opped = \
                cls._ask_for_data(get_translation("Set timeout for op (0 - for unlimited timeout) (in seconds, int)") +
                                  "\n> ",
                                  try_int=True, int_high_than=0)
        print(get_translation("Timeout for op set to {0} sec.")
              .format(str(cls.get_timeouts_settings().await_seconds_when_opped)))
        if cls.get_timeouts_settings().await_seconds_when_opped == 0:
            print(get_translation("Limitation doesn't exist, padawan."))

        # Timeout to sleep while bot pinging server for info
        if cls.get_timeouts_settings().await_seconds_when_connecting_via_rcon < 0.1:
            cls._need_to_rewrite = True
            print(get_translation("Timeout while bot pinging server for info set below 0. Change this option."))
            cls.get_timeouts_settings().await_seconds_when_connecting_via_rcon = \
                cls._ask_for_data(get_translation(
                    "Set timeout while bot pinging server for info (in seconds, float)") + "\n> ",
                                  try_float=True, float_high_than=0.1)
        print(get_translation("Timeout while bot pinging server for info set to {0} sec.")
              .format(str(cls.get_timeouts_settings().await_seconds_when_connecting_via_rcon)))
        if cls.get_timeouts_settings().await_seconds_when_connecting_via_rcon == 0:
            print(get_translation("I'm fast as f*ck, boi!"))

        # Timeout before message deletion
        if cls.get_timeouts_settings().await_seconds_before_message_deletion < 1:
            cls._need_to_rewrite = True
            print(get_translation(
                "Timeout before message deletion is set below 1. Change this option."))
            cls.get_timeouts_settings().await_seconds_before_message_deletion = \
                cls._ask_for_data(get_translation("Set timeout before message deletion (in seconds, int)") + "\n> ",
                                  try_int=True, int_high_than=1)
        print(get_translation("Timeout before message deletion is set to {0} sec.")
              .format(str(cls.get_timeouts_settings().await_seconds_before_message_deletion)))

    @classmethod
    def _setup_servers(cls):
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
        new_servers_number = cls._ask_for_data(get_translation("How much servers you intend to keep?") + "\n> ",
                                               try_int=True, int_high_than=1)
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
                        server.server_name) +
                                       " Y/n\n> ", "y"):
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
        file_extension = None
        BOLD = '\033[1m'
        END = '\033[0m'
        if sys.platform == "linux" or sys.platform == "linux2":
            file_extension = ".sh"
            print(get_translation("Bot detected your operating system is Linux.\n"
                                  "Bot will search for '*.sh' file.\n"
                                  "You need to enter file name {0}without{1} file extension!").format(BOLD, END))
        elif sys.platform == "win32":
            file_extension = ".bat"
            print(get_translation("Bot detected your operating system is Windows.\n"
                                  "Bot will search for '*.bat' file.\n"
                                  "You need to enter file name {0}without{1} file extension!").format(BOLD, END))
        else:
            print(get_translation("Bot couldn't detect your operating system.\n"
                                  "You need to enter file name {0}with{1} file extension!").format(BOLD, END))
        while True:
            start_file_name = cls._ask_for_data(get_translation("Enter server start file name") + "\n> ") + \
                              (file_extension if file_extension is not None else '')
            if Path(working_directory, start_file_name).is_file():
                return start_file_name
            else:
                print(get_translation("This start file doesn't exist."))

    @classmethod
    def _setup_server_watcher(cls):
        if cls.get_server_watcher().refresh_delay_of_console_log <= 0.05:
            print(get_translation("Watcher's delay to refresh doesn't set."))
            print(get_translation("Note: If your machine has processor with frequency 2-2.5 GHz, "
                                  "you have to set this option from '0.5' to '0.9' second "
                                  "for the bot to work properly."))
            cls.get_server_watcher().refresh_delay_of_console_log = \
                cls._ask_for_data(get_translation("Set delay to refresh (in seconds, float)") + "\n> ",
                                  try_float=True, float_high_than=0.1)

        if cls.get_server_watcher().number_of_lines_to_check_in_console_log < 1:
            print(get_translation("Watcher's number of lines to check in server log doesn't set."))
            cls.get_server_watcher().number_of_lines_to_check_in_console_log = \
                cls._ask_for_data(get_translation("Set number of lines to check") + "\n> ", try_int=True,
                                  int_high_than=1)

        if cls.get_cross_platform_chat_settings().enable_cross_platform_chat is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Would you like to enable cross-platform chat?") + " Y/n\n> ",
                                 "y"):
                cls.get_cross_platform_chat_settings().enable_cross_platform_chat = True

                if cls.get_cross_platform_chat_settings().channel_id is None:
                    if cls._ask_for_data(
                            get_translation("Channel id not found. Would you like to enter it?") + " Y/n\n> ",
                            "y"):
                        cls.get_cross_platform_chat_settings().channel_id = \
                            cls._ask_for_data(get_translation("Enter channel id") + "\n> ")
                    else:
                        print(get_translation("Cross-platform chat wouldn't work. "
                                              "To make it work type '{0}chat <id>' to create link.")
                              .format(cls._settings_instance.bot_settings.prefix))

                if cls.get_cross_platform_chat_settings().webhook_url is None:
                    if cls._ask_for_data(get_translation("Webhook url for cross-platform chat not found. "
                                                         "Would you like to enter it?") + " Y/n\n> ", "y"):
                        cls.get_cross_platform_chat_settings().webhook_url = \
                            cls._ask_for_data(get_translation("Enter webhook url") + "\n> ")
                    else:
                        print(get_translation(
                            "Cross-platform chat wouldn't work. Create webhook and enter it to bot config!"))
            else:
                cls.get_cross_platform_chat_settings().enable_cross_platform_chat = False
                print(get_translation("Cross-platform chat wouldn't work."))
        if cls.get_cross_platform_chat_settings().max_words_in_mention is None or \
                cls.get_cross_platform_chat_settings().max_words_in_mention < 1 or \
                cls.get_cross_platform_chat_settings().max_words_in_mention > 20:
            cls._need_to_rewrite = True
            cls.get_cross_platform_chat_settings().max_words_in_mention = \
                cls._ask_for_data(
                    get_translation("Enter how many words in mention from Minecraft chat bot can parse "
                                    "(0 - handle only mentions with one word) (default - 5, int)") + "\n> ",
                    try_int=True, int_high_than=0, int_low_than=20)
        if cls.get_cross_platform_chat_settings().max_wrong_symbols_in_mention_from_right is None or \
                cls.get_cross_platform_chat_settings().max_wrong_symbols_in_mention_from_right < 1 or \
                cls.get_cross_platform_chat_settings().max_wrong_symbols_in_mention_from_right > 20:
            cls._need_to_rewrite = True
            cls.get_cross_platform_chat_settings().max_wrong_symbols_in_mention_from_right = \
                cls._ask_for_data(
                    get_translation("Enter how many characters from right side of mention "
                                    "bot can remove to find similar mention in discord"
                                    " (0 - don't try to find similar ones) (default - 5, int)") + "\n> ",
                    try_int=True, int_high_than=0, int_low_than=20)

        if cls.get_cross_platform_chat_settings().enable_cross_platform_chat:
            print(get_translation("Cross-platform chat enabled."))
        else:
            print(get_translation("Cross-platform chat disabled."))

        if cls.get_secure_auth().enable_secure_auth is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Would you like to enable authorization security?") + " Y/n\n> ",
                                 "y"):
                cls.get_secure_auth().enable_secure_auth = True
            else:
                cls.get_secure_auth().enable_secure_auth = False
        if cls.get_secure_auth().max_login_attempts < 1:
            cls._need_to_rewrite = True
            cls.get_secure_auth().max_login_attempts = \
                cls._ask_for_data(get_translation("Enter how many attempts bot will accept connection from "
                                                  "a certain IP-address before it bans this IP") + "\n> ",
                                  try_int=True, int_high_than=1)
        if cls.get_secure_auth().days_before_ip_expires < 1:
            cls._need_to_rewrite = True
            cls.get_secure_auth().days_before_ip_expires = \
                cls._ask_for_data(
                    get_translation("Enter how many days IP-address will be valid before it expires (int)") +
                    "\n> ", try_int=True, int_high_than=1)
        if cls.get_secure_auth().days_before_ip_will_be_deleted < cls.get_secure_auth().days_before_ip_expires:
            cls._need_to_rewrite = True
            cls.get_secure_auth().days_before_ip_will_be_deleted = \
                cls._ask_for_data(
                    get_translation("Enter in how many days expired IP-address will be deleted (int)") +
                    "\n> ", try_int=True, int_high_than=cls.get_secure_auth().days_before_ip_expires)
        if cls.get_secure_auth().code_length < 1 or \
                cls.get_secure_auth().code_length > 60:
            cls._need_to_rewrite = True
            cls.get_secure_auth().code_length = \
                cls._ask_for_data(
                    get_translation("Enter how many characters the code should consist of (default - 6, int)") + "\n> ",
                    try_int=True, int_high_than=1, int_low_than=60)
        if cls.get_secure_auth().mins_before_code_expires < 1:
            cls._need_to_rewrite = True
            cls.get_secure_auth().mins_before_code_expires = \
                cls._ask_for_data(get_translation("Enter how many minutes code will be valid before it expires (int)") +
                                  "\n> ", try_int=True, int_high_than=1)

        if cls.get_secure_auth().enable_secure_auth:
            print(get_translation("Secure authorization enabled."))
        else:
            print(get_translation("Secure authorization disabled."))

    @classmethod
    def _setup_rss_feed(cls):
        if cls.get_rss_feed_settings().enable_rss_feed is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Would you like to enable RSS feed?") + " Y/n\n> ", "y"):
                cls.get_rss_feed_settings().enable_rss_feed = True

                if cls.get_rss_feed_settings().webhook_url is None:
                    if cls._ask_for_data(get_translation("Webhook RSS url not found. Would you like to enter it?") +
                                         " Y/n\n> ", "y"):
                        cls.get_rss_feed_settings().webhook_url = \
                            cls._ask_for_data(get_translation("Enter webhook RSS url") + "\n> ")
                    else:
                        print(get_translation("RSS wouldn't work. Create webhook and enter it to bot config!"))

                if cls.get_rss_feed_settings().rss_url is None:
                    if cls._ask_for_data(
                            get_translation("RSS url not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                        cls.get_rss_feed_settings().rss_url = cls._ask_for_data(
                            get_translation("Enter RSS url") + "\n> ")
                    else:
                        print(get_translation("RSS wouldn't work. Enter url of RSS feed to bot config!"))

                if cls.get_rss_feed_settings().rss_download_delay < 1:
                    print(get_translation("RSS download delay doesn't set."))
                    cls.get_rss_feed_settings().rss_download_delay = \
                        cls._ask_for_data(get_translation("Enter RSS download delay (in seconds, int)") + "\n> ",
                                          try_int=True, int_high_than=1)

                cls.get_rss_feed_settings().rss_last_date = \
                    datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
            else:
                cls.get_rss_feed_settings().enable_rss_feed = False
                print(get_translation("RSS feed wouldn't work."))
        else:
            if cls.get_rss_feed_settings().enable_rss_feed:
                print(get_translation("RSS feed enabled."))
            else:
                print(get_translation("RSS feed disabled."))

    @classmethod
    def _setup_backups(cls):
        if cls.get_backups_settings().automatic_backup is None:
            cls._need_to_rewrite = True
            cls.get_backups_settings().automatic_backup = \
                cls._ask_for_data(get_translation("Automatic backup isn't set. Would you like to enable them?") +
                                  " Y/n\n> ", "y")
        if cls.get_backups_settings().period_of_automatic_backups is None:
            cls._need_to_rewrite = True
            cls.get_backups_settings().period_of_automatic_backups = \
                cls._ask_for_data(get_translation("Set period of automatic backups (in minutes, int)") + "\n> ",
                                  try_int=True, int_high_than=1)
        if not cls.get_backups_settings().name_of_the_backups_folder:
            cls._need_to_rewrite = True
            cls.get_backups_settings().name_of_the_backups_folder = \
                cls._ask_for_data(get_translation("Enter name of the backups folder for each Minecraft server") +
                                  "\n> ")
        if cls.get_backups_settings().max_backups_limit_for_server is not None and \
                cls.get_backups_settings().max_backups_limit_for_server < 1:
            cls._need_to_rewrite = True
            if cls._ask_for_data(
                    get_translation("Max backups' count limit for server not found. Would you like to set it?") +
                    " Y/n\n> ", "y"):
                cls.get_backups_settings().max_backups_limit_for_server = \
                    cls._ask_for_data(get_translation("Set max backups' count limit for server (int)") + "\n> ",
                                      try_int=True, int_high_than=1)
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
                size = cls._ask_for_data(get_translation("Backups' size limit for server in {0} (int)")
                                         .format(unit_of_bytes) + "\n> ", try_int=True, int_high_than=1)
                cls.get_backups_settings().size_limit_for_server = f"{size}{unit_of_bytes}"
            else:
                cls.get_backups_settings().size_limit_for_server = None
        if cls.get_backups_settings().compression_method is None:
            cls._need_to_rewrite = True
            cls.get_backups_settings().compression_method = \
                cls.get_backups_settings().supported_compression_methods[1]

        print(get_translation("Name of the backups folder in which bot will store them - '{0}'.")
              .format(cls.get_backups_settings().name_of_the_backups_folder))
