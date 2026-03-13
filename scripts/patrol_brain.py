#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rospy
from std_msgs.msg import Bool
from geometry_msgs.msg import PoseWithCovarianceStamped
# ！！！导入我们刚才写的导航管理类 ！！！
from nav_manager import NavigationManager
import geometry_msgs.msg


class PatrolBrain:
    def __init__(self):
        rospy.init_node('patrol_brain')
        
        # 实例化导航管理类
        self.nav = NavigationManager()
        
        # 巡逻点坐标点 (x, y, w)
        self.points = [
            (-1.0, 1.0, 2.35),   # 房间 A (左上) - 面向左上(约135度)
            (1.0, 1.0, 0.78),    # 房间 B (右上) - 面向右上(约45度)
            (-1.0, -1.0, -2.35), # 房间 C (左下) - 面向左下(约-135度)
            (1.0, -1.0, -0.78),  # 房间 D (右下) - 面向右下(约-45度)
            (0.0, 0.0, 0.0)      # 回到中心原点 - 面向正东
        ]
        self.targets_found = []
        self.is_target_present = False
        self.current_robot_x = 0.0
        self.current_robot_y = 0.0

        # 订阅视觉识别结果
        rospy.Subscriber("/target_detected", Bool, self.vision_cb)
        # 订阅定位信息
        rospy.Subscriber("/amcl_pose", PoseWithCovarianceStamped, self.pose_cb)

    def vision_cb(self, msg):
        self.is_target_present = msg.data

    def pose_cb(self, msg):
        self.current_robot_x = msg.pose.pose.position.x
        self.current_robot_y = msg.pose.pose.position.y

    def run(self):
        rospy.loginfo("=== Patrol mission start ===")
        for i, (px, py, pw) in enumerate(self.points):
            rospy.loginfo(f"Heading to point {i}...")
            success = self.nav.goto(px, py, pw)
            
            if success:
                rospy.loginfo(f"Reached point {i}. Searching...")
                found_in_this_room = False # 新增：房间锁
                
                cmd_vel_pub = rospy.Publisher('/cmd_vel', geometry_msgs.msg.Twist, queue_size=1)
                move_cmd = geometry_msgs.msg.Twist()
                move_cmd.angular.z = 0.5 
                
                for _ in range(60): 
                    cmd_vel_pub.publish(move_cmd)
                    # 只有当在这个房间还没记录过目标，且现在看到了目标时，才记录
                    if self.is_target_present and not found_in_this_room:
                        rospy.loginfo("!!! NEW TARGET DISCOVERED !!!")
                        self.targets_found.append((self.current_robot_x, self.current_robot_y))
                        found_in_this_room = True # 锁住，这个房间不再记录了
                    rospy.sleep(0.1)
                
                cmd_vel_pub.publish(geometry_msgs.msg.Twist()) 

        # --- 完美调整：打印最终期中总结报告 ---
        rospy.loginfo("================================")
        rospy.loginfo("=== FINAL PATROL REPORT ===")
        rospy.loginfo(f"Total regions visited: {len(self.points)}")
        rospy.loginfo(f"Number of targets detected: {len(self.targets_found)}")
        for idx, pos in enumerate(self.targets_found):
            rospy.loginfo(f"Target {idx+1} Location: x={pos[0]:.2f}, y={pos[1]:.2f}")
        rospy.loginfo("=== Task Completed Successfully ===")
        rospy.loginfo("================================")

if __name__ == '__main__':
    brain = PatrolBrain()
    brain.run()