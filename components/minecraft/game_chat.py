import socket
from contextlib import suppress
from io import BytesIO
from itertools import chain
from json import dumps
from re import search, split, compile
from textwrap import wrap
from typing import Tuple, List, Dict, Union
from urllib.parse import unquote

from PIL import Image, UnidentifiedImageError
from discord import (
    Message, Member, NotFound, HTTPException, Emoji
)
from discord.ext import commands
from discord.utils import get as utils_get
from requests import get as req_get, head as req_head, Timeout

from components.constants import TENOR_REGEX, EMOJI_REGEX, MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH, \
    MAX_RCON_COMMAND_RUN_STR_LENGTH, URL_REGEX
from components.localization import get_translation, check_if_string_in_all_translations
from components.minecraft.connect import get_server_players, get_server_version, connect_rcon, ServerVersion
from components.minecraft.utils import times, announce, disable_logging
from components.utils import get_author, send_msg, add_quotes, shorten_string, UserAgent, get_shortened_url, \
    has_transparency, rgb2hex
from config.init_config import Config, BotVars


async def handle_message_for_chat(
        message: Message,
        bot: commands.Bot,
        on_edit=False,
        before_message: Message = None,
        edit_command_content: str = ""
):
    edit_command = len(edit_command_content) != 0
    if message.author.id == bot.user.id or \
            (message.content.startswith(Config.get_settings().bot_settings.prefix) and not edit_command) or \
            str(message.author.discriminator) == "0000" or \
            (len(message.content) == 0 and len(message.attachments) == 0 and len(message.stickers) == 0):
        return

    author = get_author(message, bot, False)

    if not Config.get_game_chat_settings().webhook_url or not BotVars.webhook_chat:
        await send_msg(message.channel, f"{author.mention}, " +
                       get_translation("this chat can't work! Game chat disabled!"), is_reaction=True)
    elif not BotVars.is_server_on:
        await send_msg(message.channel, f"{author.mention}\n" +
                       add_quotes(get_translation("server offline").capitalize() + "!"), is_reaction=True)
    elif BotVars.is_restarting:
        await send_msg(message.channel, f"{author.mention}\n" +
                       add_quotes(get_translation("server is restarting!").capitalize()), is_reaction=True)
    elif BotVars.is_stopping and BotVars.watcher_of_log_file is None:
        await send_msg(message.channel, f"{author.mention}\n" +
                       add_quotes(get_translation("server is stopping!").capitalize()), is_reaction=True)
    elif BotVars.is_loading:
        await send_msg(message.channel, f"{author.mention}\n" +
                       add_quotes(get_translation("server is loading!").capitalize()), is_reaction=True)
    else:
        if get_server_players().get("current") == 0:
            await send_msg(message.channel, f"{author.mention}, " +
                           get_translation("No players on server!").lower(), is_reaction=True)
            return

        server_version = get_server_version()
        reply_from_minecraft_user = None
        if server_version.minor < 7:
            if server_version.minor < 3:
                message_length = 108
            elif 3 <= server_version.minor < 6:
                message_length = 112
            else:
                message_length = 1442
            space = u"\U000e0020"
            result_msg = _clean_message(message, edit_command_content)
            if not edit_command:
                result_msg, reply_from_minecraft_user = await _handle_reply_in_message(message, result_msg)
            result_msg, _ = await _handle_components_in_message(
                result_msg,
                message,
                bot,
                only_replace_links=True,
                version_lower_1_7_2=True
            )
            msg = ""
            if result_msg.get("reply", None) is not None:
                msg += space
                if not reply_from_minecraft_user:
                    result_msg["reply"][1] = result_msg["reply"][1].display_name
                if isinstance(result_msg["reply"][-1], list):
                    msg += "".join(result_msg["reply"][:-1] + ["".join(result_msg["reply"][-1])])
                else:
                    msg += "".join(result_msg["reply"])
            if not edit_command:
                msg += f"<{message.author.display_name}> "
            else:
                msg += f"<{before_message.author.name}> "
            if on_edit:
                msg += "*"
            msg += result_msg["content"]
            if (server_version.minor < 6 and len(msg) <= message_length) or \
                    (server_version.minor == 6 and len(msg.encode()) <= message_length):
                if server_version.minor < 3 and "\n" in msg:
                    messages = [m.strip() for m in msg.split("\n")]
                else:
                    messages = [msg if reply_from_minecraft_user is None else msg[1:]]
            else:
                messages = []
                if server_version.minor < 6:
                    if server_version.minor < 3 and "\n" in msg:
                        for m in msg.split("\n"):
                            if len(m) <= message_length:
                                messages.append(m.strip())
                            else:
                                for m_split in wrap(m, message_length, replace_whitespace=False):
                                    messages.append(m_split)
                    else:
                        for m_split in wrap((msg if reply_from_minecraft_user is None else msg[1:]),
                                            message_length, replace_whitespace=False):
                            messages.append(m_split)
                else:
                    split_line = ""
                    byte_line_length = 0
                    for symb in (msg if reply_from_minecraft_user is None else msg[1:]):
                        byte_line_length += len(symb.encode())
                        if byte_line_length > message_length:
                            messages.append(split_line)
                            split_line = symb
                            byte_line_length = len(symb.encode())
                        else:
                            split_line += symb
                    if len(split_line) > 0:
                        messages.append(split_line)
            with connect_rcon() as cl_r:
                for m in messages:
                    cl_r.say(m if m != "" else space)
        else:
            content_name = "contents" if server_version.minor >= 16 else "value"
            result_msg = _clean_message(message, edit_command_content)
            if not edit_command:
                result_msg, reply_from_minecraft_user = await _handle_reply_in_message(message, result_msg)
            result_msg, images_for_preview = await _handle_components_in_message(
                result_msg,
                message, bot,
                store_images_for_preview=server_version.minor >= 16 and
                                         Config.get_game_chat_settings().image_preview.enable_image_preview
            )
            # Building object for tellraw
            res_obj = [""]
            if result_msg.get("reply", None) is not None:
                if not reply_from_minecraft_user:
                    res_obj += _build_nickname_tellraw_for_discord_member(
                        server_version,
                        result_msg["reply"][1],
                        content_name,
                        brackets_color="gray",
                        left_bracket=result_msg["reply"][0],
                        right_bracket=result_msg["reply"][2]
                    )
                else:
                    res_obj += _build_nickname_tellraw_for_minecraft_player(
                        server_version,
                        result_msg["reply"][1],
                        content_name,
                        default_text_color="gray",
                        left_bracket=result_msg["reply"][0],
                        right_bracket=result_msg["reply"][2]
                    )
                _build_components_in_message(res_obj, content_name, result_msg["reply"][-1], "gray")
            if not edit_command:
                res_obj += _build_nickname_tellraw_for_discord_member(server_version, message.author, content_name)
            else:
                res_obj += _build_nickname_tellraw_for_minecraft_player(server_version,
                                                                        before_message.author.name, content_name)
            if on_edit:
                if before_message is not None:
                    result_before = _clean_message(before_message)
                    result_before, _ = await _handle_components_in_message(
                        result_before,
                        before_message,
                        bot,
                        only_replace_links=True
                    )
                    res_obj.append({"text": "*", "color": "gold",
                                    "hoverEvent": {"action": "show_text",
                                                   content_name: shorten_string(result_before["content"], 250)}})
                else:
                    res_obj.append({"text": "*", "color": "gold"})
            _build_components_in_message(res_obj, content_name, result_msg["content"])
            res_obj = _handle_long_tellraw_object(res_obj)

            with connect_rcon() as cl_r:
                if server_version.minor > 7:
                    for obj in res_obj:
                        cl_r.tellraw("@a", obj)
                else:
                    res = _split_tellraw_object(res_obj)
                    for tellraw in res:
                        cl_r.tellraw("@a", tellraw)

            if server_version.minor > 7:
                nicks = _search_mentions_in_message(message, edit_command)
                if len(nicks) > 0:
                    with suppress(ConnectionError, socket.error):
                        with connect_rcon() as cl_r:
                            with times(0, 60, 20, cl_r):
                                for nick in nicks:
                                    announce(
                                        nick,
                                        f"@{message.author.display_name} "
                                        f"-> @{nick if nick != '@a' else 'everyone'}",
                                        cl_r,
                                        server_version
                                    )

            if len(images_for_preview) > 0:
                emoji_count = len([0 for i in images_for_preview if i.get("type", "") == "emoji"])
                if emoji_count > 0:
                    if len(images_for_preview) == emoji_count:
                        if emoji_count > 1:
                            images_for_preview = images_for_preview[:1]
                    else:
                        images_for_preview = [i for i in images_for_preview if i.get("type", "") != "emoji"]
                for image in images_for_preview:
                    with suppress(UnidentifiedImageError):
                        send_image_to_chat(
                            url=image["url"],
                            image_name=image["name"],
                            required_width=image.get("width", None),
                            required_height=image.get("height", None)
                        )


