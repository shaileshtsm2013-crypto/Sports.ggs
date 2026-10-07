import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/detection_frame.dart';
import '../models/player.dart';
import '../models/volleyball_data.dart';
import '../models/kabaddi_data.dart';
import '../models/kho_kho_data.dart';
import 'api_service.dart';
import 'websocket_service.dart';

/// Central state provider for real-time sports analysis
class AnalysisProvider extends ChangeNotifier {
  final ApiService _apiService = ApiService();
  final WebSocketService _wsService = WebSocketService();

  String _selectedSport = 'volleyball';
  String _selectedSource = 'synthetic';
  bool _isRunning = false;
  bool _isPaused = false;
  double _fps = 0.0;
  int _frameCount = 0;

  DetectionFrame? _latestFrame;
  List<PlayerTrack> _activePlayers = [];
  VolleyballTelemetry? _volleyball;
  KabaddiTelemetry? _kabaddi;
  KhoKhoTelemetry? _khoKho;
  String _rallyState = 'IDLE';
  List<VolleyballViolation> _activeViolations = [];
  List<VolleyballEvent> _recentEvents = [];

  List<Map<String, String>> _chatMessages = [
    {
      'role': 'assistant',
      'content': 'Welcome to Sports Analyzer AI! Ask me any questions about Volleyball, Kabaddi, or Kho Kho rules and tactics.'
    }
  ];
  bool _isChatLoading = false;
  String _aiProvider = 'offline'; // 'gemini' or 'offline'

  StreamSubscription? _wsSubscription;

  // Getters
  String get selectedSport => _selectedSport;
  String get selectedSource => _selectedSource;
  bool get isRunning => _isRunning;
  bool get isPaused => _isPaused;
  double get fps => _fps;
  int get frameCount => _frameCount;
  DetectionFrame? get latestFrame => _latestFrame;
  List<PlayerTrack> get activePlayers => _activePlayers;
  VolleyballTelemetry? get volleyball => _volleyball;
  KabaddiTelemetry? get kabaddi => _kabaddi;
  KhoKhoTelemetry? get khoKho => _khoKho;
  String get rallyState => _rallyState;
  List<VolleyballViolation> get activeViolations => _activeViolations;
  List<VolleyballEvent> get recentEvents => _recentEvents;
  List<Map<String, String>> get chatMessages => _chatMessages;
  bool get isChatLoading => _isChatLoading;
  String get aiProvider => _aiProvider;

  void setSport(String sport) {
    _selectedSport = sport;
    notifyListeners();
  }

  void setSource(String source) {
    _selectedSource = source;
    notifyListeners();
  }

  Future<void> startAnalysis() async {
    try {
      await _apiService.startCamera(
        source: _selectedSource,
        sport: _selectedSport,
      );
      _isRunning = true;
      _isPaused = false;

      // Connect WebSocket for live telemetry
      _wsService.connect();
      _wsSubscription?.cancel();
      _wsSubscription = _wsService.frameStream.listen((frame) {
        _latestFrame = frame;
        _fps = frame.fps;
        _frameCount = frame.frameIndex;
        _activePlayers = frame.players;
        if (frame.volleyball != null) {
          _volleyball = frame.volleyball;
          _rallyState = frame.volleyball!.rallyState;
          _activeViolations = frame.volleyball!.activeViolations;
          _recentEvents = frame.volleyball!.recentEvents;
        }
        if (frame.kabaddi != null) {
          _kabaddi = frame.kabaddi;
        }
        if (frame.khoKho != null) {
          _khoKho = frame.khoKho;
        }
        notifyListeners();
      });

      notifyListeners();
    } catch (e) {
      if (kDebugMode) print('Error starting analysis: $e');
    }
  }

  Future<void> stopAnalysis() async {
    try {
      await _apiService.stopCamera();
      _wsService.disconnect();
      _wsSubscription?.cancel();
      _isRunning = false;
      _isPaused = false;
      _fps = 0.0;
      _activePlayers = [];
      _latestFrame = null;
      _volleyball = null;
      _kabaddi = null;
      _khoKho = null;
      _rallyState = 'IDLE';
      _activeViolations = [];
      _recentEvents = [];
      notifyListeners();
    } catch (e) {
      if (kDebugMode) print('Error stopping analysis: $e');
    }
  }

  Future<void> resetRally() async {
    try {
      await _apiService.resetRally();
      _rallyState = 'IDLE';
      _activeViolations = [];
      notifyListeners();
    } catch (e) {
      if (kDebugMode) print('Error resetting rally: $e');
    }
  }

  Future<void> resetRaid() async {
    try {
      await _apiService.resetRaid();
      notifyListeners();
    } catch (e) {
      if (kDebugMode) print('Error resetting raid: $e');
    }
  }

  Future<void> resetKhoKhoTurn() async {
    try {
      await _apiService.resetKhoKhoTurn();
      notifyListeners();
    } catch (e) {
      if (kDebugMode) print('Error resetting kho kho turn: $e');
    }
  }

  Future<void> togglePause() async {
    try {
      if (_isPaused) {
        await _apiService.resumeCamera();
        _isPaused = false;
      } else {
        await _apiService.pauseCamera();
        _isPaused = true;
      }
      notifyListeners();
    } catch (e) {
      if (kDebugMode) print('Error toggling pause: $e');
    }
  }

  /// Builds a compact live-game context string to inject into the chat system prompt.
  String _buildLiveContext() {
    final parts = <String>[];
    parts.add('Sport: $_selectedSport');
    if (_isRunning) {
      parts.add('Analysis: running (${_fps.toStringAsFixed(1)} fps, frame $_frameCount)');
    }
    if (_volleyball != null) {
      parts.add('Rally state: $_rallyState');
      if (_activeViolations.isNotEmpty) {
        parts.add('Active violations: ${_activeViolations.map((v) => v.type).join(', ')}');
      }
      if (_recentEvents.isNotEmpty) {
        parts.add('Recent events: ${_recentEvents.take(3).map((e) => e.type).join(', ')}');
      }
    }
    if (_kabaddi != null) {
      parts.add('Kabaddi raid state: ${_kabaddi!.raidState}');
      parts.add('Score — Team A: ${_kabaddi!.teamAScore}, Team B: ${_kabaddi!.teamBScore}');
    }
    if (_khoKho != null) {
      parts.add('Kho Kho chasers: ${_khoKho!.activeChasers}, runners out: ${_khoKho!.runnersOut}');
    }
    return parts.join(' | ');
  }

  Future<void> sendChatMessage(String message) async {
    if (message.trim().isEmpty) return;

    _chatMessages.add({'role': 'user', 'content': message});
    _isChatLoading = true;
    notifyListeners();

    try {
      final res = await _apiService.sendChatMessage(
        messages: _chatMessages,
        sport: _selectedSport,
        liveContext: _buildLiveContext(),
      );
      final reply = res['response'] as String? ?? 'No response received.';
      _aiProvider = res['provider'] as String? ?? 'offline';
      _chatMessages.add({'role': 'assistant', 'content': reply});
    } catch (e) {
      _chatMessages.add({
        'role': 'assistant',
        'content': 'Unable to connect to AI assistant. Please ensure the backend is running.'
      });
    } finally {
      _isChatLoading = false;
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _wsSubscription?.cancel();
    _wsService.dispose();
    super.dispose();
  }
}
