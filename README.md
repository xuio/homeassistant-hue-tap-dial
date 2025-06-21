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

### Troubleshooting Discovery
If auto-discovery doesn't work:
- Enable debug logging (see [TEST_DISCOVERY.md](TEST_DISCOVERY.md))
- Try the manual discovery service: `hue_tap_dial_mqtt.discover_devices`
- Ensure your device name contains "tap_dial" or rename it in zigbee2mqtt
- Use manual configuration as described above

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

## Automation Examples

### Basic Button Press
```yaml
automation:
  - alias: "Tap Dial Button 1 Press"
    trigger:
      - platform: state
        entity_id: event.hue_tap_dial_button_1
        attribute: event_type
        to: "press"
    action:
      - service: light.toggle
        target:
          entity_id: light.living_room
```

### Dial Rotation for Volume Control
```yaml
automation:
  - alias: "Tap Dial Volume Control"
    trigger:
      - platform: state
        entity_id: event.hue_tap_dial_dial
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.attributes.event_type in ['rotate_left_slow', 'rotate_right_slow'] }}"
    action:
      - service: media_player.volume_set
        target:
          entity_id: media_player.living_room
        data:
          volume_level: >
            {% set current = state_attr('media_player.living_room', 'volume_level') | float %}
            {% if trigger.to_state.attributes.direction == 'left' %}
              {{ (current - 0.05) | max(0) }}
            {% else %}
              {{ (current + 0.05) | min(1) }}
            {% endif %}
```

### Combined Button + Dial for Temperature Control
```yaml
automation:
  - alias: "Tap Dial AC Temperature Control"
    trigger:
      - platform: event
        event_type: hue_tap_dial_combined
    condition:
      - condition: template
        value_template: "{{ trigger.event.data.held_button == 1 }}"
    action:
      - service: climate.set_temperature
        target:
          entity_id: climate.living_room
        data:
          temperature: >
            {% set current = state_attr('climate.living_room', 'temperature') | float %}
            {% if trigger.event.data.direction == 'left' %}
              {{ current - 1 }}
            {% else %}
              {{ current + 1 }}
            {% endif %}
```

## Events

The integration fires three types of events:

### Button Events (`hue_tap_dial_button`)
- `button`: Button number (1-4)
- `event_type`: press, press_release, hold, hold_release
- `duration`: Hold duration (for hold events)

### Dial Events (`hue_tap_dial_dial`)
- `direction`: left or right (for rotation), up or down (for brightness steps)
- `speed`: slow or fast (for rotation events)
- `brightness`: Current brightness value (0-255)
- `brightness_delta`: Change in brightness (e.g., +32, -14) - from z2m
- `abs_brightness_delta`: Absolute value of the change (always positive)
- `step_size`: The step size used (from z2m)
- `transition_time`: Transition time in seconds (from z2m)
- `action_time`: Time of the action (from z2m)
- `action_type`: Type of action (step/rotate) (from z2m)

### Combined Events (`hue_tap_dial_combined`)
- `held_button`: Which button is being held (1-4)
- `direction`: left or right
- `speed`: slow or fast
- `brightness`: Current brightness value (0-255)
- `action_time`: Time of the action (from z2m)
- `action_type`: Type of action (from z2m)

## Using Z2M Attributes in Automations

The integration passes through additional attributes from zigbee2mqtt, particularly useful for brightness control:

### Example: Using brightness_delta
```yaml
automation:
  - alias: "Precise Brightness Control"
    trigger:
      - platform: state
        entity_id: event.hue_tap_dial_dial
    condition:
      - condition: template
        value_template: "{{ 'brightness_step' in trigger.to_state.attributes.event_type }}"
    action:
      - service: light.turn_on
        target:
          entity_id: light.living_room
        data:
          brightness_step: "{{ trigger.to_state.attributes.brightness_delta | int(0) }}"
```

This uses the exact brightness delta value from the device, providing smooth and precise dimming control.

## Troubleshooting

- Make sure your zigbee2mqtt is properly configured and the Tap Dial is paired
- Check that MQTT integration is installed and configured in Home Assistant
- The device ID should match exactly what's shown in zigbee2mqtt
- Check Home Assistant logs for any error messages

### Template Warnings
If you see warnings like `Template variable warning: 'dict object' has no attribute 'action_type'`, these are from zigbee2mqtt's auto-discovery, not our integration. See [DISABLE_Z2M_DISCOVERY.md](DISABLE_Z2M_DISCOVERY.md) for solutions.

## Device Triggers

You can also use device triggers in automations for a simpler setup:

1. Create a new automation
2. Choose "Device" as trigger type
3. Select your Tap Dial device
4. Choose from available triggers like "Button 1 pressed" or "Dial rotated left slowly"
