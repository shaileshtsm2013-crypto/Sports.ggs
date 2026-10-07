import 'dart:async';
import 'dart:convert';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../constants/app_constants.dart';
import '../models/detection_frame.dart';

/// Manages real-time WebSocket connection to backend telemetry stream
class WebSocketService {
  WebSocketChannel? _channel;
  final StreamController<DetectionFrame> _frameController =
      StreamController<DetectionFrame>.broadcast();
  bool _isConnected = false;

  Stream<DetectionFrame> get frameStream => _frameController.stream;
  bool get isConnected => _isConnected;

  void connect({String? url}) {
    disconnect();
    final targetUrl = url ?? AppConstants.baseWsUrl;

    try {
      _channel = WebSocketChannel.connect(Uri.parse(targetUrl));
      _isConnected = true;

      _channel!.stream.listen(
        (data) {
          try {
            final jsonMap = jsonDecode(data as String);
            if (jsonMap is Map<String, dynamic> && jsonMap['type'] == 'telemetry') {
              final frame = DetectionFrame.fromJson(jsonMap);
              _frameController.add(frame);
            }
          } catch (e) {
            // Ignore parse errors on ping/status packets
          }
        },
        onError: (err) {
          _isConnected = false;
        },
        onDone: () {
          _isConnected = false;
        },
      );
    } catch (e) {
      _isConnected = false;
    }
  }

  void disconnect() {
    _channel?.sink.close();
    _channel = null;
    _isConnected = false;
  }

  void dispose() {
    disconnect();
    _frameController.close();
  }
}
