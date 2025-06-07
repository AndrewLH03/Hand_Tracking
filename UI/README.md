# UI Components Package 🎨

User interface components and visual feedback systems for the robotic arm hand tracking application. This package provides reusable UI elements, real-time data visualization, and interactive controls for enhanced user experience.

## 📁 Package Structure

```
UI/
├── __init__.py           # Package initialization  
└── ui_components.py      # Core UI components and utilities
```

## 🚀 Core Components

### UI Components Module (`ui_components.py`)
Modular UI components extracted from the main hand tracking system for improved maintainability and reusability.

**Key Features:**
- **Modular Design**: Reusable UI components for various displays
- **Real-time Visualization**: Live coordinate and status displays
- **Interactive Elements**: Buttons, panels, and control interfaces
- **Visual Feedback**: Clear status indicators and information panels
- **OpenCV Integration**: Seamless integration with computer vision workflows

**Component Library:**
```
UI Components
├── Drawing Functions ──── Basic shape and text rendering
├── Information Panels ──── Coordinate and status displays  
├── Interactive Elements ── Buttons and controls
├── Layout Managers ────── Panel organization and layout
└── Visual Effects ────── Animations and transitions
```

## 🔧 API Reference

### Drawing Functions

#### Basic Drawing
```python
# Draw labeled button
draw_button(img, x, y, width, height, text, bg_color, text_color)

# Draw status indicator
draw_status_indicator(img, x, y, status, size)

# Draw progress bar
draw_progress_bar(img, x, y, width, height, progress, color)
```

#### Text Rendering
```python
# Draw formatted text
draw_text(img, text, position, font_scale, color, thickness)

# Draw multi-line text
draw_multiline_text(img, lines, start_pos, line_height, color)

# Draw text with background
draw_text_with_background(img, text, pos, bg_color, text_color)
```

### Information Panels

#### Coordinate Display
```python
def draw_coordinates_panel(ui_frame, frame_w, right_shoulder=None, right_wrist=None):
    """
    Draw real-time coordinate information panel
    
    Args:
        ui_frame: Target frame for drawing
        frame_w: Frame width for positioning
        right_shoulder: Shoulder coordinates (x, y, z)
        right_wrist: Wrist coordinates (x, y, z)
    """
```

#### Status Display
```python
def draw_status_panel(ui_frame, connection_status, robot_status, tracking_status):
    """
    Draw system status information panel
    
    Args:
        ui_frame: Target frame for drawing
        connection_status: Robot connection status
        robot_status: Robot operational status  
        tracking_status: Hand tracking status
    """
```

### Interactive Elements

#### Button System
```python
def create_button(x, y, width, height, text, action_callback):
    """
    Create interactive button element
    
    Returns:
        Button object with click detection and callback
    """

def handle_button_click(buttons, mouse_x, mouse_y):
    """
    Handle mouse click events for button interactions
    
    Args:
        buttons: List of button objects
        mouse_x, mouse_y: Mouse click coordinates
    """
```

#### Mouse Callback System
```python
def create_mouse_callback(buttons, panels):
    """
    Create mouse event callback function for UI interactions
    
    Returns:
        Callback function for OpenCV setMouseCallback
    """
```

### Layout Management

#### Panel Layout
```python
def create_ui_layout(frame_width, frame_height, panels):
    """
    Organize multiple panels in a structured layout
    
    Args:
        frame_width, frame_height: Display dimensions
        panels: List of panel configurations
        
    Returns:
        Positioned UI elements with coordinates
    """
```

## 🎯 Usage Examples

