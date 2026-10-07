import 'package:flutter/material.dart';
import '../models/player.dart';

/// Canvas painter that renders player bounding boxes, motion trails, and 17-keypoint skeletons
class PlayerOverlayPainter extends CustomPainter {
  final List<PlayerTrack> players;
  final int videoWidth;
  final int videoHeight;
  final bool showBoxes;
  final bool showTrails;
  final bool showSkeleton;

  PlayerOverlayPainter({
    required this.players,
    this.videoWidth = 1280,
    this.videoHeight = 720,
    this.showBoxes = true,
    this.showTrails = true,
    this.showSkeleton = true,
  });

  // Skeletal limb connection pairs
  static const List<List<String>> skeletonConnections = [
    ['nose', 'left_eye'],
    ['nose', 'right_eye'],
    ['left_eye', 'left_ear'],
    ['right_eye', 'right_ear'],
    ['left_shoulder', 'right_shoulder'],
    ['left_shoulder', 'left_elbow'],
    ['left_elbow', 'left_wrist'],
    ['right_shoulder', 'right_elbow'],
    ['right_elbow', 'right_wrist'],
    ['left_shoulder', 'left_hip'],
    ['right_shoulder', 'right_hip'],
    ['left_hip', 'right_hip'],
    ['left_hip', 'left_knee'],
    ['left_knee', 'left_ankle'],
    ['right_hip', 'right_knee'],
    ['right_knee', 'right_ankle'],
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final scaleX = size.width / videoWidth;
    final scaleY = size.height / videoHeight;

    final boxPaint = Paint()
      ..color = const Color(0xFF00FFCC)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    final trailPaint = Paint()
      ..color = const Color(0xFFFF007F)
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    final bonePaint = Paint()
      ..color = const Color(0xFF06B6D4)
      ..strokeWidth = 2.5
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;

    final jointFillPaint = Paint()
      ..color = const Color(0xFFFF007F)
      ..style = PaintingStyle.fill;

    final jointStrokePaint = Paint()
      ..color = Colors.white
      ..strokeWidth = 1.0
      ..style = PaintingStyle.stroke;

    final textPainter = TextPainter(textDirection: TextDirection.ltr);

    for (var player in players) {
      // 1. Motion trails
      if (showTrails && player.trail.length > 1) {
        final path = Path();
        final first = player.trail.first;
        path.moveTo(first[0] * scaleX, first[1] * scaleY);
        for (var pt in player.trail.skip(1)) {
          path.lineTo(pt[0] * scaleX, pt[1] * scaleY);
        }
        canvas.drawPath(path, trailPaint);
      }

      // 2. Skeletal joints and bones
      if (showSkeleton && player.pose.isNotEmpty) {
        // Draw limb bones
        for (var pair in skeletonConnections) {
          final k1 = player.pose[pair[0]];
          final k2 = player.pose[pair[1]];
          if (k1 != null && k2 != null && k1.confidence >= 0.30 && k2.confidence >= 0.30) {
            canvas.drawLine(
              Offset(k1.x * scaleX, k1.y * scaleY),
              Offset(k2.x * scaleX, k2.y * scaleY),
              bonePaint,
            );
          }
        }

        // Draw joint circles
        for (var kpt in player.pose.values) {
          if (kpt.confidence >= 0.30) {
            final offset = Offset(kpt.x * scaleX, kpt.y * scaleY);
            canvas.drawCircle(offset, 3.5, jointFillPaint);
            canvas.drawCircle(offset, 4.5, jointStrokePaint);
          }
        }
      }

      // 3. Bounding box & Kinematic badge
      if (showBoxes) {
        final rect = Rect.fromLTWH(
          player.x * scaleX,
          player.y * scaleY,
          player.width * scaleX,
          player.height * scaleY,
        );
        canvas.drawRect(rect, boxPaint);

        // Header label with speed and activity state
        final kin = player.kinematics;
        final badgeText = ' #${player.playerId} | ${kin.instantSpeedMps.toStringAsFixed(1)} m/s | ${kin.movementState.toUpperCase()} ';

        final span = TextSpan(
          text: badgeText,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 10,
            fontWeight: FontWeight.bold,
            backgroundColor: Color(0xDD0F172A),
          ),
        );
        textPainter.text = span;
        textPainter.layout();
        textPainter.paint(canvas, Offset(rect.left, (rect.top - 16).clamp(0.0, size.height)));
      }
    }
  }

  @override
  bool shouldRepaint(covariant PlayerOverlayPainter oldDelegate) {
    return true;
  }
}