def _handle_long_tellraw_object(tellraw_obj: list):
    if len(dumps(tellraw_obj)) <= MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
        return [tellraw_obj]

    calc_size = 4
    res = []
    tellraw_obj_length = len(tellraw_obj)
    for e in range(tellraw_obj_length):
        if tellraw_obj[e] == "":
            res += [[""]]
        elif isinstance(tellraw_obj[e], dict):
            calc_size += len(dumps(tellraw_obj[e])) + 2
            if calc_size <= MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH and \
                    not (tellraw_obj_length - e > 1 and any(i in tellraw_obj[e + 1].keys()
                                                            for i in ["insertion", "selector", "hoverEvent"]) and
                         tellraw_obj[e]["text"] == "<" and len(res[-1]) > 1):
                res[-1] += [tellraw_obj[e]]
                continue
            if len(dumps(tellraw_obj[e])) + 4 <= MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
                res += [["", tellraw_obj[e]]]
                calc_size = len(dumps(tellraw_obj[e])) + 6
            else:
                for split_str in tellraw_obj[e]["text"].split("\n"):
                    if split_str == "":
                        continue
                    split_elem = tellraw_obj[e].copy()
                    split_elem["text"] = split_str
                    if len(dumps(split_elem)) + 6 > MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
                        split_array = []
                        split_elem["text"] = ""
                        max_wrap_str_length = MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH - 6 - \
                                              len(dumps(split_elem))
                        wraps = wrap(dumps(split_str)[1:-1], max_wrap_str_length, replace_whitespace=False)
                        wraps_slice = 0
                        for i in range(len(wraps)):
                            if wraps_slice > 0:
                                wraps[i] = f"{wraps[i - 1][-wraps_slice:]}{wraps[i]}"
                                if len(wraps[i]) > max_wrap_str_length:
                                    wraps_slice = len(wraps[i]) - max_wrap_str_length
                                else:
                                    wraps_slice = 0
                            while True:
                                try:
                                    if wraps_slice > 0:
                                        parsed_sliced_str = wraps[i][:-wraps_slice] \
                                            .encode("ascii").decode("unicode-escape")
                                    else:
                                        parsed_sliced_str = wraps[i] \
                                            .encode("ascii").decode("unicode-escape")
                                except (UnicodeDecodeError, SyntaxError):
                                    wraps_slice += 1
                                    continue
                                split_array += [parsed_sliced_str]
                                break
                        if wraps_slice > 0:
                            split_array += [wraps[-1][-wraps_slice:].encode("ascii").decode("unicode-escape")]
                        for split_str_ws in split_array:
                            split_elem = tellraw_obj[e].copy()
                            split_elem["text"] = split_str_ws
                            if len(dumps(res[-1])) + \
                                    len(dumps(split_elem)) + 6 > MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
                                res += [["", split_elem]]
                            else:
                                res[-1] += [split_elem]
                    else:
                        added_split = res[-1].copy()
                        added_dict = added_split[-1].copy()
                        added_dict["text"] += f"\n{split_str}"
                        added_split[-1] = added_dict
                        if len(dumps(added_split)) > MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH:
                            res += [["", split_elem]]
                        else:
                            if res[-1][-1].get("text", "") in ["> ", "*"]:
                                res[-1] += [split_elem]
                            else:
                                res[-1] = added_split
    for elem_res in range(len(res)):
        if elem_res == 0:
            pass
        elif len(res[elem_res][1]["text"].lstrip(" \n")) == 0:
            del res[elem_res][1]
        else:
            res[elem_res][1]["text"] = res[elem_res][1]["text"].lstrip(" \n")
        if len(res[elem_res][-1]["text"].rstrip(" \n")) == 0:
            del res[elem_res][-1]
        else:
            res[elem_res][-1]["text"] = res[elem_res][-1]["text"].rstrip(" \n")
    return res


