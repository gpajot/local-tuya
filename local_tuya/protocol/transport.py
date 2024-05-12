import asyncio
import logging
import re
from typing import Optional, cast

from concurrent_tasks import BackgroundTask

from local_tuya.backoff import Backoff
from local_tuya.events import EventNotifier
from local_tuya.protocol.events import (
    ConnectionClosed,
    ConnectionEstablished,
    DataReceived,
    DataSent,
    ResponseReceived,
)

logger = logging.getLogger(__name__)


class Transport(asyncio.Protocol):
    def __init__(
        self,
        address: str,
        port: int,
        backoff: Backoff,
        timeout: float,
        event_notifier: EventNotifier,
    ):
        event_notifier.register(DataSent, self._write)
        event_notifier.register(ResponseReceived, self._connection_live)
        self._address = address
        self._port = port
        self._backoff = backoff
        self._timeout = timeout
        self._notifier = event_notifier

        self._transport: Optional[asyncio.transports.WriteTransport] = None
        self._closing = False
        self._closed = asyncio.Event()
        self._closed.set()
        self._close_exc: Optional[Exception] = None
        self._connected = asyncio.Event()
        self._connect_task = BackgroundTask(self._connect)
        self._receive_task = BackgroundTask(self._receive)
        # We need a queue as `data_received` is not async.
        self._received_bytes: asyncio.Queue[bytes] = asyncio.Queue()

    async def __aenter__(self):
        self._closed.clear()
        self._connect_task.create()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self._closing = True
        self._connect_task.cancel()
        self._receive_task.cancel()
        if self._transport:
            await self._notifier.emit(ConnectionClosed(None))
            self._transport.close()
            # Wait until `connection_lost` was called.
            try:
                await asyncio.wait_for(self._closed.wait(), timeout=self._timeout)
            except asyncio.TimeoutError:
                logger.error("timeout waiting for transport to close")

    async def _connect(self) -> None:
        # Handle errors here as `connection_lost` is not async.
        if self._close_exc:
            exc = self._close_exc
            self._close_exc = None
            await self._notifier.emit(ConnectionClosed(exc))
        while True:
            await self._backoff.wait()
            try:
                self._transport = await self._get_transport()
                break
            except Exception:
                logger.warning("could not connect, retrying...", exc_info=True)
        self._connected.set()
        logger.info("connected to device %s:%i", self._address, self._port)
        await self._notifier.emit(ConnectionEstablished())
        self._receive_task.create()

    async def _get_transport(self) -> asyncio.transports.WriteTransport:
        transport, _ = await asyncio.wait_for(
            asyncio.get_running_loop().create_connection(
                lambda: self,
                await _get_host(self._address),
                self._port,
            ),
            self._timeout,
        )
        return cast(asyncio.transports.WriteTransport, transport)

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

    def _connection_live(self, _: ResponseReceived) -> None:
        # While this event has not been received, we assume the connection is not necessarily healthy.
        # It is possible to be connected and not be able to communicated with the device.
        # We assume the connection to be healthy we can receive responses.
        # As long as it is unhealthy, connection attempts will increase the backoff.
        self._backoff.reset()

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


async def _get_host(address: str) -> str:
    """Resolve MAC to IP if given."""
    if re.match(r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$", address):
        process = await asyncio.create_subprocess_shell(
            f"arp -n | grep -w -i '{address}' | awk '{{print $1}}'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await process.communicate()
        if not stdout:
            raise ValueError(f"no device found for MAC {address}")
        return stdout.decode().strip()
    return address
