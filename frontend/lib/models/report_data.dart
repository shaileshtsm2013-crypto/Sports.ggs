/// Models for Match Analysis Reports, Individual Player Performance,
/// Time-series Charts, and Video Replay Timeline Markers.

class TimeSeriesPoint {
  final double timestamp;
  final double value;

  TimeSeriesPoint({required this.timestamp, required this.value});

  factory TimeSeriesPoint.fromJson(Map<String, dynamic> json, String valKey) {
    return TimeSeriesPoint(
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
      value: (json[valKey] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class JumpEventData {
  final double timestamp;
  final String formattedTime;
  final double heightCm;
  final String type;
  final double confidence;

  JumpEventData({
    required this.timestamp,
    required this.formattedTime,
    required this.heightCm,
    required this.type,
    required this.confidence,
  });

  factory JumpEventData.fromJson(Map<String, dynamic> json) {
    return JumpEventData(
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
      formattedTime: json['formatted_time'] as String? ?? '00:00',
      heightCm: (json['height_cm'] as num?)?.toDouble() ?? 0.0,
      type: json['type'] as String? ?? 'jump',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.8,
    );
  }
}

class MatchEventData {
  final double timestamp;
  final String formattedTime;
  final String eventType;
  final int? playerId;
  final String details;
  final double confidence;

  MatchEventData({
    required this.timestamp,
    required this.formattedTime,
    required this.eventType,
    this.playerId,
    required this.details,
    required this.confidence,
  });

  factory MatchEventData.fromJson(Map<String, dynamic> json) {
    return MatchEventData(
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
      formattedTime: json['formatted_time'] as String? ?? '00:00',
      eventType: json['event_type'] as String? ?? 'event',
      playerId: json['player_id'] as int?,
      details: json['details'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.8,
    );
  }
}

class ReplayMarker {
  final double timestamp;
  final String formattedTime;
  final String eventType;
  final int? playerId;
  final String description;
  final double confidence;

  ReplayMarker({
    required this.timestamp,
    required this.formattedTime,
    required this.eventType,
    this.playerId,
    required this.description,
    required this.confidence,
  });

  factory ReplayMarker.fromJson(Map<String, dynamic> json) {
    return ReplayMarker(
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
      formattedTime: json['formatted_time'] as String? ?? '00:00',
      eventType: json['event_type'] as String? ?? 'event',
      playerId: json['player_id'] as int?,
      description: json['description'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.8,
    );
  }
}

class PlayerSummary {
  final int playerId;
  final String jerseyNumber;
  final String team;
  final String role;
  final double distanceM;
  final double maxSpeedMps;
  final double avgSpeedMps;
  final double maxAccelMps2;
  final int jumpsCount;
  final double highestJumpCm;
  final double avgJumpHeightCm;
  final double courtCoveragePct;
  final int directionChanges;
  final String movementState;

  PlayerSummary({
    required this.playerId,
    required this.jerseyNumber,
    required this.team,
    required this.role,
    required this.distanceM,
    required this.maxSpeedMps,
    required this.avgSpeedMps,
    required this.maxAccelMps2,
    required this.jumpsCount,
    required this.highestJumpCm,
    required this.avgJumpHeightCm,
    required this.courtCoveragePct,
    required this.directionChanges,
    required this.movementState,
  });

  factory PlayerSummary.fromJson(Map<String, dynamic> json) {
    return PlayerSummary(
      playerId: json['player_id'] as int? ?? 0,
      jerseyNumber: json['jersey_number'] as String? ?? '#0',
      team: json['team'] as String? ?? 'Team A',
      role: json['role'] as String? ?? 'player',
      distanceM: (json['total_distance_m'] as num?)?.toDouble() ?? 0.0,
      maxSpeedMps: (json['max_speed_mps'] as num?)?.toDouble() ?? 0.0,
      avgSpeedMps: (json['avg_speed_mps'] as num?)?.toDouble() ?? 0.0,
      maxAccelMps2: (json['max_acceleration_mps2'] as num?)?.toDouble() ?? 0.0,
      jumpsCount: json['jumps_count'] as int? ?? 0,
      highestJumpCm: (json['highest_jump_cm'] as num?)?.toDouble() ?? 0.0,
      avgJumpHeightCm: (json['avg_jump_height_cm'] as num?)?.toDouble() ?? 0.0,
      courtCoveragePct: (json['court_coverage_pct'] as num?)?.toDouble() ?? 0.0,
      directionChanges: json['direction_changes'] as int? ?? 0,
      movementState: json['movement_state'] as String? ?? 'standing',
    );
  }
}

class MatchReportData {
  final String matchId;
  final String title;
  final String sport;
  final String status;
  final String durationFormatted;
  final double durationSec;
  final double fps;
  final int playersDetected;
  final int activePlayers;
  final double totalDistanceKm;
  final int totalJumps;
  final double maxSpeedMps;
  final double avgSpeedMps;
  final Map<String, dynamic> sportSummary;
  final List<PlayerSummary> players;
  final List<MatchEventData> events;
  final List<ReplayMarker> timelineMarkers;

  MatchReportData({
    required this.matchId,
    required this.title,
    required this.sport,
    required this.status,
    required this.durationFormatted,
    required this.durationSec,
    required this.fps,
    required this.playersDetected,
    required this.activePlayers,
    required this.totalDistanceKm,
    required this.totalJumps,
    required this.maxSpeedMps,
    required this.avgSpeedMps,
    required this.sportSummary,
    required this.players,
    required this.events,
    required this.timelineMarkers,
  });

  factory MatchReportData.fromJson(Map<String, dynamic> json) {
    return MatchReportData(
      matchId: json['match_id'] as String? ?? 'none',
      title: json['title'] as String? ?? 'Match Analysis',
      sport: json['sport'] as String? ?? 'volleyball',
      status: json['status'] as String? ?? 'active',
      durationFormatted: json['duration_formatted'] as String? ?? '00:00:00',
      durationSec: (json['duration_sec'] as num?)?.toDouble() ?? 0.0,
      fps: (json['fps'] as num?)?.toDouble() ?? 0.0,
      playersDetected: json['players_detected'] as int? ?? 0,
      activePlayers: json['active_players'] as int? ?? 0,
      totalDistanceKm: (json['total_distance_km'] as num?)?.toDouble() ?? 0.0,
      totalJumps: json['total_jumps'] as int? ?? 0,
      maxSpeedMps: (json['max_speed_mps'] as num?)?.toDouble() ?? 0.0,
      avgSpeedMps: (json['avg_speed_mps'] as num?)?.toDouble() ?? 0.0,
      sportSummary: Map<String, dynamic>.from(json['sport_summary'] ?? {}),
      players: (json['players'] as List? ?? [])
          .map((p) => PlayerSummary.fromJson(p as Map<String, dynamic>))
          .toList(),
      events: (json['events'] as List? ?? [])
          .map((e) => MatchEventData.fromJson(e as Map<String, dynamic>))
          .toList(),
      timelineMarkers: (json['timeline_markers'] as List? ?? [])
          .map((m) => ReplayMarker.fromJson(m as Map<String, dynamic>))
          .toList(),
    );
  }
}

class PlayerReportData {
  final int playerId;
  final String jerseyNumber;
  final String team;
  final String sport;
  final double distanceM;
  final double maxSpeedMps;
  final double avgSpeedMps;
  final double maxAccelMps2;
  final int jumpsCount;
  final double highestJumpCm;
  final double avgJumpHeightCm;
  final double courtCoveragePct;
  final int directionChanges;
  final String movementState;
  final List<TimeSeriesPoint> speedOverTime;
  final List<TimeSeriesPoint> accelerationOverTime;
  final List<TimeSeriesPoint> distanceOverTime;
  final List<JumpEventData> jumpTimeline;
  final List<MatchEventData> eventTimeline;

  PlayerReportData({
    required this.playerId,
    required this.jerseyNumber,
    required this.team,
    required this.sport,
    required this.distanceM,
    required this.maxSpeedMps,
    required this.avgSpeedMps,
    required this.maxAccelMps2,
    required this.jumpsCount,
    required this.highestJumpCm,
    required this.avgJumpHeightCm,
    required this.courtCoveragePct,
    required this.directionChanges,
    required this.movementState,
    required this.speedOverTime,
    required this.accelerationOverTime,
    required this.distanceOverTime,
    required this.jumpTimeline,
    required this.eventTimeline,
  });

  factory PlayerReportData.fromJson(Map<String, dynamic> json) {
    final speedList = (json['speed_over_time'] as List? ?? [])
        .map((p) => TimeSeriesPoint.fromJson(p as Map<String, dynamic>, 'speed_mps'))
        .toList();
    final accelList = (json['acceleration_over_time'] as List? ?? [])
        .map((p) => TimeSeriesPoint.fromJson(p as Map<String, dynamic>, 'acceleration_mps2'))
        .toList();
    final distList = (json['distance_over_time'] as List? ?? [])
        .map((p) => TimeSeriesPoint.fromJson(p as Map<String, dynamic>, 'distance_m'))
        .toList();
    final jumpList = (json['jump_timeline'] as List? ?? [])
        .map((j) => JumpEventData.fromJson(j as Map<String, dynamic>))
        .toList();
    final eventList = (json['event_timeline'] as List? ?? [])
        .map((e) => MatchEventData.fromJson(e as Map<String, dynamic>))
        .toList();

    return PlayerReportData(
      playerId: json['player_id'] as int? ?? 0,
      jerseyNumber: json['jersey_number'] as String? ?? '#0',
      team: json['team'] as String? ?? 'Team A',
      sport: json['sport'] as String? ?? 'volleyball',
      distanceM: (json['total_distance_m'] as num?)?.toDouble() ?? 0.0,
      maxSpeedMps: (json['max_speed_mps'] as num?)?.toDouble() ?? 0.0,
      avgSpeedMps: (json['avg_speed_mps'] as num?)?.toDouble() ?? 0.0,
      maxAccelMps2: (json['max_acceleration_mps2'] as num?)?.toDouble() ?? 0.0,
      jumpsCount: json['jumps_count'] as int? ?? 0,
      highestJumpCm: (json['highest_jump_cm'] as num?)?.toDouble() ?? 0.0,
      avgJumpHeightCm: (json['avg_jump_height_cm'] as num?)?.toDouble() ?? 0.0,
      courtCoveragePct: (json['court_coverage_pct'] as num?)?.toDouble() ?? 0.0,
      directionChanges: json['direction_changes'] as int? ?? 0,
      movementState: json['movement_state'] as String? ?? 'standing',
      speedOverTime: speedList,
      accelerationOverTime: accelList,
      distanceOverTime: distList,
      jumpTimeline: jumpList,
      eventTimeline: eventList,
    );
  }
}
