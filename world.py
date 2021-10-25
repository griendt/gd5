from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from itertools import count
from typing import Optional, TypeVar

from excepts import (
    InvalidInstruction,
    InstructionAlreadyExecuted,
    InsufficientUnitsException,
    InstructionNotInInstructionSet,
    InstructionAlreadyExecuting,
    InstructionNoSkirmishingInstructions,
    InvalidInstructionType,
    UnwindingLoopedInstructions,
    InstructionSetNotConstructible,
    InstructionNotExecuted,
)
from logger import logger

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
    units: list[Unit] = field(default_factory=lambda: list())

    def __post_init__(self):
        if not self.id:
            self.id = next(self.next_id)

    def set_owner(self, owner: Player) -> Territory:
        self.owner = owner
        return self

    def all(self, cls: type[Unit]) -> list[Unit]:
        """Convenience method."""
        return [unit for unit in self.units if isinstance(unit, cls)]

    def take_unit(self, cls: type[Unit], amount: int = 1, allow_insufficient_amount: bool = False) -> Unit | list[Unit] | None:
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


@dataclass
class Turn:
    instruction_sets: list[InstructionSet] = field(default_factory=lambda: list())

    def __init__(self, instructions: list[Instruction]):
        # Here, we will decide which instructions should go in which instruction set.
        # In principle, there should be only one instruction set, unless there are Instructions
        # that are _conditional_, i.e. may or may not be executed depending on the outcome of previous ones.
        # Those instructions should, logically, be applied only in a later InstructionSet.
        # In addition, all non-battle movements should be separated from the battle movements, so as to make
        # sure those movements all occur first.

        self.instruction_sets = []
        if distributions := [i for i in instructions if i.origin.owner == i.destination.owner]:
            self.instruction_sets.append(InstructionSet(instructions=distributions))

        while True:
            # Filter out instrunctions that have already been assigned to an InstructionSet.
            if not (instructions := [i for i in instructions if not i.instruction_set]):
                break

            instruction_set = InstructionSet()

            for instruction in instructions:

                if len(self.instruction_sets) >= 2:
                    # A distribution and an invasion set have already been made. This means this Instruction
                    # must depend on the outcomes of previous Instructions. Mark the Instruction as such, so that
                    # the Instruction is allowed to be executed partially in case not all conditions are fulfilled.
                    instruction.allow_insufficient_troops()

                if not [i for i in instructions if i.issuer == instruction.issuer and i.destination == instruction.origin]:
                    # There is no Instruction by the same issuer that should come before this Instruction; i.e.
                    # there is no construction A -> B -> C where the current Instruction is B -> C. This means
                    # we can safely add this Instruction to the current Instruction set. Any Instructions that
                    # depend on the current Instruction can then be added to the next set.

                    # FIXME: Fix the scenario in which there exists movements A -> B -> C, and A and C belong to
                    #   the same player, and that player attempts to invade B and _then_ distribute to C.
                    #   This should not be allowed!
                    instruction_set.add_instruction(instruction)

            if not instruction_set.instructions:
                # For some reason, we could not add any Instructions to this InstructionSet. This would cause an
                # infinite loop. This should never be able to occur!
                raise InstructionSetNotConstructible

            self.instruction_sets.append(instruction_set)

    def execute(self) -> Turn:
        turn_info = ''
        for instruction_set in self.instruction_sets:
            turn_info += '\n    '
            for instruction in instruction_set.instructions:
                turn_info += ' - ' + instruction.repr_arrow() + '\n    '
        logger.info(f'[yellow]Processing turn with following instructions[/yellow]:{turn_info}')

        for instruction_set in self.instruction_sets:
            for instruction in instruction_set.instructions:
                try:
                    instruction.execute()
                except InstructionAlreadyExecuted:
                    # Another Instruction may have already caused this Instruction to be executed.
                    # This is fine, as long as we check that all Instructions were executed at the end.
                    pass

            if [i for i in instruction_set.instructions if not i.is_executed]:
                # All Instructions must be executed before moving on to the next InstructionSet.
                raise InstructionNotExecuted

        return self


