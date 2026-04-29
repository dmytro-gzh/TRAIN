# TRAIN — Train Fire Suppression and Alert System
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

***

## 1. Project Overview

TRAIN is a distributed **edge–fog–cloud** fire suppression and early warning system designed for passenger trains. 
Each train car is equipped with an **ESP32 microcontroller** connected to a CO₂/smoke sensor. When fire is detected in any car, the system responds in layers:

- 🔴 The **affected car** immediately activates local suppression
- 🟠 **Adjacent cars** preemptively activate suppression before fire spreads
- 🟡 **Non-adjacent cars** receive an alarm only — no unnecessary water activation
- ☁️ The **cloud server** is notified to halt the train and log the event

This layered response minimizes structural damage and avoids unnecessary panic or water damage in unaffected cars.

***

## 2. Use Case Examples

**Example 1 — Fire in Car A:**

```
   Car A               Car B               Car C
Fire detected      Water + Alarm         Alarm only
Water + Alarm
```

**Example 2 — Fire in Car B:**

```
   Car A               Car B               Car C
Water + Alarm      Fire detected        Water + Alarm
                   Water + Alarm
```

> Adjacent cars always receive preemptive suppression. Non-adjacent cars receive alarm only.

***

## 3. Updated Solution

The solution is a three-layer distributed network:

| Layer | Device | Role |
|-------|--------|------|
| **Edge** | ESP32 (×3, one per car) | Sense, respond locally, publish alerts |
| **Fog** | Jetson Nano (×1, train head) | MQTT broker, adjacency logic, coordination |
| **Cloud** | Remote server | Event logging, remote monitoring |

### Why ESP32 at the Edge?

Replacing per-car Jetson Nanos with ESP32 units significantly reduces cost, power draw, and complexity while maintaining full capability for the sensing and response tasks required at the edge.

| | ESP32 per car | Jetson Nano per car |
|---|---|---|
| **Cost** | ~$5–10 | ~$100+ |
| **Power draw** | ~240mA | ~2A+ |
| **Built-in WiFi** | ✅ Yes | ❌ Needs add-on |
| **MQTT support** | ✅ Native (`PubSubClient`) | ✅ Yes |
| **AI/ML needed?** | ❌ No | ❌ Overkill |

The Jetson Nano retains its role as the **fog coordinator**, where its processing power is used for topology management, adjacency logic, and cloud bridging.

***

## 4. System Design Diagram

```
         ══════════════ Local WiFi Network (On-Train) ══════════════
                │                      │                      │
        ┌───────────────┐      ┌───────────────┐      ┌───────────────┐
        │   ESP32       │      │   ESP32       │      │   ESP32       │
        │   Car 1       │      │   Car 2       │      │   Car 3       │
        │  ──────────   │      │  ──────────   │      │  ──────────   │
        │  CO₂ Sensor   │      │  CO₂ Sensor   │      │  CO₂ Sensor   │
        │  Suppress LED │      │  Suppress LED │      │  Suppress LED │
        │  Alarm LED    │      │  Alarm LED    │      │  Alarm LED    │
        └───────┬───────┘      └───────┬───────┘      └───────┬───────┘
                │      MQTT pub/sub    │     MQTT pub/sub      │
                └──────────────────────┴───────────────────────┘
                                       │
                              ┌────────────────┐
                              │  Jetson Nano   │  ← Fog Layer
                              │                │
                              │ MQTT Broker    │
                              │ (Mosquitto)    │
                              │                │
                              │ Adjacency      │
                              │ Logic          │
                              │                │
                              │ Stop Command   │
                              └────────┬───────┘
                                       │
                                  playit.gg
                                  (tunnel)
                                       │
                              ┌────────────────┐
                              │  Cloud Server  │  ← Cloud Layer
                              │ (Train Station │
                              │  Command Tower)│
                              │                │
                              │ Event Logging  │
                              │ Remote Monitor │
                              └────────────────┘
```

***

## 5. Workload Distribution Diagram

