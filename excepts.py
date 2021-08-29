class InstructionException(Exception):
    """Base class for exceptions that have to do with Orders."""
    pass


class InvalidInstruction(InstructionException):
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
