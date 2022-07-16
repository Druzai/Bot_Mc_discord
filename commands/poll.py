from asyncio import sleep as asleep
from contextlib import suppress
from datetime import datetime
from enum import Enum, auto
from typing import Union

from discord import (
    Color, Embed, Status, Role, NotFound, Forbidden, HTTPException, DMChannel, Member, InvalidData, TextChannel,
    GroupChannel, RawReactionActionEvent
)
from discord.abc import Messageable
from discord.ext import commands

from components.additional_funcs import handle_unhandled_error_in_events
from components.localization import get_translation
from config.init_config import Config


class Poll(commands.Cog):
    _polls = {}
    _emoji_symbols = {"yes": "☑", "no": "❎"}
    _await_date = {}

    def __init__(self, bot: commands.Bot):
        self._bot: commands.Bot = bot
        for command in ["clear", "stop", "backup_del", "backup_del_all"]:
            self._await_date[command] = datetime.now()

    async def run(self, channel: Union[Member, TextChannel, GroupChannel, DMChannel], command: str, message: str = None,
                  need_for_voting=2, needed_role: int = None, timeout=60 * 60, remove_logs_after=None,
                  admin_needed=False, add_mention=True, add_votes_count=True, embed_message: str = None):
        if message is None and embed_message is None:
            raise ValueError("'message' and 'embed_message' is not stated!")
        if not isinstance(channel, Member) and not isinstance(channel, DMChannel):
            if isinstance(channel, GroupChannel):
                members_count = len([m for m in channel.recipients if not m.bot])
            else:
                members_count = len([m for m in channel.members if not m.bot and m.status != Status.offline])
            if members_count < need_for_voting:
                need_for_voting = members_count
        else:
            if need_for_voting > 1:
                need_for_voting = 1
        mention = "@everyone"
        if needed_role is not None:
            needed_role = self._bot.guilds[0].get_role(needed_role)
            if needed_role is not None:
                mention = needed_role.mention
        start_msg = None
        if add_votes_count or add_mention or message is not None:
            start_msg = await channel.send((f"{mention}, " if add_mention else "") +
                                           (f"{message} " if message is not None else "") +
                                           (get_translation("To win the poll needed {0} vote(s)!")
                                            .format(str(need_for_voting)) if add_votes_count else ""))
        poll_msg = await self.make_embed(channel, embed_message)
        current_poll = PollContent(channel, command, need_for_voting, needed_role, remove_logs_after, admin_needed)
        self._polls[poll_msg.id] = current_poll
        seconds = 0
        while current_poll.state == States.NONE:
            await asleep(1)
            seconds += 1
            if timeout <= seconds:
                current_poll.cancel()
        if start_msg is not None:
            with suppress(NotFound, Forbidden, HTTPException):
                await start_msg.delete()
        del self._polls[poll_msg.id]
        if current_poll.state == States.CANCELED:
            poll_res = "`" + get_translation("Poll result: canceled!") + "`"
        else:
            poll_res = get_translation("granted") if current_poll.state == \
                                                     States.GRANTED else get_translation("refused")
            poll_res = "`" + get_translation("Poll result: permission {0}!").format(poll_res) + "`"
        try:
            await poll_msg.edit(content=poll_res, embed=None)
            await poll_msg.delete(delay=remove_logs_after)
        except (NotFound, Forbidden, HTTPException):
            await channel.send(poll_res, delete_after=remove_logs_after)
        return None if current_poll.state == States.CANCELED else current_poll.state == States.GRANTED

    async def make_embed(self, channel: Messageable, embed_message: str = None):
        emb = Embed(title=get_translation("Survey. Voting!") if embed_message is None else embed_message,
                    color=Color.orange())
        emb.add_field(name=get_translation("yes"), value=self._emoji_symbols.get("yes"))
        emb.add_field(name=get_translation("no"), value=self._emoji_symbols.get("no"))
        add_reactions_to = await channel.send(embed=emb)
        for emote in self._emoji_symbols.values():
            await add_reactions_to.add_reaction(emote)
        return add_reactions_to

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent):
        with handle_unhandled_error_in_events():
            if payload.message_id not in self._polls or \
                    (payload.member is not None and payload.member.id == self._bot.user.id) or \
                    (payload.member is None and payload.user_id == self._bot.user.id):
                return
            channel = self._bot.get_channel(payload.channel_id)
            if channel is None:
                with suppress(InvalidData, HTTPException, NotFound, Forbidden):
                    channel = await self._bot.fetch_channel(payload.channel_id)
            current_poll = self._polls[payload.message_id]
            emoji = self._emoji_symbols["yes" if payload.emoji.name == self._emoji_symbols["yes"] else "no"]
            if payload.member is None:
                if isinstance(channel, DMChannel):
                    user = await self._bot.fetch_user(payload.user_id)
                else:
                    user = await self._bot.guilds[0].fetch_member(payload.user_id)
            else:
                user = payload.member
            if payload.emoji.name not in self._emoji_symbols.values() \
                    or not await current_poll.count_add_voice(channel, user, emoji,
                                                              payload.emoji.name == self._emoji_symbols["yes"]):
                message = await channel.fetch_message(payload.message_id)
                await message.remove_reaction(payload.emoji, user)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: RawReactionActionEvent):
        with handle_unhandled_error_in_events():
            if payload.message_id not in self._polls or \
                    (payload.member is not None and payload.member.id == self._bot.user.id) or \
                    (payload.member is None and payload.user_id == self._bot.user.id):
                return
            current_poll = self._polls[payload.message_id]
            if payload.emoji.name not in [v for k, v in current_poll.poll_voted_uniq.items() if k == payload.user_id]:
                return
            channel = self._bot.get_channel(payload.channel_id)
            if channel is None:
                with suppress(InvalidData, HTTPException, NotFound, Forbidden):
                    channel = await self._bot.fetch_channel(payload.channel_id)
            if payload.member is None:
                if isinstance(channel, DMChannel):
                    user = await self._bot.fetch_user(payload.user_id)
                else:
                    user = await self._bot.guilds[0].fetch_member(payload.user_id)
            else:
                user = payload.member
            await current_poll.count_del_voice(channel, user, payload.emoji.name == self._emoji_symbols["yes"])

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        with handle_unhandled_error_in_events():
            if payload.message_id in self.get_polls().keys():
                self.get_polls()[payload.message_id].cancel()

    async def timer(self, ctx, seconds: int, command: str):
        if (datetime.now() - self._await_date[command]).seconds > seconds:  # Starting a poll
            self._await_date[command] = datetime.now()
            return True
        else:
            await ctx.send(f"{ctx.author.mention}, " +
                           get_translation("what are you doing? Time hasn't passed yet. Waiting {0} sec...")
                           .format((datetime.now() - self._await_date[command]).seconds),
                           delete_after=Config.get_timeouts_settings().await_seconds_before_message_deletion)
            return False

    def get_polls(self):
        return self._polls


