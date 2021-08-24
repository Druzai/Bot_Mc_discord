from ast import literal_eval
from asyncio import sleep as asleep
from contextlib import contextmanager
from datetime import datetime
from hashlib import md5
from json import load, dump, JSONDecodeError
from os import chdir, system
from os.path import basename
from pathlib import Path
from random import choice, randint
from re import search, split, findall
from string import ascii_letters, digits
from sys import platform, argv

from discord import Activity, ActivityType
from discord.ext import commands
from mcipc.query import Client as Client_q
from mcipc.rcon import Client as Client_r
from psutil import process_iter, NoSuchProcess
from requests import post as req_post

from components.watcher_handle import create_watcher
from config.init_config import Config, BotVars

if platform == "win32":
    from os import startfile


async def send_msg(ctx, msg, is_reaction=False):
    if is_reaction:
        await ctx.send(content=msg,
                       delete_after=Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
    else:
        await ctx.send(msg)


async def delete_after_by_msg_id(ctx, message_id):
    await asleep(Config.get_awaiting_times_settings().await_seconds_before_message_deletion)
    msg = await ctx.channel.fetch_message(message_id)
    await msg.delete()


def get_author_and_mention(ctx, bot, is_reaction=False):
    if is_reaction:
        author_mention = BotVars.react_auth.mention
        author = BotVars.react_auth
    else:
        if hasattr(ctx, 'author'):
            author_mention = ctx.author.mention
            author = ctx.author
        else:
            author_mention = bot.user.mention
            author = bot.user
    return author, author_mention


async def send_status(ctx, is_reaction=False):
    if BotVars.is_server_on:
        await send_msg(ctx, "```Server have already started!```", is_reaction)
    else:
        if BotVars.is_loading:
            await send_msg(ctx, "```Server is loading!```", is_reaction)
        elif BotVars.is_stopping:
            await send_msg(ctx, "```Server is stopping!```", is_reaction)
        else:
            await send_msg(ctx, "```Server have already been stopped!```", is_reaction)


async def start_server(ctx, bot, shut_up=False, is_reaction=False):
    BotVars.is_loading = True
    print("Loading server")
    if ctx and not shut_up:
        await send_msg(ctx, "```Loading server.......\nPlease wait)```", is_reaction)
    chdir(Config.get_selected_server_from_list().working_directory)
    try:
        if platform == "linux" or platform == "linux2":
            if ".sh" not in Config.get_selected_server_from_list().start_file_name:
                raise NameError()
            system("screen -dmS " + Config.get_selected_server_from_list().server_name.replace(" ", "_") +
                   " ./" + Config.get_selected_server_from_list().start_file_name)
        elif platform == "win32":
            if ".bat" not in Config.get_selected_server_from_list().start_file_name:
                raise NameError()
            startfile(Config.get_selected_server_from_list().start_file_name)
        BotVars.server_start_time = int(datetime.now().timestamp())
    except BaseException:
        print("Couldn't open script! Check naming and extension of the script!")
        await send_msg(ctx, "```Couldn't open script because of naming! Retreating...```", is_reaction)
        BotVars.is_loading = False
        if BotVars.is_restarting:
            BotVars.is_restarting = False
        return
    chdir(Config.get_bot_config_path())
    await asleep(5)
    check_time = datetime.now()
    while True:
        if len(get_list_of_processes()) == 0:
            await send_msg(ctx, "```Error while loading server```", is_reaction)
            await bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                        name=Config.get_settings().bot_settings.idle_status))
            BotVars.is_loading = False
            if BotVars.is_restarting:
                BotVars.is_restarting = False
            return
        timedelta_secs = (datetime.now() - check_time).seconds
        if Config.get_selected_server_from_list().server_loading_time:
            percentage = round((timedelta_secs / Config.get_selected_server_from_list().server_loading_time) * 100)
            output_bot = "Loading: " + ((str(percentage) + "%") if percentage < 101 else "100%...")
        else:
            output_bot = "Server, elapsed time: " + (
                str(timedelta_secs // 60) + ":" + f"{(timedelta_secs % 60):02d}" if timedelta_secs // 60 != 0 else str(
                    timedelta_secs % 60) + " sec")
        await bot.change_presence(activity=Activity(type=ActivityType.listening, name=output_bot))
        await asleep(Config.get_awaiting_times_settings().await_seconds_when_connecting_via_rcon)
        try:
            with Client_q(Config.get_settings().bot_settings.local_address,
                          BotVars.port_query, timeout=0.5) as cl_q:
                _ = cl_q.basic_stats
            break
        except BaseException:
            pass
    if Config.get_cross_platform_chat_settings().enable_cross_platform_chat and \
            Config.get_cross_platform_chat_settings().channel_id and \
            Config.get_cross_platform_chat_settings().webhook_url:
        create_watcher()
        BotVars.watcher_of_log_file.start()
    if Config.get_selected_server_from_list().server_loading_time:
        Config.get_selected_server_from_list().server_loading_time = \
            (Config.get_selected_server_from_list().server_loading_time + (datetime.now() - check_time).seconds) // 2
    else:
        Config.get_selected_server_from_list().server_loading_time = (datetime.now() - check_time).seconds
    Config.save_config()
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
    if ctx and not shut_up:
        await send_msg(ctx, author_mention + "\n```Server's on now```", is_reaction)
        print("Server on!")
        if randint(0, 8) == 0:
            await send_msg(ctx, "Kept you waiting, huh?", is_reaction)
    BotVars.is_loading = False
    BotVars.is_server_on = True
    if BotVars.is_restarting:
        BotVars.is_restarting = False
    Config.get_server_config().states.started_info.date = datetime.now().strftime("%d/%m/%y, %H:%M:%S")
    Config.get_server_config().states.started_info.user = str(author)
    Config.save_server_config()
    await bot.change_presence(activity=Activity(type=ActivityType.playing,
                                                name=Config.get_settings().bot_settings.gaming_status))


