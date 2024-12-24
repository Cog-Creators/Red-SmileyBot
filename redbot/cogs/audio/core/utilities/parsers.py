import re
import struct

from typing import Final, Optional

import aiohttp
from red_commons.logging import getLogger

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = getLogger("red.cogs.Audio.cog.Utilities.Parsing")

STREAM_TITLE: Final[re.Pattern] = re.compile(rb"StreamTitle='([^']*)';")


class ParsingUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def icyparser(self, url: str) -> Optional[str]:
        try:
            async with self.session.get(url, headers={"Icy-MetaData": "1"}) as resp:
                metaint = int(resp.headers["icy-metaint"])
                for _ in range(5):
                    await resp.content.readexactly(metaint)
                    metadata_length = struct.unpack("B", await resp.content.readexactly(1))[0] * 16
                    metadata = await resp.content.readexactly(metadata_length)
                    m = re.search(STREAM_TITLE, metadata.rstrip(b"\0"))
                    if m:
                        title = m.group(1)
                        if title:
                            title = title.decode("utf-8", errors="replace")
                            return title
                    else:
                        return None
        except (KeyError, aiohttp.ClientConnectionError, aiohttp.ClientResponseError):
            return None
