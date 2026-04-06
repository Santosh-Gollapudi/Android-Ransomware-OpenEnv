"""
schemas.py — Pydantic type definitions for the Android Ransomware Detection OpenEnv.

This module defines the full observation and action spaces consumed by AI agents.
All fields are strictly typed so that an LLM agent can introspect the schema and
understand exactly what it is seeing and what it is allowed to do.

Observation Space
-----------------
The agent receives a rich snapshot of a simulated Android device at each time step:
  • A list of running processes with CPU/memory stats and recent API call logs.
  • A list of user files with Shannon-entropy scores (high entropy → likely encrypted).
  • System-level alerts and counters that summarise overall device health.

Action Space
------------
Four discrete action types mirror realistic Android security tooling:
  • monitor_process  — attach deeper telemetry to a PID (raises suspicion flag).
  • kill_process     — terminate a process by PID (may be benign or malicious).
  • quarantine_file  — move a file to an isolated sandbox directory.
  • alert_user       — surface an in-app security notification.

Each step, exactly ONE action is taken. Multi-action batching is not supported in v1.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    """
    Discrete set of actions an agent may take each time step.

    Using str-based Enum ensures JSON serialisation works without custom encoders
    and allows LLMs to emit the action name as a plain string.
    """
    MONITOR_PROCESS  = "monitor_process"   # gather extra telemetry on a PID
    KILL_PROCESS     = "kill_process"       # terminate a process by PID
    QUARANTINE_FILE  = "quarantine_file"    # isolate a file from the filesystem
    ALERT_USER       = "alert_user"         # trigger a user-visible security alert


class ProcessStatus(str, Enum):
    """
    Lifecycle status of a simulated process.
    Processes transition:  RUNNING → MONITORED (optional) → KILLED
    """
    RUNNING    = "running"
    MONITORED  = "monitored"   # agent has called monitor_process on this PID
    KILLED     = "killed"


class FileStatus(str, Enum):
    """
    Tracks whether a user file is intact, encrypted by ransomware, or quarantined.
    """
    INTACT       = "intact"
    ENCRYPTED    = "encrypted"   # ransomware has processed this file
    QUARANTINED  = "quarantined" # agent has moved file to sandbox


# ---------------------------------------------------------------------------
# Observation sub-models
# ---------------------------------------------------------------------------

class APICallRecord(BaseModel):
    """
    Represents a single Android API call captured by the simulated system logger.

    Ransomware typically chains suspicious calls like:
        getExternalStorageDirectory → openFileDescriptor → Cipher.doFinal
    Benign apps show more varied, lower-risk call patterns.
    """
    api_name    : str  = Field(..., description="Fully-qualified Android API method name.")
    call_count  : int  = Field(..., ge=0, description="Number of times called this step.")
    risk_score  : float = Field(
        ...,
        ge=0.0, le=1.0,
        description=(
            "Heuristic danger rating for this API (0.0 = safe, 1.0 = highly suspicious). "
            "Crypto and storage-write APIs score 0.8–1.0."
        ),
    )


class ProcessInfo(BaseModel):
    """
    Snapshot of one simulated Android process for a single environment time step.

    The ransomware process is intentionally given a plausible-looking package name
    (e.g., 'com.media.gallery.pro') to make blind trust of names dangerous.
    Agents must correlate CPU spikes, memory growth, and API call patterns.
    """
    pid          : int            = Field(..., ge=1,   description="Simulated Linux PID.")
    package_name : str            = Field(...,          description="Android package or process name.")
    cpu_usage    : float          = Field(..., ge=0.0, le=100.0, description="CPU % averaged over step.")
    memory_mb    : float          = Field(..., ge=0.0,  description="RSS memory usage in megabytes.")
    status       : ProcessStatus  = Field(ProcessStatus.RUNNING, description="Current lifecycle status.")
    is_system    : bool           = Field(
        ...,
        description=(
            "True if this is a protected Android system process (e.g., zygote, surfaceflinger). "
            "Killing system processes incurs a heavy collateral-damage penalty."
        ),
    )
    is_flagged   : bool           = Field(
        False,
        description="True once the agent has called monitor_process on this PID.",
    )
    api_calls    : List[APICallRecord] = Field(
        default_factory=list,
        description="API calls attributed to this process during the current step.",
    )
    suspicion_score : float = Field(
        0.0,
        ge=0.0, le=1.0,
        description=(
            "Environment-computed aggregate suspicion (0.0 = clean, 1.0 = certainly malicious). "
            "This is NOT directly visible to the agent — it is used internally by graders. "
            "Agents must infer suspicion from cpu_usage, memory_mb, and api_calls."
        ),
    )

    class Config:
        # Expose the field in serialised output but mark it as internal-only
        # in documentation; agent prompts should note this field is grader-only.
        json_schema_extra = {
            "x-agent-hidden": ["suspicion_score"],
        }


class FileInfo(BaseModel):
    """
    Represents one user-space file on the simulated /sdcard/ filesystem.

    Shannon entropy is the primary detection signal:
        • Normal text/image files:   entropy ≈ 3.0 – 5.5 bits/byte
        • AES-256 ciphertext:        entropy ≈ 7.9 – 8.0 bits/byte  ← ransomware indicator
    """
    path          : str        = Field(..., description="Absolute simulated path on the Android device.")
    extension     : str        = Field(..., description="File extension, e.g. '.jpg', '.pdf', '.mp4'.")
    size_bytes    : int        = Field(..., ge=0,  description="File size in bytes.")
    entropy_score : float      = Field(
        ...,
        ge=0.0, le=8.0,
        description=(
            "Shannon entropy of file contents (bits/byte). Values above 7.5 strongly "
            "suggest AES encryption by ransomware."
        ),
    )
    status        : FileStatus = Field(FileStatus.INTACT, description="Current file status.")
    last_modified : int        = Field(
        ...,
        description="Simulated Unix timestamp of last modification (seconds since epoch).",
    )


# ---------------------------------------------------------------------------
# Top-level Observation model (returned by reset / step / state)
# ---------------------------------------------------------------------------

class Observation(BaseModel):
    """
    Full device snapshot delivered to the agent at each time step.

    Agents should track changes across steps:
        • Rapid growth in encrypted_file_count signals active ransomware.
        • A process whose memory_mb climbs alongside rising entropy in /sdcard/
          is the primary suspect.
        • API call chains involving Cipher, FileOutputStream, and
          getExternalStorageDirectory are near-certain ransomware signatures.
    """
    step_number         : int             = Field(..., ge=0,  description="Current environment time step (0-indexed).")
    max_steps           : int             = Field(...,         description="Episode length before forced termination.")
    timestamp_sim       : int             = Field(...,         description="Simulated Unix timestamp at step start.")

    # ---- Process table ----
    processes           : List[ProcessInfo] = Field(
        ...,
        description="All currently running (or recently killed) processes on the device.",
    )

    # ---- Filesystem ----
    filesystem          : List[FileInfo]  = Field(
        ...,
        description="User files on /sdcard/ — the ransomware's target.",
    )

    # ---- Summary counters ----
    total_user_files    : int   = Field(..., ge=0, description="Total number of user files in the episode.")
    encrypted_file_count: int   = Field(..., ge=0, description="Files that have been encrypted so far.")
    quarantined_file_count: int = Field(..., ge=0, description="Files the agent has quarantined.")
    safe_file_count     : int   = Field(
        ..., ge=0,
        description="Files that are still INTACT (neither encrypted nor quarantined but still accessible).",
    )

    # ---- Alerts ----
    system_alerts       : List[str] = Field(
        default_factory=list,
        description=(
            "System-generated alert strings (e.g., 'High entropy write detected on /sdcard/DCIM/'). "
            "These are noisy signals — not all alerts correspond to the ransomware."
        ),
    )
    agent_alerted       : bool = Field(
        False,
        description="True if the agent has successfully called alert_user this episode.",
    )

    # ---- Episode terminal signal ----
    done                : bool  = Field(False, description="True when the episode has ended.")
    reward              : float = Field(0.0,   description="Reward earned on the PREVIOUS step.")


# ---------------------------------------------------------------------------
# Action model
# ---------------------------------------------------------------------------

class Action(BaseModel):
    """
    A single action submitted by the agent to the environment's step() endpoint.

    Exactly one of (target_pid, target_file) must be populated depending on
    the action_type:

        monitor_process  → target_pid required
        kill_process     → target_pid required
        quarantine_file  → target_file required
        alert_user       → message required; target_pid and target_file ignored
    """
    action_type  : ActionType      = Field(..., description="Which action to perform.")
    target_pid   : Optional[int]   = Field(None, ge=1, description="PID of the target process.")
    target_file  : Optional[str]   = Field(None, description="Absolute path of the file to quarantine.")
    message      : Optional[str]   = Field(
        None,
        max_length=512,
        description="Human-readable alert message shown to the simulated user.",
    )

    @field_validator("target_pid")
    @classmethod
    def _pid_required_for_process_actions(cls, v: Optional[int], info) -> Optional[int]:
        """Ensure process-targeting actions carry a PID."""
        action = info.data.get("action_type")
        if action in (ActionType.MONITOR_PROCESS, ActionType.KILL_PROCESS) and v is None:
            raise ValueError(f"action_type='{action}' requires target_pid to be set.")
        return v

    @field_validator("target_file")
    @classmethod
    def _file_required_for_quarantine(cls, v: Optional[str], info) -> Optional[str]:
        """Ensure quarantine actions carry a file path."""
        action = info.data.get("action_type")
        if action == ActionType.QUARANTINE_FILE and v is None:
            raise ValueError("action_type='quarantine_file' requires target_file to be set.")
        return v


# ---------------------------------------------------------------------------
# Step result wrapper
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    """
    Returned by env.step(action). Bundles the new observation with bookkeeping.
    """
    observation  : Observation = Field(..., description="New device state after the action.")
    reward       : float       = Field(..., description="Scalar reward for this transition.")
    done         : bool        = Field(..., description="Whether the episode is finished.")
    info         : dict        = Field(
        default_factory=dict,
        description=(
            "Diagnostic metadata (e.g., ransomware_alive, files_encrypted_this_step). "
            "Not used for training but useful for debugging and grader computation."
        ),
    )


# ---------------------------------------------------------------------------
# Grader result schema
# ---------------------------------------------------------------------------

class GraderResult(BaseModel):
    """
    Standardised output for each of the three automated graders.
    All scores are normalised floats in [0.0, 1.0] per OpenEnv spec.
    """
    task_id      : str   = Field(..., description="Unique grader identifier, e.g. 'swift_identification'.")
    score        : float = Field(..., ge=0.0, le=1.0, description="Agent score for this task.")
    max_score    : float = Field(1.0, description="Always 1.0 — scores are pre-normalised.")
    description  : str   = Field(..., description="Human-readable explanation of the score.")
    details      : dict  = Field(default_factory=dict, description="Raw metrics used to compute the score.")
