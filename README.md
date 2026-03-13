# AIE1902_Midterm_Project
Midterm project for AIE1902

# Autonomous Target Search and Patrol Robot 🤖

This repository contains the source code for the AIE1902 Midterm Project (Topic 3: Target Search and Patrol Task). 

Our system features an autonomous TurtleBot3 that navigates through a multi-region environment, detects high-priority targets (green cubes) using computer vision, and integrates a **Vision-Language Model (Qwen-VL)** to generate semantic site survey reports for each room.

## ✨ Key Features
* **Robust Autonomous Navigation**: Utilizes ROS `move_base` and DWA local planner for collision-free routing across 4 distinct regions.
* **Vision Perception**: Real-time HSV color segmentation and contour detection to accurately pinpoint target coordinates.
* **LLM Integration (Embodied AI)**: Seamlessly pauses at each region to capture panoramic snapshots, calling Aliyun's Qwen-VL API to generate structured, human-readable environmental reports.
* **State Machine Control**: Highly reliable task flow (Navigate $\rightarrow$ Snapshot & AI Analysis $\rightarrow$ 360° Search $\rightarrow$ Log $\rightarrow$ Return Home).

## 🛠️ Prerequisites
Before running the code, ensure you have the following installed:
* ROS Noetic & TurtleBot3 Simulation Packages
* Python 3.x
* OpenCV (`cv2`) & `cv_bridge`
* Aliyun DashScope SDK (for Qwen-VL integration):
  ```bash
  pip install dashscope
