"""The Mikrotik component."""
import logging

from homeassistant.const import CONF_HOST
from .const import ATTR_MANUFACTURER, DOMAIN
from .hub import MikrotikHub

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass, config):
    """Component doesn't support configuration through configuration.yaml."""
    return True


async def async_setup_entry(hass, config_entry):
    """Set up the Mikrotik component."""
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    hub = MikrotikHub(hass, config_entry)
    hass.data[DOMAIN][config_entry.data[CONF_HOST]] = hub

    if not await hub.async_setup():
        return False

    device_registry = await hass.helpers.device_registry.async_get_registry()
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        connections={(DOMAIN, hub.serial_num)},
        manufacturer=ATTR_MANUFACTURER,
        model=hub.model,
        name=hub.hostname,
        sw_version=hub.firmware,
    )

    return True


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    await hass.config_entries.async_forward_entry_unload(config_entry, "device_tracker")

    hass.data[DOMAIN].pop(config_entry.data[CONF_HOST])

    return True
