import time

import pytest

from local_tuya.backoff import SequenceBackoff


class TestSequenceBackoff:
    @pytest.fixture(scope="session")
    def backoff(self):
        return SequenceBackoff(0.01, 0.02)

    async def test_max_index(self, backoff):
        start = time.monotonic()
        with backoff:
            await backoff()
            await backoff()
            await backoff()
        end = time.monotonic()
        assert round(end - start, 2) == 0.05

    async def test_reset(self, backoff):
        start = time.monotonic()
        with backoff:
            await backoff()
        with backoff:
            await backoff()
        end = time.monotonic()
        assert round(end - start, 2) == 0.02
