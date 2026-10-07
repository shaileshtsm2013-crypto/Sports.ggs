/// Model representing a recorded or active sports match session
class MatchSession {
  final int id;
  final String sportType;
  final String title;
  final String startedAt;
  final String? endedAt;
  final String status;
  final int totalPlayers;
  final double fps;
  final String? notes;

  MatchSession({
    required this.id,
    required this.sportType,
    required this.title,
    required this.startedAt,
    this.endedAt,
    this.status = 'active',
    this.totalPlayers = 0,
    this.fps = 0.0,
    this.notes,
  });

  factory MatchSession.fromJson(Map<String, dynamic> json) {
    return MatchSession(
      id: json['id'] as int? ?? 0,
      sportType: json['sport_type'] as String? ?? 'volleyball',
      title: json['title'] as String? ?? 'Match Session',
      startedAt: json['started_at'] as String? ?? '',
      endedAt: json['ended_at'] as String?,
      status: json['status'] as String? ?? 'active',
      totalPlayers: json['total_players'] as int? ?? 0,
      fps: (json['fps'] as num?)?.toDouble() ?? 0.0,
      notes: json['notes'] as String?,
    );
  }
}
