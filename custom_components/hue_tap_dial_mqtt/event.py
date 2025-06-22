"""Event platform for Hue Tap Dial MQTT."""

from __future__ import annotations

import logging

from homeassistant.components.event import EventDeviceClass, EventEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ACTION,
    ATTR_ACTION_TIME,
    ATTR_ACTION_TYPE,
    ATTR_BATTERY,
    ATTR_BRIGHTNESS,
    ATTR_BRIGHTNESS_DELTA,
    ATTR_BUTTON,
    ATTR_DIRECTION,
    ATTR_DURATION,
    ATTR_HELD_BUTTON,
    ATTR_SPEED,
    ATTR_STEP_SIZE,
    ATTR_TRANSITION_TIME,
    DOMAIN,
    EVENT_TYPE_BUTTON,
    EVENT_TYPE_COMBINED,
    EVENT_TYPE_DIAL,
    MANUFACTURER,
    MODEL,
    ATTR_DEVICE_ID,
)

_LOGGER = logging.getLogger(__name__)

# Event type mappings
BUTTON_EVENT_TYPES = ["press", "press_release", "hold", "hold_release"]
DIAL_EVENT_TYPES = [
    "rotate_left_slow",
    "rotate_left_fast",
    "rotate_right_slow",
    "rotate_right_fast",
    "brightness_step_up",
    "brightness_step_down",
]
COMBINED_EVENT_TYPES = ["button_dial_rotate"]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hue Tap Dial MQTT event entities."""
    device_id = config_entry.data[CONF_DEVICE_ID]
    device_name = config_entry.data[CONF_NAME]

    entities = []

    # Create separate entities for short and long press
    for button_num in range(1, 5):
        entities.append(
            HueTapDialButtonPressEvent(
                config_entry.entry_id,
                device_id,
                device_name,
                button_num,
                "short",
            )
        )
        entities.append(
            HueTapDialButtonPressEvent(
                config_entry.entry_id,
                device_id,
                device_name,
                button_num,
                "long",
            )
        )

    # Create dial event entity
    entities.append(
        HueTapDialDialEvent(
            config_entry.entry_id,
            device_id,
            device_name,
        )
    )

    # Create combined button+dial event entity (per held button)
    for button_num in range(1, 5):
        entities.append(
            HueTapDialButtonDialEvent(
                config_entry.entry_id,
                device_id,
                device_name,
                button_num,
            )
        )

    async_add_entities(entities)


class HueTapDialButtonPressEvent(EventEntity):
    """Representation of a Hue Tap Dial button press event."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = BUTTON_EVENT_TYPES

    def __init__(
        self,
        config_entry_id: str,
        device_id: str,
        device_name: str,
        button_num: int,
        press_type: str,
    ) -> None:
        """Initialize the button press event."""
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        self._button_num = button_num
        self._press_type = press_type
        self._attr_unique_id = f"{device_id}_button_{button_num}_{press_type}"
        self._attr_name = f"{device_name} Button {button_num} {press_type}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

        self._attr_event_types = [press_type]

    async def async_added_to_hass(self) -> None:
        """Subscribe to button events."""

        @callback
        def handle_button_event(event):
            data = event.data
            if (
                data.get(ATTR_BUTTON) != self._button_num
                or data.get(ATTR_DEVICE_ID) != self._device_id
            ):
                return
            if data.get("press_type") != self._press_type:
                return
            attrib = {
                ATTR_BUTTON: self._button_num,
            }
            if ATTR_DURATION in data:
                attrib[ATTR_DURATION] = data[ATTR_DURATION]
            self._trigger_event(self._press_type, attrib)
            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_TYPE_BUTTON, handle_button_event)
        )


