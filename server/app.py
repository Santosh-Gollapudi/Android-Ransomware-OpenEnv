from server.android_ransomware_env_environment import AndroidRansomwareEnvironment
from models import AndroidAction, AndroidObservation
from openenv.core.env_server import create_web_interface_app

app = create_web_interface_app(
    AndroidRansomwareEnvironment,
    AndroidAction,
    AndroidObservation
)