import argparse
import cv2
import mediapipe as mp
import numpy as np
import socket
import json
import threading
import time
import sys
import os

# Add UI directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'UI'))
from ui_components import create_ui_elements, create_mouse_callback

class RobotClient:
    """TCP client to send coordinates to the robot controller"""
    
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.retry_interval = 5.0  # seconds
        self.last_coordinates = None
        
    def connect(self):
        """Connect to the robot controller"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"Connected to robot controller at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to robot controller: {e}")
            self.connected = False
            return False
            
    def disconnect(self):
        """Disconnect from the robot controller"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False
        
    def send_coordinates(self, shoulder, wrist):
        """Send shoulder and wrist coordinates to the robot controller"""
        if not self.connected:
            return False
            
        try:
            data = {
                'shoulder': shoulder,
                'wrist': wrist,
                'timestamp': time.time()
            }
            
            message = json.dumps(data) + '\n'
            self.socket.send(message.encode('utf-8'))
            self.last_coordinates = data
            return True
            
        except Exception as e:
            print(f"Error sending coordinates: {e}")
            self.connected = False
            return False
            
    def auto_reconnect(self):
        """Automatically reconnect to the robot controller if connection is lost"""
        while True:
            if not self.connected:
                print("Attempting to reconnect to robot controller...")
                self.connect()
            time.sleep(self.retry_interval)