### Basic UI Setup
```python
#!/usr/bin/env python3
import cv2
import numpy as np
from UI.ui_components import draw_button, draw_coordinates_panel, create_mouse_callback

# Create main display frame
frame_width, frame_height = 1200, 800
ui_frame = np.zeros((frame_height, frame_width, 3), dtype=np.uint8)

# Add coordinate display panel
coordinates = {'shoulder': [100, 200, 300], 'wrist': [150, 180, 320]}
draw_coordinates_panel(ui_frame, 800, 
                      coordinates['shoulder'], coordinates['wrist'])

# Add control buttons
buttons = [
    {'pos': (900, 100), 'size': (120, 40), 'text': 'Start', 'color': (0, 255, 0)},
    {'pos': (900, 160), 'size': (120, 40), 'text': 'Stop', 'color': (0, 0, 255)},
    {'pos': (900, 220), 'size': (120, 40), 'text': 'Reset', 'color': (255, 255, 0)}
]

for btn in buttons:
    draw_button(ui_frame, btn['pos'][0], btn['pos'][1], 
               btn['size'][0], btn['size'][1], 
               btn['text'], btn['color'])

# Display frame
cv2.imshow('Robot Control UI', ui_frame)
cv2.waitKey(0)
cv2.destroyAllWindows()
```

### Interactive Control Panel
```python
#!/usr/bin/env python3
import cv2
from UI.ui_components import create_ui_elements, create_mouse_callback

class RobotControlUI:
    def __init__(self):
        self.frame_width = 1200
        self.frame_height = 800
        self.ui_frame = None
        self.buttons = []
        self.status = {
            'connection': 'Disconnected',
            'robot_enabled': False,
            'tracking_active': False
        }
        
        self.setup_ui()
        
    def setup_ui(self):
        """Initialize UI layout and components"""
        # Create main frame
        self.ui_frame = np.zeros((self.frame_height, self.frame_width, 3), dtype=np.uint8)
        
        # Define button layout
        self.buttons = [
            {
                'id': 'connect',
                'rect': (50, 50, 120, 40),
                'text': 'Connect',
                'color': (0, 255, 0),
                'action': self.connect_robot
            },
            {
                'id': 'enable',
                'rect': (50, 110, 120, 40),
                'text': 'Enable Robot',
                'color': (255, 255, 0),
                'action': self.enable_robot
            },
            {
                'id': 'start_tracking',
                'rect': (50, 170, 120, 40),
                'text': 'Start Tracking',
                'color': (0, 255, 255),
                'action': self.start_tracking
            },
            {
                'id': 'emergency_stop',
                'rect': (50, 250, 120, 40),
                'text': 'EMERGENCY',
                'color': (0, 0, 255),
                'action': self.emergency_stop
            }
        ]
        
        # Setup mouse callback
        mouse_callback = create_mouse_callback(self.buttons, [])
        cv2.setMouseCallback('Robot Control', mouse_callback)
    
    def update_display(self, coordinates=None, robot_status=None):
        """Update UI display with current data"""
        # Clear frame
        self.ui_frame.fill(0)
        
        # Draw buttons
        for btn in self.buttons:
            x, y, w, h = btn['rect']
            draw_button(self.ui_frame, x, y, w, h, 
                       btn['text'], btn['color'])
        
        # Draw status panel
        self.draw_status_panel()
        
        # Draw coordinates if available
        if coordinates:
            draw_coordinates_panel(self.ui_frame, 400, 
                                 coordinates.get('shoulder'),
                                 coordinates.get('wrist'))
        
        # Draw robot status
        if robot_status:
            self.draw_robot_status(robot_status)
    
    def draw_status_panel(self):
        """Draw system status information"""
        status_y = 350
        cv2.putText(self.ui_frame, "System Status:", 
                   (50, status_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Connection status
        conn_color = (0, 255, 0) if self.status['connection'] == 'Connected' else (0, 0, 255)
        cv2.putText(self.ui_frame, f"Connection: {self.status['connection']}", 
                   (50, status_y + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, conn_color, 1)
        
        # Robot enabled status
        robot_color = (0, 255, 0) if self.status['robot_enabled'] else (255, 255, 0)
        cv2.putText(self.ui_frame, f"Robot Enabled: {self.status['robot_enabled']}", 
                   (50, status_y + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, robot_color, 1)
        
        # Tracking status
        track_color = (0, 255, 0) if self.status['tracking_active'] else (128, 128, 128)
        cv2.putText(self.ui_frame, f"Tracking: {self.status['tracking_active']}", 
                   (50, status_y + 80), cv2.FONT_HERSHEY_SIMPLEX, 0.5, track_color, 1)
    
    def connect_robot(self):
        """Handle connect button click"""
        print("Connecting to robot...")
        self.status['connection'] = 'Connected'
        
    def enable_robot(self):
        """Handle enable robot button click"""
        print("Enabling robot...")
        self.status['robot_enabled'] = True
        
    def start_tracking(self):
        """Handle start tracking button click"""
        print("Starting hand tracking...")
        self.status['tracking_active'] = True
        
    def emergency_stop(self):
        """Handle emergency stop button click"""
        print("EMERGENCY STOP ACTIVATED!")
        self.status['robot_enabled'] = False
        self.status['tracking_active'] = False
    
    def run(self):
        """Main UI loop"""
        cv2.namedWindow('Robot Control')
        
        while True:
            # Update display
            self.update_display()
            
            # Show frame
            cv2.imshow('Robot Control', self.ui_frame)
            
            # Handle keyboard input
            key = cv2.waitKey(30) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('c'):
                self.connect_robot()
            elif key == ord('e'):
                self.enable_robot()
            elif key == ord('s'):
                self.start_tracking()
            elif key == ord(' '):
                self.emergency_stop()
        
        cv2.destroyAllWindows()

# Usage
if __name__ == "__main__":
    ui = RobotControlUI()
    ui.run()
```