def _split_tellraw_object(tellraw_obj: Union[list, dict]):
    if not isinstance(tellraw_obj, list):
        tellraw_obj = [tellraw_obj]

    res = []
    for obj in tellraw_obj:
        for elem in obj:
            if elem == "":
                res += [[""]]
            elif isinstance(elem, dict):
                if elem["text"] != "*" and "\n" in elem["text"]:
                    first_elem = True
                    for split_str in elem["text"].split("\n"):
                        split_elem = elem.copy()
                        split_elem["text"] = split_str
                        if first_elem:
                            res[-1] += [split_elem]
                            first_elem = False
                        else:
                            res += [["", split_elem]]
                else:
                    res[-1] += [elem]
    return res


def _clean_message(message: Message, edit_command_content: str = ""):
    result_msg = {}
    if len(edit_command_content) == 0:
        content = message.clean_content.replace("\u200b", "").strip()
    else:
        content = edit_command_content.replace("\u200b", "").strip()
    result_msg["content"] = content
    return result_msg


async def _handle_reply_in_message(message: Message, result_msg: dict) -> Tuple[dict, bool]:
    reply_from_minecraft_user = None
    if message.reference is not None:
        reply_msg = message.reference.resolved
        cnt = reply_msg.clean_content.replace("\u200b", "").strip()
        if reply_msg.author.discriminator == "0000":
            # reply to Minecraft player
            nick = reply_msg.author.display_name
            reply_from_minecraft_user = True
        else:
            # Reply to discord user
            nick = await message.guild.fetch_member(reply_msg.author.id)
            reply_from_minecraft_user = False
        result_msg["reply"] = ["\n -> <", nick, "> ", cnt]
    return result_msg, reply_from_minecraft_user


