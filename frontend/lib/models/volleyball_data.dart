/// Models for Volleyball sport-specific rules, events, and telemetry

class VolleyballViolation {
  final String rule;
  final String violationType;
  final int playerId;
  final String team;
  final double confidenceScore;
  final String confidenceLevel;
  final String description;
  final double timestamp;
  final int frameIdx;

  VolleyballViolation({
    required this.rule,
    required this.violationType,
    required this.playerId,
    required this.team,
    required this.confidenceScore,
    required this.confidenceLevel,
    required this.description,
    this.timestamp = 0.0,
    this.frameIdx = 0,
  });

  factory VolleyballViolation.fromJson(Map<String, dynamic> json) {
    return VolleyballViolation(
      rule: json['rule'] as String? ?? 'FIVB Rule Infraction',
      violationType: json['violation_type'] as String? ?? 'UNKNOWN_FAULT',
      playerId: json['player_id'] as int? ?? 0,
      team: json['team'] as String? ?? 'Unknown',
      confidenceScore: (json['confidence_score'] as num?)?.toDouble() ?? 0.0,
      confidenceLevel: json['confidence_level'] as String? ?? 'Medium',
      description: json['description'] as String? ?? '',
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
      frameIdx: json['frame_idx'] as int? ?? 0,
    );
  }
}

class VolleyballEvent {
  final String eventType;
  final int playerId;
  final String team;
  final double jumpHeightCm;
  final String confidenceLevel;
  final String description;
  final double timestamp;

  VolleyballEvent({
    required this.eventType,
    required this.playerId,
    required this.team,
    this.jumpHeightCm = 0.0,
    required this.confidenceLevel,
    required this.description,
    this.timestamp = 0.0,
  });

  factory VolleyballEvent.fromJson(Map<String, dynamic> json) {
    return VolleyballEvent(
      eventType: json['event_type'] as String? ?? 'EVENT',
      playerId: json['player_id'] as int? ?? 0,
      team: json['team'] as String? ?? 'Unknown',
      jumpHeightCm: (json['jump_height_cm'] as num?)?.toDouble() ?? 0.0,
      confidenceLevel: json['confidence_level'] as String? ?? 'Medium',
      description: json['description'] as String? ?? '',
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class VolleyballTelemetry {
  final String rallyState;
  final double rallyDurationSeconds;
  final int contactsCount;
  final String? servingTeam;
  final List<VolleyballViolation> activeViolations;
  final List<VolleyballEvent> recentEvents;

  VolleyballTelemetry({
    this.rallyState = 'IDLE',
    this.rallyDurationSeconds = 0.0,
    this.contactsCount = 0,
    this.servingTeam,
    this.activeViolations = const [],
    this.recentEvents = const [],
  });

  factory VolleyballTelemetry.fromJson(Map<String, dynamic> json) {
    var rawViolations = json['active_violations'] as List? ?? [];
    List<VolleyballViolation> violations = rawViolations
        .map((v) => VolleyballViolation.fromJson(v as Map<String, dynamic>))
        .toList();

    var rawEvents = json['recent_events'] as List? ?? [];
    List<VolleyballEvent> events = rawEvents
        .map((e) => VolleyballEvent.fromJson(e as Map<String, dynamic>))
        .toList();

    return VolleyballTelemetry(
      rallyState: json['rally_state'] as String? ?? 'IDLE',
      rallyDurationSeconds: (json['rally_duration_seconds'] as num?)?.toDouble() ?? 0.0,
      contactsCount: json['contacts_count'] as int? ?? 0,
      servingTeam: json['serving_team'] as String?,
      activeViolations: violations,
      recentEvents: events,
    );
  }
}
