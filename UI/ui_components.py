#!/usr/bin/env python3
"""
UI Components Module

Extracted UI functionality from Hand_Tracking.py to reduce code duplication
and improve maintainability.
"""

import cv2
import numpy as np
from typing import Dict, Any, Tuple, Optional


def draw_button(img, x, y, w, h, text, bg_color, text_color=(255, 255, 255)):
    """Draw a labeled rectangle on the given image."""
    cv2.rectangle(img, (x, y), (x + w, y + h), bg_color, -1)
    text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
    text_x = x + (w - text_size[0]) // 2
    text_y = y + (h + text_size[1]) // 2
    cv2.putText(img, text, (text_x, text_y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)


def draw_coordinates_panel(ui_frame, frame_w, right_shoulder=None, right_wrist=None):
    """Draw coordinate information panel"""
    if right_shoulder and right_wrist:
        # Shoulder coordinates
        cv2.putText(ui_frame, "Shoulder coordinates:", 
                   (frame_w + 10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        cv2.putText(ui_frame, f"X: {right_shoulder[0]:.2f}", 
                   (frame_w + 20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(ui_frame, f"Y: {right_shoulder[1]:.2f}", 
                   (frame_w + 20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
        cv2.putText(ui_frame, f"Z: {right_shoulder[2]:.2f}", 
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


def draw_robot_status(ui_frame, frame_w, running_state, robot_client=None):
    """Draw robot connection status"""
    if running_state['robot_enabled']:
        robot_status_text = "Robot: CONNECTED" if robot_client and robot_client.connected else "Robot: DISCONNECTED"
        robot_status_color = (0, 255, 0) if robot_client and robot_client.connected else (0, 0, 255)
        cv2.putText(ui_frame, robot_status_text, 
                   (frame_w + 10, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.6, robot_status_color, 1)
        return 300  # Adjust button position
    else:
        return 290  # Original position


def create_ui_elements(frame, running_state, right_shoulder=None, right_wrist=None, robot_client=None):
    """Create and position all UI elements on the frame"""
    frame_h, frame_w = frame.shape[:2]
    
    # UI panel dimensions
    panel_width = 300
    button_w = 200
    button_h = 40
    button_margin = 10
    
    # Create a wider frame with space on the right
    ui_frame = np.zeros((frame_h, frame_w + panel_width, 3), dtype=np.uint8)
    
    # Copy the original frame to the left side
    ui_frame[:, :frame_w, :] = frame
    
    # Right panel background (dark gray)
    ui_frame[:, frame_w:, :] = (40, 40, 40)
    
    # Draw coordinate and status panels
    draw_coordinates_panel(ui_frame, frame_w, right_shoulder, right_wrist)
    status_y = draw_robot_status(ui_frame, frame_w, running_state, robot_client)
    
    # Status indicator
    status_text = "PAUSED" if running_state['paused'] else "RUNNING"
    status_color = (0, 165, 255) if running_state['paused'] else (0, 255, 0)
    draw_button(ui_frame, frame_w + button_margin, status_y,
                button_w, button_h, status_text, (70, 70, 70), status_color)
    
    # Control buttons
    pause_button_x = frame_w + button_margin
    pause_button_y = status_y + button_h + 10
    pause_text = "RESUME" if running_state['paused'] else "PAUSE"
    draw_button(ui_frame, pause_button_x, pause_button_y,
                button_w, button_h, pause_text, (255, 165, 0))

    stop_button_x = frame_w + button_margin
    stop_button_y = pause_button_y + button_h + 10
    draw_button(ui_frame, stop_button_x, stop_button_y,
                button_w, button_h, "STOP", (0, 0, 255))

    mirror_button_x = frame_w + button_margin
    mirror_button_y = stop_button_y + button_h + 10
    mirror_text = "MIRROR ON" if running_state['mirrored'] else "MIRROR OFF"
    draw_button(ui_frame, mirror_button_x, mirror_button_y,
                button_w, button_h, mirror_text, (128, 0, 128))
    
    return ui_frame, {
        'panel_width': panel_width,
        'frame_width': frame_w,
        'pause_button': {
            'x': pause_button_x, 'y': pause_button_y, 'w': button_w, 'h': button_h
        },
        'stop_button': {
            'x': stop_button_x, 'y': stop_button_y, 'w': button_w, 'h': button_h
        },
        'mirror_button': {
            'x': mirror_button_x, 'y': mirror_button_y, 'w': button_w, 'h': button_h
        }
    }


def create_mouse_callback(ui_layout):
    """Create mouse callback function for button clicks"""
    def mouse_callback(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and x >= ui_layout['frame_width']:
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

            # Check mirror button
            mirror_btn = ui_layout['mirror_button']
            if (mirror_btn['x'] <= x <= mirror_btn['x'] + mirror_btn['w'] and
                mirror_btn['y'] <= y <= mirror_btn['y'] + mirror_btn['h']):
                param['mirrored'] = not param['mirrored']
    
    return mouse_callback