```
┌──────────────────────┬───────────────────────────┬──────────────────────────┐
│   ESP32 — Edge       │   Jetson Nano — Fog        │   Cloud Server           │
├──────────────────────┼───────────────────────────┼──────────────────────────┤
│ • Read CO₂/smoke     │ • Run MQTT Broker          │ • Receive event stream   │
│   sensor (ADC)       │   (Mosquitto)              │ • Store logs to DB       │
│ • Threshold check    │ • Maintain train           │ • Timestamp all events   │
│ • Activate local     │   topology map             │ • Display dashboard      │
│   LED/suppression    │ • Adjacency logic          │ • Remote monitoring      │
│ • Publish alert to   │   (suppress vs alarm only) │   for operators          │
│   broker             │ • Broadcast global alarm   │ • Cross-train analytics  │
│ • Subscribe to       │ • Issue train stop command │                          │
│   suppress + alarm   │ • Bridge events → cloud    │                          │
│   topics             │   via playit.gg tunnel     │                          │
├──────────────────────┼───────────────────────────┼──────────────────────────┤
│ Latency:  < 1ms      │ Latency:  ~5–20ms (LAN)   │ Latency:  100ms+ (OK)    │
│ Language: C/C++      │ Language: Python           │ Language: Python / Node  │
│ Power:    ~240mA     │ Power:    ~2A              │ —                        │
└──────────────────────┴───────────────────────────┴──────────────────────────┘
```

### MQTT Topic Structure

| Topic | Publisher | Subscriber(s) | Purpose |
|-------|-----------|---------------|---------|
| `train/car/N/alert` | ESP32 Car N | Jetson Nano | Fire detected in car N |
| `train/car/N/suppress` | Jetson Nano | ESP32 Car N | Trigger suppression in car N |
| `train/global/alarm` | Jetson Nano | All ESP32s | System-wide alarm broadcast |
| `train/control/stop` | Jetson Nano | Cloud / external system | Halt the train |

### Message Flow — Car 2 Fire Detection

```
1. ESP32 Car 2 — sensor threshold crossed
   ├─► Activates local LED/suppression        ← INSTANT (no network)
   └─► Publishes → train/car/2/alert          ← WiFi LAN ~5ms

2. Jetson Nano — receives alert on train/car/2/alert
   ├─► Publishes → train/car/1/suppress       ← WiFi LAN ~10ms
   ├─► Publishes → train/car/3/suppress       ← WiFi LAN ~10ms
   ├─► Publishes → train/global/alarm         ← WiFi LAN ~10ms
   └─► Publishes → train/control/stop

3. ESP32 Car 1 & Car 3 — receive suppress command
   └─► Activate suppression LED + alarm LED

4. Cloud Server — receives bridged event via playit.gg
   └─► Logs: { timestamp, car_id: "car_2", sensor_value, actions: [...] }
```

***

## 6. Technical Worksheet — Tool Inventory

### Hardware

| Component | Qty | Role | Layer | Key Specs |
|-----------|-----|------|-------|-----------|
| ESP32 Dev Board | 3 | Car sensor + actuator node | Edge | Dual-core 240MHz, built-in 2.4GHz WiFi, 520KB SRAM |
| Jetson Nano Developer Kit | 1 | Fog coordinator, MQTT broker | Fog | Quad-core ARM A57, 4GB RAM, 128-core Maxwell GPU |
| MQ-2 or MQ-135 Smoke/CO₂ Sensor | 3 | Fire/smoke detection | Edge | Analog + digital output, detects CO, CH₄, LPG, smoke |
| Red LED | 3 | Simulates local suppression activation | Edge | 3.3V GPIO-controlled |
| Yellow/Blue LED | 3 | Simulates alarm indicator | Edge | 3.3V GPIO-controlled |
| USB WiFi Dongle (if needed) | 1 | Wireless connectivity for Jetson Nano | Fog | 802.11 b/g/n, 2.4GHz |
| USB-C / MicroUSB Power Supply | 4 | Power for ESP32s and Jetson Nano | All | 5V 2A minimum for Nano |
| Jumper Wires + Breadboard | — | Circuit prototyping | Edge | Standard 3.3V/5V logic |

### Software

| Software / Library | Device | Purpose |
|--------------------|--------|---------|
| Arduino IDE / PlatformIO | ESP32 | Firmware development |
| `PubSubClient` | ESP32 | MQTT client over WiFi |
| `WiFi.h` | ESP32 | WiFi connection management |
| Mosquitto MQTT Broker | Jetson Nano | Local message broker |
| `paho-mqtt` (Python) | Jetson Nano | Fog logic, adjacency algorithm |
| Python 3 | Jetson Nano | Fog application runtime |
| playit.gg agent | Jetson Nano | Tunnel to cloud server |
| Flask or Node.js | Cloud Server | Event log API + dashboard |
| SQLite / PostgreSQL | Cloud Server | Persistent event storage |

