"""Support for the DirecTV receivers."""
import logging

from DirectPy import DIRECTV
import requests
import voluptuous as vol

from homeassistant.components.media_player import PLATFORM_SCHEMA, MediaPlayerDevice
from homeassistant.components.media_player.const import (
    MEDIA_TYPE_CHANNEL,
    MEDIA_TYPE_MOVIE,
    MEDIA_TYPE_TVSHOW,
    SUPPORT_NEXT_TRACK,
    SUPPORT_PAUSE,
    SUPPORT_PLAY,
    SUPPORT_PLAY_MEDIA,
    SUPPORT_PREVIOUS_TRACK,
    SUPPORT_STOP,
    SUPPORT_TURN_OFF,
    SUPPORT_TURN_ON,
)
from homeassistant.const import (
    CONF_DEVICE,
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    STATE_OFF,
    STATE_PAUSED,
    STATE_PLAYING,
)
import homeassistant.helpers.config_validation as cv
import homeassistant.util.dt as dt_util

from .const import (
    ATTR_MEDIA_CURRENTLY_RECORDING,
    ATTR_MEDIA_RATING,
    ATTR_MEDIA_RECORDED,
    ATTR_MEDIA_START_TIME,
    DATA_DIRECTV,
    DEFAULT_DEVICE,
    DEFAULT_NAME,
    DEFAULT_PORT,
)

_LOGGER = logging.getLogger(__name__)

SUPPORT_DTV = (
    SUPPORT_PAUSE
    | SUPPORT_TURN_ON
    | SUPPORT_TURN_OFF
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_STOP
    | SUPPORT_NEXT_TRACK
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_PLAY
)

