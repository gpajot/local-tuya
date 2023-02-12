import asyncio
import logging
from typing import Optional, cast

from concurrent_tasks import BackgroundTask

from local_tuya.backoff import Backoff
from local_tuya.events import EventNotifier
from local_tuya.protocol.events import (
    ConnectionEstablished,
    ConnectionLost,
    DataReceived,
    DataSent,
)

logger = logging.getLogger(__name__)


class Transport(asyncio.Protocol):
    def __init__(
        self,
        address: str,
        port: int,
        backoff: Backoff,
        event_notifier: EventNotifier,
    ):
        event_notifier.register(DataSent, self._write)
        self._notifier = event_notifier
        self._address = address
        self._port = port
        self._transport: Optional[asyncio.transports.WriteTransport] = None
        self._closing = False
        self._closed = asyncio.Event()
        self._closed.set()
        self._close_exc: Optional[Exception] = None
        self._connected = asyncio.Event()
        self._backoff = backoff
        self._connect_task = BackgroundTask(self._connect)
        self._receive_task = BackgroundTask(self._receive)
        # We need a queue as `data_received` is not async.
        self._received_bytes: asyncio.Queue[bytes] = asyncio.Queue()

    async def __aenter__(self):
        self._closed.clear()
        await self._connect_task.create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._closing = True
        self._connect_task.cancel()
        self._receive_task.cancel()
        if self._transport:
            self._transport.close()
            # Wait until `connection_lost` was called.
            try:
                await asyncio.wait_for(self._closed.wait(), timeout=10)
                await self._notifier.emit(ConnectionLost(None))
            except asyncio.TimeoutError:
                logger.error("timeout waiting for transport to close")

    async def _connect(self) -> None:
        if self._close_exc:
            exc = self._close_exc
            self._close_exc = None
            await self._notifier.emit(ConnectionLost(exc))
        self._transport = await self._get_transport()
        self._connected.set()
        logger.info("connected to device %s:%i", self._address, self._port)
        await self._notifier.emit(ConnectionEstablished())
        self._receive_task.create()

    async def _get_transport(self) -> asyncio.transports.WriteTransport:
        with self._backoff as backoff:
            while True:
                try:
                    transport, _ = await asyncio.get_running_loop().create_connection(
                        lambda: self,
                        self._address,
                        self._port,
                    )
                    return cast(asyncio.transports.WriteTransport, transport)
                except Exception:
                    logger.warning("could not connect, retrying...", exc_info=True)
                    await backoff()

    def connection_lost(self, exc: Optional[Exception]) -> None:
        self._close_exc = exc
        if not exc:
            logger.info("disconnected from device %s:%i", self._address, self._port)
            # Notify the transport was properly closed.
            self._closed.set()
        else:
            logger.warning(f"connection lost, {exc}, reconnecting...")
            self._connect_task.cancel()
            self._receive_task.cancel()
            # Attempt to reconnect.
            self._connected.clear()
            self._transport = None
            self._received_bytes = asyncio.Queue()
            self._connect_task.create()

    def data_received(self, data: bytes) -> None:
        self._received_bytes.put_nowait(data)

    async def _receive(self) -> None:
        while True:
            data = await self._received_bytes.get()
            await self._notifier.emit(DataReceived(data))

    async def _write(self, data: DataSent) -> None:
        if self._closed.is_set():
            raise RuntimeError("transport is closed")
        if self._closing:
            raise RuntimeError("transport is closing")
        await self._connected.wait()
        # Writing is asynchronous, errors will be raised through the `connection_lost` method.
        cast(asyncio.transports.WriteTransport, self._transport).write(data)
