# Capability: Process Execution UI

## Overview

The Process Execution UI capability provides operators with a dedicated interface for executing manufacturing processes with real-time visual guidance, step-by-step navigation, and automated inspection feedback.

---

## ADDED Requirements

### Requirement: Launch process execution window

The system SHALL provide a mechanism to launch the process execution interface from the process information page.

#### Scenario: Start process from process card

**GIVEN** the user is viewing the Process Information page
**AND** a process card displays a process in "active" status
**WHEN** the user clicks the "启动工艺" (Start Process) button on the card
**THEN** the system shall open a new ProcessExecutionWindow as a modal dialog
**AND** the window shall display the first step of the selected process as "current"
**AND** all subsequent steps shall display as "pending"
**AND** the window shall load the process name, version, and step data from the process card

#### Scenario: Window initialization with product data

**GIVEN** the process execution window is launching
**WHEN** the window initializes
**THEN** the header shall display product SN "SN-2025-VM-00123"
**AND** the header shall display order number "ME-ASM-2024-001"
**AND** the header shall display operator name "张三 (A01)"
**AND** the header shall display network status as "在线" (online) with green color
**AND** the window size shall be fixed at 1800px width × 900px height

---

### Requirement: Display process steps list

The system SHALL provide a left sidebar panel showing all process steps with visual status indicators.

#### Scenario: Render step list on window load

**GIVEN** the process execution window has opened
**WHEN** the step list panel renders
**THEN** each step shall display as a card with step name and description
**AND** the first step shall have status "current" with orange gradient background
**AND** all other steps shall have status "pending" with gray background
**AND** the current step card shall display an orange pulsing dot icon
**AND** pending step cards shall display a gray circle outline icon
**AND** the panel width shall be fixed at 288px

#### Scenario: Current step is visible and centered

**GIVEN** the step list contains more steps than fit in viewport
**WHEN** the window loads or current step changes
**THEN** the step list shall automatically scroll to bring the current step into view
**AND** the current step card shall be positioned at vertical center of the scrollable area
**AND** the scroll animation shall use smooth behavior

#### Scenario: Step status visual differentiation

