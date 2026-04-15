from __future__ import annotations

from dataclasses import dataclass

DEFAULT_COLORS = ("red", "green", "blue")
SERVICE_NAME = "example_service"


@dataclass(frozen=True)
class Greeting:
    subject: str
    message: str


def greet(subject: str) -> Greeting:
    normalized = subject.strip()
    return Greeting(subject=normalized, message=f"Hello, {normalized}!")


def choose_colors(limit: int = 3) -> list[str]:
    return list(DEFAULT_COLORS[: max(0, limit)])


def build_summary(subject: str, limit: int = 3) -> str:
    greeting = greet(subject)
    colors = choose_colors(limit)
    return f"{greeting.message} Colors: {', '.join(colors)}"


def as_record(subject: str, limit: int = 3) -> dict[str, object]:
    greeting = greet(subject)
    colors = choose_colors(limit)
    return {
        "service": SERVICE_NAME,
        "subject": greeting.subject,
        "message": greeting.message,
        "colors": colors,
    }


def main() -> None:
    print(build_summary("world"))


if __name__ == "__main__":
    main()
