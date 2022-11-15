from contextlib import contextmanager, suppress
from pathlib import Path
from re import search, findall
from typing import Optional

from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r, WrongPassword
from requests import get as req_get, Timeout

from components.localization import get_translation
from components.utils import UserAgent
from config.init_config import Config


# TODO: Create Thread-Queue to execute rcon commands

@contextmanager
def connect_rcon(timeout=1):
    try:
        with Client_r(Config.get_settings().bot_settings.local_address, Config.get_server_config().rcon_port,
                      passwd=Config.get_server_config().rcon_password, timeout=timeout) as cl_r:
            yield cl_r
    except WrongPassword:
        print(get_translation("Bot Error: {0}")
              .format(get_translation("RCON password '{0}' doesn't match with its value in '{1}'!")
                      .format(Config.get_server_config().rcon_password,
                              Path(Config.get_selected_server_from_list().working_directory + "/server.properties")
                              .as_posix())))
        raise ConnectionError()


@contextmanager
def connect_query():
    with Client_q(Config.get_settings().bot_settings.local_address,
                  Config.get_server_config().query_port, timeout=1) as cl_q:
        yield cl_q


def get_server_players() -> dict:  # TODO: Create class!!!
    """Returns dict, keys: current, max, players"""
    with connect_query() as cl_q:
        info = cl_q.full_stats
    return dict(current=info.num_players, max=info.max_players, players=info.players)


class ServerVersion:
    def __init__(self, version_string: str):
        parsed_version = version_string
        snapshot_version = False
        snapshot_regex = r"(?P<version>\d+w\d+[a-e~])"
        snapshot_match = search(snapshot_regex, parsed_version)
        if any(i in parsed_version.lower() for i in ["snapshot", "release"]) or snapshot_match is not None:
            print(get_translation("Minecraft server is not in release state! Proceed with caution!"))
            if "snapshot" in parsed_version.lower():
                parsed_version = parsed_version.lower().split("snapshot")[0]
                snapshot_version = True
            elif "release" in parsed_version.lower():
                parsed_version = parsed_version.lower().split("release")[0]
            elif snapshot_match is not None:
                parsed_version = parse_snapshot(snapshot_match.group("version"))
                if parsed_version is None:
                    parsed_version = ""
                snapshot_version = True
        matches = findall(r"\d+", parsed_version)
        if len(matches) < 2:
            raise ValueError(f"Can't parse server version '{version_string}'!")
        self.major = int(matches[0])
        self.minor = int(matches[1])
        self.patch = int(matches[2]) if len(matches) > 2 else 0
        self.version_string = version_string
        if snapshot_version and self.patch > 0:
            self.patch -= 1
        elif snapshot_version and self.minor > 0 and self.patch == 0:
            self.minor -= 1
            self.patch = 10


def get_server_version() -> ServerVersion:
    with connect_query() as cl_q:
        version = cl_q.full_stats.version
    return ServerVersion(version)


def parse_snapshot(version: str) -> Optional[str]:
    with suppress(Timeout):
        answer = req_get(
            url="https://minecraft.fandom.com/api.php",
            params={
                "action": "parse",
                "page": f"Java Edition {version}",
                "prop": "categories",
                "format": "json"
            },
            timeout=(3, 6),
            headers={"User-Agent": UserAgent.get_header()}
        ).json()
        if answer.get("parse", None) is not None and answer["parse"].get("categories", None) is not None:
            for category in answer["parse"]["categories"]:
                if all(i in category["*"].lower() for i in ["java_edition", "snapshots"]) and \
                        version in category["sortkey"]:
                    return category["*"]
