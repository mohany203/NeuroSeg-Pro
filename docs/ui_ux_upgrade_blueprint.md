# NeuroSeg Pro — UI/UX & Viewer Modernization Blueprint

## 1) High-priority issues observed in current app

### A. Layout and drawer behavior
1. **Main left navigation is a hard hide/show instead of a responsive/docked drawer**, which can cause unstable content reflow and poor small-screen behavior. The app currently hides the sidebar widget directly with no animated width policy, breakpoint behavior, or persisted collapsed state. (`toggle_sidebar()` with `hide()/show()`).
2. **Left navigation width is fixed at 260 px**, which reduces usable viewport area and does not adapt to window size (`setFixedWidth(260)`).
3. **Right control panel has a minimum width of 300 px with large interior margins**, increasing crowding risk in narrower windows and causing apparent overlap/truncation in dense states (`setMinimumWidth(300)`, margins `25,25,25,25`).
4. **Control stack order is awkward for long panels** because a stretch is inserted before the Navigation section, making scrolling and visual grouping less predictable (`self.control_layout.addStretch()` before Section 4).

### B. Comparison workflow / slice sync correctness
5. **In comparison mode, only axial slider updates both panes; sagittal/coronal slider updates can go stale** because `update_slice()` refreshes all views only when plane is axial.
6. **Recent-file loading always assumes MRI type**, which can mis-handle previously loaded masks/folders from history (`on_recent_file_clicked(..., 'mri')`).
7. **Model B placeholder labels are inconsistent**, increasing UX ambiguity (`"None (Single Model Mode)"` vs `"None (Single Model)"`).

### C. 3D viewer capability gap
8. **3D volume rendering is effectively a placeholder** (`pass` for volume data), so users do not get real volumetric MRI context.
9. **3D segmentation rendering is a single-color downsampled scatter cloud**, with no class-aware coloring, no mesh, no ground-truth/model toggles, no clipping planes, and no quantitative overlays.

### D. Metrics and explainability gaps
10. **Metrics table displays Dice only** although helper text references sensitivity/specificity/Hausdorff; this mismatch can confuse users and reduces trust.
11. **No per-class confidence/uncertainty visualization, no threshold sweep, no calibration plot, and no model-vs-model delta table**, despite comparison mode intent.

### E. Interaction and clarity gaps
12. **Legend behavior is mode-dependent and not fully explicit for all states**, especially when masks are missing or model B is absent.
13. **Crosshair mapping is manually inferred and brittle**, increasing risk of orientation confusion (especially with non-canonical affine orientations).
14. **Screenshot export saves only axial viewport by default**, not full multi-pane comparative layouts.

---

## 2) Feature expansion roadmap (professional-grade)

### Foundation (must-have)
- Responsive app shell with:
  - Collapsible left nav (expanded, icon-only, hidden)
  - Resizable right inspector with min/max constraints
  - Breakpoints for laptop/desktop/ultrawide
  - Persisted layout state (Qt settings)
- Deterministic viewport layout manager:
  - Grid presets (2x2, 3x2 compare, 1x3 strips, focus mode)
  - No overlap under any window width >= 1200
- Canonical orientation engine:
  - RAS/LPS handling
  - explicit orientation badges (A/P, R/L, S/I markers)

### Clinical comparison & explainability
- True **multi-model workspace**:
  - Compare N models (not only A/B)
  - Baseline pinning
  - Pairwise and aggregate ranking
- Comparison modes:
  - Checkerboard, swipe, split, blink, XOR/difference heatmap
  - TP/FP/FN class-specific overlay controls
- Metrics:
  - Dice, IoU, Precision, Recall, Specificity, HD95, ASSD, Volume Error
  - per-class + whole tumor + confidence intervals
  - table + sparkline trend + export CSV/JSON

### 3D viewer next level
- Real 3D rendering stack:
  - MRI volume ray casting
  - Segmentation isosurface extraction (marching cubes)
  - class-specific opacity and color LUT
  - synchronized 2D/3D crosshair and linked camera presets
- Advanced controls:
  - clipping planes (axial/sagittal/coronal)
  - ROI box tool
  - class visibility matrix
  - lighting/shading presets (clinical, contrast, print)

### Productivity and professionalism
- Workspace presets (Radiologist, ML Engineer, Reviewer)
- Session timeline (all runs, model versions, metrics snapshots)
- Reproducibility metadata panel (model hash, preprocessing hash, spacing, orientation)
- Report generator (PDF/HTML): images + metrics + method card + signoff

---

## 3) Detailed prompt to give your coding agent

Use the prompt below as-is.

```text
You are a senior medical-imaging product engineer. Implement a production-grade UI/UX overhaul and 3D visualization upgrade for NeuroSeg Pro (PyQt5 + pyqtgraph stack) while preserving existing inference flows.

## Product objective
Transform the app into a robust, professional, clinically legible segmentation analysis workstation.
Primary outcomes:
1) Zero layout overlap/truncation in normal desktop ranges.
2) High-confidence model-vs-ground-truth and model-vs-model comparison workflows.
3) Advanced, performant 3D viewing with clear class semantics.
4) Measurable usability and reliability improvements with tests.

## Non-functional constraints
- Keep existing inference interfaces stable unless absolutely necessary.
- Maintain backward compatibility for current settings and model registration where possible.
- Avoid blocking UI thread during heavy rendering/inference.
- Ensure memory-safe behavior with large NIfTI volumes.
- Add feature flags for experimental modules.

## Architecture tasks
1. Introduce a responsive layout manager layer:
   - Replace ad-hoc hide/show sidebar with stateful drawer controller:
     states = {expanded, collapsed-icons, hidden}
   - Persist state in settings.
   - Add window-resize breakpoints with deterministic panel min/max widths.
   - Enforce splitter constraints so no panel overlaps another.

2. Refactor viewer into modular components:
   - ViewportManager (2D panes, sync, orientation markers)
   - OverlayManager (mask composition, LUT, opacity, blending mode)
   - ComparisonEngine (A/B/N comparisons, diff maps, TP/FP/FN)
   - MetricsEngine UI adapter (table + chart model)
   - Viewer3DController (volume + surface + scatter fallback)

3. Standardize data contracts:
   - Create typed structures for:
     VolumeData, SegmentationMask, ModelRunResult, MetricsBundle.
   - Explicitly carry spacing, affine, orientation labels.
   - Add validation utilities and user-facing error messages.

## UI/UX implementation details
1. Shell and drawers
   - Left nav:
     - animated width transitions
     - compact icon mode with tooltips
   - Right inspector:
     - tabbed groups: Analysis, Overlays, Metrics, Export
     - sticky run controls at top
     - sticky slice controls at bottom
   - Add command palette (Ctrl/Cmd+K) for actions.

2. 2D viewports
   - Add orientation tags (R/L/A/P/S/I) in each pane corner.
   - Add scale bar and voxel coordinate readout.
   - Fully synchronized crosshair for axial/sagittal/coronal in all modes.
   - Add viewport presets and one-click reset camera/zoom.

3. Overlay system
   - Implement class LUT editor (with reset defaults).
   - Add blending modes: alpha, additive, multiply, outline-only.
   - Independent opacity sliders per class and per source (A, B, GT).
   - Missing-data states must show clear neutral UI badges.

4. Comparison modes
   - Support:
     - Model A vs GT
     - Model B vs GT
     - A vs B
     - A vs B vs GT (tri-compare)
   - Visual methods:
     - split slider
     - checkerboard
     - blink
     - TP/FP/FN map with legend and counts
   - Keep titles and legends always synchronized with active mode.

5. Metrics & analytics
   - Extend metrics table columns:
     Dice, IoU, Precision, Recall, Specificity, HD95, ASSD, Volume(ml), ΔVolume.
   - Add class rows: NCR, ED, ET, WT.
   - Add mini charts:
     - per-class bar chart for A/B/GT deltas
     - trend chart across runs
   - Add CSV/JSON export for metrics and overlay counts.

## 3D viewer overhaul
1. Rendering
   - Replace placeholder 3D volume code with actual rendering pipeline.
   - Implement:
     - MRI volume rendering (ray-march or slice stack fallback)
     - Segmentation surfaces via marching cubes
     - class-wise mesh coloring
   - Keep a fallback low-memory mode.

2. Controls
   - Camera presets: axial, sagittal, coronal, iso-left, iso-right.
   - Lighting controls: ambient/diffuse/specular sliders.
   - Clip planes linked to 2D slice sliders.
   - Toggle visibility for MRI volume / A / B / GT / diff surface.

3. Performance
   - Cache generated meshes by (mask_hash, class, threshold).
   - Debounce high-frequency UI events.
   - Background thread for mesh generation and metric-heavy ops.

## Reliability & QA
1. Add automated checks:
   - layout integrity tests (no overlapping widgets at key widths)
   - slice-sync tests across all 3 planes in compare mode
   - legend-title consistency tests
   - metrics-calculation smoke tests for A-only, A+B, A+GT, A+B+GT
2. Add manual QA script:
   - scenario-based checklist for loading modalities, inference, compare, export.
3. Add telemetry hooks (local logs only):
   - inference duration
   - rendering FPS snapshots
   - memory warnings

## Migration + rollout
- Phase 1: Fix critical layout and sync bugs first.
- Phase 2: Metrics and comparison expansion.
- Phase 3: Advanced 3D rendering and performance optimization.
- Provide changelog and user-facing help updates per phase.

## Acceptance criteria
- No visual overlap in left/right drawers and no clipped controls at 1280x800 and above.
- Comparison mode updates all panes correctly for axial/sagittal/coronal slider moves.
- 3D panel supports class-aware rendering and synchronized clip planes.
- Metrics panel shows expanded metrics with export.
- User can clearly interpret colors/legends in every mode.
- App remains responsive during inference and 3D updates.

Deliverables:
- Refactored code modules
- Updated settings schema + migration code
- Tests and QA checklist
- Demo screenshots for each major mode
- Technical notes on performance tradeoffs and fallback behavior
```

---

## 4) Implementation order recommendation

1. **Stability first**: layout/splitter/drawer + compare sync bug fixes.
2. **Trust layer**: legend, metrics consistency, explicit states for missing data.
3. **Clinical comparison layer**: richer A/B/GT workflows and exports.
4. **3D advancement**: rendering pipeline and performance tuning.
5. **Polish**: presets, command palette, report generation.

