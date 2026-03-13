#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
patrol_brain_new.py - 智能巡逻大脑（修复终极版）
功能：
1. 巡逻多个区域
2. 检测目标并进行 AI 分析
3. 记录目标位置和描述
4. 生成巡逻报告
"""

import rospy
import cv2
import os
import dashscope
from std_msgs.msg import Bool
from geometry_msgs.msg import Twist, PoseWithCovarianceStamped
from nav_manager import NavigationManager
from cv_bridge import CvBridge
from sensor_msgs.msg import Image

# ============================================================
# AI 配置
# ============================================================
dashscope_api_key = "YOUR_API_KEY_HERE" # When running the code, replace it with the real APi key.
class PatrolBrainNew:
    def __init__(self):
        """初始化巡逻大脑节点"""
        rospy.init_node('patrol_brain_new')
        self.nav = NavigationManager()
        
        # 安全的空地巡逻坐标点
        self.points = [
            (-1.0, 1.0, 2.35),   # 房间 A 
            (1.0, 1.0, 0.78),    # 房间 B 
            (-1.0, -1.0, -2.35), # 房间 C 
            (1.0, -1.0, -0.78),  # 房间 D 
            (0.0, 0.0, 0.0)      # 回到中心原点
        ]
        
        self.targets_found = []
        self.is_target_present = False
        self.current_robot_x = 0.0
        self.current_robot_y = 0.0
        
        self.latest_frame = None
        self.bridge = CvBridge()
        
        # 订阅话题
        rospy.Subscriber("/target_detected", Bool, self.vision_cb)
        rospy.Subscriber("/amcl_pose", PoseWithCovarianceStamped, self.pose_cb)
        rospy.Subscriber("/camera/rgb/image_raw", Image, self.image_callback)
        
        # 速度控制发布者
        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=1)
        
        rospy.loginfo("=== Patrol Brain New Initialized ===")
    
    def image_callback(self, msg):
        try:
            self.latest_frame = self.bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as e:
            pass
            
    def vision_cb(self, msg):
        self.is_target_present = msg.data
    
    def pose_cb(self, msg):
        self.current_robot_x = msg.pose.pose.position.x
        self.current_robot_y = msg.pose.pose.position.y
    
    def ask_qwen_vl(self, image_path, prompt_text):
        """调用通义千问大模型分析照片"""
        rospy.loginfo("Calling Qwen-VL API...")
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"image": f"file://{image_path}"},
                        {"text": prompt_text}
                    ]
                }
            ]
            dashscope.api_key = dashscope_api_key
            response = dashscope.MultiModalConversation.call(model='qwen-vl-plus', messages=messages)
            
            if response.status_code == 200:
                return response.output.choices[0].message.content[0]['text']
            else:
                rospy.logwarn(f"AI API failed with status {response.status_code}")
                return "AI Analysis Failed - Network Error"
        except Exception as e:
            rospy.logerr(f"AI Analysis error: {e}")
            return "AI Analysis Failed - Exception"
    
    def run(self):
        room_names = ["Region A", "Region B", "Region C", "Region D", "Home"]
        rospy.loginfo("=== Patrol mission start ===")
        
        for i, (px, py, pw) in enumerate(self.points):
            rospy.loginfo(f"Heading to {room_names[i]}...")
            success = self.nav.goto(px, py, pw)
            
            if success:
                # ==========================================
                # 【新增逻辑】：如果当前到达的是 Home，直接跳过拍照和扫描！
                # ==========================================
                if room_names[i] == "Home":
                    rospy.loginfo("Successfully returned to Home. Preparing final report...")
                    continue  # 这句 continue 会直接跳过后面的 AI 分析和转圈，直接结束循环！
                
                rospy.loginfo(f"Reached {room_names[i]}. Stabilizing camera for AI analysis...")
                rospy.sleep(1.5) # 稍微停顿，让摄像头画面稳定
                
                # ==========================================
                # 1. 拍全景图并呼叫大模型
                # ==========================================
                prompt = (
                    "你是一个部署在ROS环境下的智能巡逻机器人的视觉分析中枢。"
                    "这是一张机器人在巡逻到达指定房间后拍摄的照片。请根据图像内容生成一份结构化的现场勘测报告，要求如下："
                    "1. 环境描述：简练客观地描述房间内的结构与主要物体（如墙壁颜色、可见的家具如桌子、椅子、锥形桶等障碍物）。"
                    "2. 目标核查：排查画面中是否存在'绿色立方体'（高优巡逻目标）。如果存在，描述其在画面中的相对位置。"
                    "请保持工程师汇报的严谨客观语气，总字数控制在100字以内。"
                )
                image_path = "/tmp/current_scene.jpg"
                
                # 调用千问 API
                if os.path.exists(image_path):
                    description = self.ask_qwen_vl(image_path, prompt)
                else:
                    description = "No image found for analysis."
                
                rospy.loginfo(f"AI Brain says: \n{description}")
                
                # ==========================================
                # 2. 原地旋转寻找精确坐标
                # ==========================================
                rospy.loginfo("Rotating 360 degrees to scan for target coordinates...")
                found_in_this_room = False 
                
                move_cmd = Twist()
                move_cmd.angular.z = 0.5
                
                for _ in range(60): # 旋转约一圈
                    self.cmd_vel_pub.publish(move_cmd)
                    if self.is_target_present and not found_in_this_room:
                        rospy.loginfo(f"!!! TARGET DETECTED in {room_names[i]} !!!")
                        # 将坐标和 AI 描述打包存入字典，为生成最终报告做准备
                        self.targets_found.append({
                            "pos": (self.current_robot_x, self.current_robot_y),
                            "desc": description
                        })
                        found_in_this_room = True 
                    rospy.sleep(0.1)
                
                self.cmd_vel_pub.publish(Twist()) # 停止旋转
                rospy.loginfo(f"Search in {room_names[i]} completed.\n")

        # --- 巡逻结束，打印最终报告 ---
        self.print_final_report()
    
    def print_final_report(self):
        """打印最终巡逻报告（符合 Topic 3 要求格式）"""
        rospy.loginfo("================================")
        rospy.loginfo("=== Patrol Report ===")
        rospy.loginfo(f"Number of targets detected: {len(self.targets_found)}")
        
        if self.targets_found:
            rospy.loginfo("List of target locations:")
            for idx, item in enumerate(self.targets_found):
                x, y = item['pos']
                rospy.loginfo(f"  {idx+1}. ({x:.2f}, {y:.2f}, 0.1)")
                # 打印 AI 总结的前 100 个字符
                rospy.loginfo(f"     AI Summary: {item['desc'][:100]}...")
        else:
            rospy.loginfo("No targets found during patrol.")
        
        rospy.loginfo("=== Mission Complete. Standing by. ===")
        rospy.loginfo("================================")

if __name__ == '__main__':
    try:
        brain = PatrolBrainNew()
        brain.run()
    except rospy.ROSInterruptException:
        rospy.loginfo("Patrol task interrupted.")