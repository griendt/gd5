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

    def __hash__(self):
        # Names are static and hence can be used as a hash safely
        return hash(self.name)

    def __setattr__(self, key, value):
        if key == "name" and hasattr(self, "name"):
            raise AttributeError("Cannot re-assign player names")

        object.__setattr__(self, key, value)


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

    def all(self, cls: type) -> set[T]:
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
    num_troops_moved: int = 0
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

    def resolve_invasion(self) -> None:
        """When the Instruction has been marked to be an invasion, this function resolves it.
        By default we will assume no troops have yet been moved, but this may be altered by the
        *num_troops_moved* parameter. This is useful in case of skirmishes that wind up having
        a section that is to be parsed as an invasion."""

        # Apply the 1-Troop penalty to the attacker.
        self.origin.take_unit(Troop).remove()
        self.num_troops_moved += 1

        while self.num_troops > self.num_troops_moved:
            # Remove a troop from both sides in an equal ratio, as long as this is possible
            # and we still have troops to move.
            if self.origin.all(Troop) and self.destination.all(Troop):
                self.origin.take_unit(Troop).remove()
                self.destination.take_unit(Troop).remove()
            else:
                # Either army is completely exhausted.
                # The battle ends.
                break

            self.num_troops_moved += 1

        # Determine whether the attacker has units left. If so, move them to the target
        # territory and set the attacker as the new owner of the target.
        if remainder := self.origin.take_unit(Troop, self.num_troops - self.num_troops_moved):
            # If the attacker has Troops remaining, move them to the target territory.
            self.destination.set_owner(self.origin.owner)

            if isinstance(remainder, Troop):
                remainder.move(self.destination)
                self.num_troops_moved += 1
            else:
                for troop in remainder:
                    troop.move(self.destination)
                    self.num_troops_moved += 1
        elif self.destination.is_empty():
            # The destination has been rendered empty with this invasion. This will
            # turn the destination neutral.
            self.destination.owner = None

    def resolve_skirmish(self, skirmishes: list[Instruction]) -> None:
        """This is a skirmish with other Instructions. Right now we're assuming each Instruction
        belongs to a different player, and hence they can be treated as individual armies. What we
        want to establish however, is that if some instructions involved in this skirmish belong to
        the same player, we will create a "virtual" territory so we can consider the Instructions
        as being one. However, that is not yet implemented."""

        issuers = {instruction.issuer for instruction in skirmishes}
        issuers.add(self.issuer)
        if len(issuers) < len(skirmishes) + 1:
            # There are less issuers than total Instructions involved.
            # By the pigeonhole principle, at least one player has two Instructions involved.
            # This will require virtual territories to parse correctly.
            raise NotImplementedError("Skirmish from same player in multiple origins is not implemented")

        # First, we will check which party has the least amount of troops in this skirmish.
        # We can then subtract troops from all skirmishes up until this point, after which
        # that party (or parties) has run out of troops. The skirmish may continue with fewer
        # parties involved, but that can be its own separate resolve.
        min_troops_to_move_among_skirmishes = min(
            map(lambda instruction: instruction.num_troops - instruction.num_troops_moved, skirmishes)
        )

        for i in range(min_troops_to_move_among_skirmishes):
            # Subtracrt a troop.
            self.origin.take_unit(Troop).remove()
            self.num_troops_moved += 1

            # Subtract a troop from all involved parties.
            for skirmish in skirmishes:
                skirmish.origin.take_unit(Troop).remove()
                skirmish.num_troops_moved += 1

        # At least one skirmish has now been completed. Mark those instructions as executed.
        for skirmish in skirmishes:
            if skirmish.num_troops_moved == skirmish.num_troops:
                skirmish.is_executed = True

        if self.num_troops_moved == self.num_troops:
            # This instruction is finished. There may be remaining skirmishes, but they will
            # be resolved when their contents are being evaluated in their own turn, so there
            # is no need for a recursive call.
            return

        # We may continue fighting! We have defeated at least one opponent, but there may be some left.
        # We can resolve the remaining skirmishes through a recursive call.
        if remaining_skirmishes := [skirmish for skirmish in skirmishes if not skirmish.is_executed]:
            self.resolve_skirmish(remaining_skirmishes)

        # If we reach here, we have defeated all opponent skirmishes.
        # If the origin has troops remaining, the remainder of the units
        # move onwards to the target territory.
        remainder_after_skirmish = self.origin.take_unit(Troop, self.num_troops - self.num_troops_moved)
        if remainder_after_skirmish:
            if self.destination.is_neutral():
                self.resolve_expansion()
            else:
                self.resolve_invasion()

    def resolve_expansion(self) -> None:
        """The destination is neutral or belongs to the same player. We will
        simply move the units from the origin to the destination and set the ownership."""
        self.destination.set_owner(self.origin.owner)

        while self.num_troops > self.num_troops_moved:
            # Note: we regard each troop here as being identical.
            self.origin.take_unit(Troop).move(self.destination)
            self.num_troops_moved += 1

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
