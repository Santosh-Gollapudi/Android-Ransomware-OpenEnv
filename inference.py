import os
import requests

URL = os.getenv("OPENENV_URL", "http://localhost:7860")

def run_inference():
    print(f"Connecting to environment at {URL}...")
    try:
        print("Sending /reset...")
        reset_res = requests.post(f"{URL}/reset")
        reset_res.raise_for_status()
        print("Reset successful!")

        sample_action = {
            "action_type": "monitor_process",
            "target_pid": 1
        }
        
        print("Sending /step...")
        step_res = requests.post(f"{URL}/step", json=sample_action)
        step_res.raise_for_status()
        print("Step successful! Reward earned:", step_res.json().get("reward"))
        
    except Exception as e:
        print(f"Inference script stopped: {e}")

if __name__ == "__main__":
    run_inference()