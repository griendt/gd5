from __future__ import annotations

from abc import abstractmethod, ABC
from collections import defaultdict
from dataclasses import field, dataclass
from enum import Enum
from itertools import count

from gd.excepts import (
    AdjacentTerritoryNotEmpty,
    InstructionAlreadyExecuted,
    InstructionAlreadyExecuting,
    InstructionNotExecuted,
    InstructionNoSkirmishingInstructions,
    InstructionNotInInstructionSet,
    InstructionSetNotConstructible,
    InsufficientInfluencePoints,
    InsufficientUnitsException,
    InvalidInstructionType,
    IssuerAlreadyPresentInWorld,
    IssuerDoesNotOwnTerritory,
    SpawnNotInHeadquarter,
    TargetTerritoryNotAdjacent,
    TerritoryNotNeutral,
    UnwindingLoopedInstructions,
    UnknownPhase,
    MovementsNotChained,
)
from gd.logger import logger
from gd.world import Player, Territory, World, Headquarter, Troop

# Amount of troops to start out with when entering the world.
NUM_TROOPS_START = 5

# Amount of troops penalty by default when invading another player's territory.
NUM_INVASION_PENALTY = 2

# How many IP it costs to spawn bonus troops per turn.
BONUS_TROOP_IP_COST = 10

class Phase(Enum):
    NATURAL = 1
    GENERATION = 2
    CONSTRUCTION = 3
    MOVEMENT = 4
    BATTLE = 5
    FINAL = 6


class Turn:
    instruction_sets: dict[Phase, list[InstructionSet]] = field(default_factory=lambda: list())

    def __init__(self, instructions: list[Instruction | MovementChain], is_initial=True):
        # Here, we will decide which instructions should go in which instruction set.
        # In principle, there should be only one instruction set for each Phase, unless there are Instructions
        # that are _conditional_, i.e. may or may not be executed depending on the outcome of previous ones
        # within the same Phase. Those instructions should, logically, be applied only in a later InstructionSet.
        # In addition, all non-battle movements should be separated from the battle movements, to make
        # sure those movements all occur first.
        for instruction in instructions:
            if isinstance(instruction, MovementChain):
                # Unwrap the MovementChain in its underlying Movements.
                instruction.assert_is_valid()
                instructions += instruction.movements

        # Filter out any MovementChains from the argument, as they are already unwrapped and we don't need them anymore.
        instructions = {instruction for instruction in instructions if isinstance(instruction, Instruction)}

        self.instruction_sets = defaultdict(list)
        for phase in Phase:
            self.register(phase, instructions)
            instructions = {instruction for instruction in instructions if not instruction.instruction_set}

    def register(self, phase: Phase, instructions: set[Instruction]) -> None:
        match phase:
            case phase.NATURAL:
                if constructions := [i for i in instructions if isinstance(i, CreateHeadquarter)]:
                    self.instruction_sets[Phase.NATURAL].append(InstructionSet(instructions=constructions))
            case phase.GENERATION:
                if generations := [i for i in instructions if isinstance(i, SpawnTroops)]:
                    self.instruction_sets[Phase.GENERATION].append(InstructionSet(instructions=generations))
            case phase.MOVEMENT:
                # TODO: Figure out order of movements. For example, there may be distributions A->B and B->C;
                #   those should be figured out in the correct order. We should not depend on the order of the
                #   input for this.
                if distributions := [
                    i for i in instructions
                    if isinstance(i, Movement) and (i.origin.owner is None or i.destination.owner is None or i.issuer == i.origin.owner == i.destination.owner)
                ]:
                    self.instruction_sets[Phase.MOVEMENT].append(InstructionSet(instructions=distributions))
            case phase.BATTLE:
                self.register_battle_phase(instructions)
            case phase.CONSTRUCTION | phase.FINAL:
                # Not yet implemented, or nothing to be done
                pass
            case _:
                raise UnknownPhase(phase)

    def register_battle_phase(self, instructions: set[Instruction]) -> None:
        while True:
            # Filter out instructions that have already been assigned to an InstructionSet.
            if not (instructions := [i for i in instructions if not i.instruction_set]):
                break

            instruction_set = InstructionSet()

            for instruction in instructions:

                if self.instruction_sets.get(Phase.BATTLE):
                    # An invasion InstructionSet has already been made. This means this Instruction
                    # must depend on the outcomes of previous Instructions. Mark the Instruction as such, so that
                    # the Instruction is allowed to be executed partially in case not all conditions are fulfilled.
                    instruction.allow_insufficient_troops()

                if not [i for i in instructions if
                        i.issuer == instruction.issuer and i.destination == instruction.origin]:
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

            self.instruction_sets[Phase.BATTLE].append(instruction_set)

    def execute(self) -> Turn:
        for phase, instruction_sets in self.instruction_sets.items():
            phase_info = ''
            for instruction_set in instruction_sets:
                phase_info += '\n   '
                for instruction in instruction_set.instructions:
                    phase_info += f' - {instruction}\n   '
            logger.info(f'[yellow]Processing phase {phase} with following instructions[/yellow]:{phase_info}')

            for instruction_set in instruction_sets:
                for instruction in instruction_set.instructions:
                    try:
                        instruction.assert_is_valid()
                        instruction.execute()
                    except InstructionAlreadyExecuted:
                        # Another Instruction may have already caused this Instruction to be executed.
                        # This is fine, as long as we check that all Instructions were executed at the end.
                        pass

                if any([not instruction.is_executed for instruction in instruction_set.instructions]):
                    # All Instructions must be executed before moving on to the next InstructionSet.
                    raise InstructionNotExecuted

        return self


