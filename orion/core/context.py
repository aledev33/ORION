from dataclasses import dataclass


@dataclass
class OrionContext:
    listener: object
    speaker: object
    logger: object
    sysctl: object
    search_manager: object