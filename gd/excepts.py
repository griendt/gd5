class InstructionException(Exception):
    """Base class for exceptions that have to do with Instructions."""
    pass


class InvalidInstruction(InstructionException):
    pass


class IssuerDoesNotOwnTerritory(InstructionException):
    pass


class SpawnNotInHeadquarter(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("Issuer must spawn in one of their Headquarters, but the given Territory contains no Headquarter", *args, **kwargs)


class InsufficientInfluencePoints(InstructionException):
    pass


class TargetTerritoryNotAdjacent(InstructionException):
    pass


class InstructionAlreadyExecuting(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("Instruction already executing", *args, **kwargs)


class UnwindingLoopedInstructions(InstructionException):
    """This is a helper class to unwind a loop and not actually an exception."""
    pass


class InstructionAlreadyExecuted(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("Instruction already executed", *args, **kwargs)


class InsufficientUnitsException(InstructionException):
    def __init__(self, cls: type, amount: int, *args, **kwargs):
        super().__init__(f"Insufficient units of type {cls} to fetch {amount} of", *args, **kwargs)


class InstructionNotInInstructionSet(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("Instruction must be in an InstructionSet prior to execution", *args, **kwargs)


class InstructionNoSkirmishingInstructions(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("Instruction is marked as Skirmish, but has no linked Skirmish Instructions", *args, **kwargs)


class InvalidInstructionType(InstructionException):
    def __init__(self, instruction_type: str, *args, **kwargs):
        super().__init__(f"Instruction is of unexpected type: '{instruction_type}'", *args, **kwargs)


class InstructionSetNotConstructible(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(f"Could not construct an InstructionSet from the given Instructions", *args, **kwargs)


class InstructionNotExecuted(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("Instruction expected to be executed, but was not", *args, **kwargs)


class IssuerAlreadyPresentInWorld(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("Issuer is already present in the world", *args, **kwargs)


class AdjacentTerritoryNotEmpty(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("An adjacent territory contains units", *args, **kwargs)


class TerritoryNotNeutral(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("The territory is not neutral", *args, **kwargs)


class UnknownPhase(Exception):
    def __init__(self, phase, *args, **kwargs):
        super().__init__(f"Unknown phase type: {phase}", *args, **kwargs)
