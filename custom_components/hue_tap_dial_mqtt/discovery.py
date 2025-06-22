"""Discovery support for Hue Tap Dial via zigbee2mqtt."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from homeassistant.components import mqtt
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Store processed devices to avoid duplicate discoveries
_discovered_devices: set[str] = set()
_configured_ids: set[str] = set()


async def async_setup_discovery(hass: HomeAssistant) -> None:
    """Set up discovery for Hue Tap Dial devices."""

    @callback
    def async_device_discovered(msg):
        """Handle discovery message from zigbee2mqtt bridge/devices."""
        _LOGGER.debug("Received devices message on topic: %s", msg.topic)
        try:
            # Parse the devices list
            devices = json.loads(msg.payload)
            _LOGGER.debug("Parsed devices payload: %s", type(devices))

            if isinstance(devices, list):
                _LOGGER.info("Processing %d devices from zigbee2mqtt", len(devices))
                for device in devices:
                    process_device(hass, device)
            elif isinstance(devices, dict):
                process_device(hass, devices)

        except Exception as err:
            _LOGGER.error("Error processing devices message: %s", err)
            _LOGGER.debug("Raw payload: %s", msg.payload)

    @callback
    def async_bridge_log(msg):
        """Handle log messages to detect device availability."""
        try:
            log_data = json.loads(msg.payload)
            if log_data.get("type") == "device_connected":
                message = log_data.get("message", "")
                # Check if it mentions a tap dial
                if any(x in message.lower() for x in ["tap dial", "rdm002"]):
                    _LOGGER.debug("Detected Tap Dial connection in logs: %s", message)

        except Exception:
            pass

    @callback
    def async_device_announce(msg):
        """Handle device announce messages."""
        _LOGGER.debug("Device announce on topic: %s", msg.topic)
        try:
            # Extract device name from topic
            topic_parts = msg.topic.split("/")
            if len(topic_parts) >= 2 and topic_parts[0] == "zigbee2mqtt":
                device_name = topic_parts[1]
                if device_name not in ["bridge", "availability"]:
                    # Check if this could be a tap dial
                    payload = json.loads(msg.payload)
                    _LOGGER.debug("Device %s payload: %s", device_name, payload)

                    # If it has action field, it might be a tap dial
                    if "action" in payload or "battery" in payload:
                        # Request device info
                        _LOGGER.info(
                            "Requesting info for potential Tap Dial: %s", device_name
                        )
                        hass.async_create_task(
                            mqtt.async_publish(
                                hass,
                                f"zigbee2mqtt/bridge/devices/{device_name}",
                                "",
                                0,
                                False,
                            )
                        )

        except Exception as err:
            _LOGGER.debug("Error in device announce: %s", err)

    def process_device(
        hass: HomeAssistant, device: dict, device_id: str = None
    ) -> None:
        """Process a discovered device."""
        # Log device info for debugging
        _LOGGER.debug(
            "Processing device: %s",
            json.dumps(
                {
                    "model": device.get("model", ""),
                    "manufacturer": device.get("manufacturer", ""),
                    "friendly_name": device.get("friendly_name", ""),
                    "type": device.get("type", ""),
                }
            ),
        )

        # Get device info
        model = device.get("model", "")
        manufacturer = device.get("manufacturer", "")
        friendly_name = device.get("friendly_name", device_id)
        ieee_addr = device.get("ieee_address", device.get("ieeeAddr", ""))
        device_type = device.get("type", "")

        # Check if this is a Tap Dial device - expanded detection
        is_tap_dial = any(
            [
                "RDM002" in model,
                "8719514491069" in str(device.get("model_id", "")),  # Product code
                "Tap Dial" in model,
                "tap dial" in model.lower(),
                "tap_dial" in friendly_name.lower() if friendly_name else False,
                "dial" in device_type.lower(),
                (manufacturer.lower() == "philips" and "dial" in model.lower()),
                # Check definition if available
                "dial"
                in str(device.get("definition", {}).get("description", "")).lower(),
            ]
        )

        if not is_tap_dial:
            _LOGGER.debug(
                "Device %s is not a Tap Dial (model: %s, manufacturer: %s, type: %s)",
                friendly_name,
                model,
                manufacturer,
                device_type,
            )
            return

        if not friendly_name:
            _LOGGER.warning("Tap Dial device found but no friendly_name")
            return

        # Use IEEE address or friendly name as unique ID
        unique_id = ieee_addr if ieee_addr else friendly_name

        # Skip if device already configured
        if (
            friendly_name in _configured_ids
            or ieee_addr in _configured_ids
            or device_id in _configured_ids
        ):
            _LOGGER.debug(
                "Device %s already configured, skipping discovery", friendly_name
            )
            return

        # Check if already discovered
        if unique_id in _discovered_devices:
            _LOGGER.debug("Device %s already discovered", unique_id)
            return

        _discovered_devices.add(unique_id)

        discovery_info = {
            "name": friendly_name,
            "device": device,
            "device_id": friendly_name,
        }

        _LOGGER.info(
            "Discovered Hue Tap Dial device: %s (model: %s, manufacturer: %s)",
            friendly_name,
            model,
            manufacturer,
        )

        # Create discovery flow
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "mqtt"},
                data=discovery_info,
            )
        )

    # Subscribe to various topics for discovery
    await mqtt.async_subscribe(
        hass, "zigbee2mqtt/bridge/devices", async_device_discovered, 0
    )

    await mqtt.async_subscribe(hass, "zigbee2mqtt/bridge/log", async_bridge_log, 0)

    # Subscribe to all device messages to detect tap dials
    await mqtt.async_subscribe(hass, "zigbee2mqtt/+", async_device_announce, 0)

    # Wait a bit for MQTT to be ready
    await asyncio.sleep(2)

    # Request current devices list
    _LOGGER.info("Requesting device list from zigbee2mqtt")
    await mqtt.async_publish(hass, "zigbee2mqtt/bridge/devices/get", "", 0, False)

    # build configured id set
    for ent in hass.config_entries.async_entries(DOMAIN):
        _configured_ids.add(ent.data.get(CONF_DEVICE_ID, ""))
        if ent.unique_id:
            _configured_ids.add(ent.unique_id)

    # No runtime listener needed; duplicates prevented by initial set

    _LOGGER.info("Hue Tap Dial MQTT discovery set up")
