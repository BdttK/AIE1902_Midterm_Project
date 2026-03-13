#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vision_node.py - 视觉处理节点
"""

import rospy
import cv2
import numpy as np
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image
from std_msgs.msg import Bool
import yaml
import os

class VisionNode:
    def __init__(self):
        """初始化视觉处理节点"""
        rospy.init_node('vision_node')
        
        self.bridge = CvBridge()
        self.load_hsv_params()

        self.last_save_time = rospy.Time(0)

        self.image_sub = rospy.Subscriber(
            "/camera/rgb/image_raw", 
            Image, 
            self.image_callback
        )
        
        self.target_pub = rospy.Publisher("/target_detected", Bool, queue_size=1)
        
        rospy.loginfo("Vision Node Initialized")
        rospy.loginfo(f"HSV Range: {self.lower_green} - {self.upper_green}")
    
    def load_hsv_params(self):
        """从 YAML 文件加载 HSV 阈值参数"""
        default_lower = [40, 50, 50]
        default_upper = [70, 255, 255]
        
        try:
            config_path = os.path.join(
                rospy.get_param('/root_path', '/tmp'),
                'hsv_params.yaml'
            )
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    params = yaml.safe_load(f)
                    self.lower_green = np.array(params['lower_green'])
                    self.upper_green = np.array(params['upper_green'])
                    rospy.loginfo("Loaded HSV params from YAML")
            else:
                rospy.logwarn("HSV params YAML not found, using defaults")
                self.lower_green = np.array(default_lower)
                self.upper_green = np.array(default_upper)
                
        except Exception as e:
            rospy.logerr(f"Error loading HSV params: {e}")
            self.lower_green = np.array(default_lower)
            self.upper_green = np.array(default_upper)
    
    def image_callback(self, data):
            try:
                cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
            except CvBridgeError as e:
                rospy.logerr(f"CvBridge error: {e}")
                return
            
            hsv = cv2.cvtColor(cv_image, cv2.COLOR_BGR2HSV)
            mask = cv2.inRange(hsv, self.lower_green, self.upper_green)
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            
            detected = False
            if len(contours) > 0:
                max_cnt = max(contours, key=cv2.contourArea)
                if cv2.contourArea(max_cnt) > 800:
                    detected = True
                    x, y, w, h = cv2.boundingRect(max_cnt)
                    cv2.rectangle(cv_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
                    center_x = x + w // 2
                    center_y = y + h // 2
                    cv2.circle(cv_image, (center_x, center_y), 5, (0, 0, 255), -1)
            
            self.target_pub.publish(detected)
            
            # --- 【修改这里】取消 if detected 的限制，持续更新当前场景照片 ---
            if (rospy.Time.now() - self.last_save_time).to_sec() > 1.0:
                # 将名字改为 current_scene.jpg，代表这是当前环境的全景图
                cv2.imwrite("/tmp/current_scene.jpg", cv_image)
                self.last_save_time = rospy.Time.now()
            # -----------------------------------------------------------
            
            cv2.imshow("Robot Camera View", cv_image)
            cv2.waitKey(3)


if __name__ == '__main__':
    try:
        node = VisionNode()
        rospy.spin()
    except rospy.ROSInterruptException:
        rospy.loginfo("Vision node shutdown.")
        cv2.destroyAllWindows()