import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/analysis_provider.dart';
import '../../services/api_service.dart';

/// Screen displaying 2D top-down court and camera coverage heatmaps
class HeatmapScreen extends StatefulWidget {
  const HeatmapScreen({Key? key}) : super(key: key);

  @override
  State<HeatmapScreen> createState() => _HeatmapScreenState();
}

class _HeatmapScreenState extends State<HeatmapScreen> {
  final ApiService _apiService = ApiService();
  bool _isLoading = false;
  String? _heatmapBase64;
  int? _selectedPlayerId; // null = Team aggregate
  String _selectedMode = 'court'; // 'court' or 'camera'

  @override
  void initState() {
    super.initState();
    _loadHeatmap();
  }

  Future<void> _loadHeatmap() async {
    setState(() => _isLoading = true);

    try {
      Map<String, dynamic> res;
      if (_selectedPlayerId != null) {
        res = await _apiService.getPlayerHeatmap(_selectedPlayerId!, mode: _selectedMode);
      } else {
        res = await _apiService.getTeamHeatmap(mode: _selectedMode);
      }

      if (res['heatmap_image_base64'] != null) {
        setState(() {
          _heatmapBase64 = res['heatmap_image_base64'] as String;
        });
      }
    } catch (_) {}

    setState(() => _isLoading = false);
  }

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<AnalysisProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Text('${provider.selectedSport.toUpperCase().replaceAll('_', ' ')} Heatmaps'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            tooltip: 'Regenerate Heatmap',
            onPressed: _isLoading ? null : _loadHeatmap,
          ),
        ],
      ),
      body: Column(
        children: [
          // Filter controls bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            color: const Color(0xFF1E293B),
            child: Row(
              children: [
                // Mode selector
                DropdownButton<String>(
                  value: _selectedMode,
                  dropdownColor: const Color(0xFF1E293B),
                  items: const [
                    DropdownMenuItem(value: 'court', child: Text('2D Tactical Court')),
                    DropdownMenuItem(value: 'camera', child: Text('Camera Perspective')),
                  ],
                  onChanged: (val) {
                    if (val != null) {
                      setState(() => _selectedMode = val);
                      _loadHeatmap();
                    }
                  },
                ),
                const SizedBox(width: 20),
                // Player selector
                DropdownButton<int?>(
                  value: _selectedPlayerId,
                  dropdownColor: const Color(0xFF1E293B),
                  hint: const Text('All Players (Team)'),
                  items: [
                    const DropdownMenuItem<int?>(
                      value: null,
                      child: Text('All Players (Team Heatmap)'),
                    ),
                    ...provider.activePlayers.map((p) {
                      return DropdownMenuItem<int?>(
                        value: p.playerId,
                        child: Text('Player #${p.playerId}'),
                      );
                    }).toList(),
                  ],
                  onChanged: (val) {
                    setState(() => _selectedPlayerId = val);
                    _loadHeatmap();
                  },
                ),
                const Spacer(),
                if (_isLoading)
                  const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  ),
              ],
            ),
          ),
          // Heatmap display canvas
          Expanded(
            child: Container(
              color: const Color(0xFF0F172A),
              padding: const EdgeInsets.all(16),
              child: Center(
                child: _heatmapBase64 != null && _heatmapBase64!.isNotEmpty
                    ? Container(
                        decoration: BoxDecoration(
                          border: Border.all(color: const Color(0xFF334155)),
                          borderRadius: BorderRadius.circular(8),
                          boxShadow: const [
                            BoxShadow(color: Colors.black45, blurRadius: 10, spreadRadius: 2),
                          ],
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.memory(
                            base64Decode(_heatmapBase64!.split(',').last),
                            fit: BoxFit.contain,
                          ),
                        ),
                      )
                    : Column(
                        mainAxisSize: MainAxisSize.min,
                        children: const [
                          Icon(Icons.graphic_eq, size: 64, color: Colors.white24),
                          SizedBox(height: 16),
                          Text(
                            'No movement tracking data yet.',
                            style: TextStyle(color: Colors.white60, fontSize: 16),
                          ),
                          SizedBox(height: 8),
                          Text(
                            'Start a live camera or synthetic session to accumulate movement heatmaps.',
                            style: TextStyle(color: Colors.white38, fontSize: 12),
                          ),
                        ],
                      ),
              ),
            ),
          ),
          // Legend bar
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
            color: const Color(0xFF1E293B),
            child: Row(
              children: [
                const Text('Density Legend: ', style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold)),
                const SizedBox(width: 12),
                Container(
                  width: 180,
                  height: 12,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Colors.blue, Colors.cyan, Colors.green, Colors.yellow, Colors.red],
                    ),
                    borderRadius: BorderRadius.circular(6),
                  ),
                ),
                const SizedBox(width: 8),
                const Text('Low  →  High Activity', style: TextStyle(fontSize: 11, color: Colors.grey)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
