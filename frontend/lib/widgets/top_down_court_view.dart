import 'dart:convert';
import 'package:flutter/material.dart';
import '../services/api_service.dart';

/// Widget displaying a 2D top-down bird's-eye tactical court map with live athlete positions
class TopDownCourtView extends StatefulWidget {
  final double height;

  const TopDownCourtView({Key? key, this.height = 240}) : super(key: key);

  @override
  State<TopDownCourtView> createState() => _TopDownCourtViewState();
}

class _TopDownCourtViewState extends State<TopDownCourtView> {
  final ApiService _apiService = ApiService();
  String? _imageBase64;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _fetchTacticalMap();
  }

  Future<void> _fetchTacticalMap() async {
    if (!mounted) return;
    try {
      final res = await _apiService.getTopDownCourtView();
      if (res['topdown_image_base64'] != null) {
        setState(() {
          _imageBase64 = res['topdown_image_base64'] as String;
        });
      }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      height: widget.height,
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(
              children: [
                const Icon(Icons.map, color: Color(0xFF06B6D4), size: 16),
                const SizedBox(width: 8),
                const Text(
                  '2D Tactical Court Projection',
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.bold),
                ),
                const Spacer(),
                IconButton(
                  icon: const Icon(Icons.refresh, size: 16),
                  onPressed: _fetchTacticalMap,
                  visualDensity: VisualDensity.compact,
                  tooltip: 'Refresh Map',
                ),
              ],
            ),
          ),
          Expanded(
            child: Center(
              child: _imageBase64 != null
                  ? Image.memory(
                      base64Decode(_imageBase64!.split(',').last),
                      fit: BoxFit.contain,
                    )
                  : const Center(
                      child: Text(
                        'Tactical map standby...',
                        style: TextStyle(color: Colors.grey, fontSize: 12),
                      ),
                    ),
            ),
          ),
        ],
      ),
    );
  }
}