### Real-time Data Visualization
```python
#!/usr/bin/env python3
import cv2
import numpy as np
from collections import deque
from UI.ui_components import draw_coordinates_panel, draw_progress_bar

class DataVisualizationUI:
    def __init__(self):
        self.coordinate_history = {
            'shoulder': deque(maxlen=100),
            'wrist': deque(maxlen=100)
        }
        self.performance_metrics = {
            'fps': 0,
            'detection_rate': 0,
            'network_latency': 0
        }
        
    def add_coordinate_data(self, shoulder, wrist):
        """Add new coordinate data to history"""
        self.coordinate_history['shoulder'].append(shoulder)
        self.coordinate_history['wrist'].append(wrist)
    
    def draw_coordinate_plot(self, frame, start_x, start_y, width, height):
        """Draw real-time coordinate plot"""
        plot_area = frame[start_y:start_y+height, start_x:start_x+width]
        plot_area.fill(0)  # Clear plot area
        
        if len(self.coordinate_history['wrist']) < 2:
            return
        
        # Draw coordinate traces
        points = []
        for i, coord in enumerate(self.coordinate_history['wrist']):
            if coord:
                x = int((i / len(self.coordinate_history['wrist'])) * width)
                y = int((1 - (coord[1] + 200) / 400) * height)  # Normalize Y coordinate
                points.append((start_x + x, start_y + y))
        
        # Draw connecting lines
        for i in range(1, len(points)):
            cv2.line(frame, points[i-1], points[i], (0, 255, 255), 2)
    
    def draw_performance_panel(self, frame, start_x, start_y):
        """Draw performance metrics panel"""
        y_offset = 0
        
        # FPS display
        cv2.putText(frame, f"FPS: {self.performance_metrics['fps']:.1f}", 
                   (start_x, start_y + y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
        y_offset += 30
        
        # Detection rate with progress bar
        cv2.putText(frame, "Detection Rate:", 
                   (start_x, start_y + y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        y_offset += 20
        draw_progress_bar(frame, start_x, start_y + y_offset, 150, 10, 
                         self.performance_metrics['detection_rate'], (0, 255, 0))
        y_offset += 25
        
        # Network latency
        latency_color = (0, 255, 0) if self.performance_metrics['network_latency'] < 50 else (255, 255, 0)
        cv2.putText(frame, f"Latency: {self.performance_metrics['network_latency']:.0f}ms", 
                   (start_x, start_y + y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, latency_color, 1)
    
    def update_performance(self, fps, detection_rate, network_latency):
        """Update performance metrics"""
        self.performance_metrics['fps'] = fps
        self.performance_metrics['detection_rate'] = detection_rate
        self.performance_metrics['network_latency'] = network_latency
```