@dataclass
class InstructionSet:
    """Instructions are to be invoked in conjunction with other instructions: they are not standalone.
    Consider for example a skirmish: this is a combination of two or more Instructions whose result
    is altered by each other's existence. This class orchestrates this behaviour and allows Instructions
    to see which other Instructions are relevant for its own execution."""

    instructions: list[Instruction] = field(default_factory=lambda: list())

    def add_instruction(self, instruction: Instruction) -> None:
        """The preferred way to add instructions. This is because the InstructionSet may hydrate Instructions with
        extra info, such as whether it is a skirmish and/or invasion and so on."""
        if instruction in self.instructions:
            return

        instruction.instruction_set = self
        self.instructions.append(instruction)
        self.set_instruction_type(instruction)

    def set_instruction_type(self, instruction: Instruction) -> None:
        if instruction.issuer == instruction.destination.owner:
            instruction.instruction_type = InstructionType.DISTRIBUTION
        elif [
            instr for instr in self.instructions
            if instr.destination == instruction.destination and instr.issuer != instruction.issuer and instr.issuer != instr.destination.owner
        ]:
            # There is another Player attempting to expand/invade to this destination. Hence, we're dealing with a skirmish.
            # Note that if this other Player is the same player as the destination owner (if any), there is no skirmish, because
            # such a movement is a Distribution, which is to be executed before attacks.
            instructions_to_same_destination = [instr for instr in self.instructions if instr.destination == instruction.destination]
            for instr in instructions_to_same_destination:
                instr.instruction_type = InstructionType.SKIRMISH
                instr.skirmishing_instructions = [i for i in instructions_to_same_destination if i != instr]
        elif instruction.destination.is_neutral():
            instruction.instruction_type = InstructionType.EXPANSION
        else:
            # The target Territory belongs to a different Player. Therefore this is an Invasion.
            instruction.instruction_type = InstructionType.INVASION
            try:
                mutual_invasion = [
                    instr for instr in self.instructions
                    if instr.issuer == instruction.destination.owner and instr.destination == instruction.origin
                ][0]
                instruction.mutual_invasion = mutual_invasion
                mutual_invasion.mutual_invasion = instruction
            except IndexError:
                # No mutual invasion found.
                pass

    def __post_init__(self):
        """Make sure that each Instruction is registered as being in this InstructionSet."""
        for instruction in self.instructions:
            instruction.instruction_set = self
            self.set_instruction_type(instruction)


class InstructionType(Enum):
    EXPANSION = 1
    DISTRIBUTION = 2
    INVASION = 3
    SKIRMISH = 4


