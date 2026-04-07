import os
import urllib.request
import urllib.error
import json

URL = os.getenv("OPENENV_URL", "http://localhost:7860").rstrip('/')

def send_post_request(endpoint, payload=None):
    url = f"{URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    headers = {'Content-Type': 'application/json'} if payload else {}
    
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print(f"Request failed: {e}")
        raise

def run_inference():
    print(f"Connecting to environment at {URL}...")
    try:
        print("Sending /reset...")
        reset_res = send_post_request("/reset")
        print("Reset successful!")

        sample_action = {
            "action_type": "monitor_process",
            "target_pid": 1
        }
        
        print("Sending /step...")
        step_res = send_post_request("/step", payload=sample_action)
        
        reward = step_res.get("reward") if isinstance(step_res, dict) else "No reward data"
        print("Step successful! Reward earned:", reward)
        
    except Exception as e:
        print(f"Inference script stopped gracefully: {e}")

if __name__ == '__main__':
    run_inference()