async def _handle_components_in_message(
        result_msg: dict,
        message: Message,
        bot: commands.Bot,
        only_replace_links=False,
        version_lower_1_7_2=False,
        store_images_for_preview=False
):
    if only_replace_links or version_lower_1_7_2:
        store_images_for_preview = False
    attachments, images_for_preview = _handle_attachments_in_message(message, store_images_for_preview)

    async def repl_emoji(match: str, is_reply: bool):
        obj = search(r"<a?:(?P<name>\w+):(?P<id>\d+)>", match)
        emoji_name = f":{obj.group('name')}:"
        if only_replace_links:
            return emoji_name
        else:
            emoji_id = int(obj.group("id"))
            emoji = bot.get_emoji(emoji_id)
            if emoji is None:
                emoji = utils_get(bot.guilds[0].emojis, id=emoji_id)
            if emoji is None:
                with suppress(NotFound, HTTPException):
                    emoji = await bot.guilds[0].fetch_emoji(emoji_id)
            if isinstance(emoji, Emoji):
                if store_images_for_preview and not is_reply:
                    images_for_preview.append({
                        "type": "emoji",
                        "url": emoji.url,
                        "name": obj.group("name"),
                        "height": 22
                    })
                return {"text": emoji_name, "hyperlink": str(emoji.url)}
            else:
                return emoji_name

    def repl_url(link: str, is_reply: bool):
        is_tenor = bool(search(TENOR_REGEX, link))
        if store_images_for_preview and not is_reply:
            if is_tenor:
                images_for_preview.append({
                    "type": "link",
                    "url": link,
                    "name": ""
                })
            else:
                with suppress(Timeout):
                    resp = req_head(link, timeout=(3, 6), headers={"User-Agent": UserAgent.get_header()})
                    if resp.status_code == 200 and resp.headers.get("content-length") is not None and \
                            int(resp.headers.get("content-length")) <= 20971520:
                        # Checks if Content-Length not larger than 20 MB
                        if resp.headers.get("content-type") is None or \
                                (resp.headers.get("content-type") is not None and
                                 "image" in resp.headers.get("content-type")):
                            images_for_preview.append({
                                "type": "link",
                                "url": link,
                                "name": ""
                            })
        if only_replace_links:
            if version_lower_1_7_2:
                if is_tenor:
                    return "[gif]"
                elif len(link) > 30:
                    return get_shortened_url(link)
                else:
                    return link
            else:
                return "[gif]" if is_tenor else shorten_string(link, 30)
        else:
            return {
                "text": "[gif]" if is_tenor else shorten_string(link, 30),
                "hyperlink": link if len(link) < 257 else get_shortened_url(link)
            }

    transformations = {
        EMOJI_REGEX: repl_emoji,
        URL_REGEX: repl_url
    }
    mass_regex = "|".join(transformations.keys())

    async def repl(obj, is_reply: bool):
        match = obj.group(0)
        if search(URL_REGEX, match):
            return transformations.get(URL_REGEX)(match, is_reply)
        else:
            return await transformations.get(EMOJI_REGEX)(match, is_reply)

    for key, ms in result_msg.items():
        if isinstance(ms, list):
            msg = ms.copy()
            msg = msg[-1]
        else:
            msg = ms

        temp_split = []
        if search(mass_regex, msg):
            temp_split = split(mass_regex, msg)
            i = 1
            for m in compile(mass_regex).finditer(msg):
                temp_split.insert(i, (await repl(m, key == "reply")))
                i += 2
        else:
            temp_split.append(msg)

        if attachments.get(key, None) is not None and len(attachments[key]) > 0:
            for i in attachments[key]:
                t_string = [t["text"] if isinstance(t, dict) else t for t in temp_split]
                if len("".join(t_string)) != 0:
                    if isinstance(temp_split[-1], str):
                        temp_split[-1] += " "
                    else:
                        temp_split.append(" ")
                if only_replace_links:
                    temp_split.append(i["text"])
                else:
                    temp_split.append(i)

        if key == "reply":
            if isinstance(temp_split[-1], dict):
                temp_split.append("\n")
            else:
                temp_split[-1] += "\n"

        temp_split = [s for s in temp_split if (isinstance(s, str) and len(s) > 0) or not isinstance(s, str)]

        if isinstance(ms, list):
            result_msg[key] = [ms[0], ms[1], ms[2], "".join(temp_split) if only_replace_links else temp_split]
        else:
            result_msg[key] = "".join(temp_split) if only_replace_links else temp_split
    return result_msg, images_for_preview