### Network

| Parameter | Value |
|-----------|-------|
| Local network | WiFi router or mobile hotspot (2.4GHz) |
| MQTT broker address | Local IP of Jetson Nano (e.g., `192.168.1.100`) |
| MQTT port | `1883` (unencrypted, LAN-only) |
| Cloud tunnel | playit.gg agent on Jetson Nano |
| Internet dependency | ❌ Optional — system functions fully offline |

***

## 7. Proof of Concept Demo Plan

Three ESP32 units represent **Cars 1, 2, and 3**, each connected to the Jetson Nano's MQTT broker over a shared WiFi hotspot. Each ESP32 has a CO₂/smoke sensor and two LEDs (suppression + alarm).

### Demo Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| 1 | Power on all 3 ESP32s and Jetson Nano | All devices connect to broker; no LEDs active |
| 2 | Introduce controlled combustion near Car 2 sensor (burning paper) | Car 2 sensor crosses threshold |
| 3 | Car 2 threshold exceeded | Car 2 suppression LED lights immediately (edge-local) |
| 4 | Jetson Nano receives `train/car/2/alert` | Sends suppress to Cars 1 & 3, broadcasts global alarm |
| 5 | Cars 1 & 3 receive suppress command | Suppression + alarm LEDs activate on Cars 1 & 3 |
| 6 | Global alarm broadcast received by all | All alarm LEDs active across all 3 cars |
| 7 | Server log displayed on screen | Entry shown: timestamp, `car_id: car_2`, sensor value, actions |

> The demo is fully self-contained — no internet connection is required for steps 1–6. The cloud log (step 7) requires the playit.gg tunnel to be active.

***

## 8. Team Contribution Report — Scrum Sprint Report

**Sprint:** Phase 1 → Phase 2 Update
**Sprint Goal:** Finalize architecture, select hardware components, establish repository, produce updated proposal.

### Contributions

| Member | Role | Contributions | Story Points |
|--------|------|--------------|:------------:|
| Dmytro Gozha | Edge Layer Lead | Designed ESP32 firmware architecture, defined MQTT topic structure, researched ESP32 + MQ sensor integration, set up GitHub repository | 8 |
| Stephen He | Fog Layer Lead | Designed Jetson Nano fog logic, researched Mosquitto broker setup, defined adjacency algorithm, documented workload distribution | 8 |
| Armando Hernandez | Cloud Layer Lead | Designed cloud server architecture, researched playit.gg tunnel integration, defined event logging schema, drafted cloud documentation | 7 |
| Elmer Payan | Systems Integrator | Produced system design diagram, compiled technical worksheet, coordinated demo plan, assembled final proposal document | 7 |

### ✅ Completed This Sprint

- [x] Revised architecture: Jetson Nano per car → ESP32 per car + single Jetson Nano fog node
- [x] Defined MQTT topic structure and full message flow
- [x] Selected all hardware components (ESP32, MQ-2/MQ-135, LEDs, Jetson Nano)
- [x] Produced system design diagram
- [x] Produced workload distribution diagram
- [x] Completed technical worksheet (tool inventory)
- [x] Defined proof of concept demo plan
- [x] Submitted Phase 2 updated proposal

### 🔄 In Progress — Next Sprint

- [ ] ESP32 firmware: sensor polling loop + MQTT publish on threshold
- [ ] Jetson Nano fog logic: adjacency algorithm + Mosquitto broker setup
- [ ] Cloud server: event log API + monitoring dashboard
- [ ] Integration testing across all three layers
- [ ] Demo rehearsal and final adjustments

### ⚠️ Blockers

- Awaiting hardware delivery (ESP32 units, MQ-2/MQ-135 sensors)
- Confirm WiFi hotspot availability for demo environment

***

## 9. Repository

```
TRAIN/
├── edge/               # ESP32 firmware (Arduino / PlatformIO)
├── fog/                # Jetson Nano Python fog application
├── cloud/              # Cloud server — event logging + dashboard
└── docs/               # Diagrams, proposals, and documentation
```

> 🔗 **Repository:** *(add your GitHub link here)*

***

*Phase 2 Update &nbsp;|&nbsp; Team TRAIN &nbsp;|&nbsp; Edge Computing*
