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

TRIGGER_TYPES = ALL_ACTIONS

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

    triggers = []

    # Button triggers
    for button_num in range(1, 5):
        for action in ["press", "press_release", "hold", "hold_release"]:
            triggers.append(
                {
                    CONF_PLATFORM: "device",
                    CONF_DOMAIN: DOMAIN,
                    CONF_DEVICE_ID: device_id,
                    CONF_TYPE: f"button_{button_num}_{action}",
                }
            )

    # Dial triggers
    for direction in ["left", "right"]:
        for speed in ["slow", "fast"]:
            triggers.append(
                {
                    CONF_PLATFORM: "device",
                    CONF_DOMAIN: DOMAIN,
                    CONF_DEVICE_ID: device_id,
                    CONF_TYPE: f"dial_rotate_{direction}_{speed}",
                }
            )

    # Brightness triggers
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
    if trigger_type.startswith("button_"):
        event_type = EVENT_TYPE_BUTTON
    elif trigger_type.startswith("dial_") or trigger_type.startswith("brightness_"):
        event_type = EVENT_TYPE_DIAL
    else:
        # For other actions, use a generic event
        event_type = f"{DOMAIN}_action"

    event_config = {
        event_trigger.CONF_PLATFORM: "event",
        event_trigger.CONF_EVENT_TYPE: event_type,
        event_trigger.CONF_EVENT_DATA: {
            "action": trigger_type,
        },
    }

    event_config = event_trigger.TRIGGER_SCHEMA(event_config)
    return await event_trigger.async_attach_trigger(
        hass, event_config, action, trigger_info, platform_type="device"
    )
