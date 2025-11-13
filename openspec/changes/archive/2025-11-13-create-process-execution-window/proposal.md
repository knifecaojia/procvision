# Proposal: Create Process Execution Window

## Overview

Add a dedicated process execution window that provides visual guidance and inspection capabilities for manufacturing operators. This window enables step-by-step process execution with real-time camera feeds, AI-powered inspection, and interactive visual guidance overlays.

## Context

The application currently has a Process Information page (`ProcessPage`) that displays process cards with basic information. Each process card has a "启动工艺" (Start Process) button, but clicking it has no functionality. This proposal adds the complete process execution workflow that operators will use to perform actual manufacturing tasks with visual guidance.

## Motivation

**Business Need:**
- Operators need real-time visual guidance during assembly tasks
- Manual inspection is error-prone and inconsistent
- Current system lacks interactive execution capabilities
- Quality control requires automated defect detection with visual feedback

**User Value:**
- Step-by-step visual guidance reduces assembly errors
- Real-time inspection feedback improves quality
- Clear status indicators enhance operator confidence
- Automated detection accelerates inspection workflow

**Technical Benefits:**
- Integrates existing camera infrastructure with process execution
- Modular architecture allows independent testing of visual guidance components
- Reusable inspection state machine can support multiple detection backends
- Clean separation between UI and business logic

## Goals

1. **Primary**: Create a fully functional process execution window with visual guidance
2. **Primary**: Implement step-by-step process navigation with status tracking
3. **Primary**: Integrate camera preview with visual guidance overlays
4. **Secondary**: Support inspection workflow with pass/fail detection
5. **Secondary**: Provide operator information and network status display

## Non-Goals

- Multi-camera switching (single camera view only in this phase)
- Historical inspection data persistence (future enhancement)
- Voice guidance or audio feedback
- Defect position annotation on images
- Real-time inspection parameter adjustment
- Advanced statistics or analytics dashboard

## Proposed Solution

### Architecture

```
ProcessCard (existing)
    └─> [Start Process Button] ─┐
                                  │
                                  v
                        ProcessExecutionWindow (new)
                            │
                            ├─> Header Bar (product info, operator, network status)
                            ├─> Step List Panel (left sidebar)
                            ├─> Visual Guidance Area (center, camera + overlays)
                            ├─> Instruction Footer (current operation + status)
                            └─> Floating Action Menu
```

### Key Components

1. **ProcessExecutionWindow**: Main window container (1800×900px fixed size)
2. **StepListPanel**: Left sidebar showing process steps with status indicators
3. **VisualGuidanceArea**: Center area with camera feed and guidance overlays
4. **InstructionFooter**: Bottom bar with current instruction and detection controls
5. **HeaderBar**: Top bar with product info, operator details, network status

### User Flow

1. User clicks "启动工艺" on a process card
2. System opens ProcessExecutionWindow with process data
3. Window displays first step as "current" with guidance overlay
4. User performs assembly action following visual guidance
5. User initiates inspection (manual trigger for demo)
6. System shows detection result (PASS/FAIL overlay)
7. On PASS: auto-advance to next step after 2s delay
8. On FAIL: display error details with retry/skip options
9. Repeat steps 4-8 until all steps completed
10. Show completion dialog with "Next Product" / "Return to List" options

### Visual Design Adherence

Following `ref/process_flow_design.md` specifications:
- **Color System**: Deep gray background (#1a1a1a), orange accents (#f97316), status colors (green/red)
- **Layout**: Fixed 1800×900px with header/content/footer structure
- **Step Cards**: Current step has orange gradient with pulse animation
- **Guidance Overlay**: 250×180px orange border box with corner markers and label
- **Detection Feedback**: Full-screen overlay with large PASS/FAIL indicator
- **Typography**: White primary text, gray-400 secondary, consistent sizing

### State Management

```python
StepStatus = Literal['completed', 'current', 'pending']
DetectionStatus = Literal['idle', 'detecting', 'pass', 'fail']
NetworkStatus = Literal['online', 'offline']

class ProcessExecutionState:
    process_data: dict  # Process metadata
    steps: List[ProcessStep]  # All process steps
    current_step_id: int  # Current step index
    detection_status: DetectionStatus
    network_status: NetworkStatus
    operator_name: str
    product_sn: str
```

## Dependencies

**Internal:**
- `src/ui/components/process_card.py`: Connect "Start Process" button to new window
- `src/camera/camera_service.py`: Camera preview integration (if available)
- `src/ui/main_window.py`: Parent window reference for modal behavior

**External:**
- PySide6: Qt widgets, layouts, signals
- Python 3.8+: Type hints, dataclasses

## Implementation Phases

### Phase 1: Window Shell & Navigation (Minimal Viable Product)
- Create ProcessExecutionWindow with fixed layout
- Implement step list panel with status rendering
- Add header bar with static info display
- Connect to ProcessCard button click
- Basic window show/hide and cleanup

### Phase 2: Visual Guidance System
- Integrate camera preview in center area
- Implement guidance overlay with positioning
- Add crosshair and corner markers
- Implement smooth step scrolling

### Phase 3: Inspection Workflow
- Add detection trigger button
- Implement detection state machine (idle→detecting→pass/fail)
- Create PASS/FAIL overlay UI
- Add error dialog with retry/skip actions
- Implement auto-advance on pass

### Phase 4: Polish & Integration
- Add floating action menu
- Implement product image dialog
- Add completion screen
- Improve animations and transitions
- Network status monitoring

## Testing Strategy

**Unit Testing:**
- Step status calculation logic
- State machine transitions (detection flow)
- Window lifecycle (show, close, cleanup)

**Integration Testing:**
- ProcessCard button → window launch
- Step navigation and scrolling
- Camera preview rendering (if camera available)

**Manual Testing:**
- Full process execution flow end-to-end
- Visual guidance overlay positioning
- Inspection pass/fail workflows
- UI responsiveness and animations

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Camera service unavailable | High | Use placeholder image, graceful degradation |
| Fixed window size too large for displays | Medium | Document minimum resolution requirement (1920×1080) |
| Complex state management bugs | Medium | Comprehensive state machine unit tests |
| Performance issues with overlays | Low | Use simple geometric shapes, avoid complex rendering |

## Alternatives Considered

1. **Embedded in Main Window**: Rejected due to complexity and competing navigation concerns
2. **Multi-camera support in v1**: Deferred to keep scope manageable
3. **Real-time inspection backend**: Simulated detection acceptable for UI development

## Success Metrics

- [ ] ProcessExecutionWindow launches from ProcessCard button click
- [ ] All process steps display with correct status indicators
- [ ] Visual guidance overlay renders at correct position
- [ ] Inspection workflow completes pass/fail cycles
- [ ] Window closes cleanly without memory leaks
- [ ] UI matches design specification within 95% accuracy

## Open Questions

1. Should window be modal or modeless? **Decision: Modal for operator focus**
2. Camera fallback strategy? **Decision: Use PCB placeholder image**
3. Detection timing configuration? **Decision: Hardcoded 1.5s delay for demo**

---

**Proposal Status**: Draft
**Created**: 2025-11-11
**Author**: AI Assistant
