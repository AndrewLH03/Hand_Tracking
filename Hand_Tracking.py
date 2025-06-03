import cv2
import mediapipe as mp
import numpy as np
import time
import socket
import json

class DoBotCR3:
    def __init__(self, ip_address, port=8080):
        """Initialize connection to DoBotCR3."""
        self.ip_address = ip_address
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect()
    
    def connect(self):
        """Establish connection to the robot."""
        try:
            self.socket.connect((self.ip_address, self.port))
            print(f"Connected to DoBotCR3 at {self.ip_address}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def move_to_position(self, x, y, z):
        """Send command to move robot to the specified position."""
        try:
            command = {
                "command": "move_to",
                "coordinates": {
                    "x": x,
                    "y": y,
                    "z": z
                }
            }
            self.socket.sendall(json.dumps(command).encode('utf-8'))
            return True
        except Exception as e:
            print(f"Failed to send command: {e}")
            return False
    
    def close(self):
        """Close the connection."""
        self.socket.close()

def transform_coordinates(wrist, elbow):
    """
    Transform coordinates to make elbow the origin.
    Returns wrist position relative to elbow.
    """
    # Vector from elbow to wrist
    vector = np.array(wrist) - np.array(elbow)
    
    # Scale factor for robot workspace
    scale_factor = 0.5  # Adjust based on calibration
    
    # Scale the vector
    scaled_vector = vector * scale_factor
    
    # Return coordinates
    return scaled_vector[0], scaled_vector[1], scaled_vector[2]

def main():
    # Initialize MediaPipe solutions
    mp_hands = mp.solutions.hands
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles
    
    # Custom drawing specs for better visualization
    hand_landmark_drawing_spec = mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=5, circle_radius=8)
    hand_connection_drawing_spec = mp_drawing.DrawingSpec(color=(255, 0, 0), thickness=3)
    
    # Initialize the models
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,  # Only track one hand
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
    
    # Initialize DoBotCR3 connection
    # Replace with actual IP address
    dobot = DoBotCR3("192.168.1.100")  
    
    # Set up webcam
    cap = cv2.VideoCapture(0)
    
    # Previous position for smoothing
    prev_x, prev_y, prev_z = 0, 0, 0
    smoothing_factor = 0.5  # 0 = no smoothing, 1 = no movement
    
    # Define button properties
    button_x, button_y, button_w, button_h = 10, 50, 150, 40
    button_color = (0, 0, 255)  # Red color for the stop button
    button_text = "STOP"
    
    # Define mouse callback function for button click
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            if button_x <= x <= button_x + button_w and button_y <= y <= button_y + button_h:
                param['running'] = False
    
    # Create a window and set the callback
    cv2.namedWindow('Hand and Pose Tracking')
    running_state = {'running': True}
    cv2.setMouseCallback('Hand and Pose Tracking', mouse_callback, running_state)
    
    while cap.isOpened() and running_state['running']:
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
        right_elbow = None
        right_wrist = None
        
        # Extract elbow position from pose
        if pose_results.pose_landmarks:
            # Draw pose landmarks with custom style
            mp_drawing.draw_landmarks(
                overlay,
                pose_results.pose_landmarks,
                mp_pose.POSE_CONNECTIONS,
                landmark_drawing_spec=mp_drawing.DrawingSpec(color=(255, 255, 0), thickness=4, circle_radius=6),
                connection_drawing_spec=mp_drawing.DrawingSpec(color=(255, 255, 255), thickness=2)
            )
            
            # Get right elbow position
            right_elbow = [
                pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ELBOW].x,
                pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ELBOW].y,
                pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_ELBOW].z
            ]
            
            # Fallback wrist position from pose (in case hand detection fails)
            right_wrist = [
                pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].x,
                pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].y,
                pose_results.pose_landmarks.landmark[mp_pose.PoseLandmark.RIGHT_WRIST].z
            ]
            
            # Draw elbow point with label
            elbow_pixel = (
                int(right_elbow[0] * frame.shape[1]), 
                int(right_elbow[1] * frame.shape[0])
            )
            cv2.circle(overlay, elbow_pixel, 10, (0, 0, 255), -1)
            cv2.putText(overlay, "ELBOW", (elbow_pixel[0]+10, elbow_pixel[1]), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        # Extract more precise wrist position from hand tracking
        if hand_results.multi_hand_landmarks:
            for hand_landmarks in hand_results.multi_hand_landmarks:
                # Draw hand landmarks with custom specs
                mp_drawing.draw_landmarks(
                    overlay,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS,
                    landmark_drawing_spec=hand_landmark_drawing_spec,
                    connection_drawing_spec=hand_connection_drawing_spec
                )
                
                # Update wrist position with the hand model's more precise tracking
                right_wrist = [
                    hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].x,
                    hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].y,
                    hand_landmarks.landmark[mp_hands.HandLandmark.WRIST].z
                ]
                
                # Draw wrist point with label
                wrist_pixel = (
                    int(right_wrist[0] * frame.shape[1]), 
                    int(right_wrist[1] * frame.shape[0])
                )
                cv2.circle(overlay, wrist_pixel, 10, (255, 0, 0), -1)
                cv2.putText(overlay, "WRIST", (wrist_pixel[0]+10, wrist_pixel[1]), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)
                
                # Label each finger landmark
                for i, landmark in enumerate(hand_landmarks.landmark):
                    landmark_px = (int(landmark.x * frame.shape[1]), int(landmark.y * frame.shape[0]))
                    cv2.circle(overlay, landmark_px, 5, (0, 255, 255), -1)
                    cv2.putText(overlay, str(i), landmark_px, cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        
        # If we have both the elbow and wrist positions, transform and send to robot
        if right_elbow and right_wrist:
            x, y, z = transform_coordinates(right_wrist, right_elbow)
            
            # Apply smoothing
            x = prev_x * smoothing_factor + x * (1 - smoothing_factor)
            y = prev_y * smoothing_factor + y * (1 - smoothing_factor)
            z = prev_z * smoothing_factor + z * (1 - smoothing_factor)
            
            # Update previous position
            prev_x, prev_y, prev_z = x, y, z
            
            # Send position to the robot
            dobot.move_to_position(x, y, z)
            
            # Display coordinates on frame
            cv2.putText(overlay, f"X: {x:.2f}, Y: {y:.2f}, Z: {z:.2f}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # Draw vector from elbow to wrist
            if right_elbow and right_wrist:
                elbow_px = (int(right_elbow[0] * frame.shape[1]), int(right_elbow[1] * frame.shape[0]))
                wrist_px = (int(right_wrist[0] * frame.shape[1]), int(right_wrist[1] * frame.shape[0]))
                cv2.line(overlay, elbow_px, wrist_px, (255, 0, 255), 3)
        
        # Blend the overlay with the original frame
        alpha = 0.7  # Transparency factor
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        # Add a legend
        cv2.rectangle(frame, (10, frame.shape[0] - 130), (250, frame.shape[0] - 10), (0, 0, 0), -1)
        cv2.putText(frame, "Legend:", (20, frame.shape[0] - 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.circle(frame, (30, frame.shape[0] - 70), 6, (0, 255, 0), -1)
        cv2.putText(frame, "Hand Landmarks", (50, frame.shape[0] - 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.circle(frame, (30, frame.shape[0] - 45), 6, (0, 0, 255), -1)
        cv2.putText(frame, "Elbow", (50, frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.circle(frame, (30, frame.shape[0] - 20), 6, (255, 0, 0), -1)
        cv2.putText(frame, "Wrist", (50, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Draw stop button
        cv2.rectangle(frame, (button_x, button_y), (button_x + button_w, button_y + button_h), button_color, -1)
        cv2.putText(frame, button_text, (button_x + 20, button_y + 25), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show the frame
        cv2.imshow('Hand and Pose Tracking', frame)
        
        # Break the loop on 'q' press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    dobot.close()
    print("Application stopped successfully")

if __name__ == "__main__":
    main()