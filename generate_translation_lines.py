from typing import Union

from discord import Permissions
from discord.ext import commands

from Discord_bot import build_bot
from components.constants import UNITS, DEATH_MESSAGES
from components.localization import RuntimeTextHandler, get_locales

MINECRAFT_ENTITIES = [
    '[Intentional Game Design]', 'Allay', 'Area Effect Cloud', 'Armadillo', 'Armor Stand', 'Arrow', 'Axolotl', 'Bat',
    'Bee', 'Blaze', 'Boat', 'Bogged', 'Breeze', 'Camel', 'Cat', 'Cave Spider', 'Boat with Chest', 'Minecart with Chest',
    'Chicken', 'Cod', 'Minecart with Command Block', 'Cow', 'Creeper', 'Dolphin', 'Donkey', 'Dragon Fireball',
    'Drowned', 'Thrown Egg', 'Elder Guardian', 'End Crystal', 'Ender Dragon', 'Thrown Ender Pearl', 'Enderman',
    'Endermite', 'Evoker', "Thrown Bottle o' Enchanting", 'Experience Orb', 'Fireball', 'Firework Rocket', 'Fox',
    'Frog', 'Minecart with Furnace', 'Ghast', 'Giant', 'Glow Squid', 'Goat', 'Guardian', 'Hoglin',
    'Minecart with Hopper', 'Horse', 'Husk', 'Illusioner', 'Iron Golem', 'The Killer Bunny', 'Lightning Bolt', 'Llama',
    'Magma Cube', 'Minecart', 'Mooshroom', 'Mule', 'Ocelot', 'Ominous Item Spawner', 'Panda', 'Parrot', 'Phantom',
    'Pig', 'Piglin', 'Piglin Brute', 'Pillager', 'Polar Bear', 'Pufferfish', 'Rabbit', 'Ravager', 'Salmon', 'Sheep',
    'Shulker', 'Silverfish', 'Skeleton', 'Skeleton Horse', 'Slime', 'Small Fireball', 'Sniffer', 'Snow Golem',
    'Snowball', 'Minecart with Monster Spawner', 'Spectral Arrow', 'Spider', 'Squid', 'Stray', 'Strider', 'Tadpole',
    'Primed TNT', 'Minecart with TNT', 'Trader Llama', 'Trident', 'Tropical Fish', 'Anemone', 'Black Tang', 'Blue Tang',
    'Butterflyfish', 'Cichlid', 'Clownfish', 'Cotton Candy Betta', 'Dottyback', 'Emperor Red Snapper', 'Goatfish',
    'Moorish Idol', 'Ornate Butterflyfish', 'Parrotfish', 'Queen Angelfish', 'Red Cichlid', 'Red Lipped Blenny',
    'Red Snapper', 'Threadfin', 'Tomato Clownfish', 'Triggerfish', 'Yellowtail Parrotfish', 'Yellow Tang', 'Betty',
    'Blockfish', 'Brinely', 'Clayfish', 'Dasher', 'Flopper', 'Glitter', 'Kob', 'Snooper', 'Spotty', 'Stripey',
    'Sunstreak', 'Turtle', 'Vex', 'Villager', 'Armorer', 'Butcher', 'Cartographer', 'Cleric', 'Farmer', 'Fisherman',
    'Fletcher', 'Leatherworker', 'Librarian', 'Mason', 'Nitwit', 'Shepherd', 'Toolsmith', 'Weaponsmith', 'Vindicator',
    'Wandering Trader', 'Warden', 'Witch', 'Wither', 'Wither Skeleton', 'Wither Skull', 'Wolf', 'Zoglin', 'Zombie',
    'Zombie Horse', 'Zombie Villager', 'Zombified Piglin', 'Zombie Pigman', 'Minecart with Spawner'
]


def _create_pot_lines_for_subcommands(command: Union[commands.Command, commands.Group], find_str: str):
    if not hasattr(command, "commands") or len(command.commands) == 0:
        return

    for subcommand in sorted(command.commands, key=lambda c: c.name):
        RuntimeTextHandler.add_translation(f"{find_str}_{subcommand.name}")
        for arg in sorted(subcommand.clean_params.keys()):
            RuntimeTextHandler.add_translation(f"{find_str}_{subcommand.name}_{arg}")
        _create_pot_lines_for_subcommands(subcommand, f"{find_str}_{subcommand.name}")


def create_pot_lines(bot: commands.Bot):
    for lang in get_locales():
        RuntimeTextHandler.add_translation(lang)
    for un in UNITS:
        RuntimeTextHandler.add_translation(un)
    for msg in DEATH_MESSAGES:
        RuntimeTextHandler.add_translation(msg)
    for entity in MINECRAFT_ENTITIES:
        RuntimeTextHandler.add_translation(entity)
    for command in sorted(bot.commands, key=lambda c: c.name):
        RuntimeTextHandler.add_translation(f"help_brief_{command.name}")
        RuntimeTextHandler.add_translation(f"help_{command.name}")
        for arg in sorted(command.clean_params.keys()):
            RuntimeTextHandler.add_translation(f"help_{command.name}_{arg}")
        _create_pot_lines_for_subcommands(command, f"help_{command.name}")
    for perm in sorted(Permissions.VALID_FLAGS.keys()):
        RuntimeTextHandler.add_translation(perm.replace("_", " ").replace("guild", "server").title())
    RuntimeTextHandler.freeze_translation()


if __name__ == '__main__':
    create_pot_lines(build_bot(create_pot_lines=True))
