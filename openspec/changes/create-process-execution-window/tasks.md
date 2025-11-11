# Implementation Tasks: Create Process Execution Window

## Overview

This task list provides a dependency-ordered sequence for implementing the process execution window with visual guidance and inspection capabilities.

---

## Phase 1: Foundation & Window Shell

### Task 1.1: Create ProcessExecutionWindow class skeleton
**Description**: Create the main window class with basic layout structure
**Files**:
- Create `src/ui/windows/process_execution_window.py`
- Create `src/ui/windows/__init__.py`

**Acceptance**:
- [ ] ProcessExecutionWindow inherits from QWidget or QDialog
- [ ] Constructor accepts `process_data` dict parameter
- [ ] Window has fixed size 1800×900px
- [ ] Window has frameless hint and modal behavior
- [ ] Basic init_ui() method with placeholder layout
- [ ] Window can be instantiated without errors

**Estimated Effort**: 30 minutes

---

### Task 1.2: Implement header bar layout and widgets
**Description**: Build the top header bar with product info, progress, and operator details
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Header bar has 3-column layout (left/center/right)
- [ ] Left section shows product SN with Package icon
- [ ] Left section shows order number with FileText icon
- [ ] Center section shows "步骤: X / Y" text and progress bar
- [ ] Progress bar has correct dimensions and colors per spec
- [ ] Right section has "返回任务列表" button (outline orange)
- [ ] Right section has "产品实物图" button (blue background)
- [ ] Right section shows operator info with User icon
- [ ] Right section shows network status (hardcoded "在线" green)
- [ ] Header background is #252525 with bottom border

**Estimated Effort**: 1 hour

---

### Task 1.3: Implement bottom instruction footer layout
**Description**: Build the footer bar with current instruction and detection status
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Footer has 2-column layout (left instruction / right status)
- [ ] Left section shows "当前操作" label (gray, 12px)
- [ ] Left section shows step description (white, 20px)
- [ ] Right section has status indicator area (vertical layout)
- [ ] Status indicator can display: idle / pass / fail states
- [ ] Idle state shows gray circle + "等待检测" + orange button
- [ ] Pass state shows green circle with checkmark + "PASS"
- [ ] Fail state shows red circle with alert + "FAIL" (pulsing)
- [ ] Footer background is #252525 with top border

**Estimated Effort**: 1 hour

---

### Task 1.4: Connect ProcessCard button to launch window
**Description**: Wire the "启动工艺" button to open ProcessExecutionWindow
**Files**:
- Modify `src/ui/components/process_card.py`
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] ProcessCard emits signal when "启动工艺" clicked
- [ ] Signal carries process_data dict
- [ ] ProcessPage or MainWindow receives signal
- [ ] ProcessExecutionWindow is instantiated with process_data
- [ ] Window displays as modal dialog centered on screen
- [ ] Clicking "返回任务列表" closes window
- [ ] Window cleanup is proper (no memory leaks)

**Estimated Effort**: 45 minutes

---

## Phase 2: Step List Panel

### Task 2.1: Create step data structure and state management
**Description**: Define step data model and state tracking
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] ProcessStep dataclass or dict with: id, name, description, status
- [ ] StepStatus type: 'completed' | 'current' | 'pending'
- [ ] DetectionStatus type: 'idle' | 'detecting' | 'pass' | 'fail'
- [ ] Instance variables: steps list, current_step_id, detection_status
- [ ] Method to get current step: get_current_step() -> ProcessStep
- [ ] Method to update step status: set_step_status(step_id, status)
- [ ] Sample process data with 12 steps loaded on init

**Estimated Effort**: 30 minutes

---

### Task 2.2: Build step list panel UI structure
**Description**: Create left sidebar with scrollable step cards
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Step panel is fixed 288px width on left side
- [ ] Panel has title "工艺步骤" in header
- [ ] Panel uses QScrollArea for step cards
- [ ] Panel background is #1e1e1e with right border
- [ ] Each step renders as a card widget (QFrame)
- [ ] Step cards have status icon, name, and description
- [ ] Card layout matches design spec (vertical with icon left-aligned)