@dataclass
class Instruction:
    """A basic order is invoked by someone and concerns the movement
    of some units from an origin to a destination."""
    next_id = count(1)
    issuer: Player
    origin: Territory
    destination: Territory
    id: int = None
    instruction_set: InstructionSet = None
    instruction_type: InstructionType = None
    num_troops: int = 0
    num_troops_moved: int = 0
    is_executing: bool = False
    is_executed: bool = False
    is_part_of_loop: bool = False

    skirmishing_instructions: list[Instruction] = None
    mutual_invasion: Instruction = None
    _allow_insufficient_troops: bool = False

    def __post_init__(self):
        """Make sure to register this Instruction to its InstructionSet."""
        if self.instruction_set and self not in self.instruction_set.instructions:
            self.instruction_set.add_instruction(self)

        self.id = next(self.next_id)

    def __hash__(self):
        return hash(self.id)

    def repr_arrow(self) -> str:
        return (
                f'{{id={self.id}, issuer={self.issuer.name}}} (id={self.origin.id}, owner={self.origin.owner.name}, troops={len(self.origin.all(Troop))})-[{self.num_troops - self.num_troops_moved}/{self.num_troops}]->' +
                f'(id={self.destination.id}, {self.destination.owner.name if self.destination.owner else None}, troops={len(self.destination.all(Troop))})'
        )

    def allow_insufficient_troops(self, value: bool = True) -> Instruction:
        self._allow_insufficient_troops = value
        return self

    def assert_is_valid(self) -> None:
        """Do some sanity checks to determine whether this Instruction makes sense.
        This method should be called before or during execution to prevent unwanted changes
        to the world map."""
        if self.origin.owner != self.issuer:
            logger.error('Invalid instruction: issuer is not the origin owner')
            raise InvalidInstruction("Issuer is not the origin owner")

        if self.num_troops > (troops_in_origin := len({unit for unit in self.origin.all(Troop)})):
            if self._allow_insufficient_troops:
                logger.info(f'Insufficient troops ({troops_in_origin}) in origin; {self.num_troops} requested, but partial assignment is allowed')
            else:
                logger.error(f'Invalid instruction: insufficient troops in origin territory: {self.num_troops} requested, {troops_in_origin} found')
                raise InvalidInstruction("Insufficient troops in origin territory")

        logger.debug('Instruction is valid')

    def resolve_invasion(self) -> None:
        """When the Instruction has been marked to be an invasion, this function resolves it.
        By default we will assume no troops have yet been moved, but this may be altered by the
        *num_troops_moved* parameter. This is useful in case of skirmishes that wind up having
        a section that is to be parsed as an invasion."""

        # First, we need to check whether the target territory is also moving to a (third) territory in this set.
        # If so, that invasion must be resolved first.
        if higher_priority_movements := [
            instruction for instruction in self.instruction_set.instructions
            if instruction.origin == self.destination and not instruction.is_executed
        ]:
            logger.info(f"This invasion has superseding movements:\n  - " + "\n  - ".join([invasion.repr_arrow() for invasion in higher_priority_movements]))
            try:
                for instruction in higher_priority_movements:
                    instruction.execute()
            except (InstructionAlreadyExecuting, UnwindingLoopedInstructions) as exception:
                # We must have a circular loop. Check all the instrutions that are currently executing,
                # and take the one with the lowest origin territory number. As a tie-breaker, that one will be
                # used to resolve the circle first.

                first_origin_id = min([instruction.origin.id for instruction in self.instruction_set.instructions if instruction.is_executing])
                self.is_part_of_loop = True

                if isinstance(exception, InstructionAlreadyExecuting):
                    # Only print some useful logging when first encountering the loop, to avoid clutter during unwinding.
                    logger.info(f"Found circular set of instructions\n  - " + "\n  - ".join(
                        [instruction.repr_arrow() for instruction in self.instruction_set.instructions if instruction.is_executing]
                    ))
                    logger.info(f"The chosen origin id to be executed from is {first_origin_id}")

                if self.origin.id == first_origin_id:
                    logger.debug(f"Found instruction with lowest origin id ({self.origin.id}), resolving first")
                else:
                    # Re-raise the exception so the previous instruction in the loop can catch it.
                    logger.debug(f"The current instruction is not the one with lowest origin id; skipping")
                    raise UnwindingLoopedInstructions()

            logger.info(f"Resolved superseding invasions for instruction id {self.id}")
            for instruction in [instruction for instruction in self.instruction_set.instructions if instruction.is_executing and instruction != self]:
                # The current instruction may now go through. If however this instruction was chosen because of a circular loop,
                # then the other instructions in the loop are still set as executing, while they are no longer being executed.
                # Hence, set their flag back to False so they can be processed as a normal chain.
                instruction.is_executing = False

        # Apply the 2-Troop penalty to the attacker.
        is_mutual_invasion = self.mutual_invasion and not self.mutual_invasion.is_executed
        should_incur_penalty = not (self.mutual_invasion and self.mutual_invasion.is_executed)
        if should_incur_penalty:
            origin_penalty = 0
            destination_penalty = 0
            try:
                for _ in range(2):
                    self.origin.remove_unit(Troop)
                    origin_penalty += 1
                    if is_mutual_invasion:
                        self.destination.remove_unit(Troop)
                        destination_penalty += 1
                    self.num_troops_moved += 1
            except InsufficientUnitsException as e:
                if not self._allow_insufficient_troops:
                    raise e

            logger.debug(f'Applied {origin_penalty} troop penalty to the invader')
            if is_mutual_invasion:
                logger.info(f'Also applied {destination_penalty} troop penalty to the target due to mutual invasion')

        while self.num_troops > self.num_troops_moved:
            # Remove a troop from both sides in an equal ratio, as long as this is possible
            # and we still have troops to move.
            if self.origin.all(Troop) and self.destination.all(Troop):
                self.origin.remove_unit(Troop, 1, self._allow_insufficient_troops)
                self.destination.remove_unit(Troop, 1, self._allow_insufficient_troops)
            else:
                # Either army is completely exhausted.
                # The battle ends.
                logger.debug(
                    f'At least one army is completely exhausted; the battle ends after {self.num_troops_moved} of requested {self.num_troops} invaders have been killed')
                break

            self.num_troops_moved += 1

        # Determine whether the attacker has units left. If so, move them to the target
        # territory and set the attacker as the new owner of the target.
        if remainder := self.origin.take_unit(Troop, self.num_troops - self.num_troops_moved, self._allow_insufficient_troops):
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
        belongs to a different player, and hence they can be treated as individual armies. Note that two
        Instructions with the same destination can belong to the same player and they will be treated as
        two separate armies; however, those two armies do not skirmish."""
        logger.debug(f'{self.repr_arrow()} has skirmishes with:')
        logger.indents += 1
        for skirmish in skirmishes:
            logger.debug(f'- {skirmish.repr_arrow()}')
        logger.indents -= 1
        issuers = {instruction.issuer for instruction in skirmishes}
        issuers.add(self.issuer)

        # First, we will check which party has the least amount of troops in this skirmish.
        # We can then subtract troops from all skirmishes up until this point, after which
        # that party (or parties) has run out of troops. The skirmish may continue with fewer
        # parties involved, but that can be its own separate resolve.
        min_troops_to_move_among_skirmishes = min(
            list(map(lambda instruction: instruction.num_troops - instruction.num_troops_moved, skirmishes)) +
            [self.num_troops - self.num_troops_moved]
        )
        logger.debug(f'Removing {min_troops_to_move_among_skirmishes} troops from all skirmishing territories')

        for i in range(min_troops_to_move_among_skirmishes):
            # Subtract a troop.
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
            logger.debug('There are remaining skirmishes which we will now resolve')
            self.resolve_skirmish(remaining_skirmishes)

        # If we reach here, we have defeated all opponent skirmishes.
        # If the origin has troops remaining, the remainder of the units
        # move onwards to the target territory.
        if self.origin.take_unit(Troop, self.num_troops - self.num_troops_moved):
            logger.debug('Skirmish has been resolved; issuer has troops remaining')
            if self.destination.is_neutral():
                logger.debug('Destination was rendered neutral by the skirmish')
                self.resolve_expansion()
            else:
                self.resolve_invasion()

    def resolve_expansion(self) -> None:
        """The destination is neutral or belongs to the same player. We will
        simply move the units from the origin to the destination and set the ownership."""
        if self.destination.owner is not None and self.destination.owner != self.issuer:
            # When this Instruction was originally created, it was considered an Expansion.
            # However, other Instructions have occurred before this one, and the empty Territory
            # has been taken by another Player. Therefore, we should now resolve this as an Invasion instead.
            logger.debug(f'Movement to {self.destination.id} was originally an expansion, but a new owner ({self.destination.owner.name}) has been detected; resolving to invasion')
            return self.resolve_invasion()

        logger.debug(f'Movement to {self.destination.id} is considered an expansion or relocation')
        self.destination.set_owner(self.issuer)

        while self.num_troops > self.num_troops_moved:
            # Note: we regard each troop here as being identical.
            if (
                (unit := self.origin.take_unit(Troop, 1, self._allow_insufficient_troops)) is None
                and self._allow_insufficient_troops
            ):
                # Not all requested units could be moved, because there are too few available.
                # However, this Instruction was marked as allowed to occur with insufficient troops, so this is OK.
                # Stop moving more units and continue as usual.
                break

            unit.move(self.destination)
            self.num_troops_moved += 1

        logger.debug(f'Moved {self.num_troops_moved} troops')

    def execute(self) -> Instruction:
        """Execute the order. This will alter the territories it belongs to."""

        if self.is_executing:
            raise InstructionAlreadyExecuting()

        if self.is_executed:
            raise InstructionAlreadyExecuted()

        logger.info(f'[blue]Executing[/blue]: {self.repr_arrow()}')

        self.is_executing = True
        self.assert_is_valid()

        if not self.instruction_set:
            logger.error('Instruction is not in InstructionSet')
            raise InstructionNotInInstructionSet()

        if self.num_troops <= 0 or self.num_troops - self.num_troops_moved <= 0:
            logger.warning(f'No troops left to execute instruction ({self.num_troops} instructed, {self.num_troops - self.num_troops_moved} available)')

        if self.instruction_type in [InstructionType.EXPANSION, InstructionType.DISTRIBUTION]:
            """The destination is neutral or belongs to the same player. We will
            simply move the units from the origin to the destination and set the ownership."""
            logger.debug('Instruction is of type Expansion or Distribution')
            self.resolve_expansion()
        elif self.instruction_type == InstructionType.SKIRMISH:
            if not self.skirmishing_instructions:
                logger.error('Instruction is marked as Skirmish but has no Skirmishing Instructions')
                raise InstructionNoSkirmishingInstructions()

            """There are other Instructions that conflict with this one. This leads to skirmishes.
            We will have to resolve those skirmishes first."""
            logger.debug(f'Found {len(self.skirmishing_instructions)} skirmish' + ('es' if len(self.skirmishing_instructions) > 1 else ''))
            self.resolve_skirmish(self.skirmishing_instructions)
        elif self.instruction_type == InstructionType.INVASION:
            """We are dealing with an invasion here: the target territory already belongs
            to another player. We will have to resolve the battle and units will be lost."""
            logger.debug('Resolving invasion (not an expansion and no skirmishes found)')
            self.resolve_invasion()
        else:
            logger.error(f'Unknown instruction type: {self.instruction_type.name}')
            raise InvalidInstructionType(self.instruction_type.name)

        self.is_executed = True
        self.is_executing = False
        logger.info(
            f'[green]Finished execution[/green] of Instruction id {self.id} with results: \n' +
            f'    - origin     : (id={self.origin.id}, {self.origin.owner.name}, troops={len(self.origin.all(Troop))})\n' +
            f'    - destination: (id={self.destination.id}, {self.destination.owner.name if self.destination.owner else None}, troops={len(self.destination.all(Troop))})')

        if self.is_part_of_loop:
            if instructions_from_target := [
                instruction for instruction in self.instruction_set.instructions
                if instruction.origin == self.destination and not instruction.is_executed
            ]:
                logger.info(f"This instruction was part of a loop; resolving instructions from target:\n  - " + "\n  - ".join([instruction.repr_arrow() for instruction in instructions_from_target]))

            for instruction in instructions_from_target:
                instruction.allow_insufficient_troops().execute()

        return self
