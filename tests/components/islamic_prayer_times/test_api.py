"""Tests for Islamic Prayer Times init."""
from datetime import timedelta
import re
from unittest.mock import patch

from homeassistant.components import islamic_prayer_times
import homeassistant.util.dt as dt_util

from tests.common import MockConfigEntry, async_fire_time_changed

from . import (  # MOCK_RESPONSE2,; NEW_PRAYER_TIMES,; PRAYER_TIMES,
    MOCK_RESPONSE,
    MOCK_RESPONSE1,
    NEW_PRAYER_TIMES_TIMESTAMPS,
    NOW,
    PRAYER_TIMES_TIMESTAMPS,
)


async def test_async_update(hass, aioclient_mock):
    """Test sensors are updated with new prayer times."""
    entry = MockConfigEntry(domain=islamic_prayer_times.DOMAIN, data={})
    entry.add_to_hass(hass)

    # generate responses for the 7 days timings
    for i in range(0, 8):
        timestamp = int(dt_util.as_timestamp(NOW + timedelta(days=i)))
        url = f"{islamic_prayer_times.const.API_URL}/{timestamp}"
        aioclient_mock.get(
            re.compile(url + ".+"), json=MOCK_RESPONSE[i],
        )

    with patch("homeassistant.util.dt.now", return_value=NOW):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        pt_data = hass.data[islamic_prayer_times.DOMAIN]
        assert pt_data.today_prayer_times == PRAYER_TIMES_TIMESTAMPS
        # assert pt_data.weekly_prayer_times ==

        future = pt_data.today_prayer_times["Midnight"] + timedelta(days=1, minutes=1)

    with patch("homeassistant.util.dt.now", return_value=NOW + timedelta(days=1)):
        async_fire_time_changed(hass, future)
        await hass.async_block_till_done()
        assert (
            hass.data[islamic_prayer_times.DOMAIN].today_prayer_times
            == NEW_PRAYER_TIMES_TIMESTAMPS
        )


async def test_islamic_prayer_times_timestamp_format(hass, aioclient_mock):
    """Test Islamic prayer times timestamp format."""
    entry = MockConfigEntry(domain=islamic_prayer_times.DOMAIN, data={})
    entry.add_to_hass(hass)
    aioclient_mock.get(
        re.compile(".+"), json=MOCK_RESPONSE1,
    )

    with patch("homeassistant.util.dt.now", return_value=NOW):

        await hass.config_entries.async_setup(entry.entry_id)

        assert (
            hass.data[islamic_prayer_times.DOMAIN].today_prayer_times
            == PRAYER_TIMES_TIMESTAMPS
        )
