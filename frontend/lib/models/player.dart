/// Model representing a single body keypoint landmark
class PoseKeypoint {
  final String name;
  final double x;
  final double y;
  final double normX;
  final double normY;
  final double confidence;

  PoseKeypoint({
    required this.name,
    required this.x,
    required this.y,
    required this.normX,
    required this.normY,
    required this.confidence,
  });

  factory PoseKeypoint.fromJson(Map<String, dynamic> json) {
    return PoseKeypoint(
      name: json['name'] as String? ?? '',
      x: (json['x'] as num?)?.toDouble() ?? 0.0,
      y: (json['y'] as num?)?.toDouble() ?? 0.0,
      normX: (json['norm_x'] as num?)?.toDouble() ?? 0.0,
      normY: (json['norm_y'] as num?)?.toDouble() ?? 0.0,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
    );
  }
}

/// Model representing athletic biomechanical kinematics
class KinematicsData {
  final double instantSpeedMps;
  final double avgSpeedMps;
  final double maxSpeedMps;
  final double accelerationMps2;
  final double maxAccelerationMps2;
  final double totalDistanceM;
  final int directionChanges;
  final int jumpsCount;
  final double highestJumpCm;
  final String movementState;
  final List<double> velocity;

  KinematicsData({
    this.instantSpeedMps = 0.0,
    this.avgSpeedMps = 0.0,
    this.maxSpeedMps = 0.0,
    this.accelerationMps2 = 0.0,
    this.maxAccelerationMps2 = 0.0,
    this.totalDistanceM = 0.0,
    this.directionChanges = 0,
    this.jumpsCount = 0,
    this.highestJumpCm = 0.0,
    this.movementState = 'standing',
    this.velocity = const [0.0, 0.0],
  });

  factory KinematicsData.fromJson(Map<String, dynamic> json) {
    var rawVel = json['velocity'] as List? ?? [0.0, 0.0];
    List<double> parsedVel = rawVel.map((v) => (v as num).toDouble()).toList();

    return KinematicsData(
      instantSpeedMps: (json['instant_speed_mps'] as num?)?.toDouble() ?? 0.0,
      avgSpeedMps: (json['avg_speed_mps'] as num?)?.toDouble() ?? 0.0,
      maxSpeedMps: (json['max_speed_mps'] as num?)?.toDouble() ?? 0.0,
      accelerationMps2: (json['acceleration_mps2'] as num?)?.toDouble() ?? 0.0,
      maxAccelerationMps2: (json['max_acceleration_mps2'] as num?)?.toDouble() ?? 0.0,
      totalDistanceM: (json['total_distance_m'] as num?)?.toDouble() ?? 0.0,
      directionChanges: json['direction_changes'] as int? ?? 0,
      jumpsCount: json['jumps_count'] as int? ?? 0,
      highestJumpCm: (json['highest_jump_cm'] as num?)?.toDouble() ?? 0.0,
      movementState: json['movement_state'] as String? ?? 'standing',
      velocity: parsedVel.length >= 2 ? parsedVel : [0.0, 0.0],
    );
  }
}

/// Model representing a tracked player in real-time sports analysis
class PlayerTrack {
  final int playerId;
  final double x;
  final double y;
  final double width;
  final double height;
  final double confidence;
  final List<List<double>> trail;
  final double speed;
  final double totalDistance;
  final String team;
  final String courtZone;
  final String courtRow;
  final String role;
  final Map<String, PoseKeypoint> pose;
  final KinematicsData kinematics;

  PlayerTrack({
    required this.playerId,
    required this.x,
    required this.y,
    required this.width,
    required this.height,
    required this.confidence,
    required this.trail,
    this.speed = 0.0,
    this.totalDistance = 0.0,
    this.team = 'unknown',
    this.courtZone = '',
    this.courtRow = '',
    this.role = '',
    Map<String, PoseKeypoint>? pose,
    KinematicsData? kinematics,
  })  : pose = pose ?? {},
        kinematics = kinematics ?? KinematicsData();

  factory PlayerTrack.fromJson(Map<String, dynamic> json) {
    // Parse bbox (either direct coordinates or nested dict)
    double x = 0.0, y = 0.0, width = 0.0, height = 0.0;
    if (json['bbox'] is Map) {
      final b = json['bbox'] as Map<String, dynamic>;
      x = (b['x1'] as num?)?.toDouble() ?? 0.0;
      y = (b['y1'] as num?)?.toDouble() ?? 0.0;
      width = (b['width'] as num?)?.toDouble() ?? 0.0;
      height = (b['height'] as num?)?.toDouble() ?? 0.0;
    } else {
      x = (json['x'] as num?)?.toDouble() ?? 0.0;
      y = (json['y'] as num?)?.toDouble() ?? 0.0;
      width = (json['width'] as num?)?.toDouble() ?? 0.0;
      height = (json['height'] as num?)?.toDouble() ?? 0.0;
    }

    var rawTrail = json['trail'] as List? ?? [];
    List<List<double>> parsedTrail = rawTrail.map((pt) {
      if (pt is List) {
        return pt.map((v) => (v as num).toDouble()).toList();
      }
      return <double>[];
    }).where((pt) => pt.length >= 2).toList();

    // Parse pose keypoints
    Map<String, PoseKeypoint> parsedPose = {};
    if (json['pose'] is Map) {
      final poseMap = json['pose'] as Map<String, dynamic>;
      poseMap.forEach((k, v) {
        if (v is Map<String, dynamic>) {
          parsedPose[k] = PoseKeypoint.fromJson(v);
        }
      });
    }

    // Parse kinematics
    KinematicsData parsedKinematics = KinematicsData();
    if (json['kinematics'] is Map) {
      parsedKinematics = KinematicsData.fromJson(json['kinematics'] as Map<String, dynamic>);
    }

    return PlayerTrack(
      playerId: json['player_id'] as int? ?? 0,
      x: x,
      y: y,
      width: width,
      height: height,
      confidence: (json['confidence'] as num?)?.toDouble() ?? 0.0,
      trail: parsedTrail,
      speed: (json['speed_px_per_frame'] as num?)?.toDouble() ?? 0.0,
      totalDistance: (json['total_distance_px'] as num?)?.toDouble() ?? 0.0,
      team: json['team'] as String? ?? 'unknown',
      courtZone: json['zone'] as String? ?? '',
      courtRow: json['row'] as String? ?? '',
      role: json['role'] as String? ?? '',
      pose: parsedPose,
      kinematics: parsedKinematics,
    );
  }
}
