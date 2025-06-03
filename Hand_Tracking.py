import cv2
import mediapipe as mp
import numpy as np
import time

def main():
    # Initialize MediaPipe solutions
    mp_hands = mp.solutions.hands
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    
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
    
    # Define button dimensions
    button_w = 120
    button_h = 40
    button_margin = 10
    
    # Stop button (bottom)
    stop_button_x = button_margin
    stop_button_y = frame_h - button_h - button_margin
    stop_button_color = (0, 0, 255)  # Red
    
    # Pause button (above stop button)
    pause_button_x = button_margin
    pause_button_y = stop_button_y - button_h - 5
    pause_button_color = (255, 165, 0)  # Orange
    
    # Program state
    running_state = {'running': True, 'paused': False}
    
    # Define mouse callback function for button clicks
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            # Check stop button
            if (stop_button_x <= x <= stop_button_x + button_w and 
                stop_button_y <= y <= stop_button_y + button_h):
                param['running'] = False
            
            # Check pause button
            elif (pause_button_x <= x <= pause_button_x + button_w and 
                  pause_button_y <= y <= pause_button_y + button_h):
                param['paused'] = not param['paused']
    
    # Create a window and set the callback
    window_name = 'Hand and Pose Tracking'
    cv2.namedWindow(window_name)
    cv2.setMouseCallback(window_name, mouse_callback, running_state)
    
    # Display an initial message while loading
    init_frame = np.zeros((frame_h, frame_w, 3), dtype=np.uint8)
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
            
            # If we have both elbow and wrist positions, display their coordinates
            if right_elbow and right_wrist:
                # Display coordinates on frame
                cv2.putText(overlay, f"Wrist: ({right_wrist[0]:.2f}, {right_wrist[1]:.2f}, {right_wrist[2]:.2f})", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Draw vector from elbow to wrist
                elbow_px = (int(right_elbow[0] * frame.shape[1]), int(right_elbow[1] * frame.shape[0]))
                wrist_px = (int(right_wrist[0] * frame.shape[1]), int(right_wrist[1] * frame.shape[0]))
                cv2.line(overlay, elbow_px, wrist_px, (255, 0, 255), 3)
            
            # Blend the overlay with the original frame
            alpha = 0.7  # Transparency factor
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        # Add a legend
        cv2.rectangle(frame, (frame.shape[1] - 250, frame.shape[0] - 130), (frame.shape[1] - 10, frame.shape[0] - 10), (0, 0, 0), -1)
        cv2.putText(frame, "Legend:", (frame.shape[1] - 240, frame.shape[0] - 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.circle(frame, (frame.shape[1] - 230, frame.shape[0] - 70), 6, (0, 255, 0), -1)
        cv2.putText(frame, "Hand Landmarks", (frame.shape[1] - 210, frame.shape[0] - 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.circle(frame, (frame.shape[1] - 230, frame.shape[0] - 45), 6, (0, 0, 255), -1)
        cv2.putText(frame, "Elbow", (frame.shape[1] - 210, frame.shape[0] - 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.circle(frame, (frame.shape[1] - 230, frame.shape[0] - 20), 6, (255, 0, 0), -1)
        cv2.putText(frame, "Wrist", (frame.shape[1] - 210, frame.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        
        # Calculate right panel position
        right_panel_x = frame_w - button_w - button_margin
        
        # Status position (top right)
        status_height = 30
        status_y = button_margin
        cv2.rectangle(frame, (right_panel_x, status_y), 
                 (right_panel_x + button_w, status_y + status_height), (70, 70, 70), -1)
        
        # Status text
        status_text = "PAUSED" if running_state['paused'] else "RUNNING"
        status_color = (0, 165, 255) if running_state['paused'] else (0, 255, 0)
        cv2.putText(frame, status_text, (right_panel_x + 20, status_y + 20),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
        
        # Pause button (below status)
        pause_button_x = right_panel_x
        pause_button_y = status_y + status_height + 10
        cv2.rectangle(frame, (pause_button_x, pause_button_y), 
                 (pause_button_x + button_w, pause_button_y + button_h), pause_button_color, -1)
        pause_text = "RESUME" if running_state['paused'] else "PAUSE"
        cv2.putText(frame, pause_text, (pause_button_x + 20, pause_button_y + 27), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Stop button (below pause button)
        stop_button_x = right_panel_x
        stop_button_y = pause_button_y + button_h + 10
        cv2.rectangle(frame, (stop_button_x, stop_button_y), 
                 (stop_button_x + button_w, stop_button_y + button_h), stop_button_color, -1)
        cv2.putText(frame, "STOP", (stop_button_x + 40, stop_button_y + 27), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show the frame
        cv2.imshow(window_name, frame)
        
        # Break the loop on 'q' press
        key = cv2.waitKey(10) & 0xFF
        if key == ord('q'):
            running_state['running'] = False
        elif key == ord('p'):
            running_state['paused'] = not running_state['paused']
    
    # Clean up
    cap.release()
    cv2.destroyAllWindows()
    print("Application stopped successfully")

if __name__ == "__main__":
    main()
