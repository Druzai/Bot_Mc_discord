import sys
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from random import randint, choice
from threading import Thread
from typing import List, Optional, Union, AsyncIterator
from zipfile import ZipFile

from PIL import Image
from aiohttp import ClientSession
from discord import (
    Message, Status, NotFound, HTTPException, Forbidden, TextChannel, VoiceChannel, Thread as ChannelThread,
    GroupChannel, InvalidData, Interaction, Client, Role, ChannelType
)
from discord.abc import Messageable
from discord.ext import commands
from discord.ui import View
from discord.utils import get as utils_get, _get_mime_type_for_image, MISSING
from psutil import process_iter, NoSuchProcess, Process, AccessDenied
from requests import post as req_post, Timeout

from components.constants import UNITS, ANSI_ESCAPE
from components.localization import get_translation
from config.init_config import Config, BotVars, OS


# For Discord
async def send_msg(ctx: Union[Messageable, Interaction], msg: str, view: View = MISSING, is_reaction=False):
    if isinstance(ctx, Interaction):
        message = await send_interaction(ctx, msg, view=view, is_reaction=is_reaction)
    else:
        message = await ctx.send(
            content=msg,
            view=view,
            delete_after=(Config.get_timeouts_settings().await_seconds_before_message_deletion if is_reaction else None)
        )
    return message


async def send_interaction(
        interaction: Optional[Interaction],
        msg: str,
        view: View = MISSING,
        ctx: Messageable = None,
        ephemeral=False,
        is_reaction=False
):
    message = None
    try:
        if interaction is None or interaction.is_expired():
            raise ValueError()

        if interaction.response.is_done():
            message = await interaction.followup.send(msg, view=view, ephemeral=ephemeral, wait=True)
        else:
            await interaction.response.send_message(msg, view=view, ephemeral=ephemeral)
            message = await interaction.original_response()

        if is_reaction:
            await message.delete(delay=Config.get_timeouts_settings().await_seconds_before_message_deletion)
    except (NotFound, HTTPException, ValueError):
        if ctx is None and interaction is not None:
            ctx = interaction.channel
        if ctx is not None:
            if view == MISSING:
                view = None
            message = await ctx.send(
                content=msg,
                view=view,
                delete_after=(Config.get_timeouts_settings().await_seconds_before_message_deletion
                              if is_reaction else None)
            )
    return message


async def edit_interaction(interaction: Optional[Interaction], view: View, message_id: int):
    if interaction.is_expired():
        return

    if interaction.response.is_done():
        await interaction.followup.edit_message(message_id, view=view)
    else:
        await interaction.response.edit_message(view=view)


def add_quotes(msg: str) -> str:
    return f"```{msg}```"


async def delete_after_by_msg(
        message: Union[Message, int],
        ctx: Union[commands.Context, Interaction] = None,
        without_delay: bool = False
):
    if isinstance(message, Message):
        await message.delete(
            delay=Config.get_timeouts_settings().await_seconds_before_message_deletion if not without_delay else None
        )
    elif isinstance(message, int) and ctx is not None:
        channel = ctx.channel
        if channel is not None:
            await (await channel.fetch_message(message)).delete(
                delay=(Config.get_timeouts_settings().await_seconds_before_message_deletion
                       if not without_delay else None)
            )


def get_author(
        ctx: Union[commands.Context, Message, TextChannel, VoiceChannel, ChannelThread, GroupChannel, Interaction],
        bot: Union[commands.Bot, Client],
        is_reaction=False
):
    if is_reaction:
        author = BotVars.react_auth
    else:
        if hasattr(ctx, "author"):
            author = ctx.author
        elif hasattr(ctx, "user"):
            author = ctx.user
        else:
            author = bot.user
    return author


def get_bot_display_name(bot: commands.Bot):
    for member in bot.guilds[0].members:
        if member.id == bot.user.id:
            return member.display_name
    return bot.user.display_name


def get_half_members_count_with_role(channel: TextChannel, role: int):
    count = 0
    for m in channel.members:
        if not m.bot and m.status != Status.offline:
            if role:
                if role in (e.id for e in m.roles):
                    count += 1
            else:
                count += 1
    if count < 2:
        return count
    return count // 2


async def get_member_string(bot: commands.Bot, id: int, mention: bool = False):
    try:
        member = bot.guilds[0].get_member(id)
        if member is None:
            member = await bot.guilds[0].fetch_member(id)
        if not mention:
            member = f"{member.display_name}#{member.discriminator}"
        else:
            member = member.mention
    except (HTTPException, Forbidden, NotFound):
        try:
            user = await bot.fetch_user(id)
            if not mention:
                member = f"{user.name}#{user.discriminator}"
            else:
                member = user.mention
        except (HTTPException, NotFound):
            member = f"{'@' if mention else ''}invalid-user"
    return member


async def get_channel_string(bot: commands.Bot, id: int, mention: bool = False):
    try:
        channel = bot.get_channel(id)
        if channel is None:
            channel = await bot.fetch_channel(id)
        if not mention:
            channel = channel.name
        else:
            channel = channel.mention
    except (InvalidData, HTTPException, NotFound, Forbidden):
        channel = f"{'#' if mention else ''}deleted-channel"
    return channel


