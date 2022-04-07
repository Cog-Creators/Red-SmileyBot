import pytest
from redbot.pytest.audio import *


@pytest.mark.asyncio
async def test_command_play_bandcamp_custom_domain(audio, ctx):
    url = f"https://jazzinbritain.co.uk/album/revisiting-tanglewood-63-the-early-tapes"

    inv = await audio.scrape_bandcamp_url(url)

    assert inv is not None
