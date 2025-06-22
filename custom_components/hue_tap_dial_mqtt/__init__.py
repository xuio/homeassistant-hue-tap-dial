"""The Hue Tap Dial MQTT integration."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

from homeassistant.components import mqtt
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    ACTION_BUTTON_HOLD,
    ACTION_BUTTON_HOLD_RELEASE,
    ACTION_BUTTON_PRESS,
    ACTION_BUTTON_RELEASE,
    ACTION_BRIGHTNESS_STEP_DOWN,
    ACTION_BRIGHTNESS_STEP_UP,
    ACTION_DIAL_ROTATE_LEFT_FAST,
    ACTION_DIAL_ROTATE_LEFT_SLOW,
    ACTION_DIAL_ROTATE_RIGHT_FAST,
    ACTION_DIAL_ROTATE_RIGHT_SLOW,
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
    ATTR_LATEST_VERSION,
    ATTR_LINKQUALITY,
    ATTR_UPDATE_AVAILABLE,
    ATTR_INSTALLED_VERSION,
    ATTR_ABS_BRIGHTNESS_DELTA,
    ATTR_DEVICE_ID,
)
from .discovery import async_setup_discovery

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.EVENT]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Hue Tap Dial MQTT integration."""
    hass.data.setdefault(DOMAIN, {})

    # Set up discovery when integration loads
    await async_setup_discovery(hass)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hue Tap Dial MQTT from a config entry."""
    device_id = entry.data[CONF_DEVICE_ID]
    device_name = entry.data[CONF_NAME]
    topic = f"zigbee2mqtt/{device_id}"

    # Create device
    device_registry = dr.async_get(hass)
    device = device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, device_id)},
        manufacturer=MANUFACTURER,
        model=MODEL,
        name=device_name,
    )

    # Store device info
    device_data = {
        "device": device,
        "device_id": device_id,
        "name": device_name,
        "topic": topic,
        "unsubscribe": None,
        "button_states": {
            i: {"down": False, "rotated": False, "rotation": None} for i in range(1, 5)
        },
        "last_battery": None,
        "last_action": None,
        "last_action_time": 0.0,
    }

    hass.data[DOMAIN][entry.entry_id] = device_data

    # Set up MQTT subscription
    @callback
    def message_received(msg):
        """Handle new MQTT messages."""
        try:
            payload = json.loads(msg.payload)
            action = payload.get("action")

            if not action:
                return

            # Deduplicate duplicate MQTT messages emitted back-to-back by zigbee2mqtt
            now = time.monotonic()
            if (
                action == device_data.get("last_action")
                and now - device_data.get("last_action_time", 0) < 0.1
            ):
                _LOGGER.debug("Ignoring duplicate action %s", action)
                return

            device_data["last_action"] = action
            device_data["last_action_time"] = now

            # Update battery if present
            if "battery" in payload:
                device_data["last_battery"] = payload["battery"]
                async_dispatcher_send(
                    hass, f"{DOMAIN}_{entry.entry_id}_battery", payload["battery"]
                )

            # Update linkquality
            if "linkquality" in payload:
                device_data["last_linkquality"] = payload["linkquality"]
                async_dispatcher_send(
                    hass,
                    f"{DOMAIN}_{entry.entry_id}_linkquality",
                    payload["linkquality"],
                )

            # Update firmware info
            if "update" in payload and isinstance(payload["update"], dict):
                upd = payload["update"]
                if "installed_version" in upd:
                    device_data["installed_version"] = upd["installed_version"]
                    async_dispatcher_send(
                        hass,
                        f"{DOMAIN}_{entry.entry_id}_installed_version",
                        upd["installed_version"],
                    )
                if "latest_version" in upd:
                    device_data["latest_version"] = upd["latest_version"]
                    async_dispatcher_send(
                        hass,
                        f"{DOMAIN}_{entry.entry_id}_latest_version",
                        upd["latest_version"],
                    )
                # Update available bool
                update_avail = payload.get(
                    "update_available", upd.get("state") == "available"
                )
                device_data["update_available"] = update_avail
                async_dispatcher_send(
                    hass,
                    f"{DOMAIN}_{entry.entry_id}_update_available",
                    update_avail,
                )

            # Track button states
            for button_num in range(1, 5):
                if action == ACTION_BUTTON_PRESS.format(
                    button_num
                ) or action == ACTION_BUTTON_HOLD.format(button_num):
                    btn_state = device_data["button_states"][button_num]
                    if not btn_state["down"]:
                        # First press/hold transition
                        btn_state["down"] = True
                        btn_state["rotated"] = False
                elif action in [
                    ACTION_BUTTON_RELEASE.format(button_num),
                    ACTION_BUTTON_HOLD_RELEASE.format(button_num),
                ]:
                    # Button released
                    btn_state = device_data["button_states"][button_num]
                    rotated = btn_state["rotated"]
                    device_data["button_states"][button_num]["down"] = False
                    device_data["button_states"][button_num]["rotated"] = False

                    if rotated:
                        _LOGGER.debug(
                            "Suppress simple press on button %s due to rotation",
                            button_num,
                        )
                        continue
                    else:
                        # Simple press/hold without rotation
                        press_type = "short" if "press_release" in action else "long"
                        event_data = {
                            ATTR_BUTTON: button_num,
                            "press_type": press_type,
                            ATTR_ACTION: f"button_{button_num}_{press_type}",
                            ATTR_DEVICE_ID: device_id,
                        }
                        if "action_duration" in payload:
                            event_data[ATTR_DURATION] = payload["action_duration"]

                        hass.bus.async_fire(EVENT_TYPE_BUTTON, event_data)
                        _LOGGER.debug(
                            "Emitted %s button event for button %s",
                            press_type,
                            button_num,
                        )
                        continue

            down_buttons = [
                num for num, d in device_data["button_states"].items() if d["down"]
            ]

            # Handle dial/brightness_step
            if action in [ACTION_BRIGHTNESS_STEP_UP, ACTION_BRIGHTNESS_STEP_DOWN]:
                # Ignore bogus full-scale messages produced by Z2M when delta = ±255
                if (
                    abs(payload.get("action_brightness_delta", 0)) == 255
                    and payload.get("action_step_size", 0) == 255
                ):
                    _LOGGER.debug("Ignoring bogus brightness_step ±255 message")
                    return

                # Ignore zero-delta (no-op) brightness steps
                try:
                    delta_val = int(payload.get("action_brightness_delta", 0))
                except (TypeError, ValueError):
                    delta_val = 0
                if delta_val == 0:
                    _LOGGER.debug("Ignoring brightness_step with delta 0")
                    return

                # Determine direction
                direction = "up" if action == ACTION_BRIGHTNESS_STEP_UP else "down"

                if down_buttons:
                    btn = down_buttons[0]
                    btn_state = device_data["button_states"][btn]
                    btn_state["rotated"] = True
                    event_data = {
                        ATTR_HELD_BUTTON: btn,
                        ATTR_DIRECTION: direction,
                        ATTR_BRIGHTNESS_DELTA: payload.get(
                            "action_brightness_delta", 0
                        ),
                        ATTR_ABS_BRIGHTNESS_DELTA: abs(
                            payload.get("action_brightness_delta", 0)
                        ),
                        ATTR_ACTION: f"button_{btn}_dial_brightness_step_{direction}",
                        ATTR_DEVICE_ID: device_id,
                    }
                    if "brightness" in payload:
                        event_data[ATTR_BRIGHTNESS] = payload["brightness"]
                    hass.bus.async_fire(EVENT_TYPE_COMBINED, event_data)
                    _LOGGER.debug("Emitted combined event (button %s + dial)", btn)

                    # no need to store rotation dict anymore
                    btn_state["rotation"] = None
                else:
                    # Free rotation
                    direction = "up" if action == ACTION_BRIGHTNESS_STEP_UP else "down"
                    event_data = {
                        ATTR_DIRECTION: direction,
                        ATTR_BRIGHTNESS_DELTA: payload.get(
                            "action_brightness_delta", 0
                        ),
                        ATTR_ABS_BRIGHTNESS_DELTA: abs(
                            payload.get("action_brightness_delta", 0)
                        ),
                        ATTR_ACTION: f"brightness_step_{direction}",
                        ATTR_DEVICE_ID: device_id,
                    }
                    if "brightness" in payload:
                        event_data[ATTR_BRIGHTNESS] = payload["brightness"]
                    hass.bus.async_fire(EVENT_TYPE_DIAL, event_data)
                    _LOGGER.debug("Emitted dial event (free rotation)")
                return

            # Handle dial_rotate events
            if action in [
                ACTION_DIAL_ROTATE_LEFT_SLOW,
                ACTION_DIAL_ROTATE_LEFT_FAST,
                ACTION_DIAL_ROTATE_RIGHT_SLOW,
                ACTION_DIAL_ROTATE_RIGHT_FAST,
            ]:
                # Ignore '*_step' variants and zero-effect rotate messages (no brightness change)
                if "_step" in action:
                    _LOGGER.debug("Ignoring dial_rotate _step message")
                    return
                # Ignore rotate packets that don't change brightness (no delta and brightness unchanged)
                if "action_brightness_delta" not in payload:
                    return

                device_data["last_brightness"] = payload.get("brightness")

                direction = "up" if "right" in action else "down"
                speed = "fast" if "fast" in action else "slow"

                if down_buttons:
                    btn = down_buttons[0]
                    btn_state = device_data["button_states"][btn]
                    btn_state["rotated"] = True
                    event_data = {
                        ATTR_HELD_BUTTON: btn,
                        ATTR_DIRECTION: direction,
                        ATTR_SPEED: speed,
                        ATTR_BRIGHTNESS_DELTA: payload.get(
                            "action_brightness_delta", 0
                        ),
                        ATTR_ABS_BRIGHTNESS_DELTA: abs(
                            payload.get("action_brightness_delta", 0)
                        ),
                        ATTR_ACTION: f"button_{btn}_dial_brightness_step_{direction}",
                        ATTR_DEVICE_ID: device_id,
                    }
                    hass.bus.async_fire(EVENT_TYPE_COMBINED, event_data)
                    _LOGGER.debug("Emitted combined legacy rotate event (btn %s)", btn)
                else:
                    event_data = {
                        ATTR_DIRECTION: direction,
                        ATTR_SPEED: speed,
                        ATTR_BRIGHTNESS_DELTA: payload.get(
                            "action_brightness_delta", 0
                        ),
                        ATTR_ABS_BRIGHTNESS_DELTA: abs(
                            payload.get("action_brightness_delta", 0)
                        ),
                        ATTR_ACTION: f"brightness_step_{direction}",
                        ATTR_DEVICE_ID: device_id,
                    }
                    hass.bus.async_fire(EVENT_TYPE_DIAL, event_data)
                    _LOGGER.debug("Emitted dial event from legacy rotate")
                return

        except Exception as err:
            _LOGGER.error("Error processing MQTT message: %s", err)

    # Subscribe to MQTT topic
    device_data["unsubscribe"] = await mqtt.async_subscribe(
        hass, topic, message_received, 1
    )

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register device triggers
    entry.async_on_unload(entry.add_update_listener(update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unsubscribe from MQTT
    if unsubscribe := hass.data[DOMAIN][entry.entry_id].get("unsubscribe"):
        unsubscribe()

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
