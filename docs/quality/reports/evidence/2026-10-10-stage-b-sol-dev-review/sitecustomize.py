import socket, ipaddress
_original_connect=socket.socket.connect
_original_connect_ex=socket.socket.connect_ex
def _allowed(address):
    if isinstance(address, str): return True
    host=address[0]
    try: return ipaddress.ip_address(host).is_loopback
    except ValueError: return host == "localhost"
def _connect(self,address):
    if not _allowed(address): raise RuntimeError("review blocks non-loopback sockets")
    return _original_connect(self,address)
def _connect_ex(self,address):
    if not _allowed(address): raise RuntimeError("review blocks non-loopback sockets")
    return _original_connect_ex(self,address)
socket.socket.connect=_connect
socket.socket.connect_ex=_connect_ex
from summit_everything.integrations.settings import MacOSKeychainBackend, SettingsError
def _deny(*args, **kwargs): raise SettingsError("credential_store_unavailable")
MacOSKeychainBackend.__init__=_deny
MacOSKeychainBackend.get=_deny
MacOSKeychainBackend.set=_deny
MacOSKeychainBackend.delete=_deny
