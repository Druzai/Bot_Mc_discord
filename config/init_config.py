import datetime as dt
import sys
from ast import literal_eval
from dataclasses import dataclass, field
from datetime import datetime
from glob import glob
from json import load
from locale import getdefaultlocale
from os.path import isfile, isdir
from pathlib import Path
from secrets import choice as sec_choice
from string import ascii_letters, digits
from typing import List, Optional, TYPE_CHECKING

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
    server_start_time: int = None
    is_server_on: bool = False
    is_loading: bool = False
    is_stopping: bool = False
    is_restarting: bool = False
    is_doing_op: bool = False
    is_voting: bool = False
    op_deop_list: List = []  # List of nicks of players to op and then to deop
    port_query: int = None
    port_rcon: int = None
    rcon_pass: str = None
    watcher_of_log_file: 'Watcher' = None
    watcher_last_line: str = None
    webhook_chat: Webhook = None
    webhook_rss: Webhook = None
    bot_for_webhooks: Bot = None


@dataclass
class Cross_platform_chat:
    enable_cross_platform_chat: Optional[bool] = None
    channel_id: Optional[int] = None
    webhook_url: Optional[str] = None
    refresh_delay_of_console_log: float = -1.0
    number_of_lines_to_check_in_console_log: int = 0


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
    role: Optional[str] = None
    ip_address: str = ""
    local_address: str = ""
    deletion_messages_limit_without_poll: int = -1
    menu_id: Optional[int] = None
    forceload: bool = False
    default_number_of_times_to_op: int = -1
    vk_ask_credentials: bool = True
    vk_login: Optional[str] = None
    _vk_password = None
    vk_password_encrypted: Optional[str] = None

    @property
    def vk_password(self):
        return self._vk_password

    @vk_password.setter
    def vk_password(self, vk_password_decrypted):
        self._vk_password = vk_password_decrypted
        self.vk_password_encrypted = None if vk_password_decrypted is None else encrypt_string(vk_password_decrypted)

    cross_platform_chat: Cross_platform_chat = Cross_platform_chat()
    rss_feed: Rss_feed = Rss_feed()
    timeouts: Timeouts = Timeouts()

    def __post_init__(self):
        if self.token_encrypted:
            self._token = decrypt_string(self.token_encrypted)
        if self.vk_password_encrypted:
            self._vk_password = decrypt_string(self.vk_password_encrypted)


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
    date: Optional[str] = None

    def set_state_info(self, user: str, date: str):
        self.user, self.date = user, date


@dataclass
class States:
    started_info: State_info = State_info()
    stopped_info: State_info = State_info()


@dataclass
class Player:
    player_minecraft_nick: str = ""
    number_of_times_to_op: int = -1


@dataclass
class Server_config:
    states: States = States()
    seen_players: List[Player] = field(default_factory=list)