async def stop_server(ctx, bot, how_many_sec=10, is_restart=False, is_reaction=False):
    BotVars.is_stopping = True
    no_connection = False
    print("Stopping server")
    await send_msg(ctx, "```Stopping server.......\nPlease wait " + str(how_many_sec) + " sec.```", is_reaction)
    try:
        with Client_r(Config.get_settings().bot_settings.local_address, BotVars.port_rcon, timeout=1) as cl_r:
            cl_r.login(BotVars.rcon_pass)
            if how_many_sec != 0:
                w = 1
                if how_many_sec > 5:
                    while True:
                        w += 1
                        if how_many_sec % w == 0 and w <= 10:
                            break
                        elif how_many_sec % w == 0 and w > 10:
                            how_many_sec += 1
                            w = 1
                if not is_restart:
                    cl_r.say('Server\'s shutting down in ' + str(how_many_sec) + ' seconds')
                else:
                    cl_r.say('Server\'s restarting in ' + str(how_many_sec) + ' seconds')
                for i in range(how_many_sec, -1, -w):
                    cl_r.say(str(i) + ' sec to go')
                    await asleep(w)
            cl_r.run("stop")
    except BaseException:
        if len(get_list_of_processes()) == 0:
            print("Exception: Couldn't connect to server, because it's stopped")
            await send_msg(ctx, "Couldn't connect to server to shut it down! Server stopped...", is_reaction)
            BotVars.is_stopping = False
            BotVars.is_server_on = False
            return
        no_connection = True

    if not no_connection:
        if BotVars.watcher_of_log_file.is_running():
            BotVars.watcher_of_log_file.stop()
        while True:
            await asleep(Config.get_awaiting_times_settings().await_seconds_when_connecting_via_rcon)
            try:
                with Client_q(Config.get_settings().bot_settings.local_address,
                              BotVars.port_query, timeout=0.5) as cl_q:
                    _ = cl_q.basic_stats
            except BaseException:
                break
    else:
        print("Exception: Couldn't connect to server, so killing it now...")
        await send_msg(ctx, "Couldn't connect to server to shut it down! Killing it now...", is_reaction)
    kill_server()
    BotVars.is_stopping = False
    BotVars.is_server_on = False
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
    print("Server's off now")
    await send_msg(ctx, author_mention + "\n```Server's off now```", is_reaction)
    Config.get_server_config().states.stopped_info.date = datetime.now().strftime("%d/%m/%y, %H:%M:%S")
    Config.get_server_config().states.stopped_info.user = str(author)
    Config.save_server_config()
    await bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                name=Config.get_settings().bot_settings.idle_status))


def get_list_of_processes() -> list:
    basename_of_executable = basename(argv[0])
    process_name = "java"
    list_proc = []

    for proc in process_iter():
        try:
            parents_name_list = [i.name() for i in proc.parents()]
            if process_name in proc.name() and ("screen" in parents_name_list or
                                                basename_of_executable in parents_name_list or
                                                "python.exe" in parents_name_list) \
                    and abs(int(proc.create_time()) - BotVars.server_start_time) < 5:
                list_proc.append(proc)
        except NoSuchProcess:
            pass
    return list_proc


