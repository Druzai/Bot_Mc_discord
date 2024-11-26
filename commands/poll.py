import datetime as dt
from asyncio import sleep as asleep
from contextlib import suppress
from datetime import datetime
from enum import Enum, auto
from typing import Union, Optional

from discord import (
    Status, Role, NotFound, Forbidden, HTTPException, DMChannel, Member, InvalidData, TextChannel,
    GroupChannel, Thread, Interaction, User, Poll as DiscordPoll, ClientException, RawPollVoteActionEvent, Message
)
from discord.abc import Messageable
from discord.enums import ButtonStyle
from discord.ext import commands
from discord.ext.commands import Context
from discord.ui import button, Button, View

from components.additional_funcs import handle_unhandled_error_in_events, send_msg
from components.localization import get_translation


class Poll(commands.Cog):
    _polls = {}
    _emoji_symbols = {"yes": "☑", "no": "❎"}
    _await_date = {}

    def __init__(self, bot: commands.Bot, create_pot_lines=False):
        self._bot: commands.Bot = bot
        for command in ["clear", "stop", "backup_remove", "backup_remove_all"]:
            self._await_date[command] = datetime.now()

    async def run(
            self,
            channel: Union[Member, TextChannel, GroupChannel, DMChannel, Thread],
            command: str,
            message: str = None,
            need_for_voting=2,
            needed_role: int = None,
            timeout=3600,
            remove_logs_after=None,
            admin_needed=False,
            add_mention=True,
            add_votes_count=True,
            poll_message: str = None
    ):
        if message is None and poll_message is None:
            raise ValueError("'message' and 'poll_message' is not stated!")
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
            start_msg = await channel.send(
                content=(f"{mention}, " if add_mention else "") +
                        (f"{message} " if message is not None else "") +
                        (get_translation("To win the poll needed {0} vote(s)!").format(str(need_for_voting))
                         if add_votes_count else "")
            )
        current_poll = PollContent(channel, command, need_for_voting, needed_role, remove_logs_after, admin_needed)
        poll_msg = await self.make_poll(channel, timeout, current_poll, poll_message)
        self._polls[poll_msg.id] = current_poll
        seconds = 0
        while current_poll.state == States.NONE:
            await asleep(1)
            seconds += 1
            if current_poll.poll.is_finalised() or timeout <= seconds:
                current_poll.cancel()
        if not current_poll.poll.is_finalised():
            with suppress(ClientException, HTTPException):
                await current_poll.poll.end()
        if start_msg is not None:
            with suppress(NotFound, Forbidden, HTTPException):
                await start_msg.delete()

        async def del_poll():
            await asleep(10)
            with suppress(KeyError):
                del self._polls[poll_msg.id]

        self._bot.loop.create_task(del_poll())
        if current_poll.state == States.CANCELED:
            poll_res = "`" + get_translation("Poll result: canceled!") + "`"
        else:
            poll_res = get_translation("granted") if current_poll.state == \
                                                     States.GRANTED else get_translation("refused")
            poll_res = "`" + get_translation("Poll result: permission {0}!").format(poll_res) + "`"
        await channel.send(poll_res, delete_after=remove_logs_after)
        with suppress(NotFound, Forbidden, HTTPException):
            await poll_msg.delete(delay=remove_logs_after)
        return None if current_poll.state == States.CANCELED else current_poll.state == States.GRANTED

    async def make_poll(
            self,
            channel: Messageable,
            duration_seconds: int,
            poll_content: 'PollContent',
            poll_message: str = None
    ):
        poll = DiscordPoll(
            question=get_translation("Voting!") if poll_message is None else poll_message,
            duration=dt.timedelta(seconds=duration_seconds if duration_seconds >= 3600 else 3600)
        )
        poll.add_answer(text=get_translation("yes").capitalize(), emoji=self._emoji_symbols["yes"])
        poll.add_answer(text=get_translation("no").capitalize(), emoji=self._emoji_symbols["no"])
        msg = await channel.send(poll=poll)
        poll_content.set_discord_poll(poll)
        return msg

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        with handle_unhandled_error_in_events():
            if message.author == self._bot.user and message.reference is not None \
                    and message.reference.message_id in self._polls:
                if self._polls[message.reference.message_id].RLA is not None:
                    await message.delete(delay=self._polls[message.reference.message_id].RLA)
                del self._polls[message.reference.message_id]

    @commands.Cog.listener()
    async def on_raw_poll_vote_add(self, payload: RawPollVoteActionEvent):
        with handle_unhandled_error_in_events():
            if payload.message_id not in self._polls or payload.user_id == self._bot.user.id:
                return
            channel = self._bot.get_channel(payload.channel_id)
            if channel is None:
                with suppress(InvalidData, HTTPException, NotFound, Forbidden):
                    channel = await self._bot.fetch_channel(payload.channel_id)
            current_poll: PollContent = self._polls[payload.message_id]
            if isinstance(channel, DMChannel):
                user = await self._bot.fetch_user(payload.user_id)
            else:
                user = await self._bot.guilds[0].fetch_member(payload.user_id)
            answer = current_poll.poll.get_answer(payload.answer_id)
            if answer is not None:
                await current_poll.count_add_voice(
                    channel,
                    user,
                    self._emoji_symbols["yes" if answer.emoji.name == self._emoji_symbols["yes"] else "no"],
                    answer.emoji.name == self._emoji_symbols["yes"]
                )

    @commands.Cog.listener()
    async def on_raw_poll_vote_remove(self, payload: RawPollVoteActionEvent):
        with handle_unhandled_error_in_events():
            if payload.message_id not in self._polls or payload.user_id == self._bot.user.id:
                return
            current_poll: PollContent = self._polls[payload.message_id]
            channel = self._bot.get_channel(payload.channel_id)
            if channel is None:
                with suppress(InvalidData, HTTPException, NotFound, Forbidden):
                    channel = await self._bot.fetch_channel(payload.channel_id)
            if isinstance(channel, DMChannel):
                user = await self._bot.fetch_user(payload.user_id)
            else:
                user = await self._bot.guilds[0].fetch_member(payload.user_id)
            answer = current_poll.poll.get_answer(payload.answer_id)
            if answer is not None:
                await current_poll.count_del_voice(channel, user, answer.emoji.name == self._emoji_symbols["yes"])

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload):
        with handle_unhandled_error_in_events():
            if payload.message_id in self.get_polls().keys():
                self.get_polls()[payload.message_id].cancel()

    async def timer(self, ctx: Union[Context, Interaction], author: Union[Member, User], seconds: int, command: str):
        if (datetime.now() - self._await_date[command]).seconds > seconds:  # Starting a poll
            self._await_date[command] = datetime.now()
            return True
        else:
            await send_msg(
                ctx,
                f"{author.mention}, " +
                get_translation("what are you doing? Time hasn't passed yet. Waiting {0} sec...")
                .format((datetime.now() - self._await_date[command]).seconds),
                is_reaction=True
            )
            return False

    def get_polls(self):
        return self._polls


class States(Enum):
    NONE = auto()
    GRANTED = auto()
    REFUSED = auto()
    CANCELED = auto()


class PollContent:
    def __init__(
            self,
            channel: Messageable,
            command: str,
            need_for_voting=2,
            needed_role: Role = None,
            remove_logs_after=0,
            admin_needed=False
    ):
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
        self.poll: Optional[DiscordPoll] = None

    def set_discord_poll(self, poll: DiscordPoll):
        self.poll = poll

    async def count_add_voice(self, channel: Union[Messageable, Interaction], user: Member, emoji: str, to_left: bool):
        if self.state is not States.NONE:
            await send_msg(
                channel,
                f"{user.mention}, " + get_translation("poll have already finished!"),
                delete_delay=self.RLA
            )
            return False
        if user.id in self.poll_voted_uniq.keys():
            await send_msg(
                channel,
                f"{user.mention}, " + get_translation("you've already voted!"),
                delete_delay=self.RLA
            )
            return False
        if not self.AN and self.NR and self.NR.id not in (e.id for e in user.roles):
            await send_msg(
                channel,
                f"{user.mention}, " + get_translation("you don't have needed '{0}' role").format(self.NR.name),
                delete_delay=self.RLA
            )
            return False
        if self.AN and self.NR and self.NR.id not in (e.id for e in user.roles) and \
                not user.guild_permissions.administrator:
            if self.NR != "":
                await send_msg(
                    channel,
                    f"{user.mention}, " + get_translation("you don't have needed '{0}' role").format(self.NR.name),
                    delete_delay=self.RLA
                )
            await send_msg(
                channel,
                f"{user.mention}, " + get_translation("you don't have permission 'Administrator'"),
                delete_delay=self.RLA
            )
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

    async def count_del_voice(self, channel: Union[Messageable, Interaction], user: Member, to_left: bool):
        if self.state is not States.NONE:
            await send_msg(
                channel,
                f"{user.mention}, " + get_translation("poll have already finished!"),
                delete_delay=self.RLA
            )
            return
        if self.NR and self.NR.id not in (e.id for e in user.roles):
            await send_msg(
                channel,
                f"{user.mention}, " + get_translation("you don't have needed '{0}' role").format(self.NR.name),
                delete_delay=self.RLA
            )
            return
        self.poll_voted_uniq.pop(user.id)
        if to_left:
            self.poll_yes -= 1
        else:
            self.poll_no -= 1

    def cancel(self):
        self.state = States.CANCELED