class Config:
    _current_bot_path: str = path.dirname(sys.argv[0])
    _config_name = "bot_config.yml"
    _settings_instance: Settings = Settings()
    _server_config_name = "server_config.yml"
    _server_config_instance: Server_config = Server_config()
    _op_log_name = "op.log"
    _need_to_rewrite = False

    @classmethod
    def read_config(cls):
        file_exists = False
        if isfile(cls._config_name):
            cls._settings_instance = cls._load_from_yaml(Path(cls._current_bot_path + "/" + cls._config_name), Settings)
            file_exists = True
        cls._setup_config(file_exists)

    @classmethod
    def save_config(cls):
        cls._save_to_yaml(cls._settings_instance, Path(cls._current_bot_path + "/" + cls._config_name))

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
    def get_bot_config_path(cls) -> str:
        return cls._current_bot_path

    @classmethod
    def get_settings(cls) -> Settings:
        return cls._settings_instance

    @classmethod
    def get_cross_platform_chat_settings(cls) -> Cross_platform_chat:
        return cls._settings_instance.bot_settings.cross_platform_chat

    @classmethod
    def get_rss_feed_settings(cls) -> Rss_feed:
        return cls._settings_instance.bot_settings.rss_feed

    @classmethod
    def get_awaiting_times_settings(cls) -> Timeouts:
        return cls._settings_instance.bot_settings.timeouts

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
            Player(player_minecraft_nick, Config._settings_instance.bot_settings.default_number_of_times_to_op))

    @classmethod
    def decrease_number_to_op_for_player(cls, player_minecraft_nick: str):
        for p in range(len(Config._server_config_instance.seen_players)):
            if Config._server_config_instance.seen_players[p].player_minecraft_nick == player_minecraft_nick:
                Config._server_config_instance.seen_players[p].number_of_times_to_op -= 1

    @classmethod
    def read_server_config(cls):
        if path.isfile(Path(cls.get_selected_server_from_list().working_directory + '/' + cls._server_config_name)):
            cls._server_config_instance = cls._load_from_yaml(Path(cls.get_selected_server_from_list().working_directory
                                                                   + '/' + cls._server_config_name), Server_config)
        else:
            cls._server_config_instance = Server_config()

    @classmethod
    def save_server_config(cls):
        cls._save_to_yaml(cls._server_config_instance,
                          Path(cls.get_selected_server_from_list().working_directory + '/' + cls._server_config_name))

    @classmethod
    def get_server_config(cls):
        return cls._server_config_instance

    @classmethod
    def read_server_info(cls):
        cls.read_server_config()
        filepath = Path(cls.get_selected_server_from_list().working_directory + "/server.properties")
        if not filepath.exists():
            raise RuntimeError(get_translation("File '{0}' doesn't exist! "
                                               "Run minecraft server manually to create one and accept eula!")
                               .format(filepath.as_posix()))
        with open(filepath, "r", encoding="utf8") as f:
            lines = f.readlines()
            if len(lines) < 3:
                raise RuntimeError(get_translation("File '{0}' doesn't have any parameters! "
                                                   "Accept eula and run minecraft server manually to fill it with parameters!")
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
                changed_parameters.append(f"rcon.password={BotVars.rcon_pass}\n" +
                                          get_translation("Reminder: For better security "
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
                properties_file.append(f"query.port={str(BotVars.port_query)}\n")
                changed_parameters.append(f"query.port={str(BotVars.port_query)}")
            if BotVars.port_rcon is None:
                BotVars.port_rcon = 25575
                properties_file.append(f"rcon.port={str(BotVars.port_rcon)}\n")
                changed_parameters.append(f"rcon.port={str(BotVars.port_rcon)}")
            if not rewritten_rcon_pass:
                properties_file.append(f"rcon.password={BotVars.rcon_pass}\n")
            with open(filepath, "w", encoding="utf8") as f:
                f.writelines(properties_file)
            print("\n" + get_translation("Note: In '{0}' bot set these parameters:").format(
                filepath.as_posix()) + "\n" +
                  "\n".join(changed_parameters) + "\n")

    @classmethod
    def get_ops_json(cls):
        return load(open(Path(cls.get_selected_server_from_list().working_directory + '/ops.json'), 'r'))

    @classmethod
    def append_to_op_log(cls, message_line: str):
        with open(Path(cls.get_bot_config_path() + f'/{cls._op_log_name}'), 'a', encoding='utf8') as f:
            f.write(f"{message_line}\n")

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
    def _ask_for_data(message: str, match_str=None,
                      try_int=False, int_high_than=None, try_float=False, float_hight_than=None):
        while True:
            answer = str(input(message))
            if answer != "":
                if match_str is not None and answer.lower() != match_str:
                    return False
                if try_int or int_high_than is not None:
                    try:
                        if int_high_than is not None and int(answer) < int_high_than:
                            print(get_translation("Your number lower than {0}!").format(int_high_than))
                            continue
                        return int(answer)
                    except ValueError:
                        print(get_translation("Your string doesn't contain an integer!"))
                        continue
                if try_float or float_hight_than is not None:
                    try:
                        if float_hight_than is not None and float(answer) < float_hight_than:
                            print(get_translation("Your number lower than {0}!").format(float_hight_than))
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
        cls._setup_role()
        cls._setup_bot_statuses()
        cls._setup_ip_address()
        cls._setup_local_address()
        cls._setup_clear_delete_limit_without_poll()
        cls._setup_menu_id()
        cls._setup_default_number_of_times_to_op()
        cls._setup_vk_credentials()
        cls._setup_cross_platform_chat()
        cls._setup_rss_feed()
        cls._setup_timeouts()
        cls._setup_servers()

        if cls._need_to_rewrite:
            cls._need_to_rewrite = False
            cls.save_config()
            print(get_translation("Config saved!"))
        print(get_translation("Config read!"))

    @classmethod
    def _setup_language(cls):
        if cls._settings_instance.bot_settings.language is None or \
                set_locale(cls._settings_instance.bot_settings.language):
            if cls._settings_instance.bot_settings.language is not None and \
                    set_locale(cls._settings_instance.bot_settings.language):
                print("Language setting in bot config is wrong! Setting up language again...")

            cls._need_to_rewrite = True
            lang = getdefaultlocale()[0].split('_')[0].lower()
            output = set_locale(lang, set_eng_if_error=True)
            if output:
                print("Bot doesn't have your system language. So bot selected English.")
            else:
                print(get_translation("Bot selected language based on your system language."))
            cls._settings_instance.bot_settings.language = "en" if output else lang.lower()

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
    def _setup_role(cls):
        if cls._settings_instance.bot_settings.role is not None:
            command_role = cls._settings_instance.bot_settings.role
            if command_role:
                print(get_translation("Role for specific commands is '{0}'.").format(command_role))
            else:
                print(get_translation("Role for specific commands doesn't stated."))
        else:
            cls._need_to_rewrite = True
            if cls._ask_for_data(
                    get_translation("Do you want to set role for some specific commands?") + " Y/n\n> ", "y"):
                cls._settings_instance.bot_settings.role = \
                    cls._ask_for_data(get_translation(
                        "Set discord role for some specific commands such as start, stop, etc.") + "\n> ")
            else:
                cls._settings_instance.bot_settings.role = ""

    @classmethod
    def _setup_vk_credentials(cls):
        if not cls._settings_instance.bot_settings.vk_login or not cls._settings_instance.bot_settings.vk_password:
            cls._settings_instance.bot_settings.vk_login = None
            cls._settings_instance.bot_settings.vk_password = None
        if cls._settings_instance.bot_settings.vk_ask_credentials:
            if cls._settings_instance.bot_settings.vk_login is not None:
                word = get_translation('change')
            else:
                word = get_translation('enter')
            if cls._ask_for_data(get_translation("Would you like to ") + word +
                                 get_translation(" vk account data?") + " Y/n\n> ", "y"):
                cls._settings_instance.bot_settings.vk_login = cls._ask_for_data(
                    get_translation("Enter vk login") + "\n> ")
                cls._settings_instance.bot_settings.vk_password = cls._ask_for_data(
                    get_translation("Enter vk password") + "\n> ")
                cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Never ask about it again?") + " Y/n\n> ", "y"):
                cls._settings_instance.bot_settings.vk_ask_credentials = False
                cls._need_to_rewrite = True
                if cls._settings_instance.bot_settings.vk_login is not None and \
                        cls._settings_instance.bot_settings.vk_password is not None:
                    print(get_translation("I'll never ask you about it again."))
                else:
                    print(get_translation("Vk account data not received.\n"
                                          "I'll never ask you about it again.\n"
                                          "Note: Command {0}say won't work.").format(
                        cls._settings_instance.bot_settings.prefix))
            else:
                if cls._settings_instance.bot_settings.vk_login is not None and \
                        cls._settings_instance.bot_settings.vk_password is not None:
                    print(get_translation("Vk account data not received. Why man?"))
                else:
                    print(get_translation("Vk account data not received."))
        else:
            if cls._settings_instance.bot_settings.vk_login is not None and \
                    cls._settings_instance.bot_settings.vk_password is not None:
                print(get_translation("Vk account data received."))
            else:
                print(get_translation("Vk account data not received.\n"
                                      "Note: Command {0}say won't work.").format(
                    cls._settings_instance.bot_settings.prefix))

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
    def _setup_clear_delete_limit_without_poll(cls):
        if cls._settings_instance.bot_settings.deletion_messages_limit_without_poll < 0:
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.deletion_messages_limit_without_poll = \
                cls._ask_for_data(get_translation("Set limit for deletion messages "
                                                  "without poll (0 - for disable poll) (int)") + "\n> ",
                                  try_int=True, int_high_than=-1)

    @classmethod
    def _setup_menu_id(cls):
        if cls._settings_instance.bot_settings.menu_id is None:
            if cls._ask_for_data(
                    get_translation("Menu message id not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                cls._need_to_rewrite = True
                cls._settings_instance.bot_settings.menu_id = cls._ask_for_data(
                    get_translation("Enter menu message id") + "\n> ",
                    try_int=True, int_high_than=0)
            else:
                print(get_translation("Menu via reactions wouldn't work. To make it work type "
                                      "'{0}menu' to create new menu and its id.").format(
                    cls._settings_instance.bot_settings.prefix))

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
        if cls._settings_instance.bot_settings.timeouts.await_seconds_in_check_ups < 1:
            cls._need_to_rewrite = True
            print(get_translation("Timeout between check-ups 'Server on/off' set below 1. Change this option."))
            print(get_translation("Note: If your machine has processor with frequency 2-2.5 GHz, "
                                  "you have to set this option at least to '2' seconds "
                                  "or higher for the bot to work properly."))
            cls._settings_instance.bot_settings.timeouts.await_seconds_in_check_ups = \
                cls._ask_for_data(
                    get_translation("Set timeout between check-ups 'Server on/off' (in seconds, int)") + "\n> ",
                    try_int=True, int_high_than=1)
        print(get_translation("Timeout between check-ups 'Server on/off' set to {0} sec.")
              .format(str(cls._settings_instance.bot_settings.timeouts.await_seconds_in_check_ups)))

        # Timeout for op
        if cls._settings_instance.bot_settings.timeouts.await_seconds_when_opped < 0:
            cls._need_to_rewrite = True
            print(get_translation("Timeout for op set below 0. Change this option."))
            cls._settings_instance.bot_settings.timeouts.await_seconds_when_opped = \
                cls._ask_for_data(get_translation("Set timeout for op (0 - for unlimited timeout) (in seconds, int)") +
                                  "\n> ",
                                  try_int=True, int_high_than=-1)
        print(get_translation("Timeout for op set to {0} sec.")
              .format(str(cls._settings_instance.bot_settings.timeouts.await_seconds_when_opped)))
        if cls._settings_instance.bot_settings.timeouts.await_seconds_when_opped == 0:
            print(get_translation("Limitation doesn't exist, padawan."))

        # Timeout to sleep while bot pinging server for info
        if cls._settings_instance.bot_settings.timeouts.await_seconds_when_connecting_via_rcon < 0.05:
            cls._need_to_rewrite = True
            print(get_translation("Timeout while bot pinging server for info set below 0. Change this option."))
            cls._settings_instance.bot_settings.timeouts.await_seconds_when_connecting_via_rcon = \
                cls._ask_for_data(get_translation(
                    "Set timeout while bot pinging server for info (in seconds, float)") + "\n> ",
                                  try_float=True, float_hight_than=0.05)
        print(get_translation("Timeout while bot pinging server for info set to {0} sec.")
              .format(str(cls._settings_instance.bot_settings.timeouts.await_seconds_when_connecting_via_rcon)))
        if cls._settings_instance.bot_settings.timeouts.await_seconds_when_connecting_via_rcon == 0:
            print(get_translation("I'm fast as f*ck, boi!"))

        # Timeout before message deletion
        if cls._settings_instance.bot_settings.timeouts.await_seconds_before_message_deletion < 1:
            cls._need_to_rewrite = True
            print(get_translation(
                "Timeout before message deletion is set below 1. Change this option."))
            cls._settings_instance.bot_settings.timeouts.await_seconds_before_message_deletion = \
                cls._ask_for_data(get_translation("Set timeout before message deletion (in seconds, int)") + "\n> ",
                                  try_int=True, int_high_than=0)
        print(get_translation("Timeout before message deletion is set to {0} sec.")
              .format(str(cls._settings_instance.bot_settings.timeouts.await_seconds_before_message_deletion)))

    @classmethod
    def _setup_servers(cls):
        if not 0 < cls._settings_instance.selected_server_number <= len(cls._settings_instance.servers_list):
            cls._settings_instance.selected_server_number = 1
            print(get_translation("Selected minecraft server number is out of range! Bot set it to '1'."))
            cls._need_to_rewrite = True
        if not cls._settings_instance.ask_to_change_servers_list:
            print(get_translation("Selected minecraft server dir set to path '{0}' also known as '{1}'.")
                  .format(cls.get_selected_server_from_list().working_directory,
                          cls.get_selected_server_from_list().server_name))
            return

        cls._need_to_rewrite = True
        new_servers_number = cls._ask_for_data(get_translation("How much servers you intend to keep?") + "\n> ",
                                               try_int=True, int_high_than=0)
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
        print(get_translation("Selected minecraft server dir set to path '{0}' also known as '{1}'.")
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
                                  "Bot will search for '***.sh' file.\n"
                                  "You need to enter file name {0}without{1} file extension!").format(BOLD, END))
        elif sys.platform == "win32":
            file_extension = ".bat"
            print(get_translation("Bot detected your operating system is Windows.\n"
                                  "Bot will search for '***.bat' file.\n"
                                  "You need to enter file name {0}without{1} file extension!").format(BOLD, END))
        else:
            print(get_translation("Bot couldn't detect your operating system.\n"
                                  "You need to enter file name {0}with{1} file extension!").format(BOLD, END))
        while True:
            start_file_name = cls._ask_for_data(get_translation("Enter server start file name") + "\n> ") + \
                              (file_extension if file_extension is not None else '')
            if isfile(Path(working_directory + "/" + start_file_name)):
                return start_file_name
            else:
                print(get_translation("This start file doesn't exist."))

    @classmethod
    def _setup_cross_platform_chat(cls):
        if cls._settings_instance.bot_settings.cross_platform_chat.enable_cross_platform_chat is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Would you like to enable cross-platform chat?") + " Y/n\n> ",
                                 "y"):
                cls._settings_instance.bot_settings.cross_platform_chat.enable_cross_platform_chat = True

                if cls._settings_instance.bot_settings.cross_platform_chat.channel_id is None:
                    if cls._ask_for_data(
                            get_translation("Channel id not found. Would you like to enter it?") + " Y/n\n> ",
                            "y"):
                        cls._settings_instance.bot_settings.cross_platform_chat.channel_id = \
                            cls._ask_for_data(get_translation("Enter channel id") + "\n> ")
                    else:
                        print(get_translation("Cross-platform chat wouldn't work. "
                                              "To make it work type '{0}chat <id>' to create link.")
                              .format(cls._settings_instance.bot_settings.prefix))

                if cls._settings_instance.bot_settings.cross_platform_chat.webhook_url is None:
                    if cls._ask_for_data(get_translation("Webhook url for cross-platform chat not found. "
                                                         "Would you like to enter it?") + " Y/n\n> ", "y"):
                        cls._settings_instance.bot_settings.cross_platform_chat.webhook_url = \
                            cls._ask_for_data(get_translation("Enter webhook url") + "\n> ")
                    else:
                        print(get_translation(
                            "Cross-platform chat wouldn't work. Create webhook and enter it to bot config!"))

                if cls._settings_instance.bot_settings.cross_platform_chat.refresh_delay_of_console_log <= 0.05:
                    print(get_translation("Watcher's delay to refresh doesn't set."))
                    print(get_translation("Note: If your machine has processor with frequency 2-2.5 GHz, "
                                          "you have to set this option from '0.5' to '0.9' second for the bot to work properly."))
                    cls._settings_instance.bot_settings.cross_platform_chat.refresh_delay_of_console_log = \
                        cls._ask_for_data(get_translation("Set delay to refresh (in seconds, float)") + "\n> ",
                                          try_float=True, float_hight_than=0.05)

                if cls._settings_instance.bot_settings.cross_platform_chat.number_of_lines_to_check_in_console_log < 1:
                    print(get_translation("Watcher's number of lines to check in server log doesn't set."))
                    cls._settings_instance.bot_settings.cross_platform_chat.number_of_lines_to_check_in_console_log = \
                        cls._ask_for_data(get_translation("Set number of lines to check") + "\n> ", try_int=True,
                                          int_high_than=0)
            else:
                cls._settings_instance.bot_settings.cross_platform_chat.enable_cross_platform_chat = False
                print(get_translation("Cross-platform chat wouldn't work."))

        if cls._settings_instance.bot_settings.cross_platform_chat.enable_cross_platform_chat:
            print(get_translation("Cross-platform chat enabled."))
        else:
            print(get_translation("Cross-platform chat disabled."))

    @classmethod
    def _setup_rss_feed(cls):
        if cls._settings_instance.bot_settings.rss_feed.enable_rss_feed is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data(get_translation("Would you like to enable rss feed?") + " Y/n\n> ", "y"):
                cls._settings_instance.bot_settings.rss_feed.enable_rss_feed = True

                if cls._settings_instance.bot_settings.rss_feed.webhook_url is None:
                    if cls._ask_for_data(
                            get_translation("Webhook rss url not found. Would you like to enter it?") + " Y/n\n> ",
                            "y"):
                        cls._settings_instance.bot_settings.rss_feed.webhook_url = \
                            cls._ask_for_data(get_translation("Enter webhook rss url") + "\n> ")
                    else:
                        print(get_translation("Rss wouldn't work. Create webhook and enter it to bot config!"))

                if cls._settings_instance.bot_settings.rss_feed.rss_url is None:
                    if cls._ask_for_data(
                            get_translation("Rss url not found. Would you like to enter it?") + " Y/n\n> ", "y"):
                        cls._settings_instance.bot_settings.rss_feed.rss_url = cls._ask_for_data(
                            get_translation("Enter rss url") + "\n> ")
                    else:
                        print(get_translation("Rss wouldn't work. Enter url of rss feed to bot config!"))

                if cls._settings_instance.bot_settings.rss_feed.rss_download_delay < 1:
                    print(get_translation("Rss download delay doesn't set."))
                    cls._settings_instance.bot_settings.rss_feed.rss_download_delay = \
                        cls._ask_for_data(get_translation("Enter rss download delay (in seconds, int)") + "\n> ",
                                          try_int=True, int_high_than=0)

                cls._settings_instance.bot_settings.rss_feed.rss_last_date = \
                    datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
            else:
                cls._settings_instance.bot_settings.rss_feed.enable_rss_feed = False
                print(get_translation("Rss feed wouldn't work."))
        else:
            if cls._settings_instance.bot_settings.rss_feed.enable_rss_feed:
                print(get_translation("Rss feed enabled."))
            else:
                print(get_translation("Rss feed disabled."))