def main():
    parser = argparse.ArgumentParser(description="Hand and pose tracking demo")
    parser.add_argument(
        "--hand",
        choices=["Right", "Left"],
        default="Right",
        help="Which hand to track",
    )
    parser.add_argument(
        "--mirror",
        action="store_true",
        help="Set this flag if your camera feed is mirrored",
    )
    parser.add_argument(
        "--robot-host",
        default="localhost",
        help="Host address of the robot controller",
    )
    parser.add_argument(
        "--robot-port", 
        type=int,
        default=8888,
        help="Port of the robot controller",
    )
    parser.add_argument(
        "--enable-robot",
        action="store_true",
        help="Enable robot control (sends coordinates to robot controller)",
    )
    args = parser.parse_args()

    tracked_hand_label = args.hand
    mirrored_camera = args.mirror

    # Initialize robot client if enabled
    robot_client = None
    if args.enable_robot:
        robot_client = RobotClient(args.robot_host, args.robot_port)
        
        # Start auto-reconnect thread
        reconnect_thread = threading.Thread(target=robot_client.auto_reconnect)
        reconnect_thread.daemon = True
        reconnect_thread.start()
        
        # Initial connection attempt
        robot_client.connect()

    # Initialize MediaPipe solutions
    mp_hands = mp.solutions.hands
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    
    # Custom drawing specs for better visualization
    hand_landmark_drawing_spec = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=5, circle_radius=8)
    hand_connection_drawing_spec = mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=3)
    
    # Initialize the models
    # Detect up to two hands so we can explicitly choose the right one
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=2,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    pose = mp_pose.Pose(
        static_image_mode=False,
        model_complexity=1,
        smooth_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    )
    # Set up webcam
    cap = cv2.VideoCapture(0)
    
    # Check if the webcam is opened correctly
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return
    
    # Get frame dimensions
    ret, first_frame = cap.read()
    if not ret:
        print("Error: Could not read from webcam")
        cap.release()
        return
    
    frame_h, frame_w = first_frame.shape[:2]
      # Program state
    running_state = {'running': True, 'paused': False, 'mirrored': mirrored_camera, 'robot_enabled': args.enable_robot}
      # Create initial UI to determine layout
    ui_frame, ui_layout = create_ui_elements(first_frame, running_state, None, None, robot_client)
      # Create mouse callback function using imported ui_components
    mouse_callback = create_mouse_callback(ui_layout)
    
    # Create a window and set the callback
    window_name = 'Hand and Pose Tracking'
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback, running_state)
    
    # Display an initial message while loading
    init_frame = np.zeros((frame_h, frame_w + ui_layout['panel_width'], 3), dtype=np.uint8)
    cv2.putText(init_frame, "Initializing...", (frame_w//2-100, frame_h//2), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.imshow(window_name, init_frame)
    cv2.waitKey(1)
    
    while cap.isOpened() and running_state['running']:
        if not running_state['paused']:
            ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break
                
            # Convert to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process frame with both MediaPipe models
            hand_results = hands.process(rgb_frame)
            pose_results = pose.process(rgb_frame)
            
            # Create an overlay layer
            overlay = frame.copy()
            
            # Variables to store landmarks
            right_shoulder = None
            right_wrist = None
            
            # Extract shoulder position from pose
            if pose_results.pose_landmarks:
                # Draw pose landmarks with custom style
                mp_drawing.draw_landmarks(
                    overlay,
                    pose_results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing.DrawingSpec(color=(255, 255, 0), thickness=4, circle_radius=6),
                    connection_drawing_spec=mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
                )
                
                # Get right shoulder position
                right_shoulder = [
                    pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER].x,
                    pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER].y,
                    pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_SHOULDER].z
                ]
                
                # Fallback wrist position from pose (in case hand detection fails)
                right_wrist = [
                    pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].x,
                    pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].y,
                    pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].z
                ]

                # Draw shoulder point with label
                shoulder_pixel = (
                    int(right_shoulder[0] * frame.shape[1]), 
                    int(right_shoulder[1] * frame.shape[0])
                )
                cv2.circle(overlay, shoulder_pixel, 10, (0, 0, 255), -1)
                cv2.putText(overlay, "SHOULDER", (shoulder_pixel[0]+10, shoulder_pixel[1]), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Extract more precise wrist position from hand tracking
            if hand_results.multi_hand_landmarks and hand_results.multi_handedness:
                for hand_landmarks, hand_info in zip(hand_results.multi_hand_landmarks,
                                                     hand_results.multi_handedness):
                    label = hand_info.classification[0].label
                    if running_state['mirrored']:
                        label = "Left" if label == "Right" else "Right"
                    if label != tracked_hand_label:
                        # Skip detections that are not the desired hand
                        continue

                    # Draw landmarks only for the right hand
                    mp_drawing.draw_landmarks(
                        overlay,
                        hand_landmarks,
                        mp_hands.HAND_CONNECTIONS,
                        landmark_drawing_spec=hand_landmark_drawing_spec,
                        connection_drawing_spec=hand_connection_drawing_spec
                    )

                    right_wrist = [
                        hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].x,
                        hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].y,
                        hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].z
                    ]

                    wrist_pixel = (
                        int(right_wrist[0] * frame.shape[1]),
                        int(right_wrist[1] * frame.shape[0])
                    )
                    cv2.circle(overlay, wrist_pixel, 10, (255, 0, 0), -1)
                    cv2.putText(overlay, "WRIST", (wrist_pixel[0]+10, wrist_pixel[1]),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

                    for i, landmark in enumerate(hand_landmarks.landmark):
                        landmark_px = (int(landmark.x * frame.shape[1]), int(landmark.y * frame.shape[0]))
                        cv2.circle(overlay, landmark_px, 5, (0, 255, 255), -1)
                        cv2.putText(overlay, str(i), landmark_px,
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    break
              # If we have both shoulder and wrist positions, display a vector connecting them
            if right_shoulder is not None and right_wrist is not None:
                # Draw vector from shoulder to wrist
                shoulder_px = (int(right_shoulder[0] * frame.shape[1]), int(right_shoulder[1] * frame.shape[0]))
                wrist_px = (int(right_wrist[0] * frame.shape[1]), int(right_wrist[1] * frame.shape[0]))
                cv2.line(overlay, shoulder_px, wrist_px, (255, 0, 255), 3)
                
                # Send coordinates to robot if enabled and connected
                if robot_client and running_state['robot_enabled'] and robot_client.connected:
                    robot_client.send_coordinates(right_shoulder, right_wrist)

            # Blend the overlay with the original frame
            alpha = 0.7  # Transparency factor
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
          # Create UI elements with the current frame
        ui_frame, ui_layout = create_ui_elements(frame, running_state, right_shoulder, right_wrist, robot_client)

        # Show the frame
        cv2.imshow(window_name, ui_frame)
        
        # Break the loop on 'q' press
        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            running_state['running'] = False
        elif key == ord('p'):
            running_state['paused'] = not running_state['paused']
      # Clean up
    cap.release()
    cv2.destroyAllWindows()
    
    # Disconnect robot client
    if robot_client:
        robot_client.disconnect()
        
    print("Application stopped successfully")

if __name__ == "__main__":
    main()
