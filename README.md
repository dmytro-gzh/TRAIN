# Platform Alert System
### Updated Project Proposal — Phase 2

> **Team:** TRAIN &nbsp;|&nbsp; **Course:** Edge Computing &nbsp;|&nbsp; **Due:** End of Week 5

| Name | Student ID |
|------|------------|
| Dmytro Gozha | 862553342 |
| Stephen He | 862437911 |
| Armando Hernandez | 862323898 |
| Elmer Payan | 860905133 |

***

## 📋 Table of Contents

1. [Project Overview](#1-project-overview)
2. [Use Case Examples](#2-use-case-examples)
3. [Updated Solution](#3-updated-solution)
4. [System Design Diagram](#4-system-design-diagram)
5. [Workload Distribution](#5-workload-distribution-diagram)
6. [Technical Worksheet](#6-technical-worksheet--tool-inventory)
7. [Proof of Concept Demo](#7-proof-of-concept-demo-plan)
8. [Team Contribution Report](#8-team-contribution-report--scrum-sprint-report)
9. [Repository Structure](#9-repository)
10. [Phase 3 Deployment Report](Deployment)

***

## 1. Project Overview

The Platform Alert System is a distributed edge–cloud safety system designed to prevent train-related accidents at station platforms. Two Jetson Nano units are deployed on opposite sides of the platform, each equipped with a camera and a manual stop button.

If a person is detected on the railroad tracks — either by the camera's on-device computer vision model or by a passenger pressing the emergency button — the system immediately alerts the server so an incoming train can be stopped before reaching the platform.

Why Two Inputs?
> * Camera (CV inference): Automatically detects people on the tracks using a YOLOv8-nano object detection model running directly on the Jetson Nano's GPU. This handles the common case.
> * Manual Button (GPIO): Allows a bystander to trigger an alert in edge cases where the camera may fail — for example, a small child who falls onto the tracks may be too small or partially obscured for the model to detect confidently.

Why This Requires Edge Computing
> Running real-time person detection on a live camera feed is genuine edge computation. The Jetson Nano's 128-core Maxwell GPU runs the inference model locally — no cloud round-trip is needed to decide whether a person is on the tracks. This keeps latency in the range of milliseconds, which is critical when a train may be seconds away.

***

## 2. Use Case Examples

**Example**

```
PLATFORM SIDE A                  RAILROAD                  PLATFORM SIDE B

[Button A] [Jetson A]                                    [Jetson B] [Button B]
           [Camera >────────────────────────────────────────< Camera]
                      watching the railroad area
```

```
PLATFORM SIDE A                  RAILROAD                  PLATFORM SIDE B

[Button A] [Jetson A]                                    [Jetson B] [Button B]
                                                                         ↑ pressed
                                                    alert sent to server + Jetson A notified
```

> Cameras are positioned on both platforms, overlooking the railroad.

***

## 3. Updated Solution

The solution is a three-layer distributed network deployed across two platform ends:

| Layer | Device        | Role |
|-------|---------------|---------------------------------------------------------------------------|
| Edge  | Jetson Nano   | A & B	Camera CV inference, button GPIO, local alarm activation
| Cloud | Remote server	| Train stop command, event logging, remote monitoring

Architecture Rationale
Each Jetson Nano operates as an edge device. The two Jetsons communicate directly over the local network via MQTT — if either side triggers an alert, the other side is notified immediately without waiting for the server. This ensures both ends of the platform react in parallel, even if the cloud connection is temporarily unavailable.

The server's role is coordination with external systems (the train) and persistent logging - not the primary decision maker. The decision to raise an alert is made entirely at the edge.

***

## 4. System Design Diagram

```
        ══════════ Local Network (WiFi / Ethernet) ══════════

   ┌─────────────────┐                           ┌─────────────────┐
   │   Jetson A      │                           │   Jetson B      │
   │  ─────────────  │                           │  ─────────────  │
   │  Camera (CV     │                           │  Camera (CV     │
   │  inference)     │◄──── MQTT peer alert ────►│  inference)     │
   │  Button (GPIO)  │                           │  Button (GPIO)  │
   └────────┬────────┘                           └────────┬────────┘
            │                                             │
            └──────────────────┬──────────────────────────┘
                               │ MQTT
                        ┌──────────────┐
                        │    Server    │
                        │  (via MQTT / │
                        │  playit.gg)  │
                        │              │
                        │ Sends STOP   │
                        │ command to   │
                        │ incoming     │
                        │ train        │
                        └──────────────┘
```

***

## 5. Workload Distribution Diagram

```
┌──────────────────────────────┬───────────────────────────┬──────────────────────────┐
│   Jetson Nano A & B — Edge   │   Jetson Nano A & B — Fog │   Cloud Server           │
├──────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ • Capture live camera feed   │ • Run MQTT Broker         │ • Receive alert event    │
│ • Run YOLOv8-nano inference  │   (Mosquitto) on Jetson A │ • Issue STOP command     │
│   on Jetson GPU              │ • Route peer alert to     │   to incoming train      │
│ • Threshold: "person"        │   other Jetson            │ • Log: timestamp,        │
│   class detected → alert     │ • Forward events to       │   source, Jetson ID,     │
│ • Read GPIO button state     │   cloud via playit.gg     │   confidence score       │
│ • On trigger: activate       │   tunnel                  │ • Remote monitoring      │
│   local LED alarm            │                           │   dashboard              │
│ • Publish to MQTT broker     │                           │                          │
├──────────────────────────────┼───────────────────────────┼──────────────────────────┤
│ Latency:  < 100ms (inference)│ Latency:  ~5–20ms (LAN)   │ Latency:  100ms+ (OK)    │
│ Language: Python             │ Language: C++             │ Language: C++            │
│ Compute:  Jetson GPU (CUDA)  │ Compute:  CPU only        │ Compute:  CPU            │
└──────────────────────────────┴───────────────────────────┴──────────────────────────┘

```

### MQTT Topic Structure

| Topic | Publisher | Subscriber(s) | Purpose |
|-------|-----------|---------------|---------|
| `platform/alert` | Jetson A or B | Both Jetsons | Person detected or button pressed |
| `platform/alarm` | Jetson A (Broker) | Both Jetsons | Activate local LED alarms on all nodes |
| `platform/stop` | Jetson A (Broker) | Server | Issue train stop command |

### Message Flow 

```
1. Jetson A camera detects person on tracks (edge inference)
   OR Jetson A button pressed
   └─► Jetson A publishes → platform/alert  (MQTT, local)
   └─► Jetson A activates local alarm/LED

2. Jetson B receives platform/alert
   └─► Jetson B activates local alarm/LED

3. Server receives platform/alert via playit.gg from Jetson A
   └─► Issues STOP command to incoming train
   └─► Logs: timestamp, source (camera/button), Jetson ID
```

***

## 6. Technical Worksheet — Tool Inventory

### Hardware

| Component | Qty | Role | Layer | Key Specs |
|-----------|-----|------|-------|-----------|
| Jetson Nano Developer Kit | 2 | Edge inference + fog coordination | Edge / Fog | Quad-core ARM A57, 4GB RAM, 128-core Maxwell GPU |
| USB Camera (e.g. Logitech C270) | 2 | Live video feed for CV inference | Edge | 720p, 30fps, USB 2.0 |
| Push Button | 2 | Manual emergency stop trigger | Edge | Momentary, GPIO 3.3V |
| Red LED | 2 | Simulates platform alarm activation | Edge | 3.3V GPIO-controlled |
| Resistor (330Ω) | 2 | Current limiting for LEDs | Edge | Through-hole |
| USB WiFi Dongle | 2 | Wireless connectivity for Jetson Nanos | Fog | 802.11 b/g/n, 2.4GHz |
| USB-C Power Supply | 2 | Power for Jetson Nanos | All | 5V 4A recommended |
| Jumper Wires + Breadboard | — | GPIO circuit prototyping | Edge | Standard 3.3V logic |

### Software

| Software / Library | Device | Purpose |
|--------------------|--------|---------|
| Python 3 | Jetson Nano A & B | Application runtime |
| YOLOv8-nano (`ultralytics`) | Jetson Nano A & B | Real-time person detection on camera feed |
| OpenCV (`cv2`) | Jetson Nano A & B | Camera capture and frame preprocessing |
| Mosquitto MQTT Broker | Jetson Nano A | Local message broker for both Jetsons |
| `paho-mqtt` (Python) | Jetson Nano A & B | MQTT publish/subscribe client |
| `Jetson.GPIO` (Python) | Jetson Nano A & B | Button input and LED output via GPIO |
| playit.gg agent | Jetson Nano A | Tunnel to expose MQTT events to cloud server |
| Flask or Node.js | Cloud Server | Event log API and monitoring dashboard |
| SQLite / PostgreSQL | Cloud Server | Persistent event storage |

### Network

| Parameter | Value |
|-----------|-------|
| Local network | WiFi router or mobile hotspot (2.4GHz) |
| MQTT broker address | Local IP of Jetson Nano A (e.g., `192.168.1.100`) |
| MQTT port | `1883` (unencrypted, LAN-only) |
| Cloud tunnel | playit.gg agent on Jetson Nano A |
| Internet dependency | ❌ Optional — alert and alarm function fully offline |

***

## 7. Proof of Concept Demo Plan

Two Jetson Nanos are placed on opposite ends of a table representing the two platform sides. Each has a USB camera pointed toward the center (the "railroad area"), a push button, and a red LED. Jetson A also runs the Mosquitto MQTT broker.

### Demo Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Power on both Jetsons, start MQTT broker on Jetson A | Both devices connect to broker; no LEDs active |
| 2 | Start camera feed + YOLOv8 inference on both Jetsons | Live detection running; no person present, no alert |
| 3a | A person is placed in the camera's view of the "track area" | YOLOv8 detects `person` class → Jetson publishes `platform/alert` |
| 3b *(alternative)* | Bystander presses the physical button | GPIO trigger → Jetson publishes `platform/alert` |
| 4 | Broker routes the alert to both Jetsons | Both red LEDs activate simultaneously |
| 5 | Server receives `platform/stop` via playit.gg | Server log displayed: timestamp, source (`camera`/`button`), Jetson ID, confidence score |

> **The demo is fully self-contained** — steps 1–4 require no internet connection. The server log (step 5) requires the playit.gg tunnel to be active.

***

### Contributions

| Member | Role | Contributions | Story Points |
|--------|------|--------------|:------------:|
| Dmytro Gozha | Cloud Layer Lead | Designed cloud server architecture, defined event logging schema, researched playit.gg tunnel integration for MQTT forwarding | 8 |
| Stephen He | Edge Detection Developer | Implemented camera-based person/fire detection pipeline on Jetson Nano B using YOLOv8, integrated inference output with MQTT event triggers | 8 |
| Armando Hernandez | Edge Logic Developer | Developed alert decision logic on edge device, implemented GPIO-based LED alarm response and threshold-based trigger conditions | 8 |
| Elmer Payan | Local Network Lead | Designed MQTT broker setup on Jetson Nano A, defined topic structure and peer alert routing, documented workload distributio | 8 |


✅ Completed This Sprint
> Pivoted architecture from fire suppression (ESP32) to platform alert system (Jetson Nano + CV)
> 
> Defined edge computation: YOLOv8-nano person detection running on Jetson GPU
>
> Defined dual-trigger input: camera inference + manual GPIO button
>
> Selected all hardware components
>
> Designed MQTT topic structure and full message flow
>
> Produced system design diagram and workload distribution diagram
>
> Completed technical worksheet (tool inventory)
>
> Defined proof of concept demo plan
>
> Submitted Phase 2 updated proposal

🔄 In Progress — Next Sprint
> Set up YOLOv8-nano on both Jetson Nanos (CUDA-accelerated)
>
> Implement GPIO button input and LED output
>
> Set up Mosquitto broker on Jetson Nano A
>
> Implement paho-mqtt client on both Jetsons
>
> Implement cloud server event logging API
>
> Integration testing across both Jetsons and server

***

## 9. Repository

```
TRAIN/
├── edge/               # Jetson Nano
├── cloud/              # Cloud server — event logging + dashboard
└── docs/               # Diagrams, proposals, and documentation
```


***

## 10. Project Overview
Phase 3 Deployment Report: https://docs.google.com/document/d/1-yZTZA6YvkL44RkCZYfoHt20mk35DeY9BIR_ChQRNmI/edit?usp=sharing
The link above contains our report for the phase 3 Deployment.

*Phase 2 Update &nbsp;|&nbsp; Team TRAIN &nbsp;|&nbsp; Edge Computing*
