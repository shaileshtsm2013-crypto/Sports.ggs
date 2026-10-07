import '../core/networking/api_client.dart';
import '../models/match.dart';

/// Service interfacing with the FastAPI backend REST API
class ApiService {
  final ApiClient client;

  ApiService({ApiClient? client}) : client = client ?? ApiClient();

  // Camera endpoints
  Future<List<Map<String, dynamic>>> getCameraSources() async {
    final res = await client.get('/camera/sources');
    if (res is List) {
      return List<Map<String, dynamic>>.from(res);
    }
    return [];
  }

  Future<Map<String, dynamic>> startCamera({
    required String source,
    required String sport,
  }) async {
    final res = await client.post('/camera/start', body: {
      'source': source,
      'sport': sport,
    });
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> stopCamera() async {
    final res = await client.post('/camera/stop');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> pauseCamera() async {
    final res = await client.post('/camera/pause');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> resumeCamera() async {
    final res = await client.post('/camera/resume');
    return Map<String, dynamic>.from(res ?? {});
  }

  // Analysis status & settings
  Future<Map<String, dynamic>> getAnalysisStatus() async {
    final res = await client.get('/analysis/status');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> updateAnalysisSettings({
    bool? showSkeleton,
    bool? showBoxes,
    bool? showTrails,
  }) async {
    final res = await client.post('/analysis/settings', body: {
      if (showSkeleton != null) 'show_skeleton': showSkeleton,
      if (showBoxes != null) 'show_boxes': showBoxes,
      if (showTrails != null) 'show_trails': showTrails,
    });
    return Map<String, dynamic>.from(res ?? {});
  }

  // Court Calibration
  Future<Map<String, dynamic>> getCalibration(String sport) async {
    final res = await client.get('/calibration/$sport');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> setCalibration(String sport, List<List<double>> corners) async {
    final res = await client.post('/calibration/$sport', body: {
      'corners': corners,
    });
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> autoDetectCorners(String sport) async {
    final res = await client.post('/calibration/$sport/auto');
    return Map<String, dynamic>.from(res ?? {});
  }

  // Heatmaps & Top-down tactical view
  Future<Map<String, dynamic>> getPlayerHeatmap(int playerId, {String mode = 'court'}) async {
    final res = await client.get('/analysis/heatmap/player/$playerId?mode=$mode');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getTeamHeatmap({String mode = 'court'}) async {
    final res = await client.get('/analysis/heatmap/team?mode=$mode');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getTopDownCourtView() async {
    final res = await client.get('/analysis/court/topdown');
    return Map<String, dynamic>.from(res ?? {});
  }

  // Match management
  Future<List<MatchSession>> getMatches() async {
    final res = await client.get('/matches/');
    if (res is List) {
      return res.map((m) => MatchSession.fromJson(m)).toList();
    }
    return [];
  }

  Future<MatchSession> createMatch({
    required String sportType,
    required String title,
  }) async {
    final res = await client.post('/matches/', body: {
      'sport_type': sportType,
      'title': title,
    });
    return MatchSession.fromJson(res);
  }

  // Chat & AI rules
  Future<Map<String, dynamic>> sendChatMessage({
    required List<Map<String, String>> messages,
    required String sport,
    String liveContext = '',
  }) async {
    final res = await client.post('/chat/message', body: {
      'messages': messages,
      'sport': sport,
      'live_context': liveContext,
    });
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getChatStatus() async {
    final res = await client.get('/chat/status');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getSportRules(String sport) async {
    final res = await client.get('/chat/rules/$sport');
    return Map<String, dynamic>.from(res ?? {});
  }

  // Volleyball Analytics
  Future<Map<String, dynamic>> getVolleyballEvents() async {
    final res = await client.get('/analysis/volleyball/events');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getVolleyballViolations() async {
    final res = await client.get('/analysis/volleyball/violations');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getVolleyballStatus() async {
    final res = await client.get('/analysis/volleyball/status');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> resetRally() async {
    final res = await client.post('/analysis/volleyball/reset-rally');
    return Map<String, dynamic>.from(res ?? {});
  }

  // Kabaddi Analytics
  Future<Map<String, dynamic>> getKabaddiEvents() async {
    final res = await client.get('/analysis/kabaddi/events');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getKabaddiViolations() async {
    final res = await client.get('/analysis/kabaddi/violations');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getKabaddiStatus() async {
    final res = await client.get('/analysis/kabaddi/status');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> resetRaid() async {
    final res = await client.post('/analysis/kabaddi/reset-raid');
    return Map<String, dynamic>.from(res ?? {});
  }

  // Kho Kho Analytics
  Future<Map<String, dynamic>> getKhoKhoEvents() async {
    final res = await client.get('/analysis/kho_kho/events');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getKhoKhoViolations() async {
    final res = await client.get('/analysis/kho_kho/violations');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getKhoKhoStatus() async {
    final res = await client.get('/analysis/kho_kho/status');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> resetKhoKhoTurn() async {
    final res = await client.post('/analysis/kho_kho/reset-turn');
    return Map<String, dynamic>.from(res ?? {});
  }

  // Reports & Analytics Dashboards
  Future<Map<String, dynamic>> getLiveMatchReport() async {
    final res = await client.get('/reports/match/live');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getMatchReport(String matchId) async {
    final res = await client.get('/reports/match/$matchId');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getLivePlayerReport(int playerId) async {
    final res = await client.get('/reports/player/live/$playerId');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<List<dynamic>> getReplayTimeline(String matchId) async {
    final res = await client.get('/reports/replay/$matchId/timeline');
    if (res is List) return res;
    return [];
  }

  String getExportMatchHtmlUrl(String matchId) {
    return '${client.baseUrl}/reports/export/match/$matchId/html';
  }

  String getExportMatchCsvUrl(String matchId) {
    return '${client.baseUrl}/reports/export/match/$matchId/csv';
  }

  String getExportMatchJsonUrl(String matchId) {
    return '${client.baseUrl}/reports/export/match/$matchId/json';
  }

  String getExportPlayerCsvUrl(int playerId) {
    return '${client.baseUrl}/reports/export/player/$playerId/csv';
  }

  // Phase 9: Hardware Acceleration & Optimization
  Future<Map<String, dynamic>> getHardwareSpecs() async {
    final res = await client.get('/optimization/hardware');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getPerformanceProfile() async {
    final res = await client.get('/optimization/profile');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> setPerformanceProfile(String profileName, {int? frameSkip}) async {
    final res = await client.post('/optimization/profile', body: {
      'profile_name': profileName,
      if (frameSkip != null) 'frame_skip': frameSkip,
    });
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> runHardwareBenchmark({int frames = 10}) async {
    final res = await client.get('/optimization/benchmark?frames=$frames');
    return Map<String, dynamic>.from(res ?? {});
  }

  Future<Map<String, dynamic>> getOfflineStatus() async {
    final res = await client.get('/optimization/offline-status');
    return Map<String, dynamic>.from(res ?? {});
  }
}



