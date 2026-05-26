import paho.mqtt.client as mqtt 
from random import uniform
import time, base64, os

alarm_status = 0
os.makedirs("images", exist_ok=True)

def on_message(client, userdata, message):
    global alarm_status
    if message.topic == "ALARM/IMAGE":
        encoded = message.payload.decode("utf-8")
        img_bytes = base64.b64decode(encoded)

        timestamp = time.strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"images/{timestamp}.jpg"

        with open(filename, "wb") as f:
            f.write(img_bytes)

        print(f"Image saved: {filename}")

        alarm_status = 1
        Publish(client, 1) 

def Publish(client, status):
  client.publish("ALARM/STATUS", status)
  print(f"Just published {status} to topic ALARM/STATUS")



## ***********************************************
mqttBroker = "broker.hivemq.com" 
websocket_port = 8000  
websocket_path = "/mqtt"
# 1883 - (TCP), unencrypted, unauthenticated
# 8883 - (TCP), encrypted (TLS/SSL), unauthenticated
# 8000 - (WebSockets), unencrypted, unauthenticated (requires websocket_path = "/mqtt")
# 8884 - (WebSockets), encrypted (WSS), unauthenticated (requires path /mqtt)

# Initialize Paho Client with WebSockets
client = mqtt.Client("Server-01", transport="websockets")
client.ws_set_options(path=websocket_path) # websockets path !!!
client.on_message = on_message

# topics: 
# ALARM/DETECTED for images
# ALARM/STATUS for turning on/off the alarm

print("Connecting to broker via WebSockets...")
try:
    # Connect using port 8000
    client.connect(mqttBroker, port=websocket_port) 

    client.loop_start()

    client.subscribe("ALARM/IMAGE")
    print("Successfully connected and loop started!")
except Exception as e:
    print(f"Connection failed: {e}")
    exit(1)
# ***************************************************

try:
    while True:
        if alarm_status == 1:
            print("⚠ Alarm is ON. Press Enter to acknowledge and reset.")
            input()           
            alarm_status = 0
            Publish(client, 0)  
            print("Alarm acknowledged and reset.")
        else:
            time.sleep(1)

except KeyboardInterrupt:
    print("\nDisconnecting...")
    client.loop_stop()
    client.disconnect()

