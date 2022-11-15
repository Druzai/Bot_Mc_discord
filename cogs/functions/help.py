import inspect
import typing
from re import sub
from typing import Tuple, List, Optional, Union

from discord.ext import commands

from components.localization import get_translation
from config.init_config import Config


def get_param_type(arg_data):
    if arg_data.annotation != inspect._empty:
        if hasattr(arg_data.annotation, '__origin__') and arg_data.annotation.__origin__._name == "Union":
            param_type = " | ".join([a.__name__ for a in arg_data.annotation.__args__ if a != type(None)])
        elif hasattr(arg_data.annotation, '__origin__') and arg_data.annotation.__origin__._name == "Literal":
            param_type = " | ".join([str(a) for a in arg_data.annotation.__args__])
        elif getattr(arg_data.annotation, '__name__', None) is not None:
            param_type = getattr(arg_data.annotation, '__name__', None)
        elif hasattr(arg_data.annotation, 'converter'):
            param_type = sub(r"\w*?\.", "", str(arg_data.annotation.converter))
            if not isinstance(arg_data.annotation.converter, typing._GenericAlias):
                param_type = param_type.strip("<>").lstrip("class").strip("' ")
        else:
            param_type = sub(r"\w*?\.", "", str(arg_data.annotation))
    elif arg_data.annotation == inspect._empty and arg_data.default != inspect._empty:
        param_type = type(arg_data.default).__name__
    else:
        param_type = "Any"
    return param_type


def parse_params_for_help(command_params: dict, string_to_add: str, create_params_dict=False) -> Tuple[str, dict]:
    params = {}
    converter = False
    for arg_name, arg_data in command_params.items():
        if arg_data.annotation != inspect._empty and hasattr(arg_data.annotation, 'converter') \
                and isinstance(arg_data.annotation.converter, typing._GenericAlias):
            converter = True
        if create_params_dict:
            params[arg_name] = get_param_type(arg_data)
        is_optional = hasattr(arg_data.annotation, '__origin__') \
                      and arg_data.annotation.__origin__._name == "Union" \
                      and type(None) in arg_data.annotation.__args__
        if arg_data.default != inspect._empty or arg_data.kind == arg_data.VAR_POSITIONAL or is_optional:
            add_data = ""
            if arg_data.default != inspect._empty and bool(arg_data.default) \
                    and arg_data.kind != arg_data.VAR_POSITIONAL:
                add_data = f"'{arg_data.default}'" if isinstance(arg_data.default, str) else str(arg_data.default)
            string_to_add += f" [{arg_name}" + (f" = {add_data}" if add_data else "") + \
                             ("..." if arg_data.kind == arg_data.VAR_POSITIONAL or converter else "") + "]"
        else:
            string_to_add += f" <{arg_name}>"
    return string_to_add, params


def parse_subcommands_for_help(
        command: Union[commands.Command, commands.Group],
        all_params=False
) -> Tuple[List[str], List[str]]:
    if not hasattr(command, "commands") or len(command.commands) == 0:
        return [], []
    command_commands = sorted(command.commands, key=lambda c: c.name)

    if not all_params:
        return [c.name for c in command_commands], []

    subcommands = []
    for subcommand in command_commands:
        sub_sub_commands_line = parse_subcommands_for_help(subcommand)[0]
        sub_commands_aliases_line = ("/" if len(subcommand.aliases) > 0 else "") + "/".join(subcommand.aliases)
        if sub_sub_commands_line:
            sub_sub_commands_line = " " + " | ".join(sub_sub_commands_line) if len(sub_sub_commands_line) else ""
            sub_command, *sub_command_params = parse_params_for_help(subcommand.clean_params,
                                                                     subcommand.name)[0].split()
            subcommands.append(sub_command + sub_commands_aliases_line + sub_sub_commands_line +
                               (" | " if len(sub_command_params) > 0 else "") + " ".join(sub_command_params))
        else:
            subcommands.append(parse_params_for_help(subcommand.clean_params,
                                                     subcommand.name + sub_commands_aliases_line)[0])
    return [c.name for c in command_commands], subcommands


def get_command_help(command: Union[commands.Command, commands.Group]):
    subcommands_names, subcommands = parse_subcommands_for_help(command, True)
    str_help = f"{Config.get_settings().bot_settings.prefix}{command}"
    str_help += " " + " | ".join(subcommands_names) if len(subcommands_names) else ""
    str_params, params = parse_params_for_help(command.clean_params, "", True)
    if len(str_params):
        str_help += " |" + str_params if len(subcommands_names) else str_params

    str_help += "\n\n" + get_translation("Description") + ":\n"
    str_help += get_translation(f'help_{str(command).replace(" ", "_")}').format(
        prefix=Config.get_settings().bot_settings.prefix
    ) + "\n\n"
    if len(command.aliases):
        str_help += get_translation("Aliases") + ": " + ", ".join(command.aliases) + "\n\n"

    if len(subcommands):
        str_help += get_translation("Subcommands") + ":\n" + "\n".join(subcommands) + "\n\n"

    if len(params.keys()):
        str_help += get_translation("Parameters") + ":\n"
        for arg_name, arg_type in params.items():
            str_help += f"{arg_name}: {arg_type}\n" + \
                        get_translation(f'help_{str(command).replace(" ", "_")}_{arg_name}').format(
                            prefix=Config.get_settings().bot_settings.prefix,
                            code_length=Config.get_secure_auth().code_length
                        ) + "\n\n"
    return str_help


def find_subcommand(
        subcommands: List[str],
        command: Union[commands.Command, commands.Group],
        pos: int
) -> Optional[Union[commands.Command, commands.Group]]:
    if hasattr(command, "all_commands") and len(command.all_commands) != 0:
        pos += 1
        for subcomm_name, subcomm in command.all_commands.items():
            if subcomm_name == subcommands[pos]:
                if len(subcommands) == pos + 1:
                    return subcomm
                else:
                    return find_subcommand(subcommands, subcomm, pos)
