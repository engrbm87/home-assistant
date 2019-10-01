"""Support for Mikrotik routers as device tracker."""
import logging

from homeassistant.components.device_tracker.config_entry import ScannerEntity
from homeassistant.components.device_tracker.const import DOMAIN, SOURCE_TYPE_ROUTER
from homeassistant.const import CONF_HOST
from homeassistant.core import callback
from homeassistant.helpers import entity_registry
from homeassistant.helpers.device_registry import CONNECTION_NETWORK_MAC
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_registry import DISABLED_CONFIG_ENTRY
import homeassistant.util.dt as dt_util

from .const import DOMAIN as MIKROTIK

LOGGER = logging.getLogger(__name__)


async def async_setup_scanner(hass, config, sync_see, discovery_info):
    """Set up the Mikrotik integration."""
    return True


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up device tracker for Mikrotik component."""
    hub = hass.data[MIKROTIK][config_entry.data[CONF_HOST]]

    tracked = {}

    registry = await entity_registry.async_get_registry(hass)

    # Restore clients that is not a part of active clients list.
    for entity in registry.entities.values():

        if entity.unique_id in hub.devices or entity.unique_id not in hub.all_devices:
            continue
        hub.restore_device(entity.unique_id)

    @callback
    def update_hub():
        """Update the status of the device."""
        update_items(hub, async_add_entities, tracked)

    async_dispatcher_connect(hass, hub.signal_update, update_hub)

    @callback
    def update_disable_on_entities():
        """Update the values of the controller."""
        for entity in tracked.values():

            disabled_by = None
            if not entity.entity_registry_enabled_default and entity.enabled:
                disabled_by = DISABLED_CONFIG_ENTRY

            registry.async_update_entity(
                entity.registry_entry.entity_id, disabled_by=disabled_by
            )

    async_dispatcher_connect(
        hass, hub.signal_options_update, update_disable_on_entities
    )
    update_hub()


@callback
def update_items(hub, async_add_entities, tracked):
    """Update tracked device state from the controller."""
    new_tracked = []
    for device in hub.devices:
        if device in tracked:
            if tracked[device].enabled:
                tracked[device].async_schedule_update_ha_state()
            continue
        tracked[device] = MikrotikHubTracker(hub.devices[device], hub)

        new_tracked.append(tracked[device])
    if new_tracked:
        async_add_entities(new_tracked)


class MikrotikHubTracker(ScannerEntity):
    """Representation of network device."""

    def __init__(self, device, hub):
        """Initialize the tracked device."""
        self.device = device
        self.hub = hub

    @property
    def entity_registry_enabled_default(self):
        """Return if the entity should be enabled when first added to the entity registry."""
        # if (self.device.is_wireless and self.hub.option_track_wireless) or (
        #     not self.device.is_wireless and self.hub.option_track_wired
        # ):
        # return True
        return self.hub.option_track_devices

    @property
    def is_connected(self):
        """Return true if the client is connected to the network."""
        if (
            self.device.last_seen
            and (dt_util.utcnow() - self.device.last_seen)
            < self.hub.option_detection_time
        ):
            return True
        return False

    @property
    def source_type(self):
        """Return the source type of the client."""
        return SOURCE_TYPE_ROUTER

    @property
    def name(self) -> str:
        """Return the name of the client."""
        return self.device.name

    @property
    def unique_id(self) -> str:
        """Return a unique identifier for this device."""
        return self.device.mac

    @property
    def available(self) -> bool:
        """Return if controller is available."""
        return self.hub.available

    @property
    def device_state_attributes(self):
        """Return the device state attributes."""
        if self.is_connected:
            return self.device.attrs

    @property
    def device_info(self):
        """Return a client description for device registry."""
        info = {
            "connections": {(CONNECTION_NETWORK_MAC, self.unique_id)},
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "via_device": (DOMAIN, self.hub.serial_num),
        }
        return info

    async def async_added_to_hass(self):
        """Client entity created."""
        LOGGER.debug("New network device tracker %s (%s)", self.name, self.unique_id)

    async def async_update(self):
        """Synchronize state with hub."""
        LOGGER.debug(
            "Updating Mikrotik tracked client %s (%s)", self.entity_id, self.unique_id
        )
        await self.hub.request_update()
