import 'package:flutter/material.dart';

/// Small visual badge showing detection confidence level
class ConfidenceBadge extends StatelessWidget {
  final double confidence;

  const ConfidenceBadge({Key? key, required this.confidence}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    final percent = (confidence * 100).clamp(0, 100).toInt();
    Color color;
    if (confidence >= 0.75) {
      color = const Color(0xFF10B981); // Green
    } else if (confidence >= 0.50) {
      color = const Color(0xFFF59E0B); // Amber
    } else {
      color = const Color(0xFFEF4444); // Red
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withOpacity(0.2),
        border: Border.all(color: color, width: 1),
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        '$percent%',
        style: TextStyle(
          color: color,
          fontSize: 10,
          fontWeight: FontWeight.bold,
        ),
      ),
    );
  }
}