async def get_role_string(bot: Union[commands.Bot, Client], id: int, mention: bool = False):
    try:
        role = bot.guilds[0].get_role(id)
        if role is None:
            role = utils_get(await bot.guilds[0].fetch_roles(), id=id)
            if role is None:
                raise ValueError()
        if not mention:
            role = role.name
        else:
            role = role.mention
    except (HTTPException, ValueError):
        role = f"{'@' if mention else ''}deleted-role"
    return role


async def get_message_and_channel(bot: Union[commands.Bot, Client], message_id: int, channel_id: Optional[int] = None):
    if channel_id is None:
        for ch in bot.guilds[0].channels:
            sub_chs = [ch]
            if hasattr(ch, "threads"):
                sub_chs.extend(ch.threads)
            for sub_ch in sub_chs:
                if isinstance(sub_ch, (TextChannel, VoiceChannel, Thread)):
                    with suppress(NotFound, Forbidden, HTTPException):
                        message = await sub_ch.fetch_message(message_id)
                        return message, sub_ch
        return None, None
    else:
        with suppress(NotFound, Forbidden, HTTPException, InvalidData):
            channel = await bot.fetch_channel(channel_id)
            message = await channel.fetch_message(message_id)
            return message, channel
        return None, None


def get_commands_channel():
    channel = BotVars.bot_for_webhooks.guilds[0] \
        .get_channel(Config.get_settings().bot_settings.commands_channel_id)
    if channel is None:
        channel = utils_get(BotVars.bot_for_webhooks.guilds[0].channels, type=ChannelType.text)
    return channel


def get_members_nicks_of_the_role(role: Role, mention_nicks: list):
    for member in role.members:
        possible_user = [u.user_minecraft_nick for u in Config.get_settings().known_users
                         if member.id == u.user_discord_id]
        if len(possible_user) != 0:
            mention_nicks.extend(possible_user)
    return mention_nicks


async def send_status(ctx: Union[commands.Context, Interaction], is_reaction=False):
    if BotVars.is_server_on:
        if BotVars.is_backing_up:
            await send_msg(ctx, add_quotes(get_translation("Bot is backing up server!")), is_reaction=is_reaction)
        else:
            await send_msg(ctx, add_quotes(get_translation("server have already started!").capitalize()),
                           is_reaction=is_reaction)
    else:
        if BotVars.is_backing_up:
            await send_msg(ctx, add_quotes(get_translation("Bot is backing up server!")), is_reaction=is_reaction)
        elif BotVars.is_restoring:
            await send_msg(ctx, add_quotes(get_translation("Bot is restoring server from backup!")),
                           is_reaction=is_reaction)
        elif BotVars.is_loading:
            await send_msg(ctx, add_quotes(get_translation("server is loading!").capitalize()), is_reaction=is_reaction)
        elif BotVars.is_stopping:
            await send_msg(ctx, add_quotes(get_translation("server is stopping!").capitalize()),
                           is_reaction=is_reaction)
        else:
            await send_msg(ctx, add_quotes(get_translation("server have already been stopped!").capitalize()),
                           is_reaction=is_reaction)


# Functions for processes
def get_list_of_processes() -> List[Process]:
    for p in BotVars.java_processes:
        if not p.is_running():
            renew_list = True
            break
    else:
        renew_list = True
    if not renew_list:
        return BotVars.java_processes

    list_proc = []
    for proc in process_iter():
        with proc.oneshot():
            with suppress(NoSuchProcess, AccessDenied):
                if "java" in proc.name() and Config.get_selected_server_from_list().working_directory == proc.cwd():
                    list_proc.append(proc)
    BotVars.java_processes = list_proc
    return list_proc


def kill_server():
    list_proc = get_list_of_processes()
    if len(list_proc) != 0:
        for p in list_proc:
            with suppress(NoSuchProcess, AccessDenied):
                p.kill()


# File system
def get_folder_size(*path: str) -> int:
    return sum(p.stat().st_size for p in Path(*path).rglob('*'))


def get_file_size(*path: str) -> int:
    return Path(*path).stat().st_size


def get_archive_uncompressed_size(*path: str):
    total_uncompressed = 0
    with ZipFile(Path(*path)) as z:
        for info in z.infolist():
            total_uncompressed += info.file_size
    return total_uncompressed


def get_human_readable_size(size: Union[int, float], stop_unit=None, round=False):
    human_radix = 1024.
    for u in UNITS[:-1]:
        if size < human_radix or stop_unit == get_translation(u):
            if round:
                return f"{int(size)} {get_translation(u)}"
            else:
                return f"{size:.2f} {get_translation(u)}"
        size /= human_radix

    if round:
        return f"{int(size)} {get_translation(UNITS[-1])}"
    else:
        return f"{size:.2f} {get_translation(UNITS[-1])}"


