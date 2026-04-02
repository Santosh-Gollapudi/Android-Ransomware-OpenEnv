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

def main(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    main(port=args.port)