import math
import random
import time
from typing import Any, Dict, List, Optional

from openenv.core.env_server.interfaces import Environment

try:
    from ..models import (
        Action, ActionType, APICallRecord, FileInfo, FileStatus,
        GraderResult, Observation, ProcessInfo, ProcessStatus, StepResult
    )
except ImportError:
    from models import (
        Action, ActionType, APICallRecord, FileInfo, FileStatus,
        GraderResult, Observation, ProcessInfo, ProcessStatus, StepResult
    )

MAX_STEPS             : int   = 20
FILES_ENCRYPTED_PER_STEP: int = 3
RANSOMWARE_PID        : int   = 3847
SIM_EPOCH_START       : int   = 1_700_000_000
SIM_STEP_SECONDS      : int   = 10

REWARD_CORRECT_KILL   : float =  5.0
REWARD_BENIGN_KILL    : float = -3.0
REWARD_QUARANTINE_HIT : float =  2.0
REWARD_MONITOR_RIGHT  : float =  1.0
REWARD_ALERT_ISSUED   : float =  1.5
REWARD_FILE_ENCRYPTED : float = -1.0
REWARD_STEP_SURVIVAL  : float =  0.1

_BENIGN_SYSTEM_PROCESSES: List[Dict[str, Any]] = [
    {"pid": 1,    "package_name": "init",                          "cpu": 0.1,  "mem": 12.0,  "is_system": True},
    {"pid": 400,  "package_name": "zygote64",                      "cpu": 0.3,  "mem": 55.0,  "is_system": True},
    {"pid": 415,  "package_name": "system_server",                 "cpu": 3.5,  "mem": 210.0, "is_system": True},
]

_BENIGN_USER_PROCESSES: List[Dict[str, Any]] = [
    {"pid": 1200, "package_name": "com.whatsapp",                  "cpu": 1.4,  "mem": 95.0,  "is_system": False},
    {"pid": 1480, "package_name": "com.android.chrome",            "cpu": 5.2,  "mem": 280.0, "is_system": False},
]

_RANSOMWARE_PROCESS: Dict[str, Any] = {
    "pid":          RANSOMWARE_PID,
    "package_name": "com.media.gallery.pro",
    "cpu":          18.7,
    "mem":          47.0,
    "is_system":    False,
}

_RANSOMWARE_API_CALLS: List[Dict[str, Any]] = [
    {"api_name": "android.os.Environment.getExternalStorageDirectory", "call_count": 1,  "risk_score": 0.6},
    {"api_name": "javax.crypto.Cipher.doFinal",                          "call_count": 24, "risk_score": 1.0},
]

_BENIGN_API_CALLS: List[Dict[str, Any]] = [
    {"api_name": "android.app.Activity.onCreate",       "call_count": 1, "risk_score": 0.0},
]

_USER_FILES: List[Dict[str, Any]] = [
    {"path": "/sdcard/DCIM/IMG_0001.jpg",  "ext": ".jpg",  "size": 3_200_000, "entropy": 4.2},
    {"path": "/sdcard/Documents/resume.pdf",        "ext": ".pdf",  "size": 80_000,  "entropy": 3.5},
    {"path": "/sdcard/Download/setup.apk",          "ext": ".apk",  "size": 8_000_000,"entropy": 5.1},
    {"path": "/sdcard/WhatsApp/Backups/msgstore.db.crypt14", "ext": ".crypt14", "size": 25_000_000, "entropy": 7.1},
]

def _build_process(data: Dict[str, Any], step: int, is_ransomware: bool = False) -> ProcessInfo:
    if is_ransomware:
        cpu = min(data["cpu"] + step * 2.5, 95.0)
        mem = data["mem"] + step * 5.0
        calls = [APICallRecord(**c) for c in _RANSOMWARE_API_CALLS]
        suspicion = min(0.5 + step * 0.05, 1.0)
    else:
        cpu = max(0.0, data["cpu"] + random.uniform(-0.5, 0.5))
        mem = max(0.0, data["mem"] + random.uniform(-2.0, 2.0))
        calls = [APICallRecord(**c) for c in _BENIGN_API_CALLS]
        suspicion = 0.0
    return ProcessInfo(
        pid=data["pid"], package_name=data["package_name"], cpu_usage=round(cpu, 2),
        memory_mb=round(mem, 2), status=ProcessStatus.RUNNING, is_system=data["is_system"],
        is_flagged=False, api_calls=calls, suspicion_score=suspicion,
    )

def _build_file(data: Dict[str, Any], step_modified: int) -> FileInfo:
    return FileInfo(
        path=data["path"], extension=data["ext"], size_bytes=data["size"],
        entropy_score=data["entropy"], status=FileStatus.INTACT,
        last_modified=SIM_EPOCH_START + step_modified * SIM_STEP_SECONDS,
    )