**Estimated Effort**: 1 hour

---

### Task 2.3: Implement step status visual styling
**Description**: Apply color schemes and icons based on step status
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Completed steps: green border, green checkmark, green text
- [ ] Current step: orange gradient bg, orange border, orange pulse dot
- [ ] Current step has shadow effect (shadow-lg shadow-orange-500/20)
- [ ] Pending steps: gray border, circle outline icon, gray text
- [ ] Step name font size 14px (sm)
- [ ] Step description font size 12px (xs)
- [ ] Hover effect on pending cards (border gray-500)
- [ ] All colors match hex codes from spec

**Estimated Effort**: 1 hour

---

### Task 2.4: Implement auto-scroll to current step
**Description**: Automatically scroll step list to center current step
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Method scroll_to_current_step() implemented
- [ ] Uses QScrollArea.ensureWidgetVisible() or equivalent
- [ ] Scroll behavior is smooth (animated)
- [ ] Current step positioned at vertical center of visible area
- [ ] Called when window opens (first step)
- [ ] Called when step changes (next/skip step)
- [ ] No jarring jumps or visual glitches

**Estimated Effort**: 30 minutes

---

## Phase 3: Visual Guidance Area

### Task 3.1: Create center visual area container
**Description**: Build the main center area for camera/image display
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Center area uses flex-1 to fill available space
- [ ] Area positioned between step panel and edges
- [ ] Background is dark (#1a1a1a)
- [ ] Container uses QLabel or QGraphicsView for image display
- [ ] PCB placeholder image loaded from resources or ref/ folder
- [ ] Image scales with object-cover (fills area, maintains aspect)
- [ ] Image opacity set to 80%
- [ ] Semi-transparent black overlay applied (bg-black/20)

**Estimated Effort**: 45 minutes

---

### Task 3.2: Implement guidance overlay box with animations
**Description**: Draw guidance box with border, corners, and label
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Guidance box positioned at center of visual area
- [ ] Box dimensions exactly 250×180px
- [ ] Box has 3px solid orange border (#f97316)
- [ ] Box has 10% orange background fill
- [ ] Four L-shaped corner markers at corners (w-5 h-5)
- [ ] Corner markers use 3px border, positioned outward by 1.5px
- [ ] Label "安装位置" positioned above box, centered
- [ ] Label has orange background, white text, padding, rounded
- [ ] Box has pulsing animation (animate-pulse equivalent)
- [ ] Overlay only visible when detection_status == 'idle'

**Estimated Effort**: 1.5 hours

---

### Task 3.3: Implement center crosshair lines
**Description**: Draw horizontal and vertical crosshair guidelines
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Horizontal line at vertical center of visual area
- [ ] Vertical line at horizontal center of visual area
- [ ] Lines cover 75% of area width/height respectively
- [ ] Line thickness is 1px
- [ ] Line color is orange (#f97316) at 40% opacity
- [ ] Lines only visible when detection_status == 'idle'
- [ ] Lines positioned using absolute positioning or custom paint

**Estimated Effort**: 45 minutes

---

### Task 3.4: Implement PASS detection overlay
**Description**: Create full-screen PASS result display
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Overlay covers entire visual area
- [ ] Background: green at 20% opacity (bg-green-500/20)
- [ ] Backdrop blur effect applied (QGraphicsBlurEffect or CSS)
- [ ] Large checkmark icon at center (w-24 h-24 equivalent ~96px)
- [ ] Text "PASS" below icon in green at 5xl size (~48px)
- [ ] Checkmark has pulsing animation
- [ ] Overlay only visible when detection_status == 'pass'
- [ ] Overlay auto-dismisses after 2 seconds with step advance

**Estimated Effort**: 45 minutes

---

### Task 3.5: Implement FAIL detection overlay with error card
**Description**: Create full-screen FAIL result display with retry options
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Overlay covers entire visual area
- [ ] Background: red at 20% opacity (bg-red-500/20)
- [ ] Backdrop blur effect applied
- [ ] Large alert icon at center (w-24 h-24)
- [ ] Text "FAIL" below icon in red at 5xl size
- [ ] Alert icon has pulsing animation
- [ ] Error card displayed below FAIL text
- [ ] Card has red background (20% opacity), 2px red border, rounded
- [ ] Card shows title "检测到缺陷" in red
- [ ] Card shows error details text (e.g., "未检测到元件" or "位置偏移")
- [ ] Card has "重新检测" button (bg-red-500)
- [ ] Card has "跳过" button (outline, border-red-500)
- [ ] Overlay only visible when detection_status == 'fail'

**Estimated Effort**: 1 hour

---

## Phase 4: Detection Workflow

### Task 4.1: Implement detection trigger logic
**Description**: Handle "开始检测" button click and state transitions
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] "开始检测 (演示)" button connected to slot
- [ ] Clicking button changes detection_status to 'detecting'
- [ ] Guidance overlay and crosshair hidden during detection
- [ ] QTimer starts 1.5 second delay
- [ ] After delay, status changes to 'pass' or 'fail' (random 70% pass)
- [ ] UI updates to show appropriate overlay (PASS/FAIL)
- [ ] Status indicator in footer updates correctly

**Estimated Effort**: 45 minutes

---

### Task 4.2: Implement auto-advance on PASS
**Description**: Automatically move to next step after successful detection
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] When detection_status becomes 'pass', QTimer starts 2s delay
- [ ] After delay, method advance_to_next_step() is called
- [ ] Current step status changes from 'current' to 'completed'
- [ ] Next step status changes from 'pending' to 'current'
- [ ] Step list scrolls to center new current step
- [ ] Detection status resets to 'idle'
- [ ] Instruction footer updates to show new step description
- [ ] Progress bar in header updates to reflect new step count
- [ ] PASS overlay disappears after transition

**Estimated Effort**: 1 hour

---

### Task 4.3: Implement retry and skip actions for FAIL
**Description**: Handle user actions when detection fails
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] "重新检测" button connected to slot on_retry_detection()
- [ ] on_retry_detection() resets detection_status to 'idle'
- [ ] FAIL overlay is hidden, guidance overlay reappears
- [ ] "跳过" button connected to slot on_skip_step()
- [ ] on_skip_step() marks current step as skipped (optional flag)
- [ ] on_skip_step() calls advance_to_next_step()
- [ ] Detection status resets to 'idle'
- [ ] No auto-advance timer on skip (manual action)

