import paho.mqtt.client as mqtt
from random import uniform
import base64, os, time, cv2, json
from datetime import datetime
from ultralytics import YOLO

alarm_status = False

# -----------------------------
# CAMERA / YOLO SETTINGS
# -----------------------------

CAMERA_INDEX = 0

MODEL_NAME = "yolov5nu.pt"

CONFIDENCE_THRESHOLD = 0.80

YOLO_IMAGE_SIZE = 224

PROCESS_EVERY_N_FRAMES = 3

CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240

PHOTO_COOLDOWN_SECONDS = 5

PHOTO_FOLDER = "captured_photos"

# ------------------------------

def create_filename():
    """
    Creates a photo filename using date and time.
    human_2026-05-19_15-42-10.jpg
    """

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    return f"human_{timestamp}.jpg"

def on_message(client, userdata, message):
  global alarm_status
  payload = message.payload.decode("utf-8").strip()

  print(f"Received message on {message.topic}: {payload}")
  
  if message.topic == "ALARM/STATUS":
    if payload == "1":
      alarm_status = 1
    else:
      alarm_status = 0

def publish_image(client):
    images = sorted(os.listdir(PHOTO_FOLDER)) 
    if not images:
        print("No images found, skipping.")
        return

    filepath = f"{PHOTO_FOLDER}/{images[0]}"  

    with open(filepath, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")

    client.publish("ALARM/IMAGE", encoded, qos=1)
    print(f"Published image: {filepath}")

    os.remove(filepath)  # Delete after sending
    print(f"Deleted: {filepath}")

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

os.makedirs(PHOTO_FOLDER, exist_ok=True)

# *** SET UP YOLO ***
print("Loading YOLO model...")
model = YOLO(MODEL_NAME)

print("Opening USB camera...")
cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Error: Could not open USB camera.")
    print("Try changing CAMERA_INDEX from 0 to 1.")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
cap.set(cv2.CAP_PROP_FPS, 30)

frame_count = 0
last_boxes = []
last_photo_time = 0

print("Jetson A human photo sender started.")

# ******


try:
    while True:
        if alarm_status:
            print("Alarm is currently ON. Waiting for status reset...")
            time.sleep(1)
            continue

        ret, frame = cap.read()
        if not ret:
            print("Error: Could not read camera frame.")
            break

        frame_count += 1

        if frame_count % PROCESS_EVERY_N_FRAMES == 0:
            results = model(
                frame,
                imgsz=YOLO_IMAGE_SIZE,
                conf=CONFIDENCE_THRESHOLD,
                classes=[0],  # COCO class 0 = person
                verbose=False
            )

            last_boxes = []
            human_detected = False
            tooClose = False  # TODO: replace with your actual proximity logic

            for result in results:
                for box in result.boxes:
                    confidence = float(box.conf[0])
                    if confidence >= CONFIDENCE_THRESHOLD:
                        human_detected = True
                        x1, y1, x2, y2 = box.xyxy[0]
                        last_boxes.append((int(x1), int(y1), int(x2), int(y2), confidence))

            current_time = time.time()

            if human_detected and current_time - last_photo_time >= PHOTO_COOLDOWN_SECONDS:
                if tooClose:
                    print("PERSON IS TOO CLOSE TO THE EDGE! PLAY SOUND ON THIS DEVICE!")

                else:
                    filename = create_filename()
                    image_path = os.path.join(PHOTO_FOLDER, filename)
                    cv2.imwrite(image_path, frame)
                    print(f"Human detected! Saved: {image_path}")
                    publish_image(client)
                    last_photo_time = current_time
            else:
                print("No person detected")

        # Draw detection boxes
        for x1, y1, x2, y2, confidence in last_boxes:
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                frame,
                f"Human {confidence:.2f}",
                (x1, max(y1 - 10, 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6, (0, 255, 0), 2
            )

        cv2.imshow("Edge Client - Human Detector", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

except KeyboardInterrupt:
    print("\nDisconnecting...")
    cap.release()
    cv2.destroyAllWindows()
    client.loop_stop()
    client.disconnect()