class States(Enum):
    NONE = auto()
    GRANTED = auto()
    REFUSED = auto()
    CANCELED = auto()


class PollContent:
    def __init__(self, channel: Messageable, command: str, need_for_voting=2, needed_role: Role = None,
                 remove_logs_after=0, admin_needed=False):
        self.poll_yes = 0
        self.poll_no = 0
        self.poll_voted_uniq = {}
        self.channel = channel
        self.NFW = need_for_voting
        self.NR = needed_role
        self.RLA = remove_logs_after
        self.state = States.NONE
        self.command = command
        self.AN = admin_needed

    async def count_add_voice(self, channel: Messageable, user: Member, emoji: str, to_left: bool):
        if self.state is not States.NONE:
            await channel.send(f"{user.mention}, " + get_translation("poll've already finished!"),
                               delete_after=self.RLA)
            return False
        if user.id in self.poll_voted_uniq.keys():
            await channel.send(f"{user.mention}, " + get_translation("you've already voted!"),
                               delete_after=self.RLA)
            return False
        if not self.AN and self.NR and self.NR.id not in (e.id for e in user.roles):
            await channel.send(f"{user.mention}, " +
                               get_translation("you don't have needed '{0}' role").format(self.NR.name),
                               delete_after=self.RLA)
            return False
        if self.AN and self.NR and self.NR.id not in (e.id for e in user.roles) and \
                not user.guild_permissions.administrator:
            if self.NR != "":
                await channel.send(f"{user.mention}, " +
                                   get_translation("you don't have needed '{0}' role").format(self.NR.name),
                                   delete_after=self.RLA)
            await channel.send(f"{user.mention}, " +
                               get_translation("you don't have permission 'Administrator'"),
                               delete_after=self.RLA)
            return False
        self.poll_voted_uniq.update({user.id: emoji})
        if to_left:
            self.poll_yes += 1
        else:
            self.poll_no += 1
        if self.poll_yes >= self.NFW:
            self.state = States.GRANTED
        elif self.poll_no >= self.NFW:
            self.state = States.REFUSED
        return True

    async def count_del_voice(self, channel: Messageable, user: Member, to_left: bool):
        if self.state is not States.NONE:
            await channel.send(f"{user.mention}, " + get_translation("poll've already finished!"),
                               delete_after=self.RLA)
            return
        if self.NR and self.NR.id not in (e.id for e in user.roles):
            await channel.send(f"{user.mention}, " +
                               get_translation("you don't have needed '{0}' role").format(self.NR.name),
                               delete_after=self.RLA)
            return
        self.poll_voted_uniq.pop(user.id)
        if to_left:
            self.poll_yes -= 1
        else:
            self.poll_no -= 1

    def cancel(self):
        self.state = States.CANCELED