**Estimated Effort**: 45 minutes

---

### Task 4.4: Implement task completion dialog
**Description**: Show completion screen when all steps finished
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Method check_task_completion() checks if all steps completed
- [ ] If last step completes, show_completion_dialog() is called
- [ ] Dialog displays "任务完成" title with success styling
- [ ] Dialog shows summary: process name, total steps, duration (optional)
- [ ] Dialog has "开始下一个产品" button (primary, green)
- [ ] Dialog has "返回任务列表" button (secondary, outline)
- [ ] "开始下一个产品" resets window to first step (new product SN)
- [ ] "返回任务列表" closes window and returns to ProcessPage

**Estimated Effort**: 1 hour

---

## Phase 5: Polish & Integration

### Task 5.1: Add floating action menu button
**Description**: Create bottom-right floating button (placeholder functionality)
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Button positioned at bottom-right (bottom-4 right-4, ~16px margin)
- [ ] Button is circular (w-12 h-12, ~48px diameter)
- [ ] Button has orange gradient background (from-orange-500 to-orange-600)
- [ ] Button has shadow effect (shadow-2xl shadow-orange-500/50)
- [ ] Button z-index is 50 (above other elements)
- [ ] Menu icon (w-6 h-6) displayed in white
- [ ] Hover effect darkens gradient
- [ ] Clicking button shows placeholder message or tooltip
- [ ] Button does not interfere with other UI elements

**Estimated Effort**: 30 minutes

---

### Task 5.2: Implement product image dialog
**Description**: Show product reference image when button clicked
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] "产品实物图" button connected to slot on_show_product_image()
- [ ] Method creates QDialog with product image display
- [ ] Dialog shows product image (placeholder or loaded from data)
- [ ] Dialog shows product info: model, order number, SN, current step
- [ ] Dialog has close button or click-outside-to-close behavior
- [ ] Dialog is modal (blocks execution window interaction)
- [ ] Dialog is centered on screen
- [ ] Dialog has dark theme matching main window

