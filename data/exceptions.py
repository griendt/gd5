class InstructionException(Exception):
    """Base class for exceptions that have to do with Orders."""
    pass


class InvalidInstruction(InstructionException):
    pass


class InstructionAlreadyExecuted(InstructionException):
    def __init__(self, *args, **kwargs):
        super().__init__("Instruction already executed", *args, **kwargs)
