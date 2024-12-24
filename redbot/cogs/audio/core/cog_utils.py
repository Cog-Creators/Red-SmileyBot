from abc import ABC
from typing import Final
from base64 import b64decode
from io import BytesIO
import struct

from redbot import VersionInfo
from redbot.core import commands

from ..converters import get_lazy_converter, get_playlist_converter

__version__ = VersionInfo.from_json({"major": 2, "minor": 5, "micro": 0, "releaselevel": "final"})

__author__ = ["aikaterna", "Draper"]
_SCHEMA_VERSION: Final[int] = 3
_OWNER_NOTIFICATION: Final[int] = 1

LazyGreedyConverter = get_lazy_converter("--")
PlaylistConverter = get_playlist_converter()


class CompositeMetaClass(type(commands.Cog), type(ABC)):
    """
    This allows the metaclass used for proper type detection to
    coexist with discord.py's metaclass
    """

    pass


# Both DataReader and DataWriter are taken from https://github.com/Devoxin/Lavalink.py/blob/master/lavalink/datarw.py
# These are licenced under MIT, Thanks Devoxin for putting these together!
# The license can be found in https://github.com/Devoxin/Lavalink.py/blob/master/LICENSE


class DataReader:
    def __init__(self, ts):
        self._buf = BytesIO(b64decode(ts))

    def _read(self, n):
        return self._buf.read(n)

    def read_byte(self):
        return self._read(1)

    def read_boolean(self):
        (result,) = struct.unpack("B", self.read_byte())
        return result != 0

    def read_unsigned_short(self):
        (result,) = struct.unpack(">H", self._read(2))
        return result

    def read_int(self):
        (result,) = struct.unpack(">i", self._read(4))
        return result

    def read_long(self):
        (result,) = struct.unpack(">Q", self._read(8))
        return result

    def read_utf(self):
        text_length = self.read_unsigned_short()
        return self._read(text_length)


class DataWriter:
    def __init__(self):
        self._buf = BytesIO()

    def _write(self, data):
        self._buf.write(data)

    def write_byte(self, byte):
        self._buf.write(byte)

    def write_boolean(self, b):
        enc = struct.pack("B", 1 if b else 0)
        self.write_byte(enc)

    def write_unsigned_short(self, s):
        enc = struct.pack(">H", s)
        self._write(enc)

    def write_int(self, i):
        enc = struct.pack(">i", i)
        self._write(enc)

    def write_long(self, l):
        enc = struct.pack(">Q", l)
        self._write(enc)

    def write_utf(self, s):
        utf = s.encode("utf8")
        byte_len = len(utf)

        if byte_len > 65535:
            raise OverflowError("UTF string may not exceed 65535 bytes!")

        self.write_unsigned_short(byte_len)
        self._write(utf)

    def finish(self):
        with BytesIO() as track_buf:
            byte_len = self._buf.getbuffer().nbytes
            flags = byte_len | (1 << 30)
            enc_flags = struct.pack(">i", flags)
            track_buf.write(enc_flags)

            self._buf.seek(0)
            track_buf.write(self._buf.read())
            self._buf.close()

            track_buf.seek(0)
            return track_buf.read()
