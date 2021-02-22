from __future__ import annotations

from dataclasses import dataclass, field
from itertools import count
from typing import Optional, TypeVar

from exceptions import InvalidInstruction, InstructionAlreadyExecuted, InsufficientUnitsException, \
    InstructionNotInInstructionSet

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

    def all(self, cls: T) -> set[T]:
        """Convenience method."""
        return {unit for unit in self.units if isinstance(unit, cls)}

    def take_unit(self, cls: T, amount: int = 1) -> T | set[T]:
        """Select one or more random items from a type of unit."""

        if amount < 0:
            raise ValueError("A non-negative amount of units must be taken")

        if amount == 0:
            return set()

        if amount > len(self.all(cls)):
            raise InsufficientUnitsException(cls, amount)

        sample, amount_taken = set(), 0
        for unit in self.all(cls):
            # If only one item is requested, simply return that item
            # rather than building a set of items.
            if amount == 1:
                return unit

            sample.add(unit)
            amount_taken += 1

            if amount_taken == amount:
                break

        return sample

    def move_all(self, cls: T, destination: Territory) -> None:
        """Convenience method. Move all units of the
        given type to the destination territory."""
        for unit in self.all(cls):
            assert isinstance(unit, Unit)
            unit.move(destination)

    def is_empty(self) -> bool:
        """Whether the territory is considered empty (devoid of units)."""
        return not self.units

    def is_neutral(self) -> bool:
        """Whether this territory is considered neutral (not belonging to any player).
        Note that this is not necessarily the same as it being empty, as the territory might contain
        a construct that does not require the availability of any units."""
        return not self.owner

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


@dataclass
class InstructionSet:
    """Instructions are to be invoked in conjunction with other instructions: they are not standalone.
    Consider for example a skirmish: this is a combination of two or more Instructions whose result
    is altered by each other's existence. This class orchestrates this behaviour and allows Instructions
    to see which other Instructions are relevant for its own execution."""

    instructions: list[Instruction] = field(default_factory=lambda: list())

    def find_skirmishes(self, instruction: Instruction) -> list[Instruction]:
        """Given *instruction*, look for other instructions that will cause a skirmish with it."""
        skirmishing_instructions: list[Instruction] = [
            other_instruction for other_instruction in self.instructions
            if (
                other_instruction.origin == instruction.destination and
                other_instruction.destination == instruction.origin
            )]

        return skirmishing_instructions

    def __post_init__(self):
        """Make sure that each Instruction is registered as being in this InstructionSet."""
        for instruction in self.instructions:
            instruction.instruction_set = self


