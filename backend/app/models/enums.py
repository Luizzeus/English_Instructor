import enum


class CefrLevel(str, enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class SessionModality(str, enum.Enum):
    TEXT = "text"
    VOICE = "voice"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MessageAuthor(str, enum.Enum):
    STUDENT = "student"
    BOT = "bot"


class ExerciseType(str, enum.Enum):
    SENTENCE_COMPLETION = "sentence_completion"
    MULTIPLE_CHOICE = "multiple_choice"
    REFORMULATION = "reformulation"
    SHADOWING = "shadowing"
