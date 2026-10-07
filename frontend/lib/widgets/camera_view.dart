import 'package:flutter/material.dart';
import '../constants/app_constants.dart';

/// Live MJPEG camera video view widget
class CameraView extends StatelessWidget {
  final bool isRunning;
  final String streamUrl;

  const CameraView({
    Key? key,
    required this.isRunning,
    this.streamUrl = AppConstants.mjpegStreamUrl,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    if (!isRunning) {
      return Container(
        color: Colors.black87,
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: const [
              Icon(Icons.videocam_off, size: 64, color: Colors.white38),
              SizedBox(height: 16),
              Text(
                'Camera Feed Inactive',
                style: TextStyle(color: Colors.white70, fontSize: 16),
              ),
              SizedBox(height: 8),
              Text(
                'Select a source and click Start to begin live tracking',
                style: TextStyle(color: Colors.white38, fontSize: 12),
              ),
            ],
          ),
        ),
      );
    }

    return Container(
      color: Colors.black,
      child: Center(
        child: Image.network(
          streamUrl,
          fit: BoxFit.contain,
          gaplessPlayback: true,
          errorBuilder: (context, error, stackTrace) {
            return Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: const [
                  CircularProgressIndicator(),
                  SizedBox(height: 12),
                  Text(
                    'Connecting to live vision feed...',
                    style: TextStyle(color: Colors.white70),
                  ),
                ],
              ),
            );
          },
        ),
      ),
    );
  }
}
