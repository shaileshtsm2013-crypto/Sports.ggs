/// Models for Kabaddi sport-specific rules, events, and telemetry

class KabaddiViolation {
  final String violationType;
  final int? raiderId;
  final int? playerId;
  final String? team;
  final String description;
  final double confidence;
  final String confidenceLevel;
  final double timestamp;

  KabaddiViolation({
    required this.violationType,
    this.raiderId,
    this.playerId,
    this.team,
    required this.description,
    this.confidence = 0.9,
    this.confidenceLevel = 'High',
    this.timestamp = 0.0,
  });

  factory KabaddiViolation.fromJson(Map<String, dynamic> json) {
    return KabaddiViolation(
      violationType: json['violation_type'] as String? ?? 'VIOLATION',
      raiderId: json['raider_id'] as int?,
      playerId: json['player_id'] as int?,
      team: json['team'] as String?,
      description: json['description'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.9,
      confidenceLevel: json['confidence_level'] as String? ?? 'High',
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class KabaddiEvent {
  final String eventType;
  final int? raiderId;
  final String? raidingTeam;
  final int points;
  final String description;
  final double confidence;
  final String confidenceLevel;
  final double timestamp;

  KabaddiEvent({
    required this.eventType,
    this.raiderId,
    this.raidingTeam,
    this.points = 0,
    required this.description,
    this.confidence = 0.9,
    this.confidenceLevel = 'High',
    this.timestamp = 0.0,
  });

  factory KabaddiEvent.fromJson(Map<String, dynamic> json) {
    return KabaddiEvent(
      eventType: json['event_type'] as String? ?? 'EVENT',
      raiderId: json['raider_id'] as int?,
      raidingTeam: json['raiding_team'] as String?,
      points: (json['points'] as int?) ?? (json['bonus_points'] as int?) ?? 0,
      description: json['description'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.9,
      confidenceLevel: json['confidence_level'] as String? ?? 'High',
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class KabaddiTelemetry {
  final String raidState;
  final int? activeRaiderId;
  final String? raidingTeam;
  final int raidPoints;
  final Map<String, int> consecutiveEmptyRaids;
  final bool doOrDieActive;
  final List<KabaddiEvent> events;
  final List<KabaddiViolation> violations;

  KabaddiTelemetry({
    this.raidState = 'WAITING',
    this.activeRaiderId,
    this.raidingTeam,
    this.raidPoints = 0,
    this.consecutiveEmptyRaids = const {},
    this.doOrDieActive = false,
    this.events = const [],
    this.violations = const [],
  });

  factory KabaddiTelemetry.fromJson(Map<String, dynamic> json) {
    var rawEvents = json['events'] as List? ?? [];
    List<KabaddiEvent> evts = rawEvents
        .map((e) => KabaddiEvent.fromJson(e as Map<String, dynamic>))
        .toList();

    var rawViolations = json['violations'] as List? ?? [];
    List<KabaddiViolation> viols = rawViolations
        .map((v) => KabaddiViolation.fromJson(v as Map<String, dynamic>))
        .toList();

    Map<String, int> emptyRaids = {};
    if (json['consecutive_empty_raids'] is Map) {
      (json['consecutive_empty_raids'] as Map).forEach((k, v) {
        emptyRaids[k.toString()] = (v as num).toInt();
      });
    }

    return KabaddiTelemetry(
      raidState: json['raid_state'] as String? ?? 'WAITING',
      activeRaiderId: json['active_raider_id'] as int?,
      raidingTeam: json['raiding_team'] as String?,
      raidPoints: json['raid_points'] as int? ?? 0,
      consecutiveEmptyRaids: emptyRaids,
      doOrDieActive: json['do_or_die_active'] as bool? ?? false,
      events: evts,
      violations: viols,
    );
  }
}
