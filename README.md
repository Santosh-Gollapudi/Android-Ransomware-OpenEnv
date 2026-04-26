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

## Results
<img width="1919" height="1079" alt="Screenshot 2026-04-26 091830" src="https://github.com/user-attachments/assets/91df9731-b39e-40a0-98db-d854318f6696" />

## Tech Stack
* **Framework:** OpenEnv Core
* **Schemas:** Pydantic Action/Observation spaces.

force rebuild