@dataclass
class Instruction:
    """A basic order is invoked by someone and concerns the movement
    of some units from an origin to a destination."""
    issuer: Player
    origin: Territory
    destination: Territory
    instruction_set: InstructionSet = None
    num_troops: int = 0
    is_executed: bool = False

    def __post_init__(self):
        """Make sure to register this Instruction to its InstructionSet."""
        if self.instruction_set and self not in self.instruction_set.instructions:
            self.instruction_set.instructions.append(self)

    def assert_is_valid(self) -> None:
        """Do some sanity checks to determine whether this Instruction makes sense.
        This method should be called before or during execution to prevent unwanted changes
        to the world map."""
        if self.origin.owner != self.issuer:
            raise InvalidInstruction("Issuer is not the origin owner")

        if self.num_troops > len({unit for unit in self.origin.all(Troop)}):
            raise InvalidInstruction("Insufficient troops in origin territory")

    def resolve_invasion(self, num_troops_moved: int = 0) -> None:
        """When the Instruction has been marked to be an invasion, this function resolves it.
        By default we will assume no troops have yet been moved, but this may be altered by the
        *num_troops_moved* parameter. This is useful in case of skirmishes that wind up having
        a section that is to be parsed as an invasion."""

        # Apply the 1-Troop penalty to the attacker.
        self.origin.take_unit(Troop).remove()
        num_troops_moved += 1

        while self.num_troops > num_troops_moved:
            # Remove a troop from both sides in an equal ratio, as long as this is possible
            # and we still have troops to move.
            if self.origin.all(Troop) and self.destination.all(Troop):
                self.origin.take_unit(Troop).remove()
                self.destination.take_unit(Troop).remove()
            else:
                # Either army is completely exhausted.
                # The battle ends.
                break

            num_troops_moved += 1

        # Determine whether the attacker has units left. If so, move them to the target
        # territory and set the attacker as the new owner of the target.
        if remainder := self.origin.take_unit(Troop, self.num_troops - num_troops_moved):
            # If the attacker has Troops remaining, move them to the target territory.
            self.destination.set_owner(self.origin.owner)

            if isinstance(remainder, Troop):
                remainder.move(self.destination)
                num_troops_moved += 1
            else:
                for troop in remainder:
                    troop.move(self.destination)
                    num_troops_moved += 1
        elif self.destination.is_empty():
            # The destination has been rendered empty with this invasion. This will
            # turn the destination neutral.
            self.destination.owner = None

    def resolve_skirmish(self, skirmishes: list[Instruction]) -> None:
        """This is a skirmish with another Instruction. Right now we're assuming there can
        be only one such skirmish, but we will have to support the more complex scenarios as well.
        We will want to implement virtual territories, that are the combination of armies from origin
        territories. But right now we are focussing on simple skirmishes only."""
        skirmish: Instruction = skirmishes[0]

        num_troops_moved = 0
        num_skirmish_troops_moved = 0
        # We have repeated code here, compared to the invasion. We should wrap this in a convenient method.
        while self.num_troops > num_troops_moved:
            if self.origin.all(Troop) and skirmish.origin.all(Troop):
                self.origin.take_unit(Troop).remove()
                skirmish.origin.take_unit(Troop).remove()
                num_skirmish_troops_moved += 1
            else:
                break

            num_troops_moved += 1

        if num_skirmish_troops_moved == skirmish.num_troops:
            # The opponent's instruction has been resolved completely, as all units in it have already
            # moved during the resolve of this skirmish. So, set the instruction to executed.
            skirmish.is_executed = True

        # If the origin has troops remaining, the remainder of the units move onwards to the
        # target territory. We know that this must be an invasion and not an expansion, since
        # lands may not be left empty.
        remainder_after_skirmish = self.origin.take_unit(Troop, self.num_troops - num_troops_moved)
        if remainder_after_skirmish:
            self.resolve_invasion(num_troops_moved)

    def resolve_expansion(self) -> None:
        """The destination is neutral or belongs to the same player. We will
        simply move the units from the origin to the destination and set the ownership."""
        num_troops_moved = 0
        self.destination.set_owner(self.origin.owner)

        while self.num_troops > num_troops_moved:
            # Note: we regard each troop here as being identical.
            self.origin.take_unit(Troop).move(self.destination)
            num_troops_moved += 1

    def execute(self) -> Instruction:
        """Execute the order. This will alter the territories it belongs to."""
        self.assert_is_valid()

        if self.is_executed:
            raise InstructionAlreadyExecuted()

        if not self.instruction_set:
            raise InstructionNotInInstructionSet()

        if self.destination.is_neutral() or self.origin.owner == self.destination.owner:
            """The destination is neutral or belongs to the same player. We will
            simply move the units from the origin to the destination and set the ownership."""
            self.resolve_expansion()
        elif skirmishes := self.instruction_set.find_skirmishes(self):
            """There are other Instructions that conflict with this one. This leads to skirmishes.
            We will have to resolve those skirmishes first."""
            self.resolve_skirmish(skirmishes)
        else:
            """We are dealing with an invasion here: the target territory already belongs
            to another player. We will have to resolve the battle and units will be lost."""
            self.resolve_invasion()

        self.is_executed = True
        return self
