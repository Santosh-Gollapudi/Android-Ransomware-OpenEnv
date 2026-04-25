---
title: Android Ransomware OpenEnv
emoji: 🛡️
colorFrom: red
colorTo: green
sdk: docker
pinned: false
app_port: 7860
---

# Android Ransomware Detection (OpenEnv)

A real-world OpenEnv simulation for the Meta x PyTorch Hackathon. Simulates an Android device under active attack by a lightweight ransomware process. 

## The Challenge
The agent must monitor running processes, identify the malicious payload (`com.media.gallery.pro`), and kill it without harming vital Android system processes (`surfaceflinger`, `system_server`).

## Graders
1. **Swift Identification**: Scores how quickly the agent flags/kills the ransomware PID.
2. **Minimal Collateral Damage**: Penalizes killing benign system/user processes.
3. **Prevention**: Evaluates the percentage of the `/sdcard/` filesystem saved from AES-256 encryption.

## Tech Stack
* **Framework:** OpenEnv Core
* **Schemas:** Pydantic Action/Observation spaces.

force rebuild