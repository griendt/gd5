from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Optional, Generic, TypeVar

from data.exceptions import InvalidInstruction, InstructionAlreadyExecuted

T = TypeVar('T')


@dataclass
class Player:
    name: str
    description: Optional[str] = ""
    influence_points: int = 0


@dataclass
class World:
    territories: dict[int, Territory] = field(default_factory=lambda: dict())

    def link_territories_by_id(self, id_1: int, id_2: int) -> None:
        territory_1, territory_2 = self.territories[id_1], self.territories[id_2]
        territory_1.linked_territories.add(territory_2)
        territory_2.linked_territories.add(territory_1)


@dataclass
class Biome:
    type: str
    color: Optional[str] = None

    def render(self):
        return f"[{self.color or 'dim'}]{self.type}"


LandBiome = Biome(type="Land", color="yellow")
WaterBiome = Biome(type="Water", color="blue")


@dataclass
class Territory:
    id: int = None
    biome: Biome = LandBiome
    name: Optional[str] = None
    owner: Optional[Player] = None
    next_id = count(1)
    linked_territories: set[Territory] = field(default_factory=lambda: set())
    units: set[Unit] = field(default_factory=lambda: set())

    def __post_init__(self):
        if not self.id:
            self.id = next(self.next_id)

    def set_owner(self, owner: Player) -> Territory:
        self.owner = owner
        return self

    def units_of(self, cls: T) -> set[T]:
        """Convenience method."""
        return {unit for unit in self.units if isinstance(unit, cls)}

    def is_neutral(self) -> bool:
        """Whether the territory is considered neutral."""
        return not self.units

    def __hash__(self):
        return self.id


class Unit:
    id: int = None
    territory: Territory = None
    next_id = count(1)

    def __init__(self, territory: Territory):
        self.id = next(self.next_id)
        self.move(territory)

    def move(self, territory: Territory):
        """Move a unit to a target territory."""

        # Remove the unit from the current location, if it has one.
        # This is not needed for newly created units.
        if self.territory:
            self.territory.units.remove(self)

        # Set the territory property and modify the territory
        # to contain this unit.
        self.territory = territory
        territory.units.add(self)

    def render(self):
        raise NotImplementedError


class Troop(Unit):
    def render(self):
        return ":kitchen_knife:"


class Cavalry(Unit):
    def render(self):
        return ":firecracker:"


class General(Unit):
    def render(self):
        return ":star:"


@dataclass
class Instruction:
    """A basic order is invoked by someone and concerns the movement
    of some units from an origin to a destination."""
    issuer: Player
    origin: Territory
    destination: Territory
    num_troops: int = 0
    is_executed: bool = False

    def assert_is_valid(self) -> None:
        """Do some sanity checks to determine whether this Instruction makes sense.
        This method should be called before or during execution to prevent unwanted changes
        to the world map."""
        if self.origin.owner != self.issuer:
            raise InvalidInstruction("Issuer is not the origin owner")

        if self.num_troops > len({unit for unit in self.origin.units_of(Troop)}):
            raise InvalidInstruction("Insufficient troops in origin territory")

    def execute(self) -> Instruction:
        """Execute the order. This will alter the territories it belongs to."""
        self.assert_is_valid()

        if self.is_executed:
            raise InstructionAlreadyExecuted()

        num_troops_moved = 0

        if self.destination.is_neutral() or self.origin.owner == self.destination.owner:
            """The destination is neutral or belongs to the same player. We will
            simply move the units from the origin to the destination and set the ownership."""

            self.destination.set_owner(self.origin.owner)

            while self.num_troops > num_troops_moved:
                # Note: we regard each troop here as being identical.
                for unit in self.origin.units_of(Troop):
                    unit.move(self.destination)
                    num_troops_moved += 1
                    break

        self.is_executed = True
        return self
