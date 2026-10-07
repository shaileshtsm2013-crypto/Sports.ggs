import 'package:flutter/material.dart';

/// Top bar displaying live performance metrics and status
class StatsBar extends StatelessWidget {
  final double fps;
  final int frameCount;
  final int playerCount;
  final String sport;
  final bool isRunning;

  const StatsBar({
    Key? key,
    required this.fps,
    required this.frameCount,
    required this.playerCount,
    required this.sport,
    required this.isRunning,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      color: const Color(0xFF1E293B),
      child: Row(
        children: [
          // Live status pill
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: isRunning ? const Color(0xFF10B981) : Colors.grey[700],
              borderRadius: BorderRadius.circular(4),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  isRunning ? Icons.fiber_manual_record : Icons.pause,
                  size: 10,
                  color: Colors.white,
                ),
                const SizedBox(width: 4),
                Text(
                  isRunning ? 'LIVE' : 'STANDBY',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          // FPS Indicator
          _buildMetric('FPS', fps.toStringAsFixed(1), const Color(0xFF06B6D4)),
          const SizedBox(width: 16),
          // Frame Count
          _buildMetric('FRAMES', frameCount.toString(), Colors.white70),
          const SizedBox(width: 16),
          // Active Players
          _buildMetric('PLAYERS', playerCount.toString(), const Color(0xFFF59E0B)),
          const Spacer(),
          // Sport indicator
          Chip(
            label: Text(
              sport.toUpperCase().replaceAll('_', ' '),
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.bold),
            ),
            backgroundColor: const Color(0xFF334155),
            visualDensity: VisualDensity.compact,
          ),
        ],
      ),
    );
  }

  Widget _buildMetric(String label, String value, Color valueColor) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          '$label: ',
          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11, fontWeight: FontWeight.bold),
        ),
        Text(
          value,
          style: TextStyle(color: valueColor, fontSize: 12, fontWeight: FontWeight.bold),
        ),
      ],
    );
  }
}
