/// Models for Kho Kho sport-specific rules, events, and telemetry

class KhoKhoViolation {
  final String violationType;
  final int? chaserId;
  final String description;
  final double confidence;
  final String confidenceLevel;
  final double timestamp;

  KhoKhoViolation({
    required this.violationType,
    this.chaserId,
    required this.description,
    this.confidence = 0.9,
    this.confidenceLevel = 'High',
    this.timestamp = 0.0,
  });

  factory KhoKhoViolation.fromJson(Map<String, dynamic> json) {
    return KhoKhoViolation(
      violationType: json['violation_type'] as String? ?? 'VIOLATION',
      chaserId: (json['chaser_id'] as int?) ?? (json['player_id'] as int?),
      description: json['description'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.9,
      confidenceLevel: json['confidence_level'] as String? ?? 'High',
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class KhoKhoEvent {
  final String eventType;
  final int? activeChaserId;
  final int? sittingChaserId;
  final int? runnerId;
  final String description;
  final double confidence;
  final String confidenceLevel;
  final double timestamp;

  KhoKhoEvent({
    required this.eventType,
    this.activeChaserId,
    this.sittingChaserId,
    this.runnerId,
    required this.description,
    this.confidence = 0.9,
    this.confidenceLevel = 'High',
    this.timestamp = 0.0,
  });

  factory KhoKhoEvent.fromJson(Map<String, dynamic> json) {
    return KhoKhoEvent(
      eventType: json['event_type'] as String? ?? 'EVENT',
      activeChaserId: json['active_chaser_id'] as int?,
      sittingChaserId: json['sitting_chaser_id'] as int?,
      runnerId: json['runner_id'] as int?,
      description: json['description'] as String? ?? '',
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.9,
      confidenceLevel: json['confidence_level'] as String? ?? 'High',
      timestamp: (json['timestamp'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

class KhoKhoTelemetry {
  final int? activeChaserId;
  final String? committedDirection;
  final int runnersRemaining;
  final int runnersInBatch;
  final List<KhoKhoEvent> events;
  final List<KhoKhoViolation> violations;

  KhoKhoTelemetry({
    this.activeChaserId,
    this.committedDirection,
    this.runnersRemaining = 3,
    this.runnersInBatch = 3,
    this.events = const [],
    this.violations = const [],
  });

  factory KhoKhoTelemetry.fromJson(Map<String, dynamic> json) {
    var rawEvents = json['events'] as List? ?? [];
    List<KhoKhoEvent> evts = rawEvents
        .map((e) => KhoKhoEvent.fromJson(e as Map<String, dynamic>))
        .toList();

    var rawViolations = json['violations'] as List? ?? [];
    List<KhoKhoViolation> viols = rawViolations
        .map((v) => KhoKhoViolation.fromJson(v as Map<String, dynamic>))
        .toList();

    return KhoKhoTelemetry(
      activeChaserId: json['active_chaser_id'] as int?,
      committedDirection: json['chaser_committed_direction'] as String? ?? json['committed_direction'] as String?,
      runnersRemaining: json['runners_remaining'] as int? ?? 3,
      runnersInBatch: json['runners_in_batch'] as int? ?? 3,
      events: evts,
      violations: viols,
    );
  }
}