# Network
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
            version = f"{randint(70, 99)}.{randint(0, 99)}.{randint(0, 9999)}.{randint(0, 999)}"
            cls._header = f"Mozilla/5.0 ({cls._get_os()}) AppleWebKit/537.36 " \
                          f"(KHTML, like Gecko) Chrome/{version} Safari/537.36"
        else:
            # Firefox
            version = f"{randint(78, 102)}.0"
            cls._header = f"Mozilla/5.0 ({cls._get_os()}; rv:{version}) Gecko/20100101 Firefox/{version}"

    @classmethod
    def get_header(cls):
        if cls._header is None:
            cls._set_header()
        return cls._header


def get_shortened_url(url: str):
    for service_url in ["https://clck.ru/--", "https://tinyurl.com/api-create.php"]:
        with suppress(Timeout):
            response = req_post(
                service_url,
                params={"url": url},
                timeout=(3, 6),
                headers={"User-Agent": UserAgent.get_header()}
            )
            if response.ok and response.text != "":
                return response.text
    print(get_translation("Bot couldn't shorten the URL \"{0}\" using link shortening services.").format(url))
    return url[:256]


async def get_avatar_info(ctx: commands.Context, url: Optional[str]):
    avatar_blob = None
    avatar_url = None
    if url is not None:
        avatar_url = url
        async with ClientSession(timeout=30) as session:
            async with session.get(url=url) as response:
                avatar_blob = await response.read()
                try:
                    _get_mime_type_for_image(avatar_blob)
                except ValueError:
                    avatar_blob = None
    if avatar_blob is None:
        for attachment in ctx.message.attachments:
            avatar_file = await attachment.to_file()
            avatar_url = attachment.url
            avatar_blob = avatar_file.fp.read()
            try:
                _get_mime_type_for_image(avatar_blob)
                break
            except ValueError:
                avatar_blob = None
    return avatar_blob, avatar_url


# Misc
def make_underscored_line(line: Union[int, float, str]):
    """This func underscores int, float or strings without spaces!"""
    underscore = "\u0332"
    if isinstance(line, int) or isinstance(line, float):
        return underscore + underscore.join(str(line))
    elif isinstance(line, str):
        return underscore.join(line) + underscore


def get_time_string(seconds: int, use_colon=False):
    sec_str = get_translation(" sec")
    if seconds == 0:
        return f"{seconds}{sec_str}"
    elif use_colon:
        if seconds // 60 != 0:
            return f"{seconds // 60}:{(seconds % 60):02d}"
        else:
            return f"{seconds}{sec_str}"
    else:
        min_str = get_translation(" min")
        return ("" if seconds // 60 == 0 else f"{str(seconds // 60)}{min_str}") + \
               (" " if seconds > 59 and seconds % 60 != 0 else "") + \
               ("" if seconds % 60 == 0 else f"{str(seconds % 60)}{sec_str}")


def get_number_of_digits(number: int):
    count = 0
    while number > 0:
        number //= 10
        count += 1
    return count


def shorten_string(string: str, max_length: int):
    if len(string) > max_length:
        return f"{string[:max_length - 3].strip(' ')}..."
    else:
        return string


def rgb2hex(r, g, b):
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def has_transparency(img: Image.Image):
    if img.info.get("transparency", None) is not None:
        return True
    if img.mode == "P":
        transparent = img.info.get("transparency", -1)
        for _, index in img.getcolors():
            if index == transparent:
                return True
    elif img.mode == "RGBA":
        extrema = img.getextrema()
        if extrema[3][0] < 255:
            return True

    return False


def func_name(func_number: int = 1):
    return sys._getframe(func_number).f_code.co_name


async def get_last_element_of_async_iterator(async_iterator: AsyncIterator):
    last_element = None
    while True:
        try:
            last_element = await async_iterator.__anext__()
        except StopAsyncIteration:
            return last_element


def setup_print_handlers():
    if Config.get_settings().bot_settings.log_bot_messages:
        file = open(Config.get_bot_log_name(), "a", encoding="utf8")
    else:
        file = None
    StdoutHandler(file)
    if file is not None:
        StderrHandler(file)


class StdoutHandler:
    def __init__(self, file=None):
        self.file = file
        self.stdout = sys.stdout
        sys.stdout = self

    def __del__(self):
        sys.stdout = self.stdout
        if self.file is not None:
            self.file.close()

    def write(self, data, **kwargs):
        if data != "\n":
            if self.file is not None:
                self.file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                                f"{ANSI_ESCAPE.sub('', data)}")
            self.stdout.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {data}")
        else:
            if self.file is not None:
                self.file.write(data)
            self.stdout.write(data)
        self.flush()
        if kwargs.pop('flush', False):
            self.stdout.flush()

    def flush(self):
        if self.file is not None:
            self.file.flush()


class StderrHandler:
    def __init__(self, file=None):
        self.file = file
        self.stderr = sys.stderr
        sys.stderr = self

    def __del__(self):
        sys.stderr = self.stderr
        if self.file is not None:
            self.file.close()

    def write(self, data, **kwargs):
        if self.file is not None:
            self.file.write(data)
        self.stderr.write(data)
        self.flush()
        if kwargs.pop('flush', False):
            self.stderr.flush()

    def flush(self):
        if self.file is not None:
            self.file.flush()
