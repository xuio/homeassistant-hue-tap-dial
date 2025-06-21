"""Config flow for Hue Tap Dial MQTT integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import mqtt
from homeassistant.const import CONF_DEVICE_ID, CONF_NAME
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hue Tap Dial MQTT."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize."""
        self._discovered_devices: dict[str, Any] = {}
        self._device_id: str | None = None
        self._device_name: str | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            skip_check = user_input.get("skip_mqtt_check", False)

            # Check if already configured
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            # Skip MQTT validation if requested
            if skip_check:
                _LOGGER.info(
                    "Skipping MQTT validation for device %s as requested",
                    device_id,
                )
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_DEVICE_ID: device_id,
                        CONF_NAME: user_input[CONF_NAME],
                    },
                )

            # Check if MQTT is available
            if not await mqtt.async_wait_for_mqtt_client(self.hass):
                errors["base"] = "mqtt_not_available"
            else:
                # Test MQTT subscription
                try:
                    topic = f"zigbee2mqtt/{device_id}"

                    # Simply test if we can subscribe - don't require messages
                    unsubscribe = await mqtt.async_subscribe(
                        self.hass, topic, lambda msg: None, 1
                    )

                    # Unsubscribe immediately - we just wanted to test the connection
                    unsubscribe()

                    _LOGGER.info(
                        "Successfully tested MQTT subscription for device %s",
                        device_id,
                    )

                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=user_input,
                    )

                except Exception as err:
                    _LOGGER.error(
                        "Failed to subscribe to MQTT topic %s: %s",
                        topic,
                        err,
                    )
                    errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_ID): str,
                    vol.Required(CONF_NAME, default="Hue Tap Dial"): str,
                    vol.Optional("skip_mqtt_check", default=False): bool,
                }
            ),
            errors=errors,
            description_placeholders={
                "mqtt_tip": "If you're having connection issues but know your device is working, you can check 'Skip MQTT validation'",
            },
        )

    async def async_step_mqtt(self, discovery_info: dict[str, Any]) -> FlowResult:
        """Handle MQTT discovery."""
        # Extract device info from zigbee2mqtt discovery
        _LOGGER.debug("MQTT discovery info: %s", discovery_info)

        # Get device info from discovery data
        device = discovery_info.get("device", {})
        device_id = discovery_info.get("device_id")
        device_name = discovery_info.get("name", device_id)

        if not device_id:
            return self.async_abort(reason="invalid_discovery_info")

        # Set unique ID based on device identifier
        ieee_addr = device.get("ieee_address", device.get("ieeeAddr", ""))
        unique_id = ieee_addr if ieee_addr else device_id

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured(
            updates={
                CONF_DEVICE_ID: device_id,
                CONF_NAME: device_name,
            }
        )

        self._device_id = device_id
        self._device_name = device_name

        # Show device info in discovery notification
        self.context["title_placeholders"] = {
            "name": device_name,
            "model": device.get("model", "Hue Tap Dial"),
        }

        return await self.async_step_confirm()

    async def async_step_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        if user_input is not None:
            return self.async_create_entry(
                title=self._device_name,
                data={
                    CONF_DEVICE_ID: self._device_id,
                    CONF_NAME: self._device_name,
                },
            )

        return self.async_show_form(
            step_id="confirm",
            description_placeholders={
                "name": self._device_name,
                "device_id": self._device_id,
            },
        )