### Custom Widget System
```python
#!/usr/bin/env python3
import cv2
import numpy as np
from abc import ABC, abstractmethod

class UIWidget(ABC):
    """Abstract base class for UI widgets"""
    
    def __init__(self, x, y, width, height):
        self.rect = (x, y, width, height)
        self.visible = True
        self.enabled = True
    
    @abstractmethod
    def draw(self, frame):
        """Draw the widget on the frame"""
        pass
    
    @abstractmethod
    def handle_mouse(self, event, x, y, flags, param):
        """Handle mouse events"""
        pass
    
    def contains_point(self, x, y):
        """Check if point is within widget bounds"""
        wx, wy, ww, wh = self.rect
        return wx <= x <= wx + ww and wy <= y <= wy + wh

class ToggleButton(UIWidget):
    """Toggle button widget"""
    
    def __init__(self, x, y, width, height, text, callback=None):
        super().__init__(x, y, width, height)
        self.text = text
        self.callback = callback
        self.state = False
        
    def draw(self, frame):
        if not self.visible:
            return
            
        x, y, w, h = self.rect
        color = (0, 255, 0) if self.state else (100, 100, 100)
        
        # Draw button background
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, -1)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
        
        # Draw text
        text_size = cv2.getTextSize(self.text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)[0]
        text_x = x + (w - text_size[0]) // 2
        text_y = y + (h + text_size[1]) // 2
        cv2.putText(frame, self.text, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    
    def handle_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and self.contains_point(x, y):
            if self.enabled:
                self.state = not self.state
                if self.callback:
                    self.callback(self.state)

class Slider(UIWidget):
    """Slider widget for numeric input"""
    
    def __init__(self, x, y, width, height, min_val, max_val, initial_val, callback=None):
        super().__init__(x, y, width, height)
        self.min_val = min_val
        self.max_val = max_val
        self.value = initial_val
        self.callback = callback
        self.dragging = False
        
    def draw(self, frame):
        if not self.visible:
            return
            
        x, y, w, h = self.rect
        
        # Draw slider track
        track_y = y + h // 2
        cv2.line(frame, (x, track_y), (x + w, track_y), (200, 200, 200), 3)
        
        # Draw slider handle
        handle_x = x + int((self.value - self.min_val) / (self.max_val - self.min_val) * w)
        cv2.circle(frame, (handle_x, track_y), 8, (0, 255, 255), -1)
        cv2.circle(frame, (handle_x, track_y), 8, (255, 255, 255), 2)
        
        # Draw value text
        value_text = f"{self.value:.1f}"
        cv2.putText(frame, value_text, (x, y - 5),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    def handle_mouse(self, event, x, y, flags, param):
        if not self.enabled:
            return
            
        if event == cv2.EVENT_LBUTTONDOWN and self.contains_point(x, y):
            self.dragging = True
        elif event == cv2.EVENT_LBUTTONUP:
            self.dragging = False
        elif event == cv2.EVENT_MOUSEMOVE and self.dragging:
            wx, wy, ww, wh = self.rect
            relative_x = max(0, min(ww, x - wx))
            self.value = self.min_val + (relative_x / ww) * (self.max_val - self.min_val)
            
            if self.callback:
                self.callback(self.value)

class UIManager:
    """Manager for multiple UI widgets"""
    
    def __init__(self):
        self.widgets = []
        
    def add_widget(self, widget):
        """Add widget to manager"""
        self.widgets.append(widget)
        
    def draw_all(self, frame):
        """Draw all widgets"""
        for widget in self.widgets:
            widget.draw(frame)
    
    def handle_mouse_event(self, event, x, y, flags, param):
        """Handle mouse events for all widgets"""
        for widget in self.widgets:
            widget.handle_mouse(event, x, y, flags, param)
```

## 🎨 Styling and Themes