SUPPORT_DTV_CLIENT = (
    SUPPORT_PAUSE
    | SUPPORT_PLAY_MEDIA
    | SUPPORT_STOP
    | SUPPORT_NEXT_TRACK
    | SUPPORT_PREVIOUS_TRACK
    | SUPPORT_PLAY
)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_DEVICE, default=DEFAULT_DEVICE): cv.string,
    }
)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Set up the DirecTV platform."""
    known_devices = hass.data.get(DATA_DIRECTV, set())
    entities = []

    if CONF_HOST in config:
        name = config[CONF_NAME]
        host = config[CONF_HOST]
        port = config[CONF_PORT]
        device = config[CONF_DEVICE]

        _LOGGER.debug(
            "Adding configured device %s with client address %s", name, device,
        )

        dtv = DIRECTV(host, port, device)
        dtv_version = _get_receiver_version(dtv)

        entities.append(DirecTvDevice(name, device, dtv, dtv_version,))
        known_devices.add((host, device))

    elif discovery_info:
        host = discovery_info.get("host")
        name = f"DirecTV_{discovery_info.get('serial', '')}"

        # Attempt to discover additional RVU units
        _LOGGER.debug("Doing discovery of DirecTV devices on %s", host)

        dtv = DIRECTV(host, DEFAULT_PORT)

        try:
            dtv_version = _get_receiver_version(dtv)
            resp = dtv.get_locations()
        except requests.exceptions.RequestException as ex:
            # Bail out and just go forward with uPnP data
            # Make sure that this device is not already configured
            # Comparing based on host (IP) and clientAddr.
            _LOGGER.debug("Request exception %s trying to get locations", ex)
            resp = {"locations": [{"locationName": name, "clientAddr": DEFAULT_DEVICE}]}

        _LOGGER.debug("Known devices: %s", known_devices)
        for loc in resp.get("locations") or []:
            if "locationName" not in loc or "clientAddr" not in loc:
                continue

            loc_name = str.title(loc["locationName"])

            # Make sure that this device is not already configured
            # Comparing based on host (IP) and clientAddr.
            if (host, loc["clientAddr"]) in known_devices:
                _LOGGER.debug(
                    "Discovered device %s on host %s with "
                    "client address %s is already "
                    "configured",
                    loc_name,
                    host,
                    loc["clientAddr"],
                )
            else:
                _LOGGER.debug(
                    "Adding discovered device %s with client address %s",
                    loc_name,
                    loc["clientAddr"],
                )

                entities.append(
                    DirecTvDevice(
                        loc_name,
                        loc["clientAddr"],
                        DIRECTV(host, DEFAULT_PORT, loc["clientAddr"]),
                        dtv_version,
                    )
                )
                known_devices.add((host, loc["clientAddr"]))

    add_entities(entities)


def _get_receiver_version(client):
    """Return the version of the DirectTV receiver."""
    try:
        return client.get_version()
    except requests.exceptions.RequestException as ex:
        _LOGGER.debug("Request exception %s trying to get receiver version", ex)
        return None


class DirecTvDevice(MediaPlayerDevice):
    """Representation of a DirecTV receiver on the network."""

    def __init__(self, name, device, dtv, version_info=None):
        """Initialize the device."""
        self.dtv = dtv
        self._name = name
        self._unique_id = None
        self._is_standby = True
        self._current = None
        self._last_update = None
        self._paused = None
        self._last_position = None
        self._is_recorded = None
        self._is_client = device != "0"
        self._assumed_state = None
        self._available = False
        self._first_error_timestamp = None

        if device != "0":
            self._unique_id = device
        elif version_info:
            self._unique_id = "".join(version_info.get("receiverId").split())

        if self._is_client:
            _LOGGER.debug("Created DirecTV client %s for device %s", self._name, device)
        else:
            _LOGGER.debug("Created DirecTV device for %s", self._name)

    def update(self):
        """Retrieve latest state."""
        _LOGGER.debug("%s: Updating status", self.entity_id)
        try:
            self._available = True
            self._is_standby = self.dtv.get_standby()
            if self._is_standby:
                self._current = None
                self._is_recorded = None
                self._paused = None
                self._assumed_state = False
                self._last_position = None
                self._last_update = None
            else:
                self._current = self.dtv.get_tuned()
                if self._current["status"]["code"] == 200:
                    self._first_error_timestamp = None
                    self._is_recorded = self._current.get("uniqueId") is not None
                    self._paused = self._last_position == self._current["offset"]
                    self._assumed_state = self._is_recorded
                    self._last_position = self._current["offset"]
                    self._last_update = (
                        dt_util.utcnow()
                        if not self._paused or self._last_update is None
                        else self._last_update
                    )
                else:
                    # If an error is received then only set to unavailable if
                    # this started at least 1 minute ago.
                    log_message = f"{self.entity_id}: Invalid status {self._current['status']['code']} received"
                    if self._check_state_available():
                        _LOGGER.debug(log_message)
                    else:
                        _LOGGER.error(log_message)

        except requests.RequestException as ex:
            _LOGGER.error(
                "%s: Request error trying to update current status: %s",
                self.entity_id,
                ex,
            )
            self._check_state_available()

        except Exception as ex:
            _LOGGER.error(
                "%s: Exception trying to update current status: %s", self.entity_id, ex
            )
            self._available = False
            if not self._first_error_timestamp:
                self._first_error_timestamp = dt_util.utcnow()
            raise

    def _check_state_available(self):
        """Set to unavailable if issue been occurring over 1 minute."""
        if not self._first_error_timestamp:
            self._first_error_timestamp = dt_util.utcnow()
        else:
            tdelta = dt_util.utcnow() - self._first_error_timestamp
            if tdelta.total_seconds() >= 60:
                self._available = False

        return self._available

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        attributes = {}
        if not self._is_standby:
            attributes[ATTR_MEDIA_CURRENTLY_RECORDING] = self.media_currently_recording
            attributes[ATTR_MEDIA_RATING] = self.media_rating
            attributes[ATTR_MEDIA_RECORDED] = self.media_recorded
            attributes[ATTR_MEDIA_START_TIME] = self.media_start_time

        return attributes

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID to use for this media player."""
        return self._unique_id

    # MediaPlayerDevice properties and methods
    @property
    def state(self):
        """Return the state of the device."""
        if self._is_standby:
            return STATE_OFF

        # For recorded media we can determine if it is paused or not.
        # For live media we're unable to determine and will always return
        # playing instead.
        if self._paused:
            return STATE_PAUSED

        return STATE_PLAYING

    @property
    def available(self):
        """Return if able to retrieve information from DVR or not."""
        return self._available

    @property
    def assumed_state(self):
        """Return if we assume the state or not."""
        return self._assumed_state

    @property
    def media_content_id(self):
        """Return the content ID of current playing media."""
        if self._is_standby:
            return None

        return self._current["programId"]

    @property
    def media_content_type(self):
        """Return the content type of current playing media."""
        if self._is_standby:
            return None

        if "episodeTitle" in self._current:
            return MEDIA_TYPE_TVSHOW

        return MEDIA_TYPE_MOVIE

    @property
    def media_duration(self):
        """Return the duration of current playing media in seconds."""
        if self._is_standby:
            return None

        return self._current["duration"]

    @property
    def media_position(self):
        """Position of current playing media in seconds."""
        if self._is_standby:
            return None

        return self._last_position

    @property
    def media_position_updated_at(self):
        """When was the position of the current playing media valid.

        Returns value from homeassistant.util.dt.utcnow().
        """
        if self._is_standby:
            return None

        return self._last_update

    @property
    def media_title(self):
        """Return the title of current playing media."""
        if self._is_standby:
            return None

        return self._current["title"]

    @property
    def media_series_title(self):
        """Return the title of current episode of TV show."""
        if self._is_standby:
            return None

        return self._current.get("episodeTitle")

    @property
    def media_channel(self):
        """Return the channel current playing media."""
        if self._is_standby:
            return None

        return f"{self._current['callsign']} ({self._current['major']})"

    @property
    def source(self):
        """Name of the current input source."""
        if self._is_standby:
            return None

        return self._current["major"]

    @property
    def supported_features(self):
        """Flag media player features that are supported."""
        return SUPPORT_DTV_CLIENT if self._is_client else SUPPORT_DTV

    @property
    def media_currently_recording(self):
        """If the media is currently being recorded or not."""
        if self._is_standby:
            return None

        return self._current["isRecording"]

    @property
    def media_rating(self):
        """TV Rating of the current playing media."""
        if self._is_standby:
            return None

        return self._current["rating"]

    @property
    def media_recorded(self):
        """If the media was recorded or live."""
        if self._is_standby:
            return None

        return self._is_recorded

    @property
    def media_start_time(self):
        """Start time the program aired."""
        if self._is_standby:
            return None

        return dt_util.as_local(dt_util.utc_from_timestamp(self._current["startTime"]))

    def turn_on(self):
        """Turn on the receiver."""
        if self._is_client:
            raise NotImplementedError()

        _LOGGER.debug("Turn on %s", self._name)
        self.dtv.key_press("poweron")

    def turn_off(self):
        """Turn off the receiver."""
        if self._is_client:
            raise NotImplementedError()

        _LOGGER.debug("Turn off %s", self._name)
        self.dtv.key_press("poweroff")

    def media_play(self):
        """Send play command."""
        _LOGGER.debug("Play on %s", self._name)
        self.dtv.key_press("play")

    def media_pause(self):
        """Send pause command."""
        _LOGGER.debug("Pause on %s", self._name)
        self.dtv.key_press("pause")

    def media_stop(self):
        """Send stop command."""
        _LOGGER.debug("Stop on %s", self._name)
        self.dtv.key_press("stop")

    def media_previous_track(self):
        """Send rewind command."""
        _LOGGER.debug("Rewind on %s", self._name)
        self.dtv.key_press("rew")

    def media_next_track(self):
        """Send fast forward command."""
        _LOGGER.debug("Fast forward on %s", self._name)
        self.dtv.key_press("ffwd")

    def play_media(self, media_type, media_id, **kwargs):
        """Select input source."""
        if media_type != MEDIA_TYPE_CHANNEL:
            _LOGGER.error(
                "Invalid media type %s. Only %s is supported",
                media_type,
                MEDIA_TYPE_CHANNEL,
            )
            return

        _LOGGER.debug("Changing channel on %s to %s", self._name, media_id)
        self.dtv.tune_channel(media_id)
