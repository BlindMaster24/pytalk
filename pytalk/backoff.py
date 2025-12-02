"""Module provides a Backoff class for implementing exponential backoff."""

import random
from dataclasses import dataclass
from enum import Enum
from typing import cast


class JitterType(Enum):
    """Enum representing different types of jitter."""

    NONE = 0
    FULL = 1
    HALF = 2


@dataclass
class BackoffConfig:
    """Configuration for the Backoff class."""

    base: int = 1
    exponent: float = 2
    max_value: float = 60
    max_tries: int | None = None
    jitter_type: JitterType = JitterType.HALF


class Backoff:
    """A class for implementing exponential backoff with configurable jitter."""

    def __init__(
        self,
        config: BackoffConfig | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize the Backoff instance.

        Args:
            config: An optional BackoffConfig object to use for configuration.
            **kwargs: Individual configuration parameters (base, exponent, etc.)
                      that will override values in the provided config object.
                      If no config object is provided, these will be used with
                      default BackoffConfig values.

        """
        if config is None:
            config = BackoffConfig()

        # Apply kwargs over config defaults
        self.base: int = cast("int", kwargs.get("base", config.base))
        self.exponent: float = cast("float", kwargs.get("exponent", config.exponent))
        self.max_value: float = cast("float", kwargs.get("max_value", config.max_value))
        self.max_tries: int | None = cast(
            "int | None", kwargs.get("max_tries", config.max_tries)
        )
        self.jitter_type: JitterType = cast(
            "JitterType", kwargs.get("jitter_type", config.jitter_type)
        )
        self.attempts: int = 0

    def _calculate_jittered_delay(self, calculated_delay: float) -> float:
        if self.jitter_type == JitterType.NONE:
            return calculated_delay
        if self.jitter_type == JitterType.FULL:
            return random.uniform(0, calculated_delay)  # noqa: S311
        if self.jitter_type == JitterType.HALF:
            return random.uniform(0.5 * calculated_delay, calculated_delay)  # noqa: S311
        raise ValueError(f"Unknown jitter type: {self.jitter_type}")

    def delay(self) -> float | None:
        """Calculate the next delay.

        Returns:
            The next delay in seconds, or None if max_tries has been reached.

        """
        if self.max_tries is not None and self.attempts >= self.max_tries:
            return None

        calculated_delay = self.base * (self.exponent**self.attempts)
        jittered_delay = self._calculate_jittered_delay(calculated_delay)
        actual_delay = min(jittered_delay, self.max_value)

        self.attempts += 1
        return actual_delay

    def reset(self) -> None:
        """Reset the attempts counter."""
        self.attempts = 0
