# Hue Tap Dial MQTT Integration for Home Assistant

This custom integration allows you to use the Philips Hue Tap Dial Switch with Home Assistant via zigbee2mqtt.

## Features

- **4 Buttons**: Each button supports press, release, hold, and hold release events
- **Dial Rotation**: Supports slow and fast rotation in both directions
- **Combined Actions**: Special events when holding a button while rotating the dial
- **Battery Sensor**: Displays the current battery level
- **Auto-discovery**: Automatically discovers Tap Dial devices via zigbee2mqtt

## HACS Installation

1. In Home Assistant, go to HACS → Integrations → ⋮ (upper-right) → Custom repositories.
2. Add `https://github.com/xuio/homeassistant-hue-tap-dial` as *Integration* category.
3. Search for "Hue Tap Dial MQTT" and install.
4. Restart Home Assistant.
5. Configure via Settings → Devices & Services.

## Manual Installation

1. Copy the `hue_tap_dial_mqtt` folder to your `custom_components` directory
2. Restart Home Assistant
3. The integration will attempt auto-discovery of your devices
4. If devices appear in the "Discovered" tab, click to configure them
5. If auto-discovery doesn't work:
   - Go to Settings → Devices & Services → Add Integration
   - Search for "Hue Tap Dial MQTT"
   - Enter your device ID (as shown in zigbee2mqtt, e.g., "tap_dial_bedroom")
   - Check "Skip MQTT validation" if you get connection errors

## Entities Created

For each Tap Dial device, the following entities are created:

### Event Entities
- **Button 1-4**: Individual event entities for each button
- **Dial**: Event entity for dial rotation
- **Combined Actions**: Event entity for button+dial combinations

### Sensor Entities
- **Battery**: Shows the current battery percentage
- **Linkquality**: Zigbee signal strength (dB)
- **Installed Firmware**: Currently installed firmware version
- **Latest Firmware**: Latest version available
- **Update Available**: Boolean that indicates if a newer firmware is available

## Events

The integration fires three types of events:

### Button Events (`hue_tap_dial_button`)
- `button`: Button number (1-4)
- `event_type`: press, press_release, hold, hold_release
- `duration`: Hold duration (for hold events)

### Dial Events (`hue_tap_dial_dial`)
- `brightness`: Current brightness value (0-255)
- `brightness_delta`: Change in brightness (e.g., +32, -14) - from z2m
- `abs_brightness_delta`: Absolute value of the change (always positive)

### Combined Events (`hue_tap_dial_combined`)
- `brightness`: Current brightness value (0-255)
- `brightness_delta`: Change in brightness (e.g., +32, -14) - from z2m
- `abs_brightness_delta`: Absolute value of the change (always positive)

## Device Triggers

You can also use device triggers in automations for a simpler setup:

1. Create a new automation
2. Choose "Device" as trigger type
3. Select your Tap Dial device
4. Choose from available triggers like "Button 1 pressed" or "Dial rotated left slowly"