def kill_server():
    list_proc = get_list_of_processes()
    if len(list_proc) != 0:
        for p in list_proc:
            try:
                p.kill()
            except NoSuchProcess:
                pass
    BotVars.server_start_time = None


async def server_checkups(bot, always=True):
    while True:
        try:
            with Client_q(Config.get_settings().bot_settings.local_address,
                          BotVars.port_query, timeout=1) as cl_q:
                info = cl_q.full_stats
            if info.num_players != 0:
                nicks_n_keys_add = {}
                for i in info.players:
                    i = i.lower()
                    if i not in Config.read_op_keys().keys():
                        nicks_n_keys_add.update({i: [generate_access_code() for _ in range(25)]})
                if nicks_n_keys_add:
                    print("New codes generated")
                    for k, v in nicks_n_keys_add.items():
                        print("For player with nickname " + k + " generated these codes:")
                        for c in v:
                            print("\t" + c)
                    orig_op = Config.read_op_keys()
                    orig_op.update(nicks_n_keys_add)
                    Config.save_op_keys(orig_op)
                    orig_op.clear()
            if not BotVars.is_server_on:
                BotVars.is_server_on = True
            if Config.get_cross_platform_chat_settings().enable_cross_platform_chat and \
                    Config.get_cross_platform_chat_settings().channel_id and \
                    Config.get_cross_platform_chat_settings().webhook_url:
                create_watcher()
                BotVars.watcher_of_log_file.start()
            number_match = findall(r", \d+", bot.guilds[0].get_member(bot.user.id).activities[0].name)
            if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 0 or info.num_players != 0 or \
                    (len(number_match) > 0 and number_match[0].split(" ")[-1] != 0):
                await bot.change_presence(activity=Activity(type=ActivityType.playing,
                                                            name=Config.get_settings().bot_settings.gaming_status + ", "
                                                                 + str(info.num_players) + " player(s) online"))
        except BaseException:
            if len(get_list_of_processes()) == 0:
                if BotVars.is_server_on:
                    BotVars.is_server_on = False
                if BotVars.watcher_of_log_file is not None and BotVars.watcher_of_log_file.is_running():
                    BotVars.watcher_of_log_file.stop()
            if bot.guilds[0].get_member(bot.user.id).activities[0].type.value != 2:
                await bot.change_presence(activity=Activity(type=ActivityType.listening,
                                                            name=Config.get_settings().bot_settings.idle_status +
                                                                 (" thinking..." if len(
                                                                     get_list_of_processes()) != 0 else "")))
            if always and Config.get_settings().bot_settings.forceload and not BotVars.is_stopping \
                    and not BotVars.is_loading and not BotVars.is_restarting:
                sent = False
                for guild in bot.guilds:
                    if sent:
                        break
                    for channel in guild.channels:
                        try:
                            await channel.fetch_message(Config.get_settings().bot_settings.menu_id)
                            await send_msg(ctx=channel,
                                           msg='```Bot detected: Server\'s offline!\n'
                                               f'Time: {datetime.now().strftime("%d/%m/%y, %H:%M:%S")}\n'
                                               'Starting up server again!```',
                                           is_reaction=True)
                            await start_server(ctx=channel, bot=bot, shut_up=True)
                            sent = True
                            break
                        except BaseException:
                            pass
        if Config.get_awaiting_times_settings().await_seconds_in_check_ups > 0 and always:
            await asleep(Config.get_awaiting_times_settings().await_seconds_in_check_ups)
        if not always:
            break


def generate_access_code(length=16, sep='-', sep_interval=4) -> str:
    """Генератор кодов доступа
    Частота повторений символов вариативная для кода
    в пределах от 1 к 2, до 1 к 1000
    :param length: Длинна кода в символах, без учёта разделителей
    :param sep: Символ разделитель внутри кода, для читаемости
    :param sep_interval: Шаг раздела, 0 для отключения разделения
    :return: Код доступа
    """
    alphabet = digits + ascii_letters
    code = ''
    duplicate_chance = randint(1, 1000)
    for i in range(length):
        if i and sep_interval and not i % sep_interval:
            code += sep
        candidate_symbol = choice(alphabet)
        while candidate_symbol in code and randint(0, duplicate_chance):
            candidate_symbol = choice(alphabet)
        code += candidate_symbol
    return code


def get_offline_uuid(username):
    data = bytearray(md5(("OfflinePlayer:" + username).encode()).digest())
    data[6] &= 0x0f  # clear version
    data[6] |= 0x30  # set to version 3
    data[8] &= 0x3f  # clear variant
    data[8] |= 0x80  # set to IETF variant
    uuid = data.hex()
    return '-'.join((uuid[:8], uuid[8:12], uuid[12:16], uuid[16:20], uuid[20:]))


def get_whitelist_entry(username):
    return dict(name=username, uuid=get_offline_uuid(username))


def save_to_whitelist_json(entry: dict):
    whitelist = [entry]
    filepath = Path(Config.get_selected_server_from_list().working_directory + "/whitelist.json")
    if filepath.is_file():
        try:
            with open(filepath, "r", encoding="utf8") as file:
                whitelist = load(file)
                whitelist.append(entry)
        except JSONDecodeError:
            pass
    with open(filepath, "w", encoding="utf8") as file:
        dump(whitelist, file)


def get_server_online_mode():
    filepath = Path(Config.get_selected_server_from_list().working_directory + "/server.properties")
    if not filepath.exists():
        raise RuntimeError(f"File '{filepath.as_posix()}' doesn't exist!")
    with open(filepath, "r") as f:
        for i in f.readlines():
            if i.find("online-mode") >= 0:
                return literal_eval(i.split("=")[1].capitalize())


# Handling errors
async def send_error(ctx, bot, error, is_reaction=False):
    author, author_mention = get_author_and_mention(ctx, bot, is_reaction)
    if isinstance(error, commands.MissingRequiredArgument):
        print(f'{author} не указал аргумент')
        await send_msg(ctx, f'{author_mention}, пожалуйста, введи все аргументы', is_reaction)
    elif isinstance(error, commands.MissingPermissions):
        print(f'У {author} мало прав для команды')
        await send_msg(ctx, f'{author_mention}, у вас недостаточно прав для выполнения этой команды',
                       is_reaction)
    elif isinstance(error, commands.MissingRole):
        print(f'У {author} нет роли "{error.missing_role}" для команды')
        await send_msg(ctx,
                       f'{author_mention}, у вас нет роли "{error.missing_role}" для выполнения этой команды',
                       is_reaction)
    elif isinstance(error, commands.CommandNotFound):
        print(f'{author} ввёл несуществующую команду')
        await send_msg(ctx, f'{author_mention}, вы ввели несуществующую команду', is_reaction)
    elif isinstance(error, commands.UserInputError):
        print(f'{author} неправильно ввёл аргумент(ы) команды')
        await send_msg(ctx, f'{author_mention}, вы неправильно ввели агрумент(ы) команды', is_reaction)
    elif isinstance(error, commands.DisabledCommand):
        print(f'{author} ввёл отключённую команду')
        await send_msg(ctx, f'{author_mention}, вы ввели отлючённую команду', is_reaction)
    elif isinstance(error, commands.NoPrivateMessage):
        print(f'{author} ввёл комманду, работающую только в гильдии')
        await send_msg(ctx, f'{author_mention}, введённая команда работает только на сервере', is_reaction)
    else:
        print(", ".join(error.args))
        await send_msg(ctx, ", ".join(error.original.args), is_reaction)


