from re import sub, compile

VERSION = "1.4.7a"

UNITS = ("B", "KB", "MB", "GB", "TB", "PB")
WINDOW_AVERAGE_LENGTH = 5
DISCORD_SYMBOLS_IN_MESSAGE_LIMIT = 2000
MAX_RCON_COMMAND_STR_LENGTH = 1446
MAX_TELLRAW_OBJECT_WITH_STANDARD_MENTION_STR_LENGTH = MAX_RCON_COMMAND_STR_LENGTH - 9 - 2
DISCORD_SELECT_FIELD_MAX_LENGTH = 100
DISCORD_SELECT_OPTIONS_MAX_LENGTH = 25
DISCORD_MAX_SELECT_OPTIONS_IN_MESSAGE = DISCORD_SELECT_OPTIONS_MAX_LENGTH * 5
DISCORD_MIN_SECONDS_TIMEOUT_FOR_POLL = 3600
DISCORD_MAX_SECONDS_TIMEOUT_FOR_POLL = 32 * 24 * 3600
ANSI_ESCAPE = compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
URL_REGEX = r"https?://(?:[a-zA-Z]|[0-9]|[#-_@.&+]|[!*(),]|%[0-9a-fA-F][0-9a-fA-F])+"
EMOJI_REGEX = r"<a?:\w+:\d+>"
TENOR_REGEX = r"https?://tenor\.com/view"
CODE_LETTERS = "WERTYUPASFGHKZXCVBNM23456789~_&+="

