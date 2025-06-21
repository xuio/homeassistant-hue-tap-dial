#!/usr/bin/env python3
"""Test script for Hue Tap Dial MQTT integration.

Run this script to verify your device is working correctly.
Usage: python test_integration.py <device_id>
"""

import sys
import time
import json
import paho.mqtt.client as mqtt


def on_connect(client, userdata, flags, rc):
    """Callback for MQTT connection."""
    if rc == 0:
        print("✓ Connected to MQTT broker successfully")
        topic = f"zigbee2mqtt/{userdata['device_id']}"
        client.subscribe(topic)
        print(f"✓ Subscribed to topic: {topic}")
        print("\nNow press buttons or rotate the dial on your Tap Dial device...")
        print("Press Ctrl+C to exit\n")
    else:
        print(f"✗ Failed to connect to MQTT broker (code: {rc})")
        sys.exit(1)


def on_message(client, userdata, msg):
    """Callback for MQTT messages."""
    try:
        payload = json.loads(msg.payload.decode())

        # Format output
        print(f"{'=' * 60}")
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Topic: {msg.topic}")

        if "action" in payload:
            print(f"Action: {payload['action']}")

            # Parse action type
            action = payload["action"]
            if action.startswith("button_"):
                parts = action.split("_")
                if len(parts) >= 3:
                    button_num = parts[1]
                    action_type = "_".join(parts[2:])
                    print(f"  - Button: {button_num}")
                    print(f"  - Type: {action_type}")
            elif "dial_rotate" in action:
                direction = "left" if "left" in action else "right"
                speed = "fast" if "fast" in action else "slow"
                print(f"  - Direction: {direction}")
                print(f"  - Speed: {speed}")

        if "battery" in payload:
            print(f"Battery: {payload['battery']}%")

        if "brightness" in payload:
            print(f"Brightness: {payload['brightness']}")

        if "action_duration" in payload:
            print(f"Duration: {payload['action_duration']}s")

        print(f"{'=' * 60}\n")

    except json.JSONDecodeError:
        print(f"✗ Invalid JSON received: {msg.payload}")
    except Exception as e:
        print(f"✗ Error processing message: {e}")


def main():
    """Main test function."""
    if len(sys.argv) != 2:
        print("Usage: python test_integration.py <device_id>")
        print("Example: python test_integration.py tap_dial_bedroom")
        sys.exit(1)

    device_id = sys.argv[1]

    print(f"Testing Hue Tap Dial device: {device_id}")
    print(f"{'=' * 60}\n")

    # Create MQTT client
    userdata = {"device_id": device_id}
    client = mqtt.Client(userdata=userdata)
    client.on_connect = on_connect
    client.on_message = on_message

    # Try to connect
    try:
        # Default MQTT settings - adjust if needed
        broker = "localhost"
        port = 1883

        print(f"Connecting to MQTT broker at {broker}:{port}...")
        client.connect(broker, port, 60)

        # Start loop
        client.loop_forever()

    except KeyboardInterrupt:
        print("\n\nTest stopped by user")
        client.disconnect()
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nMake sure:")
        print("1. MQTT broker is running")
        print("2. The broker address and port are correct")
        print("3. The device ID matches your zigbee2mqtt configuration")
        sys.exit(1)


if __name__ == "__main__":
    main()
