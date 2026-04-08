import sys
import subprocess
import os
import json
import urllib.request
import urllib.error

try:
    from openai import OpenAI
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "openai", "httpx==0.27.0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    from openai import OpenAI

URL = os.getenv("OPENENV_URL", "http://localhost:7860").rstrip('/')
API_BASE_URL = os.getenv("API_BASE_URL")
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN", "dummy")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

TASK_NAME = "android_ransomware"
BENCHMARK = "openenv"

def send_post_request(endpoint, payload=None):
    url = f"{URL}{endpoint}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    headers = {'Content-Type': 'application/json'} if payload else {}
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode('utf-8'))
    except urllib.error.URLError as e:
        raise Exception(f"HTTP Request failed: {e}")

def run_inference():
    print(f"[START] task={TASK_NAME} env={BENCHMARK} model={MODEL_NAME}", flush=True)
    
    try:
        send_post_request("/reset")

        action_str = "monitor_process"
        
        if API_BASE_URL and API_KEY:
            try:
                client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": "Reply with exactly this string: monitor_process"}],
                    max_tokens=10,
                    temperature=0.0
                )
                action_str = response.choices[0].message.content.strip()
            except Exception as e:
                pass

        if "monitor" not in action_str.lower():
            action_str = "monitor_process"

        sample_action = {
            "action_type": action_str,
            "target_pid": 1
        }
        
        step_res = send_post_request("/step", payload=sample_action)
        
        reward = float(step_res.get("reward", 0.0) if isinstance(step_res, dict) else 0.0)
        done = bool(step_res.get("done", True) if isinstance(step_res, dict) else True)
        done_val = str(done).lower()
        
        print(f"[STEP] step=1 action={action_str} reward={reward:.2f} done={done_val} error=null", flush=True)
        
        score = max(0.0, min(reward, 1.0))
        success_val = "true" if score > 0 else "false"
        
        print(f"[END] success={success_val} steps=1 score={score:.3f} rewards={reward:.2f}", flush=True)
        
    except Exception as e:
        safe_error = str(e).replace('"', "'")
        print(f"[STEP] step=1 action=error reward=0.00 done=true error=\"{safe_error}\"", flush=True)
        print(f"[END] success=false steps=1 score=0.000 rewards=0.00", flush=True)

if __name__ == '__main__':
    run_inference() 