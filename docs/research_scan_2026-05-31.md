# Research Scan, 2026-05-31

Intended reader: Yifan Yang and future collaborators who want a practical open-source sports-AI project before deciding whether this becomes a product.

## Short Answer

The best first project is a golf-first, sport-extensible posture analysis toolkit. Use off-the-shelf pose estimation for the first milestone, then add golf event segmentation and interpretable motion metrics. Keep basketball as a second sport profile that reuses the same core pipeline.

This is the right order because golf has mature event labels and public baselines, while basketball shooting form has clear commercial demand but less open posture-control infrastructure.

## Technology Landscape

| Layer | Current signal | Project implication |
| --- | --- | --- |
| 2D or pseudo-3D pose | MediaPipe Pose Landmarker outputs normalized image landmarks and world landmarks, with a 33-landmark body model optimized for on-device use. Source: https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker | Use MediaPipe as the first backend because it is easy to run on personal videos and gives enough landmarks for elbow, knee, hip, shoulder, and ankle metrics. |
| Real-time keypoint detection | Ultralytics YOLO pose models expose COCO-style 17-keypoint human pose checkpoints and fine-tuning workflow. Source: https://docs.ultralytics.com/tasks/pose/ | Use YOLO pose as a second backend when detection robustness or custom training matters. |
| Research-grade pose toolkit | MMPose provides a broad pose-estimation toolkit and model zoo. Source: https://mmpose.readthedocs.io/en/latest/ | Use MMPose when experiments need reproducible benchmarks, RTMPose models, or custom datasets. |
| Sports kinematics | Sports2D computes 2D keypoint trajectories and joint or segment angles from video or webcam. Source: https://github.com/davidpagnon/Sports2D | Treat Sports2D as a reference for angle outputs and sports-biomechanics vocabulary. |
| 3D markerless kinematics | Pose2Sim supports markerless 3D kinematics from multiple cameras and points users to Sports2D for real-time single-camera analysis. Source: https://github.com/perfanalytics/pose2sim | Keep 3D reconstruction as a later milestone. The MVP should not pretend that one phone video gives full laboratory-grade 3D truth. |

## Golf Research Signals

GolfDB is the key open baseline. It frames golf swing sequencing as detection of eight events in trimmed swing videos and provides SwingNet as a PyTorch baseline. Source: https://github.com/wmcnally/golfdb and https://arxiv.org/abs/1903.06528.

CaddieSet is the most relevant recent signal for where the field is moving. It combines joint information with ball information from a single shot, segments swings into eight phases, and defines 15 expert-informed swing metrics. Source: https://openaccess.thecvf.com/content/CVPR2025W/CVSPORTS/papers/Jung_CaddieSet_A_Golf_Swing_Dataset_with_Human_Joint_Features_and_CVPRW_2025_paper.pdf.

Commercial golf tools suggest users want three things:

1. Automatic swing recording and phase analysis.
2. Clear issue labels and drill suggestions.
3. Swing comparison across sessions.

GolfFix describes AI swing analysis reports with posture issues, causes, correction solutions, and focus drills. Source: https://notice.golffix.io/en/guide/analysis.

Sportsbox AI markets single-phone-video 3D swing visualization and biomechanical measurements. Source: https://sportsbox.ai/.

## Basketball Research Signals

BASKET shows that basketball skill estimation is now a serious large-scale video understanding problem. The dataset covers more than 4,400 hours of video, more than 32,000 basketball players, and 20 fine-grained skills including shooting. Source: https://openaccess.thecvf.com/content/CVPR2025/papers/Pan_BASKET_A_Large-Scale_Video_Dataset_for_Fine-Grained_Skill_Estimation_CVPR_2025_paper.pdf.

Commercial basketball tools focus on shot form analysis, joint angles, release point, shot arc, progress tracking, and personalized drill recommendations. ShotIQ, for example, presents a MediaPipe-based shooting-analysis workflow with 12+ biomechanical measurements. Source: https://shotiqai.com/.

This suggests a practical basketball extension:

1. Start with own-best-shot comparison.
2. Add phase-specific metrics around release and follow-through.
3. Add ball tracking only after the human-pose pipeline is stable.

## Recommended First Product Requirement

Build a reproducible research prototype named SwingForm AI:

1. Single-person video input.
2. Pose extraction with MediaPipe first.
3. Golf swing phase scaffold based on GolfDB-style events.
4. Interpretable metrics from landmarks.
5. Local-only personal video policy.
6. A small report generator for practice sessions.
7. Clean sport profile abstraction for basketball.

## What Not To Do Yet

Do not build a full mobile app first. It would hide the research logic behind UI decisions too early.

Do not promise launch-monitor metrics such as true club speed, spin rate, or carry distance from one RGB video without validation data.

Do not publish personal swing videos in the repo. Use synthetic samples or public datasets with clear licenses.

Do not make AI feedback sound like medical, injury, or certified coaching advice.

## MVP Success Criteria

The MVP is successful when one local swing video can produce:

1. A pose overlay or exported landmark JSON.
2. A coarse phase timeline.
3. A table of interpretable metrics.
4. A concise feedback report.
5. A reproducible command that another collaborator can run.
