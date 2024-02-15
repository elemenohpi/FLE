""" An rcon client
Similar to https://github.com/mark9064/factorio-rcon-py except it allows interleaved calls instead of throwing a CLIENT_BUSY error

See https://developer.valvesoftware.com/wiki/Source_RCON_Protocol for the protocol spec.
"""
from typing import TYPE_CHECKING, Dict, Optional

import asyncio
import logging
import struct
from asyncio.futures import Future
from asyncio.streams import StreamReader, StreamWriter
from dataclasses import dataclass, field

LOG = logging.getLogger(__name__)


class RCONAuthFailure(Exception):
    pass


@dataclass
class _Packet:
    pkt_id: int
    type: int
    body: str


class RCONClient:
    def __init__(self, hostname: str, port: int, password: str):
        self.hostname = hostname
        self.port = port
        self.password = password
        self._next_id: int = 0
        self._reader: Optional[StreamReader] = None
        self._writer: Optional[StreamWriter] = None
        self._expected_responses_by_request_id: Dict[int, _ExpectedResponse] = {}

    async def aclose(self) -> None:
        if self._writer is not None:
            self._writer.close()
            await self._writer.wait_closed()
            self._writer = None
        if self._reader is not None:
            self._reader = None
        self._next_id = 0
        self._expected_responses_by_request_id = {}

    async def send_command(self, command: str, timeout_seconds: float = 10.0) -> str:
        """Returns the response to command"""
        pkt = _Packet(self._get_next_id(), _SERVERDATA_EXECCOMMAND, command)
        return (await self._send_packet(pkt, timeout_seconds)).body

    async def connect(self, timeout_seconds: float = 10.0) -> None:
        """Makes TCP connection and do login
        Raises RCONAuthFailure on failure to auth"""
        # TODO Apply timeout to whole func
        await self.aclose()
        self._reader, self._writer = await asyncio.open_connection(
            self.hostname, self.port
        )
        asyncio.create_task(
            _consume_reader(self._reader, self._expected_responses_by_request_id)
        )
        login_pkt = _Packet(self._get_next_id(), _SERVERDATA_AUTH, self.password)
        response = await self._send_packet(login_pkt, timeout_seconds)
        # The above line should have raised an exception were this not true.
        assert login_pkt.pkt_id == response.pkt_id

    async def _send_packet(self, pkt: _Packet, timeout_seconds: float) -> _Packet:
        async def inner_send() -> _Packet:
            expected_response = _ExpectedResponse(
                is_auth=pkt.type == _SERVERDATA_AUTH,
            )
            # Take a local ref to self._expected_responses_by_request_id because it can be replaced during close()
            expected_responses_by_request_id = self._expected_responses_by_request_id
            expected_responses_by_request_id[pkt.pkt_id] = expected_response
            try:
                assert self._writer is not None
                await _write_packet(self._writer, pkt)
                return await expected_response.response_future
            finally:
                del expected_responses_by_request_id[pkt.pkt_id]

        return await asyncio.wait_for(inner_send(), timeout=timeout_seconds)

    def _get_next_id(self) -> int:
        """Returns incremental positive 32 bit signed int id's and wraps around"""
        pkt_id = self._next_id
        self._next_id += 1
        if self._next_id > _MAX_32_BIT_SIGNED_INT:
            self._next_id = 0
        return pkt_id

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.aclose()
        return False


_MAX_32_BIT_SIGNED_INT = (2**31) - 1

# Packet Types
_SERVERDATA_AUTH = 3
_SERVERDATA_AUTH_RESPONSE = 2
_SERVERDATA_EXECCOMMAND = 2
_SERVERDATA_RESPONSE_VALUE = 0


if TYPE_CHECKING:
    # pylint: disable-next=unsubscriptable-object
    FuturePacket = Future[_Packet]
else:
    FuturePacket = Future


@dataclass
class _ExpectedResponse:
    is_auth: bool
    response_future: FuturePacket = field(
        default_factory=lambda: asyncio.get_running_loop().create_future()
    )


async def _write_packet(writer: StreamWriter, pkt: _Packet) -> None:
    packet_bytes = (
        struct.pack("<ii", pkt.pkt_id, pkt.type) + pkt.body.encode("utf8") + b"\x00\x00"
    )
    # pack size of packet + rest of packet data
    packet_with_size = struct.pack("<i", len(packet_bytes)) + packet_bytes
    writer.write(packet_with_size)
    await writer.drain()


async def _read_packet(reader: StreamReader) -> _Packet:
    # Packet Header = 3 * 4 byte
    header_bytes = await reader.readexactly(3 * 4)
    pkt_size, pkt_id, pkt_type = struct.unpack("<iii", header_bytes)
    bytes_already_read_for_id_and_type = 2 * 4
    len_to_read = pkt_size - bytes_already_read_for_id_and_type
    rest_bytes = await reader.readexactly(len_to_read)
    # Discard the last 2 bytes, 1 for the body terminator and one for the packet terminator
    body_bytes = rest_bytes[:-2]
    return _Packet(pkt_id, pkt_type, body_bytes.decode("utf-8"))


async def _consume_reader(
    reader: StreamReader, expected_responses_by_request_id: Dict[int, _ExpectedResponse]
) -> None:
    try:
        while True:
            pkt = await _read_packet(reader)
            if pkt.type == _SERVERDATA_AUTH_RESPONSE:
                # For SERVERDATA_AUTH_RESPONSE pkt_id only matches the id if its successful
                # id -1 is the auth failure sentinel
                if pkt.pkt_id == -1:
                    auth_responses = [
                        r
                        for r in expected_responses_by_request_id.values()
                        if r.is_auth
                    ]
                    # Zero is a problem, and more than one is ambiguous
                    assert len(auth_responses) == 1
                    auth_responses[0].response_future.set_exception(
                        RCONAuthFailure("Auth failed", pkt)
                    )
                    continue
            if pkt.pkt_id not in expected_responses_by_request_id:
                LOG.error(
                    "Recieved response for un-tracked request pkt_id: %s", pkt.pkt_id
                )
                continue
            expected_response = expected_responses_by_request_id[pkt.pkt_id]
            if pkt.type == _SERVERDATA_RESPONSE_VALUE and expected_response.is_auth:
                # Auth is weird. Factorio sends an empty SERVERDATA_RESPONSE_VALUE
                # matching the request id followed by a SERVERDATA_AUTH_RESPONSE
                # Skip this packet so we process the SERVERDATA_AUTH_RESPONSE instead
                continue
            expected_response.response_future.set_result(pkt)
    except asyncio.IncompleteReadError as e:
        LOG.debug(
            "IncompleteReadError in _consume_reader, probably intentional shutdown: %s",
            e,
        )
    except Exception as e:
        LOG.error("Error in _consume_reader: %s", e)
        # TODO signal failure to the client?
        raise
