# Knit Distributed Inference: Python Worker API Contract

This document defines the strict Socket.io event lifecycle and JSON payload structures required for a Python PyTorch worker to successfully join the Knit cluster. 

The Master Node (Control Plane) acts as the central router. Workers do not communicate with the database or frontend; they communicate exclusively with the Master Node via WebSockets.

---

## 1. Connection & Initial Handshake

**Endpoint:** ws://<MASTER_NODE_IPV4_ADDRESS>:3000 (Must use the local Wi-Fi IP, not localhost)
**Protocol:** WebSockets (Socket.io protocol)

### Event: `register` (Worker ➔ Master)
Must be emitted immediately upon successful connection. This provides the Master Node with the hardware specs needed to calculate proportional VRAM layer assignments.
* **Payload:**
  {
    "gpu": "String (e.g., 'NVIDIA RTX 4090')",
    "vram": "String (e.g., '24GB')"
  }

---

## 2. Fault Tolerance (Critical)

### Event: `heartbeat` (Worker ➔ Master)
The Master Node maintains a strict 1500ms drop-off window. The worker must run a background thread to pulse this event continuously, even when the main Python thread is blocked by tensor math.
* **Frequency:** Every 500 milliseconds.
* **Payload:** None.
* **Consequence:** If the Master Node misses 3 heartbeats (1500ms), the worker is marked as `dead`, the pipeline is forcibly recalculated, and any active inference is aborted.

---

## 3. Pipeline Topology

### Event: `pipeline_rebuilt` (Master ➔ Worker)
Emitted by the Master Node whenever *any* node joins or drops from the network. The payload contains the entire cluster's layer map. The worker must extract its own assignment using its specific `socket.id`.
* **Payload Structure:**
  {
    "<socket_id_1>": {
      "orderIndex": 1,
      "startLayer": 0,
      "endLayer": 47,
      "totalAssigned": 48,
      "nextNode": "<socket_id_2>"
    },
    "<socket_id_2>": {
      "orderIndex": 2,
      "startLayer": 48,
      "endLayer": 79,
      "totalAssigned": 32,
      "nextNode": null
    }
  }
* **Worker Action:** The Python script must load only the `.safetensors` associated with layers `startLayer` through `endLayer` into GPU VRAM. 

---

## 4. The Inference Relay

### Event: `start_inference` (Master ➔ Worker)
Routed strictly to the worker holding `orderIndex: 1`. 
* **Payload:**
  {
    "prompt": "String (The raw user input from the UI)"
  }
* **Worker Action:** Process the prompt through its assigned layers, generate the intermediate tensor, and transmit that tensor directly to the worker at `nextNode`.

### Event: `stream_token` (Worker ➔ Master)
Emitted by the final worker in the relay (the node where `nextNode` is `null`) as it decodes words. The Master Node acts as a pass-through to stream this to the React UI.
* **Payload:**
  {
    "token": "String (A single decoded word/sub-word, including any trailing spaces)"
  }

### Event: `inference_complete` (Worker ➔ Master)
Emitted by the final worker when the `<EOS>` (End of Sequence) token is reached.
* **Payload:** None.
* **Worker Action:** Signals the Master Node to unlock the cluster for the next prompt.