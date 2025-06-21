"""Sensor platform for Hue Tap Dial MQTT."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_DEVICE_ID,
    CONF_NAME,
    PERCENTAGE,
    SIGNAL_STRENGTH_DECIBELS,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    MANUFACTURER,
    MODEL,
    ATTR_LINKQUALITY,
    ATTR_INSTALLED_VERSION,
    ATTR_LATEST_VERSION,
    ATTR_UPDATE_AVAILABLE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Hue Tap Dial MQTT sensor."""
    device_data = hass.data[DOMAIN][config_entry.entry_id]
    device_id = config_entry.data[CONF_DEVICE_ID]
    device_name = config_entry.data[CONF_NAME]

    # Create battery sensor
    battery_sensor = HueTapDialBatterySensor(
        config_entry.entry_id,
        device_id,
        device_name,
        device_data.get("last_battery"),
    )
    link_sensor = HueTapDialLinkQualitySensor(
        config_entry.entry_id,
        device_id,
        device_name,
        device_data.get("last_linkquality"),
    )
    version_installed = HueTapDialTextSensor(
        config_entry.entry_id,
        device_id,
        device_name,
        "Installed Firmware",
        ATTR_INSTALLED_VERSION,
        device_data.get("installed_version"),
    )
    version_latest = HueTapDialTextSensor(
        config_entry.entry_id,
        device_id,
        device_name,
        "Latest Firmware",
        ATTR_LATEST_VERSION,
        device_data.get("latest_version"),
    )
    update_avail = HueTapDialTextSensor(
        config_entry.entry_id,
        device_id,
        device_name,
        "Update Available",
        ATTR_UPDATE_AVAILABLE,
        device_data.get("update_available"),
    )

    async_add_entities(
        [battery_sensor, link_sensor, version_installed, version_latest, update_avail]
    )


class HueTapDialBatterySensor(SensorEntity):
    """Representation of a Hue Tap Dial battery sensor."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(
        self,
        config_entry_id: str,
        device_id: str,
        device_name: str,
        initial_battery: int | None,
    ) -> None:
        """Initialize the battery sensor."""
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_battery"
        self._attr_name = f"{device_name} Battery"
        self._attr_native_value = initial_battery

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_added_to_hass(self) -> None:
        """Subscribe to battery updates."""

        @callback
        def battery_update(battery_level: int) -> None:
            """Handle battery update."""
            self._attr_native_value = battery_level
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._config_entry_id}_battery",
                battery_update,
            )
        )


class HueTapDialLinkQualitySensor(SensorEntity):
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, config_entry_id, device_id, device_name, initial):
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        self._attr_unique_id = f"{device_id}_linkquality"
        self._attr_name = f"{device_name} Linkquality"
        self._attr_native_value = initial
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_added_to_hass(self):
        @callback
        def _update(val):
            self._attr_native_value = val
            self.async_write_ha_state()

        self.async_on_remove(
            async_dispatcher_connect(
                self.hass, f"{DOMAIN}_{self._config_entry_id}_linkquality", _update
            )
        )


class HueTapDialTextSensor(SensorEntity):
    _attr_state_class = None

    def __init__(self, config_entry_id, device_id, device_name, label, key, initial):
        self._config_entry_id = config_entry_id
        self._device_id = device_id
        slug = key
        self._attr_unique_id = f"{device_id}_{slug}"
        self._attr_name = f"{device_name} {label}"
        self._attr_native_value = initial
        self._key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    async def async_added_to_hass(self):
        topic = f"{DOMAIN}_{self._config_entry_id}_{self._key}"

        @callback
        def _update(val):
            self._attr_native_value = val
            self.async_write_ha_state()

        self.async_on_remove(async_dispatcher_connect(self.hass, topic, _update))
