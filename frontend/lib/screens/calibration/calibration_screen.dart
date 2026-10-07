import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/analysis_provider.dart';
import '../../services/api_service.dart';

/// Interactive 4-point court calibration screen for perspective homography
class CalibrationScreen extends StatefulWidget {
  const CalibrationScreen({Key? key}) : super(key: key);

  @override
  State<CalibrationScreen> createState() => _CalibrationScreenState();
}

class _CalibrationScreenState extends State<CalibrationScreen> {
  final ApiService _apiService = ApiService();
  bool _isLoading = false;
  bool _isCalibrated = false;

  // 4 normalized corner points [0..1]
  List<Offset> _corners = [
    const Offset(0.15, 0.20), // Top-Left
    const Offset(0.85, 0.20), // Top-Right
    const Offset(0.85, 0.85), // Bottom-Right
    const Offset(0.15, 0.85), // Bottom-Left
  ];

  int? _draggedIndex;

  @override
  void initState() {
    super.initState();
    _loadCurrentCalibration();
  }

  Future<void> _loadCurrentCalibration() async {
    final sport = Provider.of<AnalysisProvider>(context, listen: false).selectedSport;
    setState(() => _isLoading = true);

    try {
      final res = await _apiService.getCalibration(sport);
      if (res['is_calibrated'] == true && res['image_corners'] is List) {
        final raw = res['image_corners'] as List;
        if (raw.length == 4) {
          setState(() {
            _corners = raw.map((pt) {
              final x = (pt[0] as num).toDouble() / 1280.0;
              final y = (pt[1] as num).toDouble() / 720.0;
              return Offset(x.clamp(0.0, 1.0), y.clamp(0.0, 1.0));
            }).toList();
            _isCalibrated = true;
          });
        }
      }
    } catch (_) {}

    setState(() => _isLoading = false);
  }

