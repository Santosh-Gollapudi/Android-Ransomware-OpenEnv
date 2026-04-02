# Android Ransomware Detection & Mitigation (OpenEnv)

A complex, real-world OpenEnv simulation built for the Meta x PyTorch Hackathon. 

This environment simulates an Android device under active attack by a lightweight ransomware process. The AI agent assumes the role of an automated security daemon and must use process telemetry and filesystem entropy to neutralize the threat before user data is lost.

# The Challenge
The agent must monitor running processes, identify the malicious payload (disguised as `com.media.gallery.pro`), and kill it. It must also avoid killing vital Android system processes (like `surfaceflinger` or `system_server`) and can optionally quarantine files to protect them.

# Automated Graders (Tasks)
This environment strictly implements 3 OpenEnv automated graders returning values between 0.0 and 1.0:
1. **Swift Identification (`swift_identification`)**: Scores the agent based on how few steps it takes to flag or kill the ransomware PID. Linear decay penalty for slowness.
2. **Minimal Collateral Damage (`minimal_collateral`)**: Penalizes the agent heavily for killing benign system processes, and moderately for killing benign user apps.
3. **Prevention (`prevention`)**: Evaluates the percentage of the simulated `/sdcard/` filesystem that remains intact and unencrypted at the end of the episode.

# Technical Implementation
* **Framework:** OpenEnv Core (`openenv-core`)
* **Schemas:** Fully typed Observation and Action spaces using `Pydantic`, ensuring LLMs understand the exact data structures (e.g., CPU %, RAM, Shannon entropy scores).
* **State Machine:** Robust step-by-step state progression simulating an AES-256 encryption attack over time.