"""Provides device triggers for Hue Tap Dial MQTT."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components.device_automation import DEVICE_TRIGGER_BASE_SCHEMA
from homeassistant.components.homeassistant.triggers import event as event_trigger
from homeassistant.const import CONF_DEVICE_ID, CONF_DOMAIN, CONF_PLATFORM, CONF_TYPE
from homeassistant.core import CALLBACK_TYPE, HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.trigger import TriggerActionType, TriggerInfo
from homeassistant.helpers.typing import ConfigType

from .const import (
    ALL_ACTIONS,
    DOMAIN,
    EVENT_TYPE_BUTTON,
    EVENT_TYPE_COMBINED,
    EVENT_TYPE_DIAL,
)

_LOGGER = logging.getLogger(__name__)

TRIGGER_TYPES = []

# short/long button
for i in range(1, 5):
    TRIGGER_TYPES.extend(
        [
            f"button_{i}_short",
            f"button_{i}_long",
            f"button_{i}_dial_brightness_step_up",
            f"button_{i}_dial_brightness_step_down",
        ]
    )

# free dial
TRIGGER_TYPES.extend(["brightness_step_up", "brightness_step_down"])

TRIGGER_SCHEMA = DEVICE_TRIGGER_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): vol.In(TRIGGER_TYPES),
    }
)


async def async_get_triggers(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, Any]]:
    """List device triggers for Hue Tap Dial MQTT devices."""
    registry = dr.async_get(hass)
    device = registry.async_get(device_id)

    if not device or device.model != "Hue Tap Dial Switch":
        return []

    triggers: list[dict[str, Any]] = []

    # Short/long press
    for btn in range(1, 5):
        for press_type in ["short", "long"]:
            triggers.append(
                {
                    CONF_PLATFORM: "device",
                    CONF_DOMAIN: DOMAIN,
                    CONF_DEVICE_ID: device_id,
                    CONF_TYPE: f"button_{btn}_{press_type}",
                }
            )

    # Combined button + dial brightness steps
    for btn in range(1, 5):
        for direction in ["up", "down"]:
            triggers.append(
                {
                    CONF_PLATFORM: "device",
                    CONF_DOMAIN: DOMAIN,
                    CONF_DEVICE_ID: device_id,
                    CONF_TYPE: f"button_{btn}_dial_brightness_step_{direction}",
                }
            )

    # Free dial brightness steps
    triggers.extend(
        [
            {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: "brightness_step_up",
            },
            {
                CONF_PLATFORM: "device",
                CONF_DOMAIN: DOMAIN,
                CONF_DEVICE_ID: device_id,
                CONF_TYPE: "brightness_step_down",
            },
        ]
    )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: ConfigType,
    action: TriggerActionType,
    trigger_info: TriggerInfo,
) -> CALLBACK_TYPE:
    """Attach a trigger."""
    trigger_type = config[CONF_TYPE]

    # Determine which event type to listen to
    if trigger_type.startswith("button_") and (
        "_short" in trigger_type or "_long" in trigger_type
    ):
        event_type = EVENT_TYPE_BUTTON
    elif "_dial_brightness_step" in trigger_type:
        event_type = EVENT_TYPE_COMBINED
    elif trigger_type.startswith("brightness_step"):
        event_type = EVENT_TYPE_DIAL
    else:
        # For other actions, use a generic event
        event_type = f"{DOMAIN}_action"

    # Resolve friendly topic from device registry -> config entry data
    topic_id = None
    registry = dr.async_get(hass)
    device = registry.async_get(config[CONF_DEVICE_ID])
    if device and device.config_entries:
        entry_id = next(iter(device.config_entries))
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and "device_id" in entry.data:
            topic_id = entry.data["device_id"]

    device_id_param = config[CONF_DEVICE_ID]
    event_config = {
        event_trigger.CONF_PLATFORM: "event",
        event_trigger.CONF_EVENT_TYPE: event_type,
        event_trigger.CONF_EVENT_DATA: {
            "action": trigger_type,
            "device_id": topic_id or device_id_param,
        },
    }

    event_config = event_trigger.TRIGGER_SCHEMA(event_config)
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
