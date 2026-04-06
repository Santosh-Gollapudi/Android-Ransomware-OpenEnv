try:
    from openenv.core.env_server.http_server import create_app
except Exception as e:
    raise ImportError("openenv-core is required.") from e

from models import Action, Observation
from server.ransomware_env_environment import RansomwareEnvironment

app = create_app(
    RansomwareEnvironment,
    Action,        
    Observation,   
    env_name="ransomware_env",
    max_concurrent_envs=1, 
)

def main():
    import uvicorn
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument(--port, type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)

if __name__ == '__main__':
    main()