class RansomwareEnvironment(Environment):
    def __init__(self, seed: Optional[int] = None) -> None:
        self._rng = random.Random(seed)
        self._step = 0
        self._processes = []
        self._files = []
        self._done = False
        self._ransomware_alive = True
        self._killed_pids = set()
        self._benign_killed_pids = set()
        self._quarantined_files = set()
        self._agent_alerted = False
        self._malicious_detected_step = None
        self._cumulative_reward = 0.0
        self._system_alerts = []

    def reset(self) -> Observation:
        self._step = 0
        self._done = False
        self._ransomware_alive = True
        self._killed_pids = set()
        self._benign_killed_pids = set()
        self._quarantined_files = set()
        self._agent_alerted = False
        self._malicious_detected_step = None
        self._cumulative_reward = 0.0
        self._processes = [_build_process(p, step=0, is_ransomware=False) for p in _BENIGN_SYSTEM_PROCESSES]
        self._processes += [_build_process(p, step=0, is_ransomware=False) for p in _BENIGN_USER_PROCESSES]
        self._processes.append(_build_process(_RANSOMWARE_PROCESS, step=0, is_ransomware=True))
        self._files = [_build_file(f, step_modified=0) for f in _USER_FILES]
        self._system_alerts = ["PackageManager: com.media.gallery.pro requested WRITE_EXTERNAL_STORAGE"]
        return self._build_observation(reward=0.0)

    def step(self, action: Action) -> StepResult:
        if self._done:
            raise RuntimeError("Episode is over. Call reset() to start a new episode.")
        action_info = self._apply_action(action)
        files_encrypted_this_step = self._advance_ransomware()
        self._emit_system_alerts(files_encrypted_this_step)
        reward = self._compute_reward(action_info, files_encrypted_this_step)
        self._cumulative_reward += reward
        self._step += 1
        self._check_done()
        obs = self._build_observation(reward=reward)
        return StepResult(
            observation=obs, reward=reward, done=self._done,
            info={**action_info, "files_encrypted_this_step": files_encrypted_this_step, "ransomware_alive": self._ransomware_alive}
        )

    def state(self) -> Observation:
        return self._build_observation(reward=0.0)

    def _apply_action(self, action: Action) -> Dict[str, Any]:
        info = {"action_type": action.action_type.value, "action_valid": True, "action_detail": ""}
        if action.action_type == ActionType.MONITOR_PROCESS:
            pid = action.target_pid
            process = self._find_process(pid)
            if process is None:
                info["action_valid"] = False
                return info
            process.status = ProcessStatus.MONITORED
            process.is_flagged = True
            if pid == RANSOMWARE_PID and self._malicious_detected_step is None:
                self._malicious_detected_step = self._step
        elif action.action_type == ActionType.KILL_PROCESS:
            pid = action.target_pid
            process = self._find_process(pid)
            if process is None or process.status == ProcessStatus.KILLED:
                info["action_valid"] = False
                return info
            process.status = ProcessStatus.KILLED
            self._killed_pids.add(pid)
            if pid == RANSOMWARE_PID:
                self._ransomware_alive = False
                if self._malicious_detected_step is None:
                    self._malicious_detected_step = self._step
            else:
                self._benign_killed_pids.add(pid)
        elif action.action_type == ActionType.QUARANTINE_FILE:
            path = action.target_file
            file = self._find_file(path)
            if file is None or file.status == FileStatus.QUARANTINED:
                info["action_valid"] = False
                return info
            file.status = FileStatus.QUARANTINED
            self._quarantined_files.add(path)
        elif action.action_type == ActionType.ALERT_USER:
            self._agent_alerted = True
        return info

    def _advance_ransomware(self) -> int:
        if not self._ransomware_alive: return 0
        intact_files = [f for f in self._files if f.status == FileStatus.INTACT]
        n_encrypt = min(FILES_ENCRYPTED_PER_STEP, len(intact_files))
        for f in intact_files[:n_encrypt]:
            f.entropy_score = round(self._rng.uniform(7.85, 7.99), 3)
            f.status = FileStatus.ENCRYPTED
        return n_encrypt

    def _emit_system_alerts(self, files_encrypted: int) -> None:
        self._system_alerts = []
        if self._ransomware_alive and files_encrypted > 0:
            self._system_alerts.append(f"High-entropy writes detected by PID {RANSOMWARE_PID}")

    def _compute_reward(self, action_info: Dict[str, Any], files_encrypted: int) -> float:
        r = 0.0
        if action_info["action_valid"]:
            if action_info["action_type"] == ActionType.KILL_PROCESS.value:
                r += REWARD_CORRECT_KILL if not self._ransomware_alive else REWARD_BENIGN_KILL
        r += REWARD_FILE_ENCRYPTED * files_encrypted
        return round(r, 4)

    def _check_done(self) -> None:
        if sum(1 for f in self._files if f.status == FileStatus.INTACT) == 0 or self._step >= MAX_STEPS:
            self._done = True

    def _build_observation(self, reward: float) -> Observation:
        return Observation(
            step_number=self._step, max_steps=MAX_STEPS,
            timestamp_sim=SIM_EPOCH_START + self._step * SIM_STEP_SECONDS,
            processes=[p for p in self._processes if p.status != ProcessStatus.KILLED],
            filesystem=self._files, total_user_files=len(self._files),
            encrypted_file_count=sum(1 for f in self._files if f.status == FileStatus.ENCRYPTED),
            quarantined_file_count=sum(1 for f in self._files if f.status == FileStatus.QUARANTINED),
            safe_file_count=sum(1 for f in self._files if f.status == FileStatus.INTACT),
            system_alerts=list(self._system_alerts), agent_alerted=self._agent_alerted, done=self._done, reward=reward
        )

    def _find_process(self, pid: Optional[int]) -> Optional[ProcessInfo]:
        return next((p for p in self._processes if p.pid == pid), None)

    def _find_file(self, path: Optional[str]) -> Optional[FileInfo]:
        return next((f for f in self._files if f.path == path), None)