  Future<void> _saveCalibration() async {
    final sport = Provider.of<AnalysisProvider>(context, listen: false).selectedSport;
    setState(() => _isLoading = true);

    try {
      final pixelCorners = _corners.map((c) => [c.dx * 1280.0, c.dy * 720.0]).toList();
      final res = await _apiService.setCalibration(sport, pixelCorners);
      if (res['status'] == 'success') {
        setState(() => _isCalibrated = true);
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Court perspective calibration saved successfully!'), backgroundColor: Color(0xFF10B981)),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error saving calibration: $e'), backgroundColor: Colors.red),
        );
      }
    }

    setState(() => _isLoading = false);
  }

  Future<void> _autoDetect() async {
    final sport = Provider.of<AnalysisProvider>(context, listen: false).selectedSport;
    setState(() => _isLoading = true);

    try {
      final res = await _apiService.autoDetectCorners(sport);
      if (res['proposed_corners'] is List) {
        final raw = res['proposed_corners'] as List;
        setState(() {
          _corners = raw.map((pt) {
            final x = (pt[0] as num).toDouble() / 1280.0;
            final y = (pt[1] as num).toDouble() / 720.0;
            return Offset(x.clamp(0.0, 1.0), y.clamp(0.0, 1.0));
          }).toList();
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Court corners detected! Fine-tune handles if needed.'), backgroundColor: Color(0xFF06B6D4)),
          );
        }
      }
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not auto-detect corners. Set points manually.'), backgroundColor: Colors.orange),
        );
      }
    }

    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    final sport = Provider.of<AnalysisProvider>(context).selectedSport;

    return Scaffold(
      appBar: AppBar(
        title: Text('Court Calibration (${sport.toUpperCase()})'),
        actions: [
          IconButton(
            icon: const Icon(Icons.auto_fix_high),
            tooltip: 'Auto Detect Lines',
            onPressed: _isLoading ? null : _autoDetect,
          ),
          IconButton(
            icon: const Icon(Icons.save),
            tooltip: 'Save Calibration',
            onPressed: _isLoading ? null : _saveCalibration,
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            color: const Color(0xFF1E293B),
            child: Row(
              children: [
                Icon(
                  _isCalibrated ? Icons.check_circle : Icons.warning_amber,
                  color: _isCalibrated ? const Color(0xFF10B981) : Colors.amber,
                  size: 18,
                ),
                const SizedBox(width: 8),
                Text(
                  _isCalibrated ? 'Homography Calibrated (Real-world metric mode)' : 'Uncalibrated (Using pixel approximation)',
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                Text(
                  'Drag 4 corner handles to align with court lines',
                  style: TextStyle(color: Colors.grey[400], fontSize: 11),
                ),
              ],
            ),
          ),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final w = constraints.maxWidth;
                final h = constraints.maxHeight;

                return GestureDetector(
                  onPanDown: (details) {
                    final pos = details.localPosition;
                    // Check which handle is closest
                    for (int i = 0; i < _corners.length; i++) {
                      final handlePos = Offset(_corners[i].dx * w, _corners[i].dy * h);
                      if ((pos - handlePos).distance < 30.0) {
                        setState(() => _draggedIndex = i);
                        break;
                      }
                    }
                  },
                  onPanUpdate: (details) {
                    if (_draggedIndex != null) {
                      setState(() {
                        final nx = (details.localPosition.dx / w).clamp(0.0, 1.0);
                        final ny = (details.localPosition.dy / h).clamp(0.0, 1.0);
                        _corners[_draggedIndex!] = Offset(nx, ny);
                      });
                    }
                  },
                  onPanEnd: (_) => setState(() => _draggedIndex = null),
                  child: Stack(
                    children: [
                      // Court floor canvas background
                      Container(
                        width: w,
                        height: h,
                        color: const Color(0xFF0B1120),
                        child: CustomPaint(
                          painter: CalibrationOverlayPainter(corners: _corners),
                        ),
                      ),
                      // Draggable handle badges
                      for (int i = 0; i < _corners.length; i++)
                        Positioned(
                          left: _corners[i].dx * w - 18,
                          top: _corners[i].dy * h - 18,
                          child: Container(
                            width: 36,
                            height: 36,
                            decoration: BoxDecoration(
                              color: _draggedIndex == i ? Colors.amber : const Color(0xFF06B6D4),
                              shape: BoxShape.circle,
                              border: Border.all(color: Colors.white, width: 2),
                              boxShadow: const [
                                BoxShadow(color: Colors.black54, blurRadius: 6, spreadRadius: 1),
                              ],
                            ),
                            child: Center(
                              child: Text(
                                ['TL', 'TR', 'BR', 'BL'][i],
                                style: const TextStyle(
                                  color: Colors.black,
                                  fontWeight: FontWeight.bold,
                                  fontSize: 11,
                                ),
                              ),
                            ),
                          ),
                        ),
                    ],
                  ),
                );
              },
            ),
          ),
          // Action button bar
          Container(
            padding: const EdgeInsets.all(16),
            color: const Color(0xFF1E293B),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                OutlinedButton.icon(
                  onPressed: _autoDetect,
                  icon: const Icon(Icons.auto_fix_high),
                  label: const Text('Auto-Detect Court'),
                ),
                ElevatedButton.icon(
                  onPressed: _saveCalibration,
                  icon: const Icon(Icons.save),
                  label: const Text('Save Calibration'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF10B981),
                    foregroundColor: Colors.white,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class CalibrationOverlayPainter extends CustomPainter {
  final List<Offset> corners;

  CalibrationOverlayPainter({required this.corners});

  @override
  void paint(Canvas canvas, Size size) {
    if (corners.length != 4) return;

    final pts = corners.map((c) => Offset(c.dx * size.width, c.dy * size.height)).toList();

    // Fill quad
    final fillPaint = Paint()
      ..color = const Color(0xFF06B6D4).withOpacity(0.15)
      ..style = PaintingStyle.fill;

    final linePaint = Paint()
      ..color = const Color(0xFF06B6D4)
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke;

    final path = Path()
      ..moveTo(pts[0].dx, pts[0].dy)
      ..lineTo(pts[1].dx, pts[1].dy)
      ..lineTo(pts[2].dx, pts[2].dy)
      ..lineTo(pts[3].dx, pts[3].dy)
      ..close();

    canvas.drawPath(path, fillPaint);
    canvas.drawPath(path, linePaint);

    // Midline
    final midTop = Offset((pts[0].dx + pts[1].dx) / 2, (pts[0].dy + pts[1].dy) / 2);
    final midBottom = Offset((pts[3].dx + pts[2].dx) / 2, (pts[3].dy + pts[2].dy) / 2);
    final midPaint = Paint()
      ..color = Colors.amber
      ..strokeWidth = 2.0
      ..style = PaintingStyle.stroke;

    canvas.drawLine(midTop, midBottom, midPaint);
  }

  @override
  bool shouldRepaint(covariant CalibrationOverlayPainter oldDelegate) => true;
}