### Color Schemes
```python
# Default color scheme
DEFAULT_COLORS = {
    'background': (0, 0, 0),
    'panel_bg': (40, 40, 40),
    'text': (255, 255, 255),
    'accent': (0, 255, 255),
    'success': (0, 255, 0),
    'warning': (255, 255, 0),
    'danger': (0, 0, 255),
    'disabled': (128, 128, 128)
}

# Dark theme
DARK_THEME = {
    'background': (25, 25, 25),
    'panel_bg': (50, 50, 50),
    'text': (220, 220, 220),
    'accent': (100, 200, 255),
    'success': (100, 255, 100),
    'warning': (255, 200, 100),
    'danger': (255, 100, 100),
    'disabled': (100, 100, 100)
}

def apply_theme(theme_colors):
    """Apply color theme to UI components"""
    global current_theme
    current_theme = theme_colors
```

### Typography
```python
# Font configurations
FONTS = {
    'title': {'font': cv2.FONT_HERSHEY_SIMPLEX, 'scale': 1.0, 'thickness': 2},
    'subtitle': {'font': cv2.FONT_HERSHEY_SIMPLEX, 'scale': 0.7, 'thickness': 2},
    'body': {'font': cv2.FONT_HERSHEY_SIMPLEX, 'scale': 0.5, 'thickness': 1},
    'button': {'font': cv2.FONT_HERSHEY_SIMPLEX, 'scale': 0.6, 'thickness': 2},
    'small': {'font': cv2.FONT_HERSHEY_SIMPLEX, 'scale': 0.4, 'thickness': 1}
}
```

## 🔧 Integration Examples

### Hand Tracking Integration
```python
from Pose_Tracking.Hand_Tracking import HandTracker
from UI.ui_components import create_ui_elements, draw_coordinates_panel

# Integrate UI with hand tracking
tracker = HandTracker()
ui_manager = UIManager()

# Add UI elements
ui_manager.add_widget(ToggleButton(50, 50, 100, 40, "Track", start_tracking))
ui_manager.add_widget(Slider(50, 100, 200, 30, 0.1, 1.0, 0.7, set_confidence))

while True:
    ret, frame = cap.read()
    results = tracker.process_frame(frame)
    
    # Create extended frame for UI
    ui_frame = np.zeros((frame.shape[0], frame.shape[1] + 300, 3), dtype=np.uint8)
    ui_frame[:, :frame.shape[1]] = frame
    
    # Draw coordinates panel
    if results['landmarks']:
        draw_coordinates_panel(ui_frame, frame.shape[1], 
                             results['landmarks'][0], results['landmarks'][8])
    
    # Draw UI widgets
    ui_manager.draw_all(ui_frame)
    
    cv2.imshow('Hand Tracking with UI', ui_frame)
```

### Robot Control Integration
```python
from robot_control import RobotController, get_connection_manager
from UI.ui_components import draw_status_panel, create_mouse_callback

# Setup robot and UI
connection = get_connection_manager("192.168.1.6")
controller = RobotController(connection)
ui_manager = UIManager()

# Add control widgets
ui_manager.add_widget(ToggleButton(50, 50, 120, 40, "Connect", toggle_connection))
ui_manager.add_widget(ToggleButton(50, 100, 120, 40, "Enable", toggle_robot))
ui_manager.add_widget(Slider(50, 150, 200, 30, 0.1, 1.0, 0.5, set_speed_factor))

def update_ui_with_robot_status():
    """Update UI with current robot status"""
    status = {
        'connected': connection.is_connected(),
        'enabled': controller.is_enabled(),
        'position': controller.get_position()[1] if controller.get_position()[0] else None
    }
    return status
```

---

## 📞 Support

For technical support with the UI components package:

1. **Display Issues**: Check OpenCV installation and video driver compatibility
2. **Mouse Events**: Verify mouse callback setup and coordinate calculations
3. **Performance**: Optimize drawing operations and reduce update frequency
4. **Integration**: Ensure proper import paths and dependency management

**Package Version**: 1.1.0 (Enhanced UI Components)  
**Last Updated**: June 6, 2025  
**Compatibility**: OpenCV 4.0+, NumPy 1.18+, Python 3.7+
