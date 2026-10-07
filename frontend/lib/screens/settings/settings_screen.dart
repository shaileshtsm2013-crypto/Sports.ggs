import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/analysis_provider.dart';
import '../../services/api_service.dart';

/// Application configuration, camera sources, hardware optimization & offline diagnostics
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({Key? key}) : super(key: key);

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final ApiService _apiService = ApiService();
  List<Map<String, dynamic>> _sources = [];
  Map<String, dynamic>? _hardwareSpecs;
  Map<String, dynamic>? _activeProfile;
  Map<String, dynamic>? _benchmarkResult;
  Map<String, dynamic>? _offlineStatus;
  bool _isLoading = false;
  bool _isBenchmarking = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    setState(() => _isLoading = true);
    try {
      final sources = await _apiService.getCameraSources();
      final hw = await _apiService.getHardwareSpecs();
      final prof = await _apiService.getPerformanceProfile();
      final offline = await _apiService.getOfflineStatus();
      setState(() {
        _sources = sources;
        _hardwareSpecs = hw;
        _activeProfile = prof['active_profile'] as Map<String, dynamic>?;
        _offlineStatus = offline;
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Future<void> _changeProfile(String name) async {
    try {
      final res = await _apiService.setPerformanceProfile(name);
      setState(() {
        _activeProfile = res['profile'] as Map<String, dynamic>?;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Switched to $name optimization profile.'),
          duration: const Duration(seconds: 1),
        ),
      );
    } catch (e) {
      // Ignored
    }
  }

  Future<void> _runBenchmark() async {
    setState(() => _isBenchmarking = true);
    try {
      final res = await _apiService.runHardwareBenchmark(frames: 10);
      setState(() {
        _benchmarkResult = res;
        _isBenchmarking = false;
      });
    } catch (e) {
      setState(() => _isBenchmarking = false);
    }
  }

  Widget _buildProfileChip(String name, String label, IconData icon) {
    final curName = _activeProfile?['name'] ?? 'balanced';
    final isSelected = curName == name;

    return ChoiceChip(
      avatar: Icon(icon, size: 14, color: isSelected ? Colors.black : Colors.white70),
      label: Text(label, style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: isSelected ? Colors.black : Colors.white)),
      selected: isSelected,
      selectedColor: const Color(0xFF06B6D4),
      backgroundColor: const Color(0xFF1E293B),
      onSelected: (_) => _changeProfile(name),
    );
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<AnalysisProvider>(context);

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: const Text('Settings & Hardware Optimization'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          // ── Camera Input ──────────────────────────────────────────────────
          const Text('Camera Video Input', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
          const SizedBox(height: 6),
          const Text('Choose simulated court generator or physical USB/webcam capture device.', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
          const SizedBox(height: 12),
          if (_isLoading)
            const Center(child: CircularProgressIndicator(color: Color(0xFF06B6D4)))
          else
            Column(
              children: _sources.map((s) {
                final id = s['id']?.toString() ?? '';
                final name = s['name']?.toString() ?? 'Device';
                final isSelected = provider.selectedSource == id;

                return RadioListTile<String>(
                  value: id,
                  groupValue: provider.selectedSource,
                  title: Text(name, style: const TextStyle(fontWeight: FontWeight.w600, color: Colors.white)),
                  subtitle: Text(id == 'synthetic' ? 'Simulated athletes on court' : 'Hardware video capture device', style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
                  activeColor: const Color(0xFF06B6D4),
                  selected: isSelected,
                  onChanged: (val) {
                    if (val != null) {
                      provider.setSource(val);
                    }
                  },
                );
              }).toList(),
            ),
          const Divider(height: 36, color: Color(0xFF334155)),

          // ── Phase 9: Hardware Acceleration & Performance Profile ─────────
          Row(
            children: const [
              Icon(Icons.bolt, color: Color(0xFF06B6D4), size: 18),
              SizedBox(width: 8),
              Text('Hardware Acceleration & Tuning', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
            ],
          ),
          const SizedBox(height: 6),
          const Text('Optimize compute pipeline for low-end hardware, Windows DirectX 12, or GPU.', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 12)),
          const SizedBox(height: 14),

          // Specs Card
          if (_hardwareSpecs != null)
            Container(
              padding: const EdgeInsets.all(14),
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
                      const Text('COMPUTE DEVICE: ', style: TextStyle(fontSize: 11, color: Color(0xFF94A3B8), fontWeight: FontWeight.bold)),
                      Text('${_hardwareSpecs!['primary_device']}'.toUpperCase(), style: const TextStyle(fontSize: 11, color: Color(0xFF4ADE80), fontWeight: FontWeight.bold)),
                      const Spacer(),
                      Text('${_hardwareSpecs!['platform']} (${_hardwareSpecs!['cpu_count']} Cores)', style: const TextStyle(fontSize: 11, color: Color(0xFF38BDF8))),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Text('${_hardwareSpecs!['device_name']}', style: const TextStyle(fontSize: 12, color: Colors.white70)),
                ],
              ),
            ),
          const SizedBox(height: 14),

          // Profile Selection Chips
          Row(
            children: [
              const Text('PERFORMANCE PROFILE:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF94A3B8))),
              const SizedBox(width: 10),
              Wrap(
                spacing: 8,
                children: [
                  _buildProfileChip('low_power', 'Low Power / Battery', Icons.battery_saver),
                  _buildProfileChip('balanced', 'Balanced (Default)', Icons.balance),
                  _buildProfileChip('max_performance', 'Max Performance', Icons.speed),
                ],
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Benchmark Button
          Row(
            children: [
              OutlinedButton.icon(
                icon: _isBenchmarking
                    ? const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2, color: Color(0xFF06B6D4)))
                    : const Icon(Icons.timer, size: 14, color: Color(0xFF06B6D4)),
                label: const Text('Run Hardware Benchmark', style: TextStyle(fontSize: 11, color: Color(0xFF06B6D4))),
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: Color(0xFF06B6D4)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                ),
                onPressed: _isBenchmarking ? null : _runBenchmark,
              ),
              if (_benchmarkResult != null) ...[
                const SizedBox(width: 14),
                Text(
                  'Latency: ${_benchmarkResult!['avg_latency_ms']} ms | Est. FPS: ${_benchmarkResult!['estimated_fps']}',
                  style: const TextStyle(fontSize: 11, color: Color(0xFF4ADE80), fontWeight: FontWeight.bold),
                ),
              ],
            ],
          ),
          const Divider(height: 36, color: Color(0xFF334155)),

          // ── Phase 9: Offline Readiness ───────────────────────────────────
          Row(
            children: const [
              Icon(Icons.cloud_off, color: Color(0xFF10B981), size: 18),
              SizedBox(width: 8),
              Text('Offline Operation & Privacy', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: const Color(0xFF1E293B),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFF10B981).withOpacity(0.4)),
            ),
            child: Row(
              children: [
                const Icon(Icons.check_circle, color: Color(0xFF10B981), size: 24),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: const [
                      Text('100% Offline Capable — Zero Cloud Dependency', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 13, color: Colors.white)),
                      SizedBox(height: 2),
                      Text('YOLOv8 vision, pose estimation, kinematics, rules KB, and reports run entirely on this local device with zero video uploads.', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}
