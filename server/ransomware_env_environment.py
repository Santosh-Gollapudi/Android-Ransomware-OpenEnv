import uuid
from openenv.core.env_server import Environment
from openenv.core.client_types import StepResult
from models import AndroidAction, AndroidObservation, AndroidState

class AndroidRansomwareEnvironment(Environment[AndroidAction, AndroidObservation, AndroidState]):
    def __init__(self):
        super().__init__()
        self.episode_id = ""
        self.step_count = 0
        self.total_reward = 0.0
        self.is_compromised = False

    async def reset(self) -> AndroidObservation:
        self.episode_id = str(uuid.uuid4())
        self.step_count = 0
        self.total_reward = 0.0
        self.is_compromised = False
        
        return AndroidObservation(
            cpu_usage_percent=12.5,
            unauthorized_encryption_flags=0,
            suspicious_system_calls=[],
            is_device_compromised=False,
            system_log="Device environment reset. Baseline normal."
        )

    async def step(self, action: AndroidAction) -> StepResult[AndroidObservation]:
        self.step_count += 1
        reward = 0.0
        done = False
        
        cpu_usage = 15.0
        encryption_flags = 0
        suspicious_calls = []
        log = f"Executed {action.action_type} on {action.target_file_or_process}."

        if action.action_type == "EXECUTE_APK" and "malware" in action.target_file_or_process.lower():
            cpu_usage = 98.5
            encryption_flags = 12
            suspicious_calls = ["crypto.Cipher.getInstance", "java.io.File.renameTo"]
            self.is_compromised = True
            log += " THREAT: Rapid encryption and CPU spike detected."
            
        elif action.action_type == "BLOCK_PROCESS":
            if self.is_compromised:
                reward = 1.0
                log += " SUCCESS: Malicious process blocked successfully."
            else:
                reward = -1.0
                log += " ERROR: Blocked benign process."
            done = True
            
        if self.step_count >= 10:
            done = True

        self.total_reward += reward

        observation = AndroidObservation(
            cpu_usage_percent=cpu_usage,
            unauthorized_encryption_flags=encryption_flags,
            suspicious_system_calls=suspicious_calls,
            is_device_compromised=self.is_compromised,
            system_log=log
        )

        return StepResult(
            observation=observation,
            reward=reward,
            done=done
        )

    async def state(self) -> AndroidState:
        return AndroidState(
            episode_id=self.episode_id,
            step_count=self.step_count,
            total_reward=self.total_reward
        )