async def handle_message_for_chat(message, bot, need_to_delete_on_error: bool, on_edit=False, before_message=None):
    if message.author == bot.user or message.content.startswith(Config.get_settings().bot_settings.prefix) or str(
            message.author.discriminator) == "0000" or (len(message.content) == 0 and len(message.attachments) == 0) \
            or message.channel.id != int(Config.get_cross_platform_chat_settings().channel_id):
        return

    _, author_mention = get_author_and_mention(message, bot, False)
    delete_user_message = True

    if not Config.get_cross_platform_chat_settings().channel_id or \
            not Config.get_cross_platform_chat_settings().webhook_url:
        await send_msg(message.channel, f"{author_mention}, this chat can't work! Cross platform chat disabled!", True)
    elif not BotVars.is_server_on:
        await send_msg(message.channel, f"{author_mention}, server offline!", True)
    elif BotVars.is_restarting:
        await send_msg(message.channel, f"{author_mention}, server is restarting!", True)
    elif BotVars.is_stopping and BotVars.watcher_of_log_file is None:
        await send_msg(message.channel, f"{author_mention}, server is stopping!", True)
    elif BotVars.is_loading:
        await send_msg(message.channel, f"{author_mention}, server is loading!", True)
    else:
        result_msg = _handle_custom_emojis(message)
        result_msg = await _handle_reply_in_message(message, result_msg)
        result_msg = _handle_urls_and_attachments_in_message(result_msg, message)

        # Building object for tellraw
        res_obj = ["", {"text": "<"}, {"text": message.author.display_name, "color": "dark_gray"},
                   {"text": "> "}]
        if result_msg.get("reply", None) is not None:
            if isinstance(result_msg.get("reply"), list):
                res_obj.extend([{"text": result_msg.get("reply")[0], "color": "gray"},
                                {"text": result_msg.get("reply")[1], "color": "dark_gray"}])
                _build_if_urls_in_message(res_obj, result_msg.get("reply")[2], "gray")
            else:
                _build_if_urls_in_message(res_obj, result_msg.get("reply"), "gray")
        if on_edit:
            result_before = _handle_custom_emojis(before_message)
            result_before = _handle_urls_and_attachments_in_message(result_before, before_message, True)
            if float(get_server_version()) >= 1.16:
                res_obj.append({"text": "*", "color": "gold",
                                "hoverEvent": {"action": "show_text", "contents": result_before.get("content")}})
            else:
                res_obj.append({"text": "*", "color": "gold",
                                "hoverEvent": {"action": "show_text", "value": result_before.get("content")}})
        _build_if_urls_in_message(res_obj, result_msg.get("content"), None)

        with Client_r(Config.get_settings().bot_settings.local_address, BotVars.port_rcon, timeout=1) as cl_r:
            cl_r.login(BotVars.rcon_pass)
            answ = cl_r.tellraw("@a", res_obj)
            # TODO: Replace with checking via query num of players for localization!

        if answ == '':
            delete_user_message = False
            nicks = _search_mentions_in_message(message)
            if len(nicks) > 0:
                try:
                    with Client_r(Config.get_settings().bot_settings.local_address,
                                  BotVars.port_rcon, timeout=1) as cl_r:
                        cl_r.login(BotVars.rcon_pass)
                        with times(500, 2500, 1500, cl_r):
                            for nick in nicks:
                                announce(nick,
                                         f"@{message.author.display_name} -> @{nick if nick != '@a' else 'everyone'}",
                                         cl_r)
                except BaseException:
                    pass
        else:
            await send_msg(message.channel, f"{author_mention}, {answ.lower()}!", True)

    if delete_user_message and need_to_delete_on_error:
        await delete_after_by_msg_id(message, message.id)


def _handle_custom_emojis(message):
    result_msg = {}
    content = message.clean_content
    if search(r"<:\w+:\d+>", content.replace("​", "").strip()):
        temp_split = split(r"<:\w+:\d+>", content.replace("​", "").strip())
        temp_arr = list(findall(r"<:\w+:\d+>", content.replace("​", "").strip()))
        i = 1
        for emoji in temp_arr:
            temp_split.insert(i, findall(r"\w+", emoji)[0])
            i += 2
        result_msg["content"] = "".join(temp_split)
    else:
        result_msg["content"] = content.replace("​", "").strip()
    return result_msg


async def _handle_reply_in_message(message, result_msg):
    if message.reference is not None:
        reply_msg = message.reference.resolved
        cnt = reply_msg.clean_content.strip()
        cnt = cnt.replace("​", "")
        if reply_msg.author.discriminator == "0000":
            # reply to minecraft player
            cnt = cnt.replace("**<", "<").replace(">**", ">")
            result_msg["reply"] = f"\n -> {cnt}"
        else:
            # Reply to discord user
            nick = (await message.guild.fetch_member(reply_msg.author.id)).display_name
            result_msg["reply"] = ["\n -> <", nick, f"> {cnt}"]
    return result_msg


def _handle_urls_and_attachments_in_message(result_msg, message, only_replace_links=False):
    attachments = _handle_attachments_in_message(message)
    for key, ms in result_msg.items():
        if isinstance(ms, list):
            msg = ms.copy()
            msg = msg[-1]
        else:
            msg = ms

        temp_split = []
        url_regex = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+'
        if search(url_regex, msg):
            temp_split = split(url_regex, msg)
            temp_arr = list(findall(url_regex, msg))
            i = 1
            for link in temp_arr:
                if only_replace_links:
                    temp_split.insert(i,
                                      shorten_url(link, 30) if "tenor" not in link and "view" not in link else "[gif]")
                else:
                    temp_split.insert(i,
                                      (shorten_url(link, 30) if "tenor" not in link and "view" not in link else "[gif]",
                                       link if len(link) < 257 else get_clck_ru_url(link)))
                i += 2
        else:
            temp_split.append(msg)

        if attachments.get(key, None) is not None and len(attachments[key]) > 0:
            for i in attachments[key]:
                if (key == "content" and len("".join(temp_split)) != 0) or \
                        (key == "reply" and "".join(temp_split) != "> "):
                    temp_split.append(" ")
                if only_replace_links:
                    temp_split.append(i[0])
                else:
                    temp_split.append(i)

        if key == "reply":
            temp_split.append("\n")

        if isinstance(ms, list):
            result_msg[key] = [ms[0], ms[1], "".join(temp_split) if only_replace_links else temp_split]
        else:
            result_msg[key] = "".join(temp_split) if only_replace_links else temp_split
    return result_msg


def _handle_attachments_in_message(message):
    attachments = {}
    messages = [message]
    if message.reference is not None:
        messages.append(message.reference.resolved)
    for i in range(len(messages)):
        if len(messages[i].attachments) != 0:
            if i == 0:
                attachments["content"] = []
                iattach = attachments["content"]
            else:
                attachments["reply"] = []
                iattach = attachments["reply"]
            for attachment in messages[i].attachments:
                if attachment.content_type is None:
                    a_type = "[file]"
                else:
                    if "image" in attachment.content_type:
                        if "image/gif" in attachment.content_type:
                            a_type = "[gif]"
                        else:
                            a_type = "[img]"
                    elif "video" in attachment.content_type or "audio" in attachment.content_type:
                        a_type = f"[{attachment.content_type.split('/')[-1]}]"
                    else:
                        a_type = "[file]"
                iattach.append((a_type,
                                attachment.url if len(attachment.url) < 257 else get_clck_ru_url(attachment.url)))
    return attachments


def _build_if_urls_in_message(res_obj, obj, default_text_color):
    if isinstance(obj, list):
        for elem in obj:
            if isinstance(elem, tuple):
                res_obj.append({"text": elem[0], "underlined": True, "color": "blue",
                                "clickEvent": {"action": "open_url", "value": elem[1]}})
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


def _search_mentions_in_message(message) -> list:
    if len(message.mentions):
        return []

    players_nicks_from_discord = [i.display_name if i.display_name else i.name for i in message.mentions]
    nicks = []
    if message.mention_everyone:
        nicks.append("@a")
    else:
        for nick in players_nicks_from_discord:
            if nick in get_server_players():
                nicks.append(nick)
    return nicks


def get_server_version() -> str:
    with Client_q(Config.get_settings().bot_settings.local_address, BotVars.port_query, timeout=1) as cl_r:
        version = cl_r.full_stats.version
    return version


def get_server_players() -> tuple:
    with Client_q(Config.get_settings().bot_settings.local_address, BotVars.port_query, timeout=1) as cl_r:
        players = cl_r.full_stats.players
    return players


def shorten_url(url: str, max_length: int):
    if len(url) > max_length:
        return url[:max_length] + "..."
    else:
        return url


def get_clck_ru_url(url: str):
    return req_post("https://clck.ru/--", params={"url": url}).text


@contextmanager
def times(fade_in, duration, fade_out, rcon_client):
    rcon_client.run(f"title @a times {fade_in} {duration} {fade_out}")
    yield
    rcon_client.run("title @a reset")


def announce(player, message, rcon_client):
    if float(get_server_version()) >= 1.11:
        rcon_client.run(f'title {player} actionbar ' + '{' + f'"text":"{message}"' + ',"bold":true,"color":"gold"}')
    else:
        rcon_client.run(f'title {player} title ' + '{"text":" "}')
        rcon_client.run(f'title {player} subtitle ' + '{' + f'"text":"{message}"' + ',"color":"gold"}')
    rcon_client.run(play_sound(player, "minecraft:entity.arrow.hit_player", "player", 1, 0.75))


def play_sound(name, sound, category="master", volume=1, pitch=1.0):
    return f"/execute as {name} at @s run playsound {sound} {category} @s ~ ~ ~ {volume} {pitch} 1"


def play_music(name, sound):
    return play_sound(name, sound, "music", 99999999999999999999999999999999999999)


def stop_music(sound, name="@a"):
    return f"/stopsound {name} music {sound}"