class HueTapDialDialEvent(EventEntity):
    """Representation of a Hue Tap Dial dial rotation event."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = DIAL_EVENT_TYPES

    def __init__(
        self,
        config_entry_id: str,
        device_id: str,
        device_name: str,
    ) -> None:
        """Initialize the dial event."""
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_dial"
        self._attr_name = f"{device_name} Dial"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to dial events."""

        @callback
        def handle_dial_event(event) -> None:
            """Handle dial event."""
            event_data = event.data
            if event_data.get(ATTR_DEVICE_ID) != self._device_id:
                return
            action = event_data.get(ATTR_ACTION, "")

            # Determine event type based on action
            if "brightness_step" in action:
                direction = event_data.get(ATTR_DIRECTION, "")
                event_type = f"brightness_step_{direction}"
            else:
                direction = event_data.get(ATTR_DIRECTION, "")
                speed = event_data.get(ATTR_SPEED, "")

                if speed == "" or direction in ("up", "down"):
                    # Treat as brightness step event
                    event_type = f"brightness_step_{direction}"
                else:
                    event_type = f"rotate_{direction}_{speed}"

            # Build attributes with all available data
            attributes = {
                ATTR_ACTION: action,
            }

            # Add direction and speed for rotation events
            if ATTR_DIRECTION in event_data:
                attributes[ATTR_DIRECTION] = event_data[ATTR_DIRECTION]
            if ATTR_SPEED in event_data:
                attributes[ATTR_SPEED] = event_data[ATTR_SPEED]

            # Add all brightness-related attributes
            if ATTR_BRIGHTNESS in event_data:
                attributes[ATTR_BRIGHTNESS] = event_data[ATTR_BRIGHTNESS]
            attributes[ATTR_BRIGHTNESS_DELTA] = event_data.get(ATTR_BRIGHTNESS_DELTA, 0)
            if ATTR_STEP_SIZE in event_data:
                attributes[ATTR_STEP_SIZE] = event_data[ATTR_STEP_SIZE]
            if ATTR_TRANSITION_TIME in event_data:
                attributes[ATTR_TRANSITION_TIME] = event_data[ATTR_TRANSITION_TIME]

            # Add additional timing attributes
            if ATTR_ACTION_TIME in event_data:
                attributes[ATTR_ACTION_TIME] = event_data[ATTR_ACTION_TIME]
            if ATTR_ACTION_TYPE in event_data:
                attributes[ATTR_ACTION_TYPE] = event_data[ATTR_ACTION_TYPE]

            self._trigger_event(event_type, attributes)
            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_TYPE_DIAL, handle_dial_event)
        )


class HueTapDialButtonDialEvent(EventEntity):
    """Event entity for dial rotation while holding a specific button."""

    _attr_device_class = EventDeviceClass.BUTTON
    _attr_event_types = ["brightness_step_up", "brightness_step_down"]

    def __init__(
        self,
        config_entry_id: str,
        device_id: str,
        device_name: str,
        button_num: int,
    ) -> None:
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        self._button_num = button_num
        self._attr_unique_id = f"{device_id}_button_{button_num}_dial"
        self._attr_name = f"{device_name} Button {button_num} + Dial"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_added_to_hass(self) -> None:
        @callback
        def handle_combined(event):
            data = event.data
            if (
                data.get(ATTR_HELD_BUTTON) != self._button_num
                or data.get(ATTR_DEVICE_ID) != self._device_id
            ):
                return
            action = data.get(ATTR_ACTION)
            direction = data.get(ATTR_DIRECTION)
            event_type = f"brightness_step_{direction}"
            attrib = {
                ATTR_DIRECTION: direction,
                ATTR_BRIGHTNESS_DELTA: data.get(ATTR_BRIGHTNESS_DELTA, 0),
            }
            if ATTR_BRIGHTNESS in data:
                attrib[ATTR_BRIGHTNESS] = data[ATTR_BRIGHTNESS]
            self._trigger_event(event_type, attrib)
            self.async_write_ha_state()

        self.async_on_remove(
            self.hass.bus.async_listen(EVENT_TYPE_COMBINED, handle_combined)
        )
