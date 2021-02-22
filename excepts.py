class InstructionException(Exception):
    """Base class for exceptions that have to do with Orders."""
    pass


class InvalidInstruction(InstructionException):
    pass


class InstructionAlreadyExecuted(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("Instruction already executed", *args, **kwargs)


class InsufficientUnitsException(Exception):
    def __init__(self, cls: type, amount: int, *args, **kwargs):
        super().__init__(f"Insufficient units of type {cls} to fetch {amount} of", *args, **kwargs)


class InstructionNotInInstructionSet(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__("Instruction must be in an InstructionSet prior to execution", *args, **kwargs)
