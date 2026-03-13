#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import rospy
import actionlib
import math  # <- 新增这一行
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from actionlib_msgs.msg import GoalStatus
from geometry_msgs.msg import Quaternion

class NavigationManager:
    def __init__(self):
        self.client = actionlib.SimpleActionClient('move_base', MoveBaseAction)
        rospy.loginfo("Waiting for move_base action server...")
        if not self.client.wait_for_server(rospy.Duration(30.0)):
            rospy.logerr("Action server not available!")
            rospy.signal_shutdown("Action server not available!")
            return
        rospy.loginfo("Connected to move_base server")
    
    def goto(self, x, y, yaw=0.0):
        """
        发送目标位置并等待结果
        Args:
            x, y: 坐标（单位：米）
            yaw: 偏航角（单位：弧度，0代表向右，1.57代表向上）
        """
        rospy.loginfo(f"Navigating to ({x}, {y})")
        
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = "map"
        goal.target_pose.header.stamp = rospy.Time.now()
        
        goal.target_pose.pose.position.x = x
        goal.target_pose.pose.position.y = y
        
        # 将欧拉角(yaw)转换为四元数(Quaternion)
        # 这样机器人到达目标点时，脸是朝着房间内部的！
        goal.target_pose.pose.orientation.z = math.sin(yaw / 2.0)
        goal.target_pose.pose.orientation.w = math.cos(yaw / 2.0)
        
        self.client.send_goal(goal)
        
        timeout = rospy.Duration(60.0)
        if not self.client.wait_for_result(timeout):
            rospy.logwarn(f"Navigation to ({x}, {y}) timeout!")
            self.client.cancel_goal()
            return False
        
        state = self.client.get_state()
        if state == GoalStatus.SUCCEEDED:
            rospy.loginfo(f"Goal reached successfully! ({x}, {y})")
            return True
        else:
            rospy.logwarn(f"Goal failed with state: {state}")
            return False
            
    def cancel(self):
        self.client.cancel_goal()
        rospy.loginfo("Navigation cancelled")