from dataclasses import dataclass, field
from typing import List
from openenv.core.env_server.types import Action, Observation, State


@dataclass
class AndroidAction(Action):
    action_type: str
    target_file_or_process: str


@dataclass
class AndroidObservation(Observation):
    cpu_usage_percent: float
    unauthorized_encryption_flags: int
    suspicious_system_calls: List[str] = field(default_factory=list)
    is_device_compromised: bool = False
    system_log: str = ""


@dataclass
class AndroidState(State):
    episode_id: str
    step_count: int
    total_reward: float = 0.0