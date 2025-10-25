"""Module provides a Backoff class for implementing exponential backoff."""

import random


class Backoff:
    """A class for implementing exponential backoff with jitter."""

    def __init__(
        self,
        base: int = 1,
        exponent: float = 2,
        max_value: float = 60,
        max_tries: int | None = None,
    ) -> None:
        """Initialize the Backoff instance.

        Args:
            base: The base delay in seconds.
            exponent: The exponent to use for calculating the delay.
            max_value: The maximum delay in seconds.
            max_tries: The maximum number of retries. If None, retries indefinitely.

        """
        self.base = base
        self.exponent = exponent
        self.max_value = max_value
        self.max_tries = max_tries
        self.attempts = 0

    def delay(self) -> float | None:
        """Calculate the next delay.

        Returns:
            The next delay in seconds, or None if max_tries has been reached.

        """
        if self.max_tries is not None and self.attempts >= self.max_tries:
            return None

        calculated_delay = self.base * (self.exponent**self.attempts)

        jitter_delay = random.uniform(0.5 * calculated_delay, calculated_delay)  # noqa: S311

        actual_delay = min(jitter_delay, self.max_value)

        self.attempts += 1
        return actual_delay

    def reset(self) -> None:
        """Reset the attempts counter."""
        self.attempts = 0
