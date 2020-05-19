"""Tests for Islamic Prayer Times init."""

import asyncio
import re

from homeassistant import config_entries
from homeassistant.components import islamic_prayer_times
from homeassistant.setup import async_setup_component

from . import MOCK_RESPONSE

from tests.common import MockConfigEntry


async def test_setup_with_config(hass, aioclient_mock):
    """Test that we import the config and setup the client."""
    config = {
        islamic_prayer_times.DOMAIN: {islamic_prayer_times.CONF_CALC_METHOD: "ISNA"}
    }
    assert await async_setup_component(hass, islamic_prayer_times.DOMAIN, config)


async def test_successful_config_entry(hass, aioclient_mock):
    """Test that Islamic Prayer Times is configured successfully."""
    aioclient_mock.get(
        re.compile(".+"), json=MOCK_RESPONSE,
    )
    entry = MockConfigEntry(domain=islamic_prayer_times.DOMAIN, data={},)
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)

    assert entry.state == config_entries.ENTRY_STATE_LOADED
    assert entry.options == {
        islamic_prayer_times.CONF_CALC_METHOD: islamic_prayer_times.DEFAULT_CALC_METHOD,
        islamic_prayer_times.CONF_SCHOOL: islamic_prayer_times.DEFAULT_SCHOOL,
        islamic_prayer_times.CONF_MIDNIGHT_MODE: islamic_prayer_times.DEFAULT_MIDNIGHT_MODE,
        islamic_prayer_times.CONF_LAT_ADJ_METHOD: islamic_prayer_times.DEFAULT_LAT_ADJ_METHOD,
    }


async def test_setup_failed(hass, aioclient_mock):
    """Test Islamic Prayer Times failed due to an error."""

    aioclient_mock.get(re.compile(".+"), exc=asyncio.TimeoutError())
    entry = MockConfigEntry(domain=islamic_prayer_times.DOMAIN, data={},)
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state == config_entries.ENTRY_STATE_SETUP_RETRY


async def test_unload_entry(hass, aioclient_mock):
    """Test removing Islamic Prayer Times."""
    entry = MockConfigEntry(domain=islamic_prayer_times.DOMAIN, data={},)
    entry.add_to_hass(hass)

    aioclient_mock.get(
        re.compile(".+"), json=MOCK_RESPONSE,
    )
    await hass.config_entries.async_setup(entry.entry_id)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == config_entries.ENTRY_STATE_NOT_LOADED
    assert islamic_prayer_times.DOMAIN not in hass.data