# Messages taken from https://minecraft.wiki/w/Death_messages
DEATH_MESSAGES = [
    '{0} was squashed by a falling anvil', '{0} was squashed by a falling anvil while fighting {1}',
    '{0} was shot by {1}', '{0} was shot by {1} using {2}', '{0} was killed by {1}', '{0} was pricked to death',
    '{0} walked into a cactus while trying to escape {1}', '{0} was squished too much', '{0} was squashed by {1}',
    "{0} was roasted in dragon's breath", "{0} was roasted in dragon's breath by {1}", '{0} drowned',
    '{0} drowned while trying to escape {1}', '{0} died from dehydration',
    '{0} died from dehydration while trying to escape {1}', '{0} was killed by even more magic', '{0} blew up',
    '{0} was blown up by {1}', '{0} was blown up by {1} using {2}', '{0} hit the ground too hard',
    '{0} hit the ground too hard while trying to escape {1}', '{0} was squashed by a falling block',
    '{0} was squashed by a falling block while fighting {1}', '{0} was skewered by a falling stalactite',
    '{0} was skewered by a falling stalactite while fighting {1}', '{0} was fireballed by {1}',
    '{0} was fireballed by {1} using {2}', '{0} went off with a bang',
    '{0} went off with a bang due to a firework fired from {2} by {1}', '{0} went off with a bang while fighting {1}',
    '{0} experienced kinetic energy', '{0} experienced kinetic energy while trying to escape {1}', '{0} froze to death',
    '{0} was frozen to death by {1}', '{0} died', '{0} died because of {1}', '{0} was killed',
    '{0} was killed while fighting {1}', '{0} discovered the floor was lava',
    '{0} walked into the danger zone due to {1}', '{0} was killed by {1} using magic',
    '{0} was killed by {1} using {2}', '{0} went up in flames', '{0} walked into fire while fighting {1}',
    '{0} suffocated in a wall', '{0} suffocated in a wall while fighting {1}', '{0} tried to swim in lava',
    '{0} tried to swim in lava to escape {1}', '{0} was struck by lightning',
    '{0} was struck by lightning while fighting {1}', '{0} was smashed by {1}', '{0} was smashed by {1} with {2}',
    '{0} was killed by magic', '{0} was killed by magic while trying to escape {1}', '{0} was slain by {1}',
    '{0} was slain by {1} using {2}', '{0} burned to death',
    '{0} was burned to a crisp while fighting {1} wielding {2}', '{0} was burned to a crisp while fighting {1}',
    '{0} fell out of the world', "{0} didn't want to live in the same world as {1}",
    '{0} left the confines of this world', '{0} left the confines of this world while fighting {1}',
    '{0} was obliterated by a sonically-charged shriek',
    '{0} was obliterated by a sonically-charged shriek while trying to escape {1} wielding {2}',
    '{0} was obliterated by a sonically-charged shriek while trying to escape {1}', '{0} was impaled on a stalagmite',
    '{0} was impaled on a stalagmite while fighting {1}', '{0} starved to death',
    '{0} starved to death while fighting {1}', '{0} was stung to death', '{0} was stung to death by {1} using {2}',
    '{0} was stung to death by {1}', '{0} was poked to death by a sweet berry bush',
    '{0} was poked to death by a sweet berry bush while trying to escape {1}',
    '{0} was killed while trying to hurt {1}', '{0} was killed by {2} while trying to hurt {1}',
    '{0} was pummeled by {1}', '{0} was pummeled by {1} using {2}', '{0} was impaled by {1}',
    '{0} was impaled by {1} with {2}', '{0} withered away', '{0} withered away while fighting {1}',
    '{0} was shot by a skull from {1}', '{0} was shot by a skull from {1} using {2}', '{0} fell from a high place',
    '{0} fell off a ladder', '{0} fell while climbing', '{0} fell off scaffolding', '{0} fell off some twisting vines',
    '{0} fell off some vines', '{0} fell off some weeping vines', '{0} was doomed to fall by {1}',
    '{0} was doomed to fall by {1} using {2}', '{0} fell too far and was finished by {1}',
    '{0} fell too far and was finished by {1} using {2}', '{0} was doomed to fall', '{0} fell out of the water',
    "{0} was shot by a {1}'s skull", '{0} was fell too far and was finished by {1}',
    '{0} was fell too far and was finished by {1} using {2}', '{0} was roasted in dragon breath',
    '{0} was roasted in dragon breath by {1}', '{0} walked into danger zone due to {1}',
    '{0} was squashed by a falling anvil whilst fighting {1}', '{0} walked into a cactus whilst trying to escape {1}',
    '{0} drowned whilst trying to escape {1}', '{0} died from dehydration whilst trying to escape {1}',
    '{0} hit the ground too hard whilst trying to escape {1}',
    '{0} was squashed by a falling block whilst fighting {1}',
    '{0} was skewered by a falling stalactite whilst fighting {1}', '{0} went off with a bang whilst fighting {1}',
    '{0} experienced kinetic energy whilst trying to escape {1}', '{0} was killed whilst fighting {1}',
    '{0} walked into fire whilst fighting {1}', '{0} suffocated in a wall whilst fighting {1}',
    '{0} was struck by lightning whilst fighting {1}', '{0} was killed by magic whilst trying to escape {1}',
    '{0} was burnt to a crisp whilst fighting {1} wielding {2}', '{0} was burnt to a crisp whilst fighting {1}',
    '{0} left the confines of this world whilst fighting {1}',
    '{0} was obliterated by a sonically-charged shriek whilst trying to escape {1} wielding {2}',
    '{0} was obliterated by a sonically-charged shriek whilst trying to escape {1}',
    '{0} was impaled on a stalagmite whilst fighting {1}', '{0} starved to death whilst fighting {1}',
    '{0} was poked to death by a sweet berry bush whilst trying to escape {1}', '{0} was killed trying to hurt {1}',
    '{0} was killed by {2} trying to hurt {1}', '{0} withered away whilst fighting {1}'
]
DEATH_MESSAGES = sorted(DEATH_MESSAGES, key=lambda s: len(s), reverse=True)
REGEX_DEATH_MESSAGES = [sub(r"\{\d}", r"(.+)", m) for m in DEATH_MESSAGES]
MASS_REGEX_DEATH_MESSAGES = "|".join(REGEX_DEATH_MESSAGES)
