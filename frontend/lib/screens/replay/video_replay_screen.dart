import 'dart:async';
import 'package:flutter/material.dart';
import '../../models/report_data.dart';
import '../../services/api_service.dart';

/// Video Replay Controller with Scrubber & Interactive Event Timeline Markers (Section 21)
class VideoReplayScreen extends StatefulWidget {
  final String matchId;

  const VideoReplayScreen({Key? key, this.matchId = 'live'}) : super(key: key);

  @override
  State<VideoReplayScreen> createState() => _VideoReplayScreenState();
}

class _VideoReplayScreenState extends State<VideoReplayScreen> {
  final ApiService _apiService = ApiService();
  bool _isLoading = true;
  bool _isPlaying = false;
  double _currentTime = 0.0;
  double _totalDuration = 300.0; // 5 minutes default
  Timer? _playbackTimer;
  List<ReplayMarker> _markers = [];
  ReplayMarker? _selectedMarker;

  @override
  void initState() {
    super.initState();
    _fetchReplayData();
  }

  @override
  void dispose() {
    _playbackTimer?.cancel();
    super.dispose();
  }

  Future<void> _fetchReplayData() async {
    setState(() => _isLoading = true);
    try {
      final rep = await _apiService.getMatchReport(widget.matchId);
      final rawMarkers = await _apiService.getReplayTimeline(widget.matchId);

      final dur = (rep['duration_sec'] as num?)?.toDouble() ?? 300.0;
      final parsedMarkers = rawMarkers.map((m) => ReplayMarker.fromJson(Map<String, dynamic>.from(m))).toList();

      setState(() {
        _totalDuration = dur > 10.0 ? dur : 300.0;
        _markers = parsedMarkers;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  void _togglePlayPause() {
    setState(() {
      _isPlaying = !_isPlaying;
      if (_isPlaying) {
        _playbackTimer = Timer.periodic(const Duration(milliseconds: 100), (timer) {
          setState(() {
            if (_currentTime >= _totalDuration) {
              _currentTime = 0.0;
              _isPlaying = false;
              timer.cancel();
            } else {
              _currentTime += 0.1;
            }
          });
        });
      } else {
        _playbackTimer?.cancel();
      }
    });
  }

  void _seekRelative(double seconds) {
    setState(() {
      _currentTime = (_currentTime + seconds).clamp(0.0, _totalDuration);
    });
  }

  void _seekTo(double timestamp) {
    setState(() {
      _currentTime = timestamp.clamp(0.0, _totalDuration);
    });
  }

  String _formatTime(double sec) {
    final s = sec.toInt();
    final m = s // 60;
    final remSec = s % 60;
    return '${m.toString().padLeft(2, '0')}:${remSec.toString().padLeft(2, '0')}';
  }

  Color _getMarkerColor(String type) {
    final t = type.toLowerCase();
    if (t.contains('spike') || t.contains('tackle')) return const Color(0xFFF87171);
    if (t.contains('jump')) return const Color(0xFF06B6D4);
    if (t.contains('rally') || t.contains('raid')) return const Color(0xFF4ADE80);
    if (t.contains('violation') || t.contains('fault')) return const Color(0xFFFBBF24);
    if (t.contains('kho')) return const Color(0xFFA855F7);
    return const Color(0xFF38BDF8);
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F172A),
        body: Center(child: CircularProgressIndicator(color: Color(0xFF06B6D4))),
      );
    }

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: const Row(
          children: [
            Icon(Icons.replay, color: Color(0xFF06B6D4), size: 20),
            SizedBox(width: 8),
            Text('VIDEO REPLAY & EVENT SCRUBBER', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 15)),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Video Viewport Area ──────────────────────────────────────────
            Container(
              height: 380,
              width: double.infinity,
              decoration: BoxDecoration(
                color: Colors.black,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  // Video Frame Placeholder / Simulation
                  Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(
                        _isPlaying ? Icons.sports_volleyball : Icons.pause_circle_outline,
                        size: 64,
                        color: const Color(0xFF06B6D4).withOpacity(0.5),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        'Replay Time: ${_formatTime(_currentTime)} / ${_formatTime(_totalDuration)}',
                        style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        _selectedMarker != null
                            ? 'Event at cursor: ${_selectedMarker!.eventType.toUpperCase()} (${_selectedMarker!.description})'
                            : 'Playback synchronized with tracking kinematics',
                        style: const TextStyle(fontSize: 12, color: Color(0xFF94A3B8)),
                      ),
                    ],
                  ),

                  // Overlay watermark
                  Positioned(
                    top: 12,
                    left: 14,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.black.withOpacity(0.7),
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: const Color(0xFF06B6D4)),
                      ),
                      child: const Row(
                        children: [
                          Icon(Icons.fiber_smart_record, color: Colors.red, size: 12),
                          SizedBox(width: 6),
                          Text('SYNCHRONIZED REPLAY', style: TextStyle(fontSize: 10, color: Colors.white, fontWeight: FontWeight.bold)),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // ── Timeline Scrubber with Event Dots (Section 21 format) ────────
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Text(_formatTime(_currentTime), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF38BDF8))),
                      const Spacer(),
                      Text(_formatTime(_totalDuration), style: const TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Color(0xFF94A3B8))),
                    ],
                  ),
                  const SizedBox(height: 8),

                  // Interactive Timeline Slider with visual markers
                  Stack(
                    alignment: Alignment.centerLeft,
                    children: [
                      SliderTheme(
                        data: SliderTheme.of(context).copyWith(
                          activeTrackColor: const Color(0xFF06B6D4),
                          inactiveTrackColor: const Color(0xFF334155),
                          thumbColor: Colors.white,
                          thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 7),
                          overlayShape: const RoundSliderOverlayShape(overlayRadius: 14),
                          trackHeight: 4,
                        ),
                        child: Slider(
                          value: _currentTime.clamp(0.0, _totalDuration),
                          min: 0.0,
                          max: _totalDuration,
                          onChanged: (val) {
                            _seekTo(val);
                          },
                        ),
                      ),

                      // Event Dots Overlaid on the Timeline Track
                      IgnorePointer(
                        child: LayoutBuilder(
                          builder: (context, constraints) {
                            final w = constraints.maxWidth - 32; // account for slider padding
                            return Container(
                              margin: const EdgeInsets.symmetric(horizontal: 16),
                              height: 14,
                              child: Stack(
                                children: _markers.map((m) {
                                  final frac = (m.timestamp / _totalDuration).clamp(0.0, 1.0);
                                  return Positioned(
                                    left: w * frac - 4,
                                    top: 3,
                                    child: Container(
                                      width: 8,
                                      height: 8,
                                      decoration: BoxDecoration(
                                        color: _getMarkerColor(m.eventType),
                                        shape: BoxShape.circle,
                                        border: Border.all(color: Colors.white, width: 1),
                                      ),
                                    ),
                                  );
                                }).toList(),
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  ),

                  // ── Transport Controller Buttons (Section 21) ──────────────
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      // -5 sec
                      ElevatedButton.icon(
                        icon: const Icon(Icons.replay_5, size: 16),
                        label: const Text('5 sec', style: TextStyle(fontSize: 11)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF0F172A),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        ),
                        onPressed: () => _seekRelative(-5.0),
                      ),
                      const SizedBox(width: 16),

                      // Play / Pause
                      IconButton(
                        iconSize: 42,
                        icon: Icon(
                          _isPlaying ? Icons.pause_circle_filled : Icons.play_circle_fill,
                          color: const Color(0xFF06B6D4),
                        ),
                        onPressed: _togglePlayPause,
                      ),
                      const SizedBox(width: 16),

                      // +5 sec
                      ElevatedButton.icon(
                        icon: const Icon(Icons.forward_5, size: 16),
                        label: const Text('5 sec', style: TextStyle(fontSize: 11)),
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF0F172A),
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                        ),
                        onPressed: () => _seekRelative(5.0),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),

            // ── Clickable Event Markers List (Section 21) ────────────────────
            Row(
              children: [
                const Icon(Icons.touch_app, color: Color(0xFF06B6D4), size: 16),
                const SizedBox(width: 8),
                const Text('TIMELINE EVENT JUMP LIST', style: TextStyle(fontSize: 13, fontWeight: FontWeight.bold, color: Colors.white)),
                const Spacer(),
                const Text('Click any event to seek replay', style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
              ],
            ),
            const SizedBox(height: 10),
            Container(
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: _markers.isEmpty
                  ? const Padding(
                      padding: EdgeInsets.all(20.0),
                      child: Center(child: Text('No replay event markers detected.', style: TextStyle(color: Color(0xFF94A3B8)))),
                    )
                  : ListView.separated(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: _markers.length,
                      separatorBuilder: (_, __) => const Divider(color: Color(0xFF334155), height: 1),
                      itemBuilder: (context, index) {
                        final m = _markers[index];
                        final isNear = (_currentTime - m.timestamp).abs() < 1.5;
                        return ListTile(
                          dense: true,
                          tileColor: isNear ? const Color(0xFF06B6D4).withOpacity(0.12) : null,
                          leading: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: _getMarkerColor(m.eventType).withOpacity(0.2),
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(color: _getMarkerColor(m.eventType)),
                            ),
                            child: Text(
                              m.eventType.toUpperCase(),
                              style: TextStyle(fontSize: 10, fontWeight: FontWeight.bold, color: _getMarkerColor(m.eventType)),
                            ),
                          ),
                          title: Text(m.description, style: const TextStyle(fontSize: 12, color: Colors.white, fontWeight: FontWeight.w600)),
                          trailing: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(m.formattedTime, style: const TextStyle(color: Color(0xFF06B6D4), fontWeight: FontWeight.bold, fontSize: 12)),
                              const SizedBox(width: 8),
                              const Icon(Icons.arrow_forward_ios, size: 10, color: Color(0xFF64748B)),
                            ],
                          ),
                          onTap: () {
                            _seekTo(m.timestamp);
                            setState(() => _selectedMarker = m);
                          },
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
