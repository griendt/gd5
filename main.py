from dataclasses import dataclass
from rich import print, box
from rich.console import ConsoleRenderable, Console
from rich.errors import NotRenderableError
from rich.panel import Panel
from rich.table import Table
from typing import Union

from world import World, Territory, WaterBiome, Player

nil = "[i dim]-[/i dim]"
logger = Console()


def render_struct(struct: dataclass) -> Union[str, ConsoleRenderable]:
    if isinstance(struct, Player):
        table = Table(padding=(0, 1), expand=True, show_header=False, box=box.SIMPLE)
        table.add_column("Key", style="dim", justify="right")
        table.add_column("Value", justify="left")

        table.add_row("Name:", f"[green]{struct.name}")
        table.add_row("Description:", f"[i]{struct.description}")
        table.add_row("Influence Points:", f"[bold blue]{struct.influence_points}")
        table.add_row("Residence:", nil)
        return Panel.fit(table, title=struct.name, border_style="scope.border", padding=(0, 0))

    if isinstance(struct, World):
        return render_struct(struct.territories)

    if isinstance(struct, dict):
        return render_struct(struct.values())

    try:
        iterator = iter(struct)
    except TypeError:
        # The struct is not iterable, but also not an object we know how to parse.
        try:
            logger.log(
                f"Unknown struct of type [b blue]{type(struct).__name__}[/b blue] received, attempting auto-render")
            return struct
        except NotRenderableError:
            raise NotImplementedError(f"Cannot render struct of type {type(struct)}")

    # The struct is a container from which we have fetched some item.
    # Build a table based on the item's type.
    # We will assume each instance in the collection to be of the same type.
    if not struct:
        return str(struct)

    if isinstance(next(iterator), Territory):
        title = "Territories"
        table = Table(padding=(0, 1), expand=True, show_header=True, box=box.SIMPLE)
        table.add_column("ID", style="dim", justify="right")
        table.add_column("Name", justify="right")
        table.add_column("Biome")
        table.add_column("Owner")
        table.add_column("Inhabitants")
        table.add_column("Neighbours", style="dim")

        territory: Territory
        for territory in struct:
            table.add_row(
                str(territory.id),
                territory.name or nil,
                territory.biome.render(),
                territory.owner.name if territory.owner else nil,
                f":kitchen_knife: {territory.id * 5:<2} :firecracker: 3" + (" :star:" if territory.id == 2 else ""),
                " ".join(sorted({str(other.id) for other in territory.linked_territories}))
            )
    else:
        raise NotImplementedError(f"Cannot parse list of {type(struct[0])}")

    return Panel.fit(table, title=title, border_style="scope.border", padding=(0, 0))


if __name__ == '__main__':
    aluce = Player(name="Aluce",
                   description="This phenomenal persona is the ultimate mastermind behind this creation, the one who "
                               "has inspired all others among the current world's leaders to wage war, "
                               "declare peace, or simply bring destruction to anything their eye comes across. Do "
                               "not question [b]Aluce[/b]'s authority, for you [u]will[/u] be cast down and punished "
                               "for your heresy.",
                   influence_points=0)
    psycho17 = Player(name="Psycho17",
                      description="Psycho17. A name most renowned through all the lands. A name synonymous with peace "
                                  "and order, but also that of terror... striking fear in the heart of those who "
                                  "oppose him. A most humble Lord, one who honors and cherishes his people and "
                                  "allies is surmountable to befriend. But if you decide to betray or do evil to his "
                                  "people and allies... all hell will come of it, and your lands will have a new "
                                  "reigning Lord.",
                      influence_points=0)

    world_map = World()

    territories = {
        Territory(name="Worthless Wasteland"),
        Territory(name="Magnificent Metropolis", owner=aluce),
        Territory(name="Omnipotent Oceans", biome=WaterBiome, owner=aluce),
    }

    world_map.territories = {territory.id: territory for territory in territories}
    world_map.link_territories_by_id(1, 2)
    world_map.link_territories_by_id(1, 3)

    print(render_struct(aluce))
    print(render_struct(psycho17))
    print(render_struct(world_map))
