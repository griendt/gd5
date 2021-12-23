from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import count
from typing import Optional, TypeVar

from gd.excepts import InsufficientUnitsException

T = TypeVar('T')


@dataclass
class World:
    territories: dict[int, Territory] = field(default_factory=lambda: dict())
    boundaries: set[Boundary] = field(default_factory=lambda: set())


world = World()


@dataclass
class Player:
    name: str
    world: World

    id: int = None
    next_id = count(1)
    description: Optional[str] = ""
    influence_points: int = 0

    def __post_init__(self):
        self.id = next(self.next_id)

    def __hash__(self):
        # Names are static and hence can be used as a hash safely
        return hash(self.id)

    def __setattr__(self, key, value):
        if key == "name" and hasattr(self, "name"):
            raise AttributeError("Cannot re-assign player names")

        object.__setattr__(self, key, value)

    def owned_territories(self) -> set[Territory]:
        return {territory for territory in self.world.territories.values() if territory.owner == self}


@dataclass
class Biome:
    type: str
    color: Optional[str] = None

    def render(self):
        return f"[{self.color or 'dim'}]{self.type}"


LandBiome = Biome(type="Land", color="yellow")
WaterBiome = Biome(type="Water", color="blue")
WastelandBiome = Biome(type="Wasteland", color="gray")


@dataclass
class Territory:
    id: int = None
    biome: Biome = LandBiome
    name: Optional[str] = None
    owner: Optional[Player] = None
    next_id = count(1)
    units: list[Unit] = field(default_factory=lambda: list())
    constructs: set[Construct] = field(default_factory=lambda: set())
    world: World = world

    def __post_init__(self):
        if not self.id:
            self.id = next(self.next_id)

    def set_owner(self, owner: Player) -> Territory:
        self.owner = owner
        return self

    def all(self, cls: type[Unit]) -> list[Unit]:
        """Convenience method."""
        return [unit for unit in self.units if isinstance(unit, cls)]

    def take_unit(self, cls: type[Unit], amount: int = 1, allow_insufficient_amount: bool = False) -> Unit | list[
        Unit] | None:
        """Select one or more random items from a type of unit."""

        if amount < 0:
            raise ValueError("A non-negative amount of units must be taken")

        if amount == 0:
            return []

        available = self.all(cls)
        if amount > len(available):
            if not allow_insufficient_amount:
                raise InsufficientUnitsException(cls, amount)

            # More units were requested than available, but this is specified to be OK.
            # However, we must check if there are any available units left, to prevent fetching units
            # from an empty list.
            if not available:
                return

            amount = len(available)

        return available[:amount] if amount > 1 else available[0]

    def remove_unit(self, cls: type[Unit], amount: int = 1, allow_insufficient_amount: bool = False) -> None:
        """Remove one or more units of the given type."""
        available = self.all(cls)
        if amount > len(available):
            if not allow_insufficient_amount:
                raise InsufficientUnitsException(cls, amount)

            amount = len(available)

        for unit in available[:amount]:
            self.units.remove(unit)

    def move_all(self, cls: type[Unit], destination: Territory) -> None:
        """Convenience method. Move all units of the
        given type to the destination territory."""
        for unit in self.all(cls):
            assert isinstance(unit, Unit)
            unit.move(destination)

    def is_empty(self) -> bool:
        """Whether the territory is considered empty (devoid of units and constructs)."""
        return not self.units and not self.constructs

    def is_neutral(self) -> bool:
        """Whether this territory is considered neutral (not belonging to any player).
        Note that this is not necessarily the same as it being empty, as the territory might contain
        a construct that does not require the availability of any units."""
        return not self.owner

    @property
    def boundaries(self) -> set[Boundary]:
        """Return the boundaries of this Territory."""
        return {boundary for boundary in self.world.boundaries if self in boundary.territories}

    @property
    def adjacent_territories(self) -> set[Territory]:
        """Return the Territories that share a boundary with this Territory."""
        return {territory for boundary in self.boundaries for territory in boundary.territories if territory != self}


    def __hash__(self):
        return self.id


class Terrain(Enum):
    FLAT = 1
    MOUNTAIN = 2


@dataclass
class Boundary:
    territories: tuple[Territory, Territory]
    terrain: Terrain = Terrain.FLAT

    def __hash__(self):
        return hash((self.territories[0].id, self.territories[1].id, self.terrain))


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
        territory.units.append(self)

    def remove(self):
        """Remove this unit (i.e. it is slain)."""
        if self.territory:
            self.territory.units.remove(self)

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


class Construct:
    territory: Territory

    def __init__(self, territory: Territory):
        self.territory = territory
        self.territory.constructs.add(self)


class Headquarter(Construct):
    pass
