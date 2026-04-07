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
        print(f"Request failed: {e}", flush=True)
        raise

def run_inference():
    task_name = "ransomware_env_test"
    
    print(f"[START] task={task_name}", flush=True)
    
    try:
        send_post_request("/reset")

        sample_action = {
            "action_type": "monitor_process",
            "target_pid": 1
        }
        
        step_res = send_post_request("/step", payload=sample_action)
        
        reward = step_res.get("reward", 0.0) if isinstance(step_res, dict) else 0.0
        
        print(f"[STEP] step=1 reward={reward}", flush=True)
        
        print(f"[END] task={task_name} score={reward} steps=1", flush=True)
        
    except Exception as e:
        print(f"Inference script stopped gracefully: {e}", flush=True)
        print(f"[END] task={task_name} score=0.0 steps=0", flush=True)

if __name__ == '__main__':
    run_inference()
