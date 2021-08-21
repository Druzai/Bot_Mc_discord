import datetime as dt
import sys
from ast import literal_eval
from dataclasses import dataclass, field
from datetime import datetime
from glob import glob
from json import load, dumps, loads
from os.path import isfile, isdir
from pathlib import Path
from secrets import choice as sec_choice
from string import ascii_letters, digits
from typing import List, Optional

from discord import Webhook, Member
from discord.ext.commands import Bot
from jsons import load as sload, DeserializationError
from omegaconf import OmegaConf as conf

from config.crypt_wrapper import *


class Bot_variables:
    react_auth: Member = None  # Variable for situation when command calls via reactions, represents author that added reaction
    server_checkups_task = None
    server_start_time: int = None
    IsServerOn: bool = False
    IsLoading: bool = False
    IsStopping: bool = False
    IsRestarting: bool = False
    IsDoOp: bool = False
    IsVoting: bool = False
    op_deop_list: List = []  # List of nicks of players to op and then to deop
    port_query: int = None
    port_rcon: int = None
    rcon_pass: str = None
    progress_bar_time: int = 0
    watcher_of_log_file = None
    webhook_chat: Webhook = None
    webhook_rss: Webhook = None
    bot_for_webhooks: Bot = None


@dataclass
class Cross_platform_chat:
    enable_cross_platform_chat: Optional[bool] = None
    channel_id: Optional[int] = None
    webhook_url: Optional[str] = None
    refresh_delay_of_console_log: float = -1.0


@dataclass
class Rss_feed:
    enable_rss_feed: Optional[bool] = None
    webhook_url: Optional[str] = None
    rss_url: Optional[str] = None
    rss_download_delay: int = -1
    rss_last_date: Optional[str] = None


@dataclass
class Awating_times:
    await_seconds_when_connecting_via_rcon: float = -1.0
    await_seconds_in_check_ups: int = -1
    await_seconds_when_opped: int = -1
    await_seconds_before_message_deletion: int = -1


@dataclass
class Bot_settings:
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
    gaming_status: str = ""
    idle_status: str = ""
    role: Optional[str] = None
    ip_address: str = ""
    local_address: str = ""
    menu_id: Optional[int] = None
    forceload: bool = False
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
    awating_times: Awating_times = Awating_times()

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
    selected_server_number: int = 0
    servers_list: List[Server_settings] = field(default_factory=list)
    known_users: List[User] = field(default_factory=list)


@dataclass
class State_info:
    user: Optional[str] = None
    date: Optional[str] = None


@dataclass
class States:
    started_info: State_info = State_info()
    stopped_info: State_info = State_info()


@dataclass
class Server_config:
    states: States = States()