def _handle_attachments_in_message(message: Message, store_images_for_preview=False):
    attachments = {}
    messages = [message]
    images_for_preview: List[Dict[str, Union[str, int]]] = []
    if message.reference is not None:
        messages.append(message.reference.resolved)
    for i in range(len(messages)):
        stickers = messages[i].stickers
        if len(stickers) != 0 or len(messages[i].attachments) != 0:
            if i == 0:
                attachments["content"] = []
                iattach = attachments["content"]
            else:
                attachments["reply"] = []
                iattach = attachments["reply"]
            if len(stickers) != 0:
                for sticker in stickers:
                    iattach.append({
                        "text": sticker.name,
                        "hyperlink": sticker.url if len(sticker.url) < 257 else get_shortened_url(sticker.url)
                    })
                    if store_images_for_preview and i == 0:
                        images_for_preview.append({
                            "type": "sticker",
                            "url": sticker.url,
                            "name": sticker.name
                        })
            if len(messages[i].attachments) != 0:
                for attachment in messages[i].attachments:
                    need_hover = True
                    if "." in attachment.filename:
                        a_type = f"[{attachment.filename.split('.')[-1]}]"
                    elif attachment.content_type is not None and \
                            any(i in attachment.content_type for i in ["image", "video", "audio"]):
                        a_type = f"[{attachment.content_type.split('/')[-1]}]"
                    else:
                        need_hover = False
                        a_type = f"[{shorten_string(attachment.filename, max_length=20)}]"
                    iattach.append({
                        "text": a_type,
                        "hyperlink": attachment.url if len(attachment.url) < 257 else get_shortened_url(attachment.url)
                    })
                    if need_hover:
                        iattach[-1].update({"hover": attachment.filename})
                    if store_images_for_preview and i == 0 and \
                            attachment.content_type is not None and "image" in attachment.content_type:
                        images_for_preview.append({
                            "type": "image",
                            "url": attachment.url,
                            "name": attachment.filename
                        })
    return attachments, images_for_preview


