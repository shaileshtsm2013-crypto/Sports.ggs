import 'player.dart';
import 'volleyball_data.dart';
import 'kabaddi_data.dart';
import 'kho_kho_data.dart';

/// Telemetry payload received per frame from the backend WebSocket
class DetectionFrame {
  final String type;
  final double timestamp;
  final int frameIndex;
  final double fps;
  final String sport;
  final int playersCount;
  final int frameWidth;
  final int frameHeight;
  final List<PlayerTrack> players;
  final VolleyballTelemetry? volleyball;
  final KabaddiTelemetry? kabaddi;
  final KhoKhoTelemetry? khoKho;

  DetectionFrame({
    required this.type,
    required this.timestamp,
    required this.frameIndex,
    required this.fps,
    required this.sport,
    required this.playersCount,
    required this.frameWidth,
    required this.frameHeight,
    required this.players,
    this.volleyball,
    this.kabaddi,
    this.khoKho,
  });

  factory DetectionFrame.fromJson(Map<String, dynamic> json) {
    var rawPlayers = json['players'] as List? ?? [];
    List<PlayerTrack> playerList = rawPlayers
        .map((p) => PlayerTrack.fromJson(p as Map<String, dynamic>))
        .toList();

    var dims = json['frame_dimensions'] as Map<String, dynamic>? ?? {};

    VolleyballTelemetry? vbData;
    if (json['volleyball'] is Map<String, dynamic>) {
      vbData = VolleyballTelemetry.fromJson(json['volleyball'] as Map<String, dynamic>);
    }

    KabaddiTelemetry? kabaddiData;
    if (json['kabaddi'] is Map<String, dynamic>) {
      kabaddiData = KabaddiTelemetry.fromJson(json['kabaddi'] as Map<String, dynamic>);
    }

    KhoKhoTelemetry? khoKhoData;
    if (json['kho_kho'] is Map<String, dynamic>) {
      khoKhoData = KhoKhoTelemetry.fromJson(json['kho_kho'] as Map<String, dynamic>);
    }

    return DetectionFrame(
      type: json['type'] as String? ?? 'telemetry',
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
      frameIndex: json['frame_index'] as int? ?? 0,
      fps: (json['fps'] as num?)?.toDouble() ?? 0.0,
      sport: json['sport'] as String? ?? 'volleyball',
      playersCount: json['players_count'] as int? ?? playerList.length,
      frameWidth: dims['width'] as int? ?? 1280,
      frameHeight: dims['height'] as int? ?? 720,
      players: playerList,
      volleyball: vbData,
      kabaddi: kabaddiData,
      khoKho: khoKhoData,
    );
  }
}

