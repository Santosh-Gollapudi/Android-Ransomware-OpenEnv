import os
import sys

sys.path.append(os.path.abspath("."))

from models import AndroidAction, AndroidObservation
from server.android_ransomware_env_environment import AndroidRansomwareEnvironment
from openenv.core.env_server import create_web_interface_app

env = AndroidRansomwareEnvironment()
app = create_web_interface_app(env, AndroidAction, AndroidObservation)