def _build_components_in_message(res_obj: list, content_name: str, obj, default_text_color: str = None):
    if isinstance(obj, list):
        for elem in obj:
            if isinstance(elem, dict):
                if "text" not in elem.keys():
                    raise KeyError(f"'text' key not in dict {elem}!")
                if default_text_color is not None:
                    res_obj.append({"text": elem["text"], "color": default_text_color})
                else:
                    res_obj.append({"text": elem["text"]})
                if "hover" in elem.keys():
                    res_obj[-1].update({"hoverEvent": {"action": "show_text",
                                                       content_name: shorten_string(elem["hover"], 250)}})
                if "hyperlink" in elem.keys():
                    res_obj[-1].update({"underlined": True, "color": "blue",
                                        "clickEvent": {"action": "open_url", "value": elem["hyperlink"]}})
            elif isinstance(elem, str):
                if default_text_color is not None:
                    res_obj.append({"text": elem, "color": default_text_color})
                else:
                    res_obj.append({"text": elem})
    else:
        if default_text_color is not None:
            res_obj.append({"text": obj, "color": default_text_color})
        else:
            res_obj.append({"text": obj})


def _search_mentions_in_message(message: Message, edit_command=False) -> set:
    if len(message.mentions) == 0 and len(message.role_mentions) == 0 and \
            not message.mention_everyone and message.reference is None and "@" not in message.content:
        return set()

    nicks = []
    if message.mention_everyone:
        nicks.append("@a")
    else:
        # Check role, user mentions and reply author mention
        members_from_roles = list(chain(*[i.members for i in message.role_mentions]))
        if message.reference is not None and not edit_command:
            if message.reference.resolved.author.discriminator != "0000":
                members_from_roles.append(message.reference.resolved.author)
            else:
                nicks.append(message.reference.resolved.author.name)
        members_from_roles.extend(message.mentions)
        members_from_roles = set(members_from_roles)
        for member in members_from_roles:
            if member.id in [i.user_discord_id for i in Config.get_known_users_list()]:
                nicks.extend([i.user_minecraft_nick for i in Config.get_known_users_list()
                              if i.user_discord_id == member.id])
        server_players = get_server_players().get("players")
        # Check @'minecraft_nick' mentions
        if "@" in message.content:
            seen_players = [i.player_minecraft_nick for i in Config.get_server_config().seen_players]
            seen_players.extend(server_players)
            seen_players = set(seen_players)
            for mc_nick in seen_players:
                if search(rf"@{mc_nick}", message.content):
                    nicks.append(mc_nick)
        nicks = set(nicks)
        # Remove nicks' mentions from author of the initial message
        if message.author.id in [i.user_discord_id for i in Config.get_known_users_list()]:
            for nick in [i.user_minecraft_nick for i in Config.get_known_users_list()
                         if i.user_discord_id == message.author.id]:
                if nick in nicks:
                    nicks.remove(nick)
        # Check if players online
        nicks = [i for i in nicks if i in server_players]
    return set(nicks)


def _build_nickname_tellraw_for_minecraft_player(
        server_version: ServerVersion,
        nick: str,
        content_name: str,
        default_text_color: str = None,
        left_bracket: str = "<",
        right_bracket: str = "> "
):
    tellraw_obj = [{"text": left_bracket}]
    if server_version.minor > 7 and len(nick.split()) == 1 and nick in get_server_players().get("players"):
        tellraw_obj += [{"selector": f"@p[name={nick}]"}]
    elif server_version.minor > 7:
        if "☠ " in nick and \
                check_if_string_in_all_translations(translate_text="☠ Obituary ☠", match_text=nick):
            entity = get_translation("Entity")
        else:
            entity = get_translation("Player")
        hover_string = f"{nick}\n" + get_translation("Type: {0}").format(entity) + f"\n{Config.get_offline_uuid(nick)}"
        tellraw_obj += [{
            "text": nick,
            "clickEvent": {"action": "suggest_command", "value": f"/tell {nick} "},
            "hoverEvent": {"action": "show_text", content_name: hover_string}
        }]
    else:
        tellraw_obj += [{
            "text": nick,
            "clickEvent": {"action": "suggest_command", "value": f"/tell {nick} "},
            "hoverEvent": {"action": "show_text", content_name: f"{nick}\n{Config.get_offline_uuid(nick)}"}
        }]
    tellraw_obj += [{"text": right_bracket}]
    if default_text_color is not None:
        for i in range(len(tellraw_obj)):
            tellraw_obj[i]["color"] = default_text_color
    return tellraw_obj


def _build_nickname_tellraw_for_discord_member(
        server_version: 'ServerVersion',
        author: Member,
        content_name: str,
        brackets_color: str = None,
        left_bracket: str = "<",
        right_bracket: str = "> "
):
    hover_string = ["", {"text": f"{author.display_name}\n"
                                 f"{author.name}#{author.discriminator}"}]
    if server_version.minor > 11:
        hover_string[-1]["text"] += "\nShift + "
        hover_string += [{"keybind": "key.attack"}]
    tellraw_obj = [
        {"text": left_bracket},
        {"text": author.display_name,
         "color": "dark_gray",
         "hoverEvent": {"action": "show_text", content_name: hover_string}},
        {"text": right_bracket}
    ]
    if server_version.minor > 7:
        tellraw_obj[-2].update({"insertion": f"@{author.display_name}"})
    if brackets_color is not None:
        for i in range(len(tellraw_obj)):
            if len(tellraw_obj[i].keys()) == 1:
                tellraw_obj[i]["color"] = brackets_color
    return tellraw_obj


def build_nickname_tellraw_for_bot(
        server_version: ServerVersion,
        nick: str,
        left_bracket: str = "<",
        right_bracket: str = "> "
) -> List[Dict[str, str]]:
    content_name = "contents" if server_version.minor >= 16 else "value"
    tellraw_obj = [{"text": left_bracket}]
    if server_version.minor > 7:
        hover_string = f"{nick}\n" + get_translation("Type: {0}").format(get_translation("Entity")) + \
                       f"\n{Config.get_offline_uuid(nick)}"
        tellraw_obj += [{
            "text": nick,
            "color": "dark_gray",
            "hoverEvent": {"action": "show_text", content_name: hover_string}
        }]
    else:
        tellraw_obj += [{
            "text": nick,
            "color": "dark_gray",
            "hoverEvent": {"action": "show_text", content_name: f"{nick}\n{Config.get_offline_uuid(nick)}"}
        }]
    tellraw_obj += [{"text": right_bracket}]
    return tellraw_obj


def get_image_data(url: str):
    if search(r"https?://tenor\.com/view", url):
        with suppress(Timeout):
            text = req_get(url, timeout=(4, 8), headers={"User-Agent": UserAgent.get_header()}).text
            match = search(rf"property=\"og:image\"\scontent=\"(?P<link>{URL_REGEX})?\"", text)
            url = match.group("link") if match is not None else None

    if url is not None:
        match = search(r"[^/]+/(?P<name>[^/\\&?]+\.\w{3,4})(?:[/?&].*$|$)", url)
        if match is not None:
            filename = match.group("name")
        else:
            filename = url.split("/")[-1].split("?", maxsplit=1)[0]
        filename = unquote(filename)
        with suppress(Timeout):
            return dict(
                bytes=BytesIO(req_get(url, timeout=(4, 8), headers={"User-Agent": UserAgent.get_header()}).content),
                name=filename
            )


def send_image_to_chat(url: str, image_name: str, required_width: int = None, required_height: int = None):
    image_data = get_image_data(url)
    if image_data is None:
        return

    if len(image_name) == 0:
        image_name = image_data["name"] if len(image_data["name"]) else "unknown"
    img = Image.open(image_data["bytes"], "r")

    if required_height is not None and \
            required_height < Config.get_game_chat_settings().image_preview.max_height:
        max_height = required_height
    else:
        max_height = Config.get_game_chat_settings().image_preview.max_height

    if required_width is not None and \
            required_width < Config.get_game_chat_settings().image_preview.max_width:
        calc_width = required_height
    else:
        calc_width = Config.get_game_chat_settings().image_preview.max_width

    calc_height = int(round((img.height * 2) / (img.width / calc_width), 0) / 9)
    if calc_height > max_height:
        calc_width = int((calc_width * max_height) / calc_height)
        calc_height = max_height
    img = img.resize((calc_width if calc_width > 0 else 1, calc_height if calc_height > 0 else 1))

    img_has_transparency = has_transparency(img)
    if img_has_transparency and img.mode != "RGBA":
        img = img.convert("RGBA")
    elif not img_has_transparency and img.mode != "RGB":
        img = img.convert("RGB")

    pixels = img.load()
    width, height = img.size

    storage_unit = "mc_chat"

    with disable_logging(disable_log_admin_commands=True, disable_send_command_feedback=True):
        with suppress(ConnectionError, socket.error):
            with connect_rcon() as cl_r:
                max_number_of_arrays = 0
                for y in range(height):
                    tellraw = [
                        {
                            "text": "",
                            "clickEvent": {"action": "open_url",
                                           "value": url if len(url) < 257 else get_shortened_url(url)},
                            "hoverEvent": {"action": "show_text", "contents": shorten_string(image_name, 250)}
                        }
                    ]
                    array_count = 0
                    tellraw_str_length = len(dumps(tellraw, ensure_ascii=False))
                    for x in range(width):
                        if img_has_transparency:
                            r, g, b, a = pixels[x, y]
                            if a < 20:
                                pixel = {"text": "·", "color": rgb2hex(r, g, b)}
                            elif 20 <= a <= 70:
                                pixel = {"text": ":", "color": rgb2hex(r, g, b)}
                            else:
                                pixel = {"text": "┇", "color": rgb2hex(r, g, b)}
                        else:
                            pixel = {"text": "┇", "color": rgb2hex(*pixels[x, y])}
                        pixel_str = len(dumps(pixel, ensure_ascii=False)) + 2

                        if len(f"data modify storage {storage_unit} {array_count + 1} set value ''") + \
                                tellraw_str_length + pixel_str > MAX_RCON_COMMAND_RUN_STR_LENGTH:
                            array_count += 1
                            cl_r.run(f"data modify storage {storage_unit} {array_count} "
                                     f"set value '{dumps(tellraw, ensure_ascii=False)}'")
                            tellraw = [pixel]
                            tellraw_str_length = pixel_str
                        else:
                            tellraw.append(pixel)
                            tellraw_str_length += pixel_str
                    if len(tellraw) > 0:
                        array_count += 1
                        cl_r.run(f"data modify storage {storage_unit} {array_count} "
                                 f"set value '{dumps(tellraw, ensure_ascii=False)}'")
                    cl_r.tellraw("@a", [
                        {"nbt": str(i), "storage": storage_unit, "interpret": True}
                        for i in range(1, array_count + 1)
                    ])
                    if max_number_of_arrays < array_count + 1:
                        max_number_of_arrays = array_count
                for number in range(1, max_number_of_arrays + 1):
                    cl_r.run(f"data remove storage {storage_unit} {number}")
