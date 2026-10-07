import 'dart:math';
import 'package:flutter/material.dart';
import '../../models/report_data.dart';
import '../../services/api_service.dart';

/// Individual Player Performance Dashboard with Time-Series Charts & Biomechanics
class PlayerReportScreen extends StatefulWidget {
  final int playerId;

  const PlayerReportScreen({Key? key, required this.playerId}) : super(key: key);

  @override
  State<PlayerReportScreen> createState() => _PlayerReportScreenState();
}

class _PlayerReportScreenState extends State<PlayerReportScreen> {
  final ApiService _apiService = ApiService();
  bool _isLoading = true;
  PlayerReportData? _report;
  int _activeChartIndex = 0; // 0: Speed, 1: Acceleration, 2: Distance, 3: Jumps

  @override
  void initState() {
    super.initState();
    _fetchPlayerReport();
  }

  Future<void> _fetchPlayerReport() async {
    setState(() => _isLoading = true);
    try {
      final res = await _apiService.getLivePlayerReport(widget.playerId);
      setState(() {
        _report = PlayerReportData.fromJson(res);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Widget _buildStatCard(String label, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icon, size: 14, color: color),
              const SizedBox(width: 6),
              Text(
                label.toUpperCase(),
                style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 6),
          Text(
            value,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold, color: Colors.white),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F172A),
        body: Center(child: CircularProgressIndicator(color: Color(0xFF06B6D4))),
      );
    }

    final p = _report;
    if (p == null) {
      return Scaffold(
        backgroundColor: const Color(0xFF0F172A),
        appBar: AppBar(title: Text('Player #${widget.playerId}')),
        body: const Center(child: Text('Player analytics not available.')),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: Row(
          children: [
            const Icon(Icons.person, color: Color(0xFF06B6D4), size: 20),
            const SizedBox(width: 8),
            Text('PLAYER ${p.jerseyNumber}', style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
            const SizedBox(width: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF0284C7).withOpacity(0.2),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF0284C7)),
              ),
              child: Text(
                '${p.team} • ${p.sport.toUpperCase()}',
                style: const TextStyle(fontSize: 10, color: Color(0xFF38BDF8), fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF94A3B8)),
            onPressed: _fetchPlayerReport,
            tooltip: 'Refresh',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Section 19 Exact Performance Metrics Grid ────────────────────
            GridView.count(
              crossAxisCount: MediaQuery.of(context).size.width > 800 ? 4 : 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 2.0,
              children: [
                _buildStatCard('Distance', '${p.distanceM} m', Icons.route, const Color(0xFFFBBF24)),
                _buildStatCard('Maximum Speed', '${p.maxSpeedMps} m/s', Icons.speed, const Color(0xFFF87171)),
                _buildStatCard('Average Speed', '${p.avgSpeedMps} m/s', Icons.directions_run, const Color(0xFF06B6D4)),
                _buildStatCard('Max Acceleration', '${p.maxAccelMps2} m/s²', Icons.flash_on, const Color(0xFFA855F7)),
                _buildStatCard('Jumps', '${p.jumpsCount}', Icons.height, const Color(0xFF38BDF8)),
                _buildStatCard('Maximum Jump', '${p.highestJumpCm} cm', Icons.vertical_align_top, const Color(0xFF4ADE80)),
                _buildStatCard('Average Jump', '${p.avgJumpHeightCm} cm', Icons.align_vertical_center, const Color(0xFF34D399)),
                _buildStatCard('Court Coverage', '${p.courtCoveragePct}%', Icons.grid_view, const Color(0xFFEC4899)),
              ],
            ),
            const SizedBox(height: 24),

            // ── Charts Switcher Tabs ─────────────────────────────────────────
            Row(
              children: [
                const Icon(Icons.show_chart, color: Color(0xFF06B6D4), size: 18),
                const SizedBox(width: 8),
                const Text('PERFORMANCE CHARTS', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
                const Spacer(),
                Wrap(
                  spacing: 6,
                  children: [
                    _buildChartTab('Speed', 0),
                    _buildChartTab('Acceleration', 1),
                    _buildChartTab('Distance', 2),
                    _buildChartTab('Jumps', 3),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 12),

            // ── Chart Canvas Container ───────────────────────────────────────
            Container(
              height: 260,
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: _buildActiveChart(p),
            ),
            const SizedBox(height: 24),

            // ── Jump Timeline Log ────────────────────────────────────────────
            Row(
              children: [
                const Icon(Icons.height, color: Color(0xFF06B6D4), size: 18),
                const SizedBox(width: 8),
                const Text('JUMP TIMELINE', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
              ],
            ),
            const SizedBox(height: 10),
            Container(
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: p.jumpTimeline.isEmpty
                  ? const Padding(
                      padding: EdgeInsets.all(20.0),
                      child: Center(child: Text('No jumps logged for this player yet.', style: TextStyle(color: Color(0xFF94A3B8)))),
                    )
                  : ListView.separated(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: p.jumpTimeline.length,
                      separatorBuilder: (_, __) => const Divider(color: Color(0xFF334155), height: 1),
                      itemBuilder: (context, index) {
                        final j = p.jumpTimeline[index];
                        return ListTile(
                          dense: true,
                          leading: Text(j.formattedTime, style: const TextStyle(color: Color(0xFF06B6D4), fontWeight: FontWeight.bold)),
                          title: Text('Jump Height: ${j.heightCm} cm', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                          subtitle: Text('Type: ${j.type.toUpperCase()}', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                          trailing: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.green.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text('${(j.confidence * 100).toInt()}% conf', style: const TextStyle(fontSize: 10, color: Colors.greenAccent)),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildChartTab(String title, int index) {
    final isSel = _activeChartIndex == index;
    return GestureDetector(
      onTap: () => setState(() => _activeChartIndex = index),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: isSel ? const Color(0xFF06B6D4) : const Color(0xFF0F172A),
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(
          title,
          style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: isSel ? Colors.black : Colors.white70),
        ),
      ),
    );
  }

  Widget _buildActiveChart(PlayerReportData p) {
    if (_activeChartIndex == 0) {
      return LineSparkChart(
        points: p.speedOverTime,
        color: const Color(0xFF06B6D4),
        unit: 'm/s',
        title: 'Speed Over Time (m/s)',
      );
    } else if (_activeChartIndex == 1) {
      return LineSparkChart(
        points: p.accelerationOverTime,
        color: const Color(0xFFA855F7),
        unit: 'm/s²',
        title: 'Acceleration Over Time (m/s²)',
      );
    } else if (_activeChartIndex == 2) {
      return LineSparkChart(
        points: p.distanceOverTime,
        color: const Color(0xFFFBBF24),
        unit: 'm',
        title: 'Cumulative Distance Over Time (m)',
      );
    } else {
      return JumpBarChart(jumps: p.jumpTimeline);
    }
  }
}

/// Custom Canvas Line Sparkline Chart
class LineSparkChart extends StatelessWidget {
  final List<TimeSeriesPoint> points;
  final Color color;
  final String unit;
  final String title;

  const LineSparkChart({
    Key? key,
    required this.points,
    required this.color,
    required this.unit,
    required this.title,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (points.isEmpty) {
      return Center(child: Text('No telemetry points recorded yet for $title.', style: const TextStyle(color: Color(0xFF94A3B8))));
    }

    final maxVal = points.map((p) => p.value).reduce(max);
    final minVal = points.map((p) => p.value).reduce(min);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
            const Spacer(),
            Text('Max: ${maxVal.toStringAsFixed(1)} $unit', style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.w600)),
          ],
        ),
        const SizedBox(height: 12),
        Expanded(
          child: CustomPaint(
            size: Size.infinite,
            painter: _LineSparkPainter(points: points, lineColor: color, maxVal: max(maxVal, 1.0), minVal: minVal),
          ),
        ),
      ],
    );
  }
}

class _LineSparkPainter extends CustomPainter {
  final List<TimeSeriesPoint> points;
  final Color lineColor;
  final double maxVal;
  final double minVal;

  _LineSparkPainter({required this.points, required this.lineColor, required this.maxVal, required this.minVal});

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = lineColor
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round;

    final fillPaint = Paint()
      ..shader = LinearGradient(
        colors: [lineColor.withOpacity(0.3), lineColor.withOpacity(0.0)],
        begin: Alignment.topCenter,
        end: Alignment.bottomCenter,
      ).createShader(Rect.fromLTWH(0, 0, size.width, size.height))
      ..style = PaintingStyle.fill;

    final gridPaint = Paint()
      ..color = const Color(0xFF334155).withOpacity(0.5)
      ..strokeWidth = 0.5;

    // Grid lines
    for (int i = 0; i <= 4; i++) {
      final y = size.height * (i / 4.0);
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }

    if (points.length < 2) return;

    final path = Path();
    final fillPath = Path();

    for (int i = 0; i < points.length; i++) {
      final x = (i / (points.length - 1)) * size.width;
      final normY = (points[i].value - minVal) / max(0.01, (maxVal - minVal));
      final y = size.height - (normY * size.height * 0.85) - size.height * 0.05;

      if (i == 0) {
        path.moveTo(x, y);
        fillPath.moveTo(x, size.height);
        fillPath.lineTo(x, y);
      } else {
        path.lineTo(x, y);
        fillPath.lineTo(x, y);
      }
    }

    fillPath.lineTo(size.width, size.height);
    fillPath.close();

    canvas.drawPath(fillPath, fillPaint);
    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => true;
}

/// Custom Canvas Jump Bar Chart
class JumpBarChart extends StatelessWidget {
  final List<JumpEventData> jumps;

  const JumpBarChart({Key? key, required this.jumps}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (jumps.isEmpty) {
      return const Center(child: Text('No jumps recorded to plot.', style: TextStyle(color: Color(0xFF94A3B8))));
    }

    final maxH = jumps.map((j) => j.heightCm).reduce(max);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Text('Jump Height Timeline (cm)', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold, color: Colors.white)),
            const Spacer(),
            Text('Max: ${maxH.toStringAsFixed(1)} cm', style: const TextStyle(fontSize: 11, color: Color(0xFF4ADE80), fontWeight: FontWeight.w600)),
          ],
        ),
        const SizedBox(height: 12),
        Expanded(
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: jumps.take(16).map((j) {
              final frac = (j.heightCm / max(maxH, 10.0)).clamp(0.05, 1.0);
              return Column(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  Text('${j.heightCm.toInt()}', style: const TextStyle(fontSize: 9, color: Colors.white70)),
                  const SizedBox(height: 4),
                  Container(
                    width: 14,
                    height: 140 * frac,
                    decoration: BoxDecoration(
                      color: const Color(0xFF06B6D4),
                      borderRadius: BorderRadius.circular(3),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(j.formattedTime, style: const TextStyle(fontSize: 8, color: Color(0xFF94A3B8))),
                ],
              );
            }).toList(),
          ),
        ),
      ],
    );
  }
}