class Instruction(ABC):
    next_id = count(1)
    id: int
    issuer: Player

    instruction_set: InstructionSet = None
    instruction_type: InstructionType = None
    is_executing: bool = False
    is_executed: bool = False

    def __init__(self, issuer: Player, instruction_set: InstructionSet = None,
                 instruction_type: InstructionType = None):
        self.issuer = issuer
        self.id = next(self.next_id)
        self.instruction_set = instruction_set
        self.instruction_type = instruction_type

    @abstractmethod
    def assert_is_valid(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def execute(self) -> Instruction:
        raise NotImplementedError

    def __str__(self) -> str:
        raise NotImplementedError


class CreateHeadquarter(Instruction):
    territory: Territory
    world: World

    def __init__(self, issuer: Player, territory: Territory, instruction_set: InstructionSet = None):
        super().__init__(issuer=issuer, instruction_set=instruction_set)
        self.territory = territory
        self.world = territory.world
        self.instruction_type = InstructionType.CREATE_HEADQUARTER

    def __str__(self) -> str:
        return f"Create Headquarter (issuer={self.issuer.name}, id={self.territory.id})"

    def assert_is_valid(self) -> None:
        if not self.territory.is_neutral():
            raise TerritoryNotNeutral()

        for territory in self.world.territories.values():
            if territory.owner == self.issuer:
                raise IssuerAlreadyPresentInWorld()

        for territory in self.territory.adjacent_territories:
            if not territory.is_empty() and territory.owner.name != 'Barbarian':
                raise AdjacentTerritoryNotEmpty()

    def execute(self) -> CreateHeadquarter:
        self.territory.owner = self.issuer

        Headquarter(territory=self.territory)
        for _ in range(NUM_TROOPS_START):
            Troop(territory=self.territory)

        self.is_executed = True

        return self


class SpawnTroops(Instruction):
    num_troops: int
    territory: Territory

    def __init__(self, issuer: Player, territory: Territory, num_troops: int = 3):
        super().__init__(issuer=issuer)
        self.territory = territory
        self.num_troops = num_troops

    def __str__(self) -> str:
        return f"Spawn Troops (issuer={self.issuer.name}, id={self.territory.id}, num_troops={self.num_troops})"

    def assert_is_valid(self) -> None:
        if self.territory not in self.issuer.owned_territories:
            raise IssuerDoesNotOwnTerritory()

        if not (territories_with_hq := {t for t in self.issuer.owned_territories if t.has_construct(Headquarter)}):
            logger.debug("Issuer has no Headquarter, hence may spawn here")
            return

        if self.territory not in territories_with_hq:
            raise SpawnNotInHeadquarter()

    def execute(self) -> Instruction:
        for _ in range(self.num_troops):
            Troop(territory=self.territory)

        self.is_executed = True
        return self


class SpawnBonusTroops(SpawnTroops):
    """At the cost of 10IP, a Player can decide to spawn additional troops."""
    num_troops: int
    territory: Territory

    def __init__(self, issuer: Player, territory: Territory, num_troops: int = 2):
        super().__init__(issuer=issuer, territory=territory, num_troops=num_troops)

    def __str__(self) -> str:
        return f"Spawn Bonus Troops (issuer={self.issuer.name}, id={self.territory.id}, num_troops={self.num_troops})"

    def assert_is_valid(self) -> None:
        if self.issuer.influence_points < BONUS_TROOP_IP_COST:
            raise InsufficientInfluencePoints()

        super().assert_is_valid()

    def execute(self) -> Instruction:
        self.issuer.influence_points -= 10
        return super().execute()


class MovementChain:
    movements: list[Movement]
    world: World

    """Convenience class to quickly define a chain of movements by the same Player.
    An entry in origin_num_destinations is a tuple of three integers: the origin territory ID,
    the amount of Troops moving, and the destination territory ID.
    """
    def __init__(self, issuer: Player, world: World, origin_num_destinations: list[tuple[int, int, int]]):
        self.issuer = issuer
        self.world = world
        self.movements = []

        for (origin, num_troops, destination) in origin_num_destinations:
            self.movements.append(Movement(
                issuer=self.issuer,
                origin=self.world.territories[origin],
                destination=self.world.territories[destination],
                num_troops=num_troops,
                instruction_set=None
            ))

    def assert_is_valid(self) -> None:
        for index, movement in enumerate(self.movements):
            if index == 0:
                continue

            if movement.origin != self.movements[index - 1].destination:
                raise MovementsNotChained()

            if movement.issuer != self.movements[index - 1].issuer:
                raise


class Movement(Instruction):
    """A basic order is invoked by someone and concerns the movement
    of some units from an origin to a destination."""
    origin: Territory
    destination: Territory
    skirmishing_movements: list[Movement] = None
    mutual_invasion: Movement = None

    _allow_insufficient_troops: bool = False
    _is_part_of_loop: bool = False
    _num_troops: int = 0
    _num_troops_moved: int = 0

    def __init__(self, issuer: Player, origin: Territory, destination: Territory, num_troops: int = 0, instruction_set: InstructionSet = None):
        super().__init__(issuer=issuer, instruction_set=instruction_set)
        self.origin = origin
        self.destination = destination
        self._num_troops = num_troops
        self._num_troops_moved = 0

        # Make sure to register this Instruction to its InstructionSet.
        if self.instruction_set and self not in self.instruction_set.instructions:
            self.instruction_set.add_instruction(self)

    def __hash__(self):
        return hash(self.id)

    def __str__(self) -> str:
        return (
                f'{{id={self.id}, issuer={self.issuer.name}}} (id={self.origin.id}, owner={self.origin.owner.name if self.origin.owner else None}, troops={len(self.origin.all(Troop))})-[{self._num_troops - self._num_troops_moved}/{self._num_troops}]->' +
                f'(id={self.destination.id}, {self.destination.owner.name if self.destination.owner else None}, troops={len(self.destination.all(Troop))})'
        )

    def allow_insufficient_troops(self, value: bool = True) -> Movement:
        self._allow_insufficient_troops = value
        return self

    def assert_is_valid(self) -> None:
        """Do some sanity checks to determine whether this Instruction makes sense.
        This method should be called before or during execution to prevent unwanted changes
        to the world map."""
        if self.origin.owner != self.issuer:
            logger.error('Invalid instruction: issuer is not the origin owner')
            raise IssuerDoesNotOwnTerritory("Issuer is not the origin owner")

        if self._num_troops > (troops_in_origin := len({unit for unit in self.origin.all(Troop)})):
            if self._allow_insufficient_troops:
                logger.info(
                    f'Insufficient troops ({troops_in_origin}) in origin; {self._num_troops} requested, but partial assignment is allowed')
            else:
                logger.error(
                    f'Invalid instruction: insufficient troops in origin territory: {self._num_troops} requested, {troops_in_origin} found')
                raise InsufficientUnitsException(Troop, self._num_troops)

        if self.destination not in self.origin.adjacent_territories:
            raise TargetTerritoryNotAdjacent("Destination is not linked to the origin")

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
            logger.info(f"This invasion has superseding movements:\n  - " + "\n  - ".join(
                [str(invasion) for invasion in higher_priority_movements]))
            try:
                for instruction in higher_priority_movements:
                    instruction.execute()
            except (InstructionAlreadyExecuting, UnwindingLoopedInstructions) as exception:
                # We must have a circular loop. Check all the instrutions that are currently executing,
                # and take the one with the lowest origin territory number. As a tie-breaker, that one will be
                # used to resolve the circle first.

                first_origin_id = min([instruction.origin.id for instruction in self.instruction_set.instructions if
                                       instruction.is_executing])
                self._is_part_of_loop = True

                if isinstance(exception, InstructionAlreadyExecuting):
                    # Only print some useful logging when first encountering the loop, to avoid clutter during unwinding.
                    logger.info(f"Found circular set of instructions\n  - " + "\n  - ".join(
                        [str(instruction) for instruction in self.instruction_set.instructions if
                         instruction.is_executing]
                    ))
                    logger.info(f"The chosen origin id to be executed from is {first_origin_id}")

                if self.origin.id == first_origin_id:
                    logger.debug(f"Found instruction with lowest origin id ({self.origin.id}), resolving first")
                else:
                    # Re-raise the exception so the previous instruction in the loop can catch it.
                    logger.debug(f"The current instruction is not the one with lowest origin id; skipping")
                    raise UnwindingLoopedInstructions()

            logger.info(f"Resolved superseding invasions for instruction id {self.id}")
            for instruction in [instruction for instruction in self.instruction_set.instructions if
                                instruction.is_executing and instruction != self]:
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
                for _ in range(NUM_INVASION_PENALTY):
                    self.origin.remove_unit(Troop)
                    origin_penalty += 1
                    if is_mutual_invasion:
                        self.destination.remove_unit(Troop)
                        destination_penalty += 1
                    self._num_troops_moved += 1
            except InsufficientUnitsException as e:
                if not self._allow_insufficient_troops:
                    raise e

            logger.debug(f'Applied {origin_penalty} troop penalty to the invader')
            if is_mutual_invasion:
                logger.info(f'Also applied {destination_penalty} troop penalty to the target due to mutual invasion')

        while self._num_troops > self._num_troops_moved:
            # Remove a troop from both sides in an equal ratio, as long as this is possible
            # and we still have troops to move.
            if self.origin.all(Troop) and self.destination.all(Troop):
                self.origin.remove_unit(Troop, 1, self._allow_insufficient_troops)
                self.destination.remove_unit(Troop, 1, self._allow_insufficient_troops)
            else:
                # Either army is completely exhausted.
                # The battle ends.
                logger.debug(
                    f'At least one army is completely exhausted; the battle ends after {self._num_troops_moved} of requested {self._num_troops} invaders have been killed')
                break

            self._num_troops_moved += 1

        # Determine whether the attacker has units left. If so, move them to the target
        # territory and set the attacker as the new owner of the target.
        if remainder := self.origin.take_unit(Troop, self._num_troops - self._num_troops_moved,
                                              self._allow_insufficient_troops):
            # If the attacker has Troops remaining, move them to the target territory.
            self.destination.set_owner(self.origin.owner)

            if isinstance(remainder, Troop):
                remainder.move(self.destination)
                self._num_troops_moved += 1
            else:
                for troop in remainder:
                    troop.move(self.destination)
                    self._num_troops_moved += 1
        elif self.destination.is_empty():
            # The destination has been rendered empty with this invasion. This will
            # turn the destination neutral.
            self.destination.owner = None

    def resolve_skirmish(self, skirmishes: list[Movement]) -> None:
        """This is a skirmish with other Instructions. Right now we're assuming each Instruction
        belongs to a different player, and hence they can be treated as individual armies. Note that two
        Instructions with the same destination can belong to the same player and they will be treated as
        two separate armies; however, those two armies do not skirmish."""
        logger.debug(f'{self} has skirmishes with:')
        logger.indents += 1
        for skirmish in skirmishes:
            logger.debug(f'- {skirmish}')
        logger.indents -= 1
        issuers = {instruction.issuer for instruction in skirmishes}
        issuers.add(self.issuer)

        # First, we will check which party has the least amount of troops in this skirmish.
        # We can then subtract troops from all skirmishes up until this point, after which
        # that party (or parties) has run out of troops. The skirmish may continue with fewer
        # parties involved, but that can be its own separate resolve.
        min_troops_to_move_among_skirmishes = min(
            list(map(lambda instruction: instruction._num_troops - instruction._num_troops_moved, skirmishes)) +
            [self._num_troops - self._num_troops_moved]
        )
        logger.debug(f'Removing {min_troops_to_move_among_skirmishes} troops from all skirmishing territories')

        for i in range(min_troops_to_move_among_skirmishes):
            # Subtract a troop.
            self.origin.take_unit(Troop).remove()
            self._num_troops_moved += 1

            # Subtract a troop from all involved parties.
            for skirmish in skirmishes:
                skirmish.origin.take_unit(Troop).remove()
                skirmish._num_troops_moved += 1

        # At least one skirmish has now been completed. Mark those instructions as executed.
        for skirmish in skirmishes:
            if skirmish._num_troops_moved == skirmish._num_troops:
                skirmish.is_executed = True

        if self._num_troops_moved == self._num_troops:
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
        if self.origin.take_unit(Troop, self._num_troops - self._num_troops_moved):
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
            logger.debug(
                f'Movement to {self.destination.id} was originally an expansion, but a new owner ({self.destination.owner.name}) has been detected; resolving to invasion')
            return self.resolve_invasion()

        logger.debug(f'Movement to {self.destination.id} is considered an expansion or relocation')
        self.destination.set_owner(self.issuer)

        while self._num_troops > self._num_troops_moved:
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
            self._num_troops_moved += 1

        logger.debug(f'Moved {self._num_troops_moved} troops')

    def execute(self) -> Movement:
        """Execute the order. This will alter the territories it belongs to."""

        if self.is_executing:
            raise InstructionAlreadyExecuting()

        if self.is_executed:
            raise InstructionAlreadyExecuted()

        logger.info(f'[blue]Executing[/blue]: {self}')

        self.is_executing = True
        self.assert_is_valid()

        if not self.instruction_set:
            logger.error('Instruction is not in InstructionSet')
            raise InstructionNotInInstructionSet()

        if self._num_troops <= 0 or self._num_troops - self._num_troops_moved <= 0:
            logger.warning(
                f'No troops left to execute instruction ({self._num_troops} instructed, {self._num_troops - self._num_troops_moved} available)')

        match self.instruction_type:
            case InstructionType.EXPANSION | InstructionType.DISTRIBUTION:
                """The destination is neutral or belongs to the same player. We will
                simply move the units from the origin to the destination and set the ownership."""
                logger.debug('Instruction is of type Expansion or Distribution')
                self.resolve_expansion()
            case InstructionType.SKIRMISH:
                if not self.skirmishing_movements:
                    logger.error('Instruction is marked as Skirmish but has no Skirmishing Instructions')
                    raise InstructionNoSkirmishingInstructions()

                """There are other Instructions that conflict with this one. This leads to skirmishes.
                We will have to resolve those skirmishes first."""
                logger.debug(f'Found {len(self.skirmishing_movements)} skirmish' + (
                    'es' if len(self.skirmishing_movements) > 1 else ''))
                self.resolve_skirmish(self.skirmishing_movements)
            case InstructionType.INVASION:
                """We are dealing with an invasion here: the target territory already belongs
                to another player. We will have to resolve the battle and units will be lost."""
                logger.debug('Resolving invasion (not an expansion and no skirmishes found)')
                self.resolve_invasion()
            case _:
                logger.error(f'Unknown instruction type: {self.instruction_type.name}')
                raise InvalidInstructionType(self.instruction_type.name)

        self.is_executed = True
        self.is_executing = False
        logger.info(
            f'[green]Finished execution[/green] of Instruction id {self.id} with results: \n' +
            f'    - origin     : (id={self.origin.id}, {self.origin.owner.name}, troops={len(self.origin.all(Troop))})\n' +
            f'    - destination: (id={self.destination.id}, {self.destination.owner.name if self.destination.owner else None}, troops={len(self.destination.all(Troop))})')

        if self._is_part_of_loop:
            if movements_from_target := [
                instruction for instruction in self.instruction_set.movements
                if instruction.origin == self.destination and not instruction.is_executed
            ]:
                logger.info(
                    f"This instruction was part of a loop; resolving instructions from target:\n  - " + "\n  - ".join(
                        [str(instruction) for instruction in movements_from_target]))

            for instruction in movements_from_target:
                instruction.allow_insufficient_troops().execute()

        return self


@dataclass
class InstructionSet:
    """Instructions are to be invoked in conjunction with other instructions: they are not standalone.
    Consider for example a skirmish: this is a combination of two or more Instructions whose result
    is altered by each other's existence. This class orchestrates this behaviour and allows Instructions
    to see which other Instructions are relevant for its own execution."""

    instructions: list[Instruction] = field(default_factory=lambda: list())

    @property
    def movements(self) -> list[Movement]:
        return [instruction for instruction in self.instructions if isinstance(instruction, Movement)]

    def add_instruction(self, instruction: Instruction) -> None:
        """The preferred way to add instructions. This is because the InstructionSet may hydrate Instructions with
        extra info, such as whether it is a skirmish and/or invasion and so on."""
        if instruction in self.instructions:
            return

        instruction.instruction_set = self
        self.instructions.append(instruction)

        if isinstance(instruction, Movement):
            self.set_movement_type(instruction)

    def set_movement_type(self, instruction: Movement) -> None:
        if instruction.issuer == instruction.destination.owner:
            instruction.instruction_type = InstructionType.DISTRIBUTION
        elif [
            instr for instr in self.movements
            if instr.destination == instruction.destination and instr.issuer != instruction.issuer and instr.issuer != instr.destination.owner
        ]:
            # There is another Player attempting to expand/invade to this destination. Hence, we're dealing with a skirmish.
            # Note that if this other Player is the same player as the destination owner (if any), there is no skirmish, because
            # such a movement is a Distribution, which is to be executed before attacks.
            instructions_to_same_destination = [instr for instr in self.movements if
                                                instr.destination == instruction.destination]
            for instr in instructions_to_same_destination:
                instr.instruction_type = InstructionType.SKIRMISH
                instr.skirmishing_movements = [i for i in instructions_to_same_destination if i != instr]
        elif instruction.destination.is_neutral():
            instruction.instruction_type = InstructionType.EXPANSION
        else:
            # The target Territory belongs to a different Player. Therefore this is an Invasion.
            instruction.instruction_type = InstructionType.INVASION
            try:
                mutual_invasion = [
                    instr for instr in self.movements
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

            if isinstance(instruction, Movement):
                self.set_movement_type(instruction)


class InstructionType(Enum):
    EXPANSION = 1
    DISTRIBUTION = 2
    INVASION = 3
    SKIRMISH = 4
    CREATE_HEADQUARTER = 5