**Estimated Effort**: 45 minutes

---

### Task 5.3: Add stylesheet and final styling polish
**Description**: Apply consistent styling, animations, and theme adherence
**Files**:
- Create or modify stylesheet for ProcessExecutionWindow
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] All colors match design spec hex codes exactly
- [ ] Font family is project's custom font (Arial fallback)
- [ ] Font sizes match spec (12px, 14px, 16px, 20px, 48px)
- [ ] Animations are smooth (pulse uses Qt or CSS animations)
- [ ] Hover states are clearly visible
- [ ] Button border-radius and padding match spec
- [ ] Spacing between elements is consistent (8px, 15px, 20px margins)
- [ ] Window background is #1a1a1a
- [ ] No visual glitches or alignment issues

**Estimated Effort**: 1 hour

---

### Task 5.4: Add comprehensive error handling
**Description**: Handle edge cases and error scenarios gracefully
**Files**:
- Modify `src/ui/windows/process_execution_window.py`

**Acceptance**:
- [ ] Handle missing or invalid process_data gracefully
- [ ] Handle empty step list (show error message)
- [ ] Handle camera service unavailable (fallback to static image)
- [ ] Handle timer cleanup on window close (prevent crashes)
- [ ] Add logging for key events (window open, step change, detection)
- [ ] Add try-except blocks around critical operations
- [ ] Validate step index bounds before accessing
- [ ] Provide user-friendly error messages (no raw exceptions)

**Estimated Effort**: 45 minutes

---

### Task 5.5: Manual end-to-end testing
**Description**: Validate full user workflow with manual testing
**Files**:
- N/A (testing task)

**Acceptance**:
- [ ] Window launches from ProcessCard button click
- [ ] First step is current, others are pending
- [ ] Guidance overlay displays correctly
- [ ] Detection trigger works and shows result
- [ ] PASS advances to next step after 2s
- [ ] FAIL shows error with retry/skip buttons
- [ ] Retry resets to idle state correctly
- [ ] Skip advances to next step immediately
- [ ] All steps can be completed sequentially
- [ ] Completion dialog displays on last step
- [ ] "返回任务列表" closes window cleanly
- [ ] Product image dialog works
- [ ] Floating menu button is visible and clickable
- [ ] Step list scrolls to current step smoothly
- [ ] No console errors or warnings
- [ ] No memory leaks (window closes properly)

**Estimated Effort**: 1 hour

---

## Phase 6: Optional Camera Integration (Future)

### Task 6.1: Integrate live camera preview
**Description**: Replace static image with live camera feed
**Files**:
- Modify `src/ui/windows/process_execution_window.py`
- Integrate with `src/camera/camera_service.py`

**Status**: DEFERRED (out of scope for initial implementation)

**Acceptance**:
- [ ] Check if camera_service is available
- [ ] Start camera preview on window open
- [ ] Display camera feed in visual guidance area
- [ ] Overlay guidance box on live feed
- [ ] Stop camera preview on window close
- [ ] Fallback to static image if camera unavailable

**Estimated Effort**: 2 hours

---

## Summary

**Total Tasks**: 21 (excluding optional camera integration)
**Total Estimated Effort**: ~18-20 hours
**Priority**: High (core user workflow)
**Dependencies**: ProcessCard, camera service (optional), main window integration

**Parallelizable Work**:
- Tasks 1.2 and 1.3 (header and footer) can be done in parallel
- Tasks 2.2 and 2.3 (step UI structure and styling) can overlap
- Tasks 3.4 and 3.5 (PASS and FAIL overlays) can be done in parallel
- Tasks 5.1 and 5.2 (floating button and product dialog) are independent

**Critical Path**:
1. Task 1.1 (window skeleton) → everything depends on this
2. Task 2.1 (state management) → all workflow logic depends on this
3. Task 4.1 (detection trigger) → Task 4.2 (auto-advance) → Task 4.3 (retry/skip)
