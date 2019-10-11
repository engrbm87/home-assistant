"""Constants used in the Mikrotik components."""

DOMAIN = "mikrotik"
# MK_CONFIG = "mikrotik_config"
DEFAULT_NAME = "Mikrotik"
DEFAULT_API_PORT = 8728
# DEFAULT_API_SSL_PORT = 8729
DEFAULT_DETECTION_TIME = 300

ATTR_MANUFACTURER = "Mikrotik"
ATTR_SERIAL_NUMBER = "serial-number"
ATTR_FIRMWARE = "current-firmware"
ATTR_MODEL = "model"

CONF_ARP_PING = "arp_ping"
CONF_FORCE_DHCP = "force_dhcp"
CONF_TRACK_DEVICES = "track_devices"
CONF_DETECTION_TIME = "detection_time"


NAME = "name"
INFO = "info"
IDENTITY = "identity"
ARP = "arp"

CAPSMAN = "capsman"
DHCP = "dhcp"
WIRELESS = "wireless"
IS_WIRELESS = "is_wireless"

MIKROTIK_SERVICES = {
    ARP: "/ip/arp/getall",
    CAPSMAN: "/caps-man/registration-table/getall",
    DHCP: "/ip/dhcp-server/lease/getall",
    IDENTITY: "/system/identity/getall",
    INFO: "/system/routerboard/getall",
    WIRELESS: "/interface/wireless/registration-table/getall",
    IS_WIRELESS: "/interface/wireless/print",
}

ATTR_DEVICE_TRACKER = [
    "comment",
    "mac-address",
    "ssid",
    "interface",
    "signal-strength",
    "signal-to-noise",
    "rx-rate",
    "tx-rate",
    "uptime",
]
