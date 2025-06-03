import cv2
import mediapipe as mp
import numpy as np

def draw_button(img, x, y, w, h, text, bg_color, text_color=(255, 255, 255)):
    """Draw a labeled rectangle on the given image."""
    cv2.rectangle(img, (x, y), (x + w, y + h), bg_color, -1)
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
    text_x = x + (w - text_size[0]) // 2
    text_y = y + (h + text_size[1]) // 2
    cv2.putText(img, text, (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)

def create_ui_elements(frame, running_state, right_elbow=None, right_wrist=None):
    """Create and position all UI elements on the frame"""
    frame_h, frame_w = frame.shape[:2]
    
    # UI panel dimensions
    panel_width = 300  # Added width for the side panel
    button_w = 200
    button_h = 40
    button_margin = 10
    
    # Create a wider frame with space on the right
    ui_frame = np.zeros((frame_h, frame_w + panel_width, 3), dtype=np.uint8)
    
    # Copy the original frame to the left side
    ui_frame[:, :frame_w, :] = frame
    
    # Right panel background (dark gray)
    ui_frame[:, frame_w:, :] = (40, 40, 40)
    
    # Coordinates panel in the top right
    if right_elbow and right_wrist:
        # Elbow coordinates
        cv2.putText(ui_frame, "Elbow coordinates:", 
                   (frame_w + 10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(ui_frame, f"X: {right_elbow[0]:.2f}", 
                   (frame_w + 20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(ui_frame, f"Y: {right_elbow[1]:.2f}", 
                   (frame_w + 20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(ui_frame, f"Z: {right_elbow[2]:.2f}", 
                   (frame_w + 20, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        
        # Wrist coordinates
        cv2.putText(ui_frame, "Wrist coordinates:", 
                   (frame_w + 10, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(ui_frame, f"X: {right_wrist[0]:.2f}", 
                   (frame_w + 20, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(ui_frame, f"Y: {right_wrist[1]:.2f}", 
                   (frame_w + 20, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(ui_frame, f"Z: {right_wrist[2]:.2f}", 
                   (frame_w + 20, 260), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
    
    # Position buttons directly below the coordinate display
    status_y = 290  # Just below the wrist coordinates which end at y=260

    # Status indicator
    status_text = "PAUSED" if running_state['paused'] else "RUNNING"
    status_color = (0, 165, 255) if running_state['paused'] else (0, 255, 0)
    draw_button(ui_frame, frame_w + button_margin, status_y,
                button_w, button_h, status_text, (70, 70, 70), status_color)


    
    # Status position
    cv2.rectangle(ui_frame, 
                 (frame_w + button_margin, status_y), 
                 (frame_w + button_margin + button_w, status_y + button_h), 
                 (70, 70, 70), -1)
    
    # Status text (centered horizontally and vertically)
    status_text = "PAUSED" if running_state['paused'] else "RUNNING"
    status_color = (0, 165, 255) if running_state['paused'] else (0, 255, 0)
    text_size = cv2.getTextSize(status_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
    text_x = frame_w + button_margin + (button_w - text_size[0]) // 2
    text_y = status_y + (button_h + text_size[1]) // 2  # Center vertically in the button
    cv2.putText(ui_frame, status_text, 
               (text_x, text_y),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, status_color, 2)
    
    # Pause button (below status)
    pause_button_x = frame_w + button_margin
    pause_button_y = status_y + button_h + 10
    pause_text = "RESUME" if running_state['paused'] else "PAUSE"
    draw_button(ui_frame, pause_button_x, pause_button_y,
                button_w, button_h, pause_text, (255, 165, 0))

    # Stop button (below pause button)
    stop_button_x = frame_w + button_margin
    stop_button_y = pause_button_y + button_h + 10
    draw_button(ui_frame, stop_button_x, stop_button_y,
                button_w, button_h, "STOP", (0, 0, 255))
    
    return ui_frame, {
        'panel_width': panel_width,
        'frame_width': frame_w,
        'pause_button': {
            'x': pause_button_x,
            'y': pause_button_y,
            'w': button_w,
            'h': button_h
        },
        'stop_button': {
            'x': stop_button_x,
            'y': stop_button_y,
            'w': button_w,
            'h': button_h
        }
    }

def main():
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
    running_state = {'running': True, 'paused': False}
    
    # Create initial UI to determine layout
    ui_frame, ui_layout = create_ui_elements(first_frame, running_state)
    
    # Define mouse callback function for button clicks
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            
            # Check if click is in side panel
            if x >= ui_layout['frame_width']:
                # Check stop button
                stop_btn = ui_layout['stop_button']
                if (stop_btn['x'] <= x <= stop_btn['x'] + stop_btn['w'] and 
                    stop_btn['y'] <= y <= stop_btn['y'] + stop_btn['h']):
                    param['running'] = False
                
                # Check pause button
                pause_btn = ui_layout['pause_button']
                if (pause_btn['x'] <= x <= pause_btn['x'] + pause_btn['w'] and 
                    pause_btn['y'] <= y <= pause_btn['y'] + pause_btn['h']):
                    param['paused'] = not param['paused']
    
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
            if hand_results.multi_hand_landmarks and hand_results.multi_handedness:
                for hand_landmarks, hand_info in zip(hand_results.multi_hand_landmarks,
                                                     hand_results.multi_handedness):
                    label = hand_info.classification[0].label
                    if label != "Right":
                        # Skip left hand detections entirely
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
            
            # If we have both elbow and wrist positions, display a vector connecting them
            if right_elbow is not None and right_wrist is not None:
                # Draw vector from elbow to wrist
                elbow_px = (int(right_elbow[0] * frame.shape[1]), int(right_elbow[1] * frame.shape[0]))
                wrist_px = (int(right_wrist[0] * frame.shape[1]), int(right_wrist[1] * frame.shape[0]))
                cv2.line(overlay, elbow_px, wrist_px, (255, 0, 255), 3)
            
            # Blend the overlay with the original frame
            alpha = 0.7  # Transparency factor
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        
        # Create UI elements with the current frame
        ui_frame, ui_layout = create_ui_elements(frame, running_state, right_elbow, right_wrist)
        
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
    print("Application stopped successfully")

if __name__ == "__main__":
    main()
