import paho.mqtt.client as mqtt
import time
from random import uniform

alarm_status = False

def on_message(client, userdata, message):
	global alarm_status
	payload = message.payload.decode("utf-8").strip()

	print(f"Received message on {message.topic}: {payload}")
	
	if message.topic == "ALARM/STATUS":
		if payload == "1":
			alarm_status = 1
		else:
			alarm_status = 0

def Publish(client, conf):
	client.publish("ALARM/DETECTED", f"{conf:.2f}")
	print(f"Just published {conf:.2f} to topic ALARM/DETECTED")

 # ******************** Establish the Connection ***************************
mqttBroker = "broker.hivemq.com"
websocket_path = "/mqtt"
websocket_port = 8000

client = mqtt.Client(client_id="Edge-01", transport="websockets")
client.ws_set_options(path=websocket_path)
client.on_message = on_message

# topics: 
# ALARM/DETECTED for images
# ALARM/STATUS for turning on/off the alarm

print("Connecting to broker via WebSockets...")
try:
	# Connect using port 8000
	client.connect(mqttBroker, port=websocket_port) 
	client.loop_start()

	client.subscribe("ALARM/STATUS")
	print("Successfully connected and loop started!")
except Exception as e:
	print(f"Connection failed: {e}")
	exit(1)

# **************************************************************************

try:
	while True:
		if alarm_status == 1:
			print("Alarm is currently ON. Waiting for status reset...")
			time.sleep(1)  # Sleep
			continue
		else:
			# Keep looking for a person to detect
			# FAKE CODE
			randConfidence = uniform(0.0, 1.0)
			tooClose = True
			
			if(randConfidence >= 0.8 and tooClose == True): # send msg to the server to turn on the alarm on ALL devices 
				Publish(client, randConfidence)
			elif(randConfidence >= 0.8 and tooClose == False):
				print(f"PERSON IS TOO CLOSE TO THE EDGE! PLAY SOUND ON THIS DEVICE!")
			else:
				print(f"No person detected")

		time.sleep(2)

except KeyboardInterrupt:
	print("\nDisconnecting...")
	client.loop_stop()
	client.disconnect()