**GIVEN** a step list with mixed statuses
**WHEN** steps are rendered
**THEN** completed steps shall have green border (#22c55e) and green checkmark icon
**AND** current step shall have orange border (#f97316) with 20% opacity gradient background
**AND** current step shall have subtle shadow effect (shadow-lg shadow-orange-500/20)
**AND** pending steps shall have gray border (#3a3a3a) and circle outline icon
**AND** step name text color shall match status (orange/green/gray)

---

### Requirement: Display visual guidance area

The system SHALL provide a central area showing camera feed or PCB image with visual guidance overlays.

#### Scenario: Render guidance overlay in idle state

**GIVEN** the process execution window is open
**AND** the detection status is "idle" (not detecting, no result)
**WHEN** the visual guidance area renders
**THEN** a guidance box shall be displayed at center of the visual area
**AND** the box dimensions shall be 250px width × 180px height
**AND** the box shall have 3px solid orange border (#f97316)
**AND** the box shall have 10% orange background (bg-orange-500/10)
**AND** the box shall have pulsing animation (animate-pulse)
**AND** four L-shaped corner markers shall be rendered at box corners
**AND** a label "安装位置" shall be displayed above the box center

#### Scenario: Display PCB background image

**GIVEN** the visual guidance area is rendering
**WHEN** camera service is unavailable or in demo mode
**THEN** a PCB image shall be displayed as background
**AND** the image shall use object-cover scaling to fill the area
**AND** the image opacity shall be 80% (opacity-80)
**AND** a semi-transparent black overlay (bg-black/20) shall be applied

#### Scenario: Display center crosshair

**GIVEN** the visual guidance area is rendering
**WHEN** detection status is "idle"
**THEN** a horizontal crosshair line shall be rendered at vertical center
**AND** a vertical crosshair line shall be rendered at horizontal center
**AND** crosshair lines shall cover 75% of the area dimensions
**AND** crosshair color shall be orange (#f97316) at 40% opacity
**AND** crosshair line thickness shall be 1px

---

### Requirement: Display current operation instructions

The system SHALL provide a bottom footer displaying the current step instruction and detection controls.

#### Scenario: Show current step instruction

**GIVEN** the process execution window is open
**AND** a step is marked as "current"
**WHEN** the instruction footer renders
**THEN** the label "当前操作" shall be displayed in gray (#9ca3af) at 12px size
**AND** the current step description shall be displayed in white at 20px size
**AND** the instruction text shall be left-aligned in the footer

#### Scenario: Display detection idle state controls

**GIVEN** the detection status is "idle"
**WHEN** the status indicator area renders
**THEN** a circular indicator icon shall be displayed (w-20 h-20)
**AND** the icon shall be a gray circle (bg-gray-700)
**AND** below the icon, text "等待检测" shall be displayed in gray
**AND** a button "开始检测 (演示)" shall be displayed
**AND** the button shall have orange background (bg-orange-500)
**AND** the button shall trigger detection workflow when clicked

#### Scenario: Display detection pass state

**GIVEN** the detection status is "pass"
**WHEN** the status indicator area renders
**THEN** a circular indicator icon shall be displayed (w-20 h-20)
**AND** the icon shall have green background (bg-green-500) with shadow
**AND** a white checkmark icon shall be displayed inside the circle
**AND** below the icon, text "PASS" shall be displayed in green (#22c55e)

#### Scenario: Display detection fail state

**GIVEN** the detection status is "fail"
**WHEN** the status indicator area renders
**THEN** a circular indicator icon shall be displayed (w-20 h-20)
**AND** the icon shall have red background (bg-red-500) with shadow
**AND** the icon shall have pulsing animation (animate-pulse)
**AND** an alert icon shall be displayed inside the circle
**AND** below the icon, text "FAIL" shall be displayed in red (#ef4444)

---

### Requirement: Implement inspection detection workflow

The system SHALL support a simulated inspection workflow with visual feedback for pass/fail results.

#### Scenario: Trigger inspection detection

**GIVEN** the detection status is "idle"
**AND** the "开始检测 (演示)" button is visible
**WHEN** the user clicks the detection button
**THEN** the detection status shall change to "detecting"
**AND** the guidance overlay shall be hidden
**AND** after 1.5 seconds delay, the status shall change to either "pass" or "fail"
**AND** the result shall be randomly determined for demo purposes

#### Scenario: Display PASS result overlay

**GIVEN** the detection status changes to "pass"
**WHEN** the visual guidance area renders
**THEN** a full-screen overlay shall be displayed covering the visual area
**AND** the overlay background shall be green at 20% opacity (bg-green-500/20)
**AND** backdrop blur effect shall be applied (backdrop-blur-sm)
**AND** a large checkmark icon (w-24 h-24) shall be displayed at center
**AND** text "PASS" shall be displayed in green at 5xl size
**AND** the checkmark icon shall have pulsing animation
**AND** after 2 seconds, the system shall auto-advance to the next step

#### Scenario: Display FAIL result overlay

**GIVEN** the detection status changes to "fail"
**WHEN** the visual guidance area renders
**THEN** a full-screen overlay shall be displayed covering the visual area
**AND** the overlay background shall be red at 20% opacity (bg-red-500/20)
**AND** backdrop blur effect shall be applied
**AND** a large alert icon (w-24 h-24) shall be displayed at center
**AND** text "FAIL" shall be displayed in red at 5xl size
**AND** the alert icon shall have pulsing animation

#### Scenario: Handle inspection failure with options

**GIVEN** the detection status is "fail"
**WHEN** the error overlay is displayed
**THEN** an error card shall be shown below the FAIL indicator
**AND** the card shall have red background at 20% opacity
**AND** the card shall have 2px red border
**AND** the card title "检测到缺陷" shall be displayed in red
**AND** error details text shall be displayed
**AND** a "重新检测" button shall be provided (bg-red-500)
**AND** a "跳过" button shall be provided (outline style)
**AND** clicking "重新检测" shall reset status to "idle"
**AND** clicking "跳过" shall advance to next step

---

### Requirement: Navigate between process steps

The system SHALL support sequential navigation through process steps with status updates.

#### Scenario: Auto-advance to next step on pass

**GIVEN** the current step index is N (not the last step)
**AND** detection result is "pass"
**WHEN** 2 seconds have elapsed after pass result displayed
**THEN** step N status shall change from "current" to "completed"
**AND** step N+1 status shall change from "pending" to "current"
**AND** the step list shall scroll to center step N+1
**AND** the detection status shall reset to "idle"
**AND** the instruction footer shall update to show step N+1 description

#### Scenario: Manual skip to next step

**GIVEN** the current step index is N (not the last step)
**AND** detection result is "fail"
**WHEN** the user clicks "跳过" button
**THEN** step N status shall remain "current" but marked as skipped
**AND** step N+1 status shall change to "current"
**AND** the step list shall scroll to center step N+1
**AND** the detection status shall reset to "idle"

#### Scenario: Complete all steps

**GIVEN** the current step is the last step in the process
**AND** detection result is "pass"
**WHEN** the auto-advance timer expires
**THEN** the last step status shall change to "completed"
**AND** a task completion dialog shall be displayed
**AND** the dialog shall show "任务完成" title
**AND** the dialog shall provide "开始下一个产品" button
**AND** the dialog shall provide "返回任务列表" button

---

### Requirement: Display header information bar

The system SHALL provide a top header bar with product information, operator details, and status indicators.

#### Scenario: Render product information

**GIVEN** the process execution window is open
**WHEN** the header bar renders
**THEN** product SN shall be displayed with Package icon (orange, w-4 h-4)
**AND** the label "产品 SN" shall be in gray at 12px size
**AND** the SN value shall be in white at 14px size
**AND** order number shall be displayed with FileText icon
**AND** a vertical separator line shall divide product info from progress

#### Scenario: Render step progress indicator

**GIVEN** the current step is N out of total M steps
**WHEN** the header progress section renders
**THEN** text "步骤: N / M" shall be displayed in white at 14px
**AND** a progress bar shall be rendered below the text
**AND** the progress bar height shall be 6px (h-1.5)
**AND** the progress bar background shall be dark gray (#3a3a3a)
**AND** the filled portion shall be orange gradient
**AND** the fill percentage shall be (N / M) * 100%

#### Scenario: Display operator information and network status

**GIVEN** the header bar is rendering
**WHEN** the right section renders
**THEN** a "返回任务列表" button shall be displayed (outline style)
**AND** the button shall have orange border and orange text
**AND** a "产品实物图" button shall be displayed (bg-blue-500)
**AND** operator info shall show User icon with "张三 (A01)" text
**AND** network status shall show Wifi icon in green with "在线" text
**AND** if network is offline, WifiOff icon in red with "离线" text

---

### Requirement: Provide floating action menu

The system SHALL provide a floating button for accessing additional actions.

#### Scenario: Render floating menu button

**GIVEN** the process execution window is open
**WHEN** the floating menu button renders
**THEN** the button shall be positioned at bottom-right corner (bottom-4 right-4)
**AND** the button shall be circular (w-12 h-12, rounded-full)
**AND** the button background shall be orange gradient (from-orange-500 to-orange-600)
**AND** the button shall have shadow effect (shadow-2xl shadow-orange-500/50)
**AND** the button z-index shall be 50
**AND** a Menu icon (w-6 h-6) shall be displayed in white
**AND** on hover, gradient shall change to darker shades

---

### Requirement: Handle window lifecycle

The system SHALL properly manage window creation, display, and cleanup.

#### Scenario: Open window as modal dialog

**GIVEN** the user clicks "启动工艺" on a process card
**WHEN** the ProcessExecutionWindow is created
**THEN** the window shall be displayed as a modal dialog
**AND** the window shall block interaction with the parent main window
**AND** the window shall be centered on screen
**AND** the window shall have frameless window hint (Qt.FramelessWindowHint)

#### Scenario: Close window and cleanup

**GIVEN** the process execution window is open
**WHEN** the user closes the window or clicks "返回任务列表"
**THEN** the window shall close gracefully
**AND** the camera preview shall be stopped if active
**AND** all timers shall be stopped and cleaned up
**AND** the parent main window shall regain focus
**AND** window instance shall be destroyed to free memory

---

## Technical Constraints

- **Window Size**: Fixed at 1800×900px (requires minimum 1920×1080 display)
- **Color Accuracy**: Must match design spec hex codes exactly
- **Font System**: Must use project's custom font (Arial fallback)
- **Animation Performance**: Pulse animations should maintain 60fps
- **Memory Management**: Must properly cleanup timers and camera resources on close
- **Modal Behavior**: Must block parent window interaction while open

---

## Dependencies

- **PySide6 Widgets**: QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
- **PySide6 Core**: Qt, Signal, QTimer, QRect
- **Camera Service**: Optional integration for live preview (fallback to static image)
- **Process Card**: Signal/slot connection for button click event

---

## Future Enhancements (Out of Scope)

- Multi-camera view switching
- Real-time inspection parameter adjustment
- Historical inspection data logging
- Voice guidance audio feedback
- Defect annotation on images
- Keyboard shortcuts for navigation
- Advanced statistics dashboard