class Config:
    _current_bot_path: str = path.dirname(sys.argv[0])
    _config_name = "bot_config.yaml"
    _settings_instance: Settings = Settings()
    _server_config_name = "server_config.yaml"
    _server_config_instance: Server_config = Server_config()
    _op_keys_name = "op_keys"
    _op_log_name = "op_log.txt"
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
    def get_awaiting_times_settings(cls) -> Awating_times:
        return cls._settings_instance.bot_settings.awating_times

    @classmethod
    def get_selected_server_from_list(cls) -> Server_settings:
        return cls._settings_instance.servers_list[cls._settings_instance.selected_server_number]

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
    def read_op_keys(cls):
        if not path.isfile(Path(cls._current_bot_path + '/' + cls._op_keys_name)):
            cls.save_op_keys(dict())
            return dict()
        else:
            return loads(decrypt_string(open(Path(cls._current_bot_path + '/' + cls._op_keys_name), "r").read()))

    @classmethod
    def save_op_keys(cls, op_keys: dict):
        open(Path(cls._current_bot_path + '/' + cls._op_keys_name), 'w') \
            .write(encrypt_string(dumps(op_keys)))

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
        Bot_variables.progress_bar_time = cls.get_selected_server_from_list().server_loading_time
        filepath = Path(cls.get_selected_server_from_list().working_directory + "/server.properties")
        if not filepath.exists():
            raise RuntimeError(f"File '{filepath.as_posix()}' doesn't exist! "
                               "Run minecraft server manually to create one and accept eula!")
        with open(filepath, "r", encoding="utf8") as f:
            lines = f.readlines()
            if len(lines) < 3:
                raise RuntimeError(f"File '{filepath.as_posix()}' doesn't have any parameters! "
                                   "Accept eula and run minecraft server manually to fill it with parameters!")
            for i in lines:
                if i.find("enable-query") >= 0:
                    enable_query = literal_eval(i.split("=")[1].capitalize())
                if i.find("enable-rcon") >= 0:
                    enable_rcon = literal_eval(i.split("=")[1].capitalize())
                if i.find("query.port") >= 0:
                    Bot_variables.port_query = int(i.split("=")[1])
                if i.find("rcon.port") >= 0:
                    Bot_variables.port_rcon = int(i.split("=")[1])
                if i.find("rcon.password") >= 0:
                    Bot_variables.rcon_pass = i.split("=")[1].strip()
        if not enable_query or not enable_rcon or not Bot_variables.rcon_pass:
            changed_parameters = []
            rewritten_rcon_pass = False
            if not enable_query:
                changed_parameters.append("enable-query=true")
            if not enable_rcon:
                changed_parameters.append("enable-rcon=true")
            if not Bot_variables.rcon_pass:
                Bot_variables.rcon_pass = "".join(sec_choice(ascii_letters + digits) for _ in range(20))
                changed_parameters.append(f"rcon.password={Bot_variables.rcon_pass}\nReminder: for better security "
                                          "you have to change this password for a more secure one.")
            with open(filepath, "r", encoding="utf8") as f:
                properties_file = f.readlines()
            for i in range(len(properties_file)):
                if "enable-query" in properties_file[i] or "enable-rcon" in properties_file[i]:
                    properties_file[i] = f"{properties_file[i].split('=')[0]}=true\n"
                if "rcon.password" in properties_file[i]:
                    rewritten_rcon_pass = True
                    properties_file[i] = f"rcon.password={Bot_variables.rcon_pass}\n"
            if Bot_variables.port_query is None:
                Bot_variables.port_query = 25565
                properties_file.append(f"query.port={str(Bot_variables.port_query)}\n")
                changed_parameters.append(f"query.port={str(Bot_variables.port_query)}")
            if Bot_variables.port_rcon is None:
                Bot_variables.port_rcon = 25575
                properties_file.append(f"rcon.port={str(Bot_variables.port_rcon)}\n")
                changed_parameters.append(f"rcon.port={str(Bot_variables.port_rcon)}")
            if not rewritten_rcon_pass:
                properties_file.append(f"rcon.password={Bot_variables.rcon_pass}\n")
            with open(filepath, "w", encoding="utf8") as f:
                f.writelines(properties_file)
            print(f"\nNote: in '{filepath.as_posix()}' bot set these parameters:\n" +
                  "\n".join(changed_parameters) + "\n")

    @classmethod
    def get_ops_json(cls):
        return load(open(Path(cls.get_selected_server_from_list().working_directory + '/ops.json'), 'r'))

    @classmethod
    def append_to_op_log(cls, message: str):
        open(Path(cls.get_bot_config_path() + f'/{cls._op_log_name}'), 'a', encoding='utf-8').write(message)

    @classmethod
    def _load_from_yaml(cls, filepath: Path, baseclass):
        try:
            return sload(json_obj=conf.to_object(conf.load(filepath)), cls=baseclass)
        except DeserializationError:
            return baseclass()

    @classmethod
    def _save_to_yaml(cls, class_instance, filepath: Path):
        conf.save(config=conf.structured(class_instance), f=filepath)

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
                            print(f"Your number lower than {int_high_than}!")
                            continue
                        return int(answer)
                    except ValueError:
                        print("Your string doesn't contain an integer!")
                        continue
                if try_float or float_hight_than is not None:
                    try:
                        if float_hight_than is not None and float(answer) < float_hight_than:
                            print(f"Your number lower than {float_hight_than}!")
                            continue
                        return float(answer)
                    except ValueError:
                        print("Your string doesn't contain a fractional number !")
                        continue
                return answer

    @classmethod
    def _setup_config(cls, file_exists=False):
        if not file_exists:
            print(f"File '{cls._config_name}' wasn't found! Setting up a new one!")
        else:
            print(f"File '{cls._config_name}' was found!")

        cls._setup_token()
        cls._setup_prefix()
        cls._setup_role()
        cls._setup_bot_statuses()
        cls._setup_ip_address()
        cls._setup_local_address()
        cls._setup_menu_id()
        cls._setup_vk_credentials()
        cls._setup_cross_platform_chat()
        cls._setup_rss_feed()
        cls._setup_awaiting_times()
        cls._setup_servers()

        if cls._need_to_rewrite:
            cls._need_to_rewrite = False
            cls.save_config()
            print("Config saved!")
        print("Config read!")

    @classmethod
    def _setup_token(cls):
        if cls._settings_instance.bot_settings.token is None:
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.token = cls._ask_for_data("Token not founded. Enter token: ")

    @classmethod
    def _setup_prefix(cls):
        if cls._settings_instance.bot_settings.prefix == "":
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.prefix = cls._ask_for_data("Enter bot prefix: ")
        print(f"Bot prefix set to '{cls._settings_instance.bot_settings.prefix}'.")

    @classmethod
    def _setup_role(cls):
        if cls._settings_instance.bot_settings.role is not None:
            Command_role = cls._settings_instance.bot_settings.role
            if Command_role:
                print(f"Current role for some commands is '{Command_role}'.")
            else:
                print("Current role doesn't stated.")
        else:
            cls._need_to_rewrite = True
            if cls._ask_for_data("Do you want to set role for some specific commands? Y/n\n", "y"):
                cls._settings_instance.bot_settings.role = \
                    cls._ask_for_data("Set discord role for some specific commands such as start, stop, etc.\n")
            else:
                cls._settings_instance.bot_settings.role = ""

    @classmethod
    def _setup_vk_credentials(cls):
        if not cls._settings_instance.bot_settings.vk_login or not cls._settings_instance.bot_settings.vk_password:
            cls._settings_instance.bot_settings.vk_login = None
            cls._settings_instance.bot_settings.vk_password = None
        if cls._settings_instance.bot_settings.vk_ask_credentials:
            if cls._ask_for_data("Would you like to " +
                                 ('change' if cls._settings_instance.bot_settings.vk_login is not None else 'enter') +
                                 " vk account data? Y/n\n", "y"):
                cls._settings_instance.bot_settings.vk_login = cls._ask_for_data("Enter vk login: ")
                cls._settings_instance.bot_settings.vk_password = cls._ask_for_data("Enter vk password: ")
                cls._need_to_rewrite = True
            if cls._ask_for_data("Never ask about it again? Y/n\n", "y"):
                cls._settings_instance.bot_settings.vk_ask_credentials = False
                cls._need_to_rewrite = True
                if cls._settings_instance.bot_settings.vk_login is not None and \
                        cls._settings_instance.bot_settings.vk_password is not None:
                    print("I'll never ask you about it again.")
                else:
                    print("Vk account data not received.\n"
                          "I'll never ask you about it again.\n"
                          f"Note: command {cls._settings_instance.bot_settings.prefix}say won't work.")
            else:
                print("Vk account data received. Why man?")
        else:
            if cls._settings_instance.bot_settings.vk_login is not None and \
                    cls._settings_instance.bot_settings.vk_password is not None:
                print("Vk account data received.")
            else:
                print("Vk account data not received.\n"
                      f"Note: command {cls._settings_instance.bot_settings.prefix}say won't work.")

    @classmethod
    def _setup_ip_address(cls):
        if cls._settings_instance.bot_settings.ip_address == "":
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.ip_address = \
                cls._ask_for_data("Enter server's real IP-address or DNS-name: ")
        print(f"Server's real IP-address or DNS-name is '{cls._settings_instance.bot_settings.ip_address}'.")

    @classmethod
    def _setup_local_address(cls):
        if cls._settings_instance.bot_settings.local_address == "":
            cls._need_to_rewrite = True
            cls._settings_instance.bot_settings.local_address = \
                cls._ask_for_data("Enter server's local address (default - 'localhost'): ")

    @classmethod
    def _setup_menu_id(cls):
        if cls._settings_instance.bot_settings.menu_id is None:
            if cls._ask_for_data("Menu message id not found. Would you like to enter it? Y/n\n", "y"):
                cls._need_to_rewrite = True
                cls._settings_instance.bot_settings.menu_id = cls._ask_for_data("Enter menu message id: ",
                                                                                try_int=True, int_high_than=0)
            else:
                print("Menu via reactions wouldn't work. To make it work type "
                      f"'{cls._settings_instance.bot_settings.prefix}menu' to create new menu and its id.")

    @classmethod
    def _setup_bot_statuses(cls):
        # Gaming status
        if cls._settings_instance.bot_settings.gaming_status == "":
            cls._settings_instance.bot_settings.gaming_status = cls._ask_for_data("Set gaming status: ")
        # Idle status
        if cls._settings_instance.bot_settings.idle_status == "":
            cls._settings_instance.bot_settings.idle_status = cls._ask_for_data("Set idle status: ")

    @classmethod
    def _setup_awaiting_times(cls):
        # Await time check-ups func
        if cls._settings_instance.bot_settings.awating_times.await_seconds_in_check_ups < 1:
            cls._need_to_rewrite = True
            print("Await time check-ups set below 1. Change this option")
            print("Note: If your machine has processor with frequency 2-2.5 GHz, "
                  "you have to set this option at least to '2' seconds or higher for the bot to work properly.")
            cls._settings_instance.bot_settings.awating_times.await_seconds_in_check_ups = \
                cls._ask_for_data("Set await time between check-ups 'Server on/off' (in seconds, int): ",
                                  try_int=True, int_high_than=1)
        print("Await time check-ups set to " +
              str(cls._settings_instance.bot_settings.awating_times.await_seconds_in_check_ups) + " sec.")

        # Await time op
        if cls._settings_instance.bot_settings.awating_times.await_seconds_when_opped < 0:
            cls._need_to_rewrite = True
            print("Await time op set below zero. Change this option")
            cls._settings_instance.bot_settings.awating_times.await_seconds_when_opped = \
                cls._ask_for_data("Set await time for op (in seconds, int): ", try_int=True, int_high_than=-1)
        print("Await time op set to " +
              str(cls._settings_instance.bot_settings.awating_times.await_seconds_when_opped) + " sec.")
        if cls._settings_instance.bot_settings.awating_times.await_seconds_when_opped == 0:
            print("Limitation doesn't exist, padawan.")

        # Await time to sleep while bot pinging server for info
        if cls._settings_instance.bot_settings.awating_times.await_seconds_when_connecting_via_rcon < 0.05:
            cls._need_to_rewrite = True
            print("Await time to sleep set below zero. Change this option")
            cls._settings_instance.bot_settings.awating_times.await_seconds_when_connecting_via_rcon = \
                cls._ask_for_data("Set await time to sleep while bot pinging server for info (in seconds, float): ",
                                  try_float=True, float_hight_than=0.05)
        print("Await time to sleep while bot pinging server for info set to " +
              str(cls._settings_instance.bot_settings.awating_times.await_seconds_when_connecting_via_rcon) + " sec.")
        if cls._settings_instance.bot_settings.awating_times.await_seconds_when_connecting_via_rcon == 0:
            print("I'm fast as f*ck, boi!")

        # Await time before_message_deletion
        if cls._settings_instance.bot_settings.awating_times.await_seconds_before_message_deletion < 1:
            cls._need_to_rewrite = True
            print("Await time to delete before message deletion set below one. Change this option")
            cls._settings_instance.bot_settings.awating_times.await_seconds_before_message_deletion = \
                cls._ask_for_data("Set await time to delete (in seconds, int): ", try_int=True, int_high_than=0)
        print("Await time to sleep set to " +
              str(cls._settings_instance.bot_settings.awating_times.await_seconds_before_message_deletion) + " sec.")

    @classmethod
    def _setup_servers(cls):
        if not cls._settings_instance.ask_to_change_servers_list:
            print("Selected minecraft server dir set to path '" + cls.get_selected_server_from_list().working_directory
                  + "' also known as '" + cls.get_selected_server_from_list().server_name + "'.")
            return

        cls._need_to_rewrite = True
        new_servers_number = cls._ask_for_data("How much servers you intend to keep?\n", try_int=True, int_high_than=0)
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
                elif cls._ask_for_data(f"Would you like to delete this server '{server.server_name}'? Y/n\n", "y"):
                    cls._settings_instance.servers_list.remove(server)

        cls._settings_instance.ask_to_change_servers_list = False
        print("Selected minecraft server dir set to path '" + cls.get_selected_server_from_list().working_directory
              + "' also known as '" + cls.get_selected_server_from_list().server_name + "'.")

    @classmethod
    def _change_server_settings(cls, server: Server_settings = None):
        changing_settings = False
        if server is not None:
            if not cls._ask_for_data(f"Would you like to change this server '{server.server_name}'? Y/n\n", "y"):
                return server
            changing_settings = True
        else:
            print("Configuring new server settings...")

        if not changing_settings:
            server = Server_settings()
            server.server_name = cls._ask_for_data(f"Enter server name: ")
            server.working_directory = cls._get_server_working_directory()
            server.start_file_name = cls._get_server_start_file_name(server.working_directory)
        else:
            if cls._ask_for_data(f"Change server name '{server.server_name}'? Y/n\n", "y"):
                server.server_name = cls._ask_for_data(f"Enter server name: ")
            if cls._ask_for_data(f"Change server working directory '{server.working_directory}'? Y/n\n", "y"):
                server.working_directory = cls._get_server_working_directory()
            if cls._ask_for_data(f"Change server start file name '{server.start_file_name}'? Y/n\n", "y"):
                server.start_file_name = cls._get_server_start_file_name(server.working_directory)
        return server

    @classmethod
    def _get_server_working_directory(cls):
        while True:
            working_directory = cls._ask_for_data(f"Enter server working directory (full path): ")
            if isdir(working_directory):
                if len(glob(Path(working_directory + "/*.jar").as_posix())) > 0:
                    return working_directory
                else:
                    print("There are no '*.jar' files in this working directory.")
            else:
                print("This working directory is wrong.")

    @classmethod
    def _get_server_start_file_name(cls, working_directory: str):
        file_extension = None
        BOLD = '\033[1m'
        END = '\033[0m'
        if sys.platform == "linux" or sys.platform == "linux2":
            file_extension = ".sh"
            print("Bot detected your operating system is Linux.\n"
                  "Bot will search for ***.sh file.\n"
                  f"You need to enter file name {BOLD}without{END} file extension!")
        elif sys.platform == "win32":
            file_extension = ".bat"
            print("Bot detected your operating system is Windows.\n"
                  "Bot will search for ***.bat file.\n"
                  f"You need to enter file name {BOLD}without{END} file extension!")
        else:
            print("Bot couldn't detect your operating system.\n"
                  f"You need to enter file name {BOLD}with{END} file extension!")
        while True:
            start_file_name = cls._ask_for_data(f"Enter server start file name: ") + \
                              (file_extension if file_extension is not None else '')
            if isfile(Path(working_directory + "/" + start_file_name)):
                return start_file_name
            else:
                print("This start file doesn't exist.")

    @classmethod
    def _setup_cross_platform_chat(cls):
        if cls._settings_instance.bot_settings.cross_platform_chat.enable_cross_platform_chat is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data("Would you like to enable cross platform chat? Y/n\n", "y"):
                cls._settings_instance.bot_settings.cross_platform_chat.enable_cross_platform_chat = True

                if cls._settings_instance.bot_settings.cross_platform_chat.channel_id is None:
                    if cls._ask_for_data("Channel id not found. Would you like to enter it? Y/n\n", "y"):
                        cls._settings_instance.bot_settings.cross_platform_chat.channel_id = \
                            cls._ask_for_data("Enter channel id: ")
                    else:
                        print("Cross platform chat wouldn't work. To make it work type '%chat <id>' to create link.")

                if cls._settings_instance.bot_settings.cross_platform_chat.webhook_url is None:
                    if cls._ask_for_data("Webhook url for cross platform chat not found. "
                                         "Would you like to enter it? Y/n\n", "y"):
                        cls._settings_instance.bot_settings.cross_platform_chat.webhook_url = \
                            cls._ask_for_data("Enter webhook url: ")
                    else:
                        print("Cross platform chat wouldn't work. Create webhook and enter it to bot config!")

                if cls._settings_instance.bot_settings.cross_platform_chat.refresh_delay_of_console_log <= 0.05:
                    print("Watcher's delay to refresh doesn't set.")
                    print("Note: If your machine has processor with frequency 2-2.5 GHz, "
                          "you have to set this option from '0.5' to '0.9' second for the bot to work properly.")
                    cls._settings_instance.bot_settings.cross_platform_chat.refresh_delay_of_console_log = \
                        cls._ask_for_data("Set delay to refresh (in seconds, float): ",
                                          try_float=True, float_hight_than=0.05)
            else:
                cls._settings_instance.bot_settings.cross_platform_chat.enable_cross_platform_chat = False
                print("Cross platform chat wouldn't work.")
        else:
            if cls._settings_instance.bot_settings.cross_platform_chat.enable_cross_platform_chat:
                print("Cross platform chat enabled.")
            else:
                print("Cross platform chat disabled.")

    @classmethod
    def _setup_rss_feed(cls):
        if cls._settings_instance.bot_settings.rss_feed.enable_rss_feed is None:
            cls._need_to_rewrite = True
            if cls._ask_for_data("Would you like to enable rss feed? Y/n\n", "y"):
                cls._settings_instance.bot_settings.rss_feed.enable_rss_feed = True

                if cls._settings_instance.bot_settings.rss_feed.webhook_url is None:
                    if cls._ask_for_data("Webhook rss url not found. Would you like to enter it? Y/n\n", "y"):
                        cls._settings_instance.bot_settings.rss_feed.webhook_url = \
                            cls._ask_for_data("Enter webhook rss url: ")
                    else:
                        print("Rss wouldn't work. Create webhook and enter it to bot config!")

                if cls._settings_instance.bot_settings.rss_feed.rss_url is None:
                    if cls._ask_for_data("Rss url not found. Would you like to enter it? Y/n\n", "y"):
                        cls._settings_instance.bot_settings.rss_feed.rss_url = cls._ask_for_data("Enter rss url: ")
                    else:
                        print("Rss wouldn't work. Enter url of rss feed to bot config!")

                if cls._settings_instance.bot_settings.rss_feed.rss_download_delay < 1:
                    print("Rss download delay doesn't set")
                    cls._settings_instance.bot_settings.rss_feed.rss_download_delay = \
                        cls._ask_for_data("Enter rss download delay (in seconds, int): ", try_int=True, int_high_than=0)

                cls._settings_instance.bot_settings.rss_feed.rss_last_date = \
                    datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
            else:
                cls._settings_instance.bot_settings.rss_feed.enable_rss_feed = False
                print("Rss feed wouldn't work.")
        else:
            if cls._settings_instance.bot_settings.rss_feed.enable_rss_feed:
                print("Rss feed enabled.")
            else:
                print("Rss feed disabled.")
