import socket
from contextlib import contextmanager, suppress
from re import search
from typing import Union

from components.minecraft.connect import connect_rcon, ServerVersion


@contextmanager
def disable_logging(disable_log_admin_commands: bool = False, disable_send_command_feedback: bool = False):
    command_regex = r"(?i)gamerule \w+ is currently set to: (?P<value>\w+)"
    log_admin_commands = True
    send_command_feedback = True
    if disable_log_admin_commands or disable_send_command_feedback:
        with suppress(ConnectionError, socket.error):
            with connect_rcon() as cl_r:
                if disable_log_admin_commands:
                    match = search(command_regex, cl_r.run("gamerule logAdminCommands"))
                    if match is not None:
                        log_admin_commands = not (match.group("value") == "false")
                        if log_admin_commands:
                            cl_r.run("gamerule logAdminCommands false")
                if disable_send_command_feedback:
                    match = search(command_regex, cl_r.run("gamerule sendCommandFeedback"))
                    if match is not None:
                        send_command_feedback = not (match.group("value") == "false")
                        if send_command_feedback:
                            cl_r.run("gamerule sendCommandFeedback false")
    yield
    if disable_log_admin_commands or disable_send_command_feedback:
        with suppress(ConnectionError, socket.error):
            with connect_rcon() as cl_r:
                if send_command_feedback and disable_send_command_feedback:
                    cl_r.run("gamerule sendCommandFeedback true")
                if log_admin_commands and disable_log_admin_commands:
                    cl_r.run("gamerule logAdminCommands true")


@contextmanager
def times(fade_in: Union[int, float], duration: Union[int, float], fade_out: Union[int, float], rcon_client):
    rcon_client.run(f"title @a times {fade_in} {duration} {fade_out}")
    yield
    rcon_client.run("title @a reset")


def announce(player: str, message: str, rcon_client, server_version: ServerVersion, subtitle=False):
    if server_version.minor >= 11 and not subtitle:
        player = player if server_version.minor < 14 else f"'{player}'"
        rcon_client.run(f'title {player} actionbar ' + '{' + f'"text":"{message}"' + ',"bold":true,"color":"gold"}')
    else:
        rcon_client.run(f'title {player} subtitle ' + '{' + f'"text":"{message}"' + ',"color":"gold"}')
        rcon_client.run(f'title {player} title ' + '{"text":""}')
    rcon_client.run(play_sound(player, "minecraft:entity.arrow.hit_player", "player", 1, 0.75))


def play_sound(name: str, sound: str, category="master", volume=1, pitch=1.0):
    return f"execute as {name} at @s run playsound {sound} {category} @s ~ ~ ~ {volume} {pitch} 1"


def play_music(name: str, sound: str):
    return play_sound(name, sound, "music", 99999999999999999999999999999999999999)


def stop_music(sound: str, name="@a"):
    return f"stopsound {name} music {sound}"
