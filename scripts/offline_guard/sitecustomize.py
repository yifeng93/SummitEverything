import ipaddress
import os
import socket

import aiodns

from summit_everything.integrations.settings import MacOSKeychainBackend, SettingsError

_original_connect = socket.socket.connect
_original_connect_ex = socket.socket.connect_ex
_original_getaddrinfo = socket.getaddrinfo
_original_async_getaddrinfo = aiodns.DNSResolver.getaddrinfo


def _allowed(address):
    if isinstance(address, str):
        return True
    host = address[0]
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return host == "localhost"


def _connect(self, address):
    if not _allowed(address):
        raise RuntimeError("review blocks non-loopback sockets")
    return _original_connect(self, address)


def _connect_ex(self, address):
    if not _allowed(address):
        raise RuntimeError("review blocks non-loopback sockets")
    return _original_connect_ex(self, address)


socket.socket.connect = _connect
socket.socket.connect_ex = _connect_ex


def _deny(*args, **kwargs):
    raise SettingsError("credential_store_unavailable")


MacOSKeychainBackend.__init__ = _deny
MacOSKeychainBackend.get = _deny
MacOSKeychainBackend.set = _deny
MacOSKeychainBackend.delete = _deny


# c-ares uses native DNS sockets, so Python socket.connect alone is insufficient.
# DNS is an external boundary: fixtures may explicitly replace this method with
# a synthetic Future, but real name resolution is forbidden in guarded checks.
def _deny_external_dns(self, host, *args, **kwargs):
    try:
        if ipaddress.ip_address(host).is_loopback:
            return _original_async_getaddrinfo(self, host, *args, **kwargs)
    except ValueError:
        pass
    raise AssertionError("offline guard: real DNS resolution forbidden")


def _guard_getaddrinfo(host, *args, **kwargs):
    if not _allowed((host, 0)):
        raise AssertionError("offline guard: system DNS resolution forbidden")
    return _original_getaddrinfo(host, *args, **kwargs)


socket.getaddrinfo = _guard_getaddrinfo


aiodns.DNSResolver.getaddrinfo = _deny_external_dns
os.environ["SUMMIT_OFFLINE_GUARD_ACTIVE"] = "1"
