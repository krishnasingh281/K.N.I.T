import socketio
import torch

# Create a standard Socket.IO client
sio = socketio.Client()

MASTER_NODE_URL = 'http://localhost:3000'

def get_hardware_specs():
    """Detects actual GPU hardware and VRAM using PyTorch."""
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        total_memory_bytes = torch.cuda.get_device_properties(0).total_memory
        vram_gb = round(total_memory_bytes / (1024**3))
        return {"gpu": gpu_name, "vram": f"{vram_gb}GB"}
    else:
        return {"gpu": "CPU Only (No CUDA detected)", "vram": "0GB"}

def heartbeat_loop():
    """Runs natively inside Socket.IO's event loop to prevent thread crashing."""
    while True:
        sio.emit('heartbeat')
        # Print a pulse so you can physically see it running in the terminal
        print("💓", end="", flush=True) 
        sio.sleep(0.5) # MUST use sio.sleep, not time.sleep!

@sio.event
def connect():
    print("\n✅ Connected to Master Node!")
    
    hw_specs = get_hardware_specs()
    print(f"🖥️  Registering hardware: {hw_specs}")
    sio.emit('register', hw_specs)
    
    # Start the heartbeat pulse safely using native Socket.io methods
    sio.start_background_task(heartbeat_loop)

@sio.on('pipeline_rebuilt')
def on_pipeline_rebuilt(assignments):
    my_id = sio.get_sid()
    if my_id in assignments:
        print(f"\n🎯 My Layer Assignment: {assignments[my_id]}")

@sio.on('start_inference')
def on_start_inference(payload):
    prompt = payload.get('prompt', '')
    print(f"\n🚀 Received prompt from Master: '{prompt}'")
    
    # Simulate thinking...
    sio.sleep(1)
    
    # --- Simulated Streaming ---
    words = ["This", "is", "a", "test", "from", "the", "real", "Python", "worker."]
    for word in words:
        sio.emit('stream_token', {'token': word + " "})
        sio.sleep(0.1) # Thread-safe sleep
        
    sio.emit('inference_complete')
    print("\n✅ Generation complete. Awaiting next prompt.")

@sio.event
def disconnect():
    print("\n❌ Disconnected from Master Node.")

if __name__ == '__main__':
    try:
        print(f"Connecting to {MASTER_NODE_URL}...")
        sio.connect(MASTER_NODE_URL)
        # Block the main thread so the script doesn't exit
        sio.wait()
    except Exception as e:
        print(f"Connection failed: {e}")