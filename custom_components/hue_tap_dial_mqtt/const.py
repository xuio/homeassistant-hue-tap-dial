"""Constants for the Hue Tap Dial MQTT integration."""

DOMAIN = "hue_tap_dial_mqtt"

# Action types
ACTION_BUTTON_PRESS = "button_{}_press"
ACTION_BUTTON_RELEASE = "button_{}_press_release"
ACTION_BUTTON_HOLD = "button_{}_hold"
ACTION_BUTTON_HOLD_RELEASE = "button_{}_hold_release"

ACTION_DIAL_ROTATE_LEFT_SLOW = "dial_rotate_left_slow"
ACTION_DIAL_ROTATE_LEFT_FAST = "dial_rotate_left_fast"
ACTION_DIAL_ROTATE_RIGHT_SLOW = "dial_rotate_right_slow"
ACTION_DIAL_ROTATE_RIGHT_FAST = "dial_rotate_right_fast"

ACTION_BRIGHTNESS_STEP_UP = "brightness_step_up"
ACTION_BRIGHTNESS_STEP_DOWN = "brightness_step_down"

# All possible actions
ALL_ACTIONS = [
    ACTION_DIAL_ROTATE_LEFT_SLOW,
    ACTION_DIAL_ROTATE_LEFT_FAST,
    ACTION_DIAL_ROTATE_RIGHT_SLOW,
    ACTION_DIAL_ROTATE_RIGHT_FAST,
    ACTION_BRIGHTNESS_STEP_UP,
    ACTION_BRIGHTNESS_STEP_DOWN,
]

# Add button actions for buttons 1-4
for i in range(1, 5):
    ALL_ACTIONS.extend(
        [
            ACTION_BUTTON_PRESS.format(i),
            ACTION_BUTTON_RELEASE.format(i),
            ACTION_BUTTON_HOLD.format(i),
            ACTION_BUTTON_HOLD_RELEASE.format(i),
        ]
    )

# Device info
MANUFACTURER = "Philips"
MODEL = "Hue Tap Dial Switch"

# MQTT Discovery
DISCOVERY_TOPIC = "homeassistant/device_automation/{}/{}/action_{}/config"
CONF_DISCOVERY_PREFIX = "discovery_prefix"
DEFAULT_DISCOVERY_PREFIX = "homeassistant"

# Event types
EVENT_TYPE_BUTTON = "hue_tap_dial_button"
EVENT_TYPE_DIAL = "hue_tap_dial_dial"
EVENT_TYPE_COMBINED = "hue_tap_dial_combined"

# Attributes
ATTR_ACTION = "action"
ATTR_BUTTON = "button"
ATTR_DIRECTION = "direction"
ATTR_SPEED = "speed"
ATTR_BRIGHTNESS = "brightness"
ATTR_BATTERY = "battery"
ATTR_DURATION = "duration"
ATTR_HELD_BUTTON = "held_button"

# Additional zigbee2mqtt attributes
ATTR_BRIGHTNESS_DELTA = "brightness_delta"
ATTR_STEP_SIZE = "step_size"
ATTR_TRANSITION_TIME = "transition_time"
ATTR_ACTION_TIME = "action_time"
ATTR_ACTION_TYPE = "action_type"

# Diagnostics / metadata
ATTR_LINKQUALITY = "linkquality"
ATTR_UPDATE_AVAILABLE = "update_available"
ATTR_INSTALLED_VERSION = "installed_version"
ATTR_LATEST_VERSION = "latest_version"

# New attribute
ATTR_ABS_BRIGHTNESS_DELTA = "abs_brightness_delta"

# New attribute
ATTR_DEVICE_ID = "device_id"
