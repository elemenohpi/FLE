from typing import Tuple

import socket


def get_available_port(socket_type: int) -> int:
    with socket.socket(socket.AF_INET, socket_type) as sock:
        sock.bind(("127.0.0.1", 0))
        addr: Tuple[str, int] = sock.getsockname()
        return addr[1]


def get_available_tcp_port() -> int:
    return get_available_port(socket.SOCK_STREAM)


def get_available_udp_port() -> int:
    return get_available_port(socket.SOCK_DGRAM)
