import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/analysis_provider.dart';
import '../../widgets/camera_view.dart';
import '../../widgets/stats_bar.dart';
import '../../widgets/ai_chat_panel.dart';
import '../../widgets/confidence_badge.dart';
import '../reports/match_dashboard_screen.dart';
import '../replay/video_replay_screen.dart';

/// Screen hosting live video feed, real-time bounding boxes, skeletons, kinematics, and AI chat
class LiveAnalysisScreen extends StatefulWidget {
  const LiveAnalysisScreen({Key? key}) : super(key: key);

  @override
  State<LiveAnalysisScreen> createState() => _LiveAnalysisScreenState();
}

class _LiveAnalysisScreenState extends State<LiveAnalysisScreen> {
  bool _showChat = true;
  bool _showSkeleton = true;
  bool _showBoxes = true;
  bool _showTrails = true;

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<AnalysisProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: Text('${provider.selectedSport.toUpperCase().replaceAll('_', ' ')} Live Analysis'),
        actions: [
          // Visual overlay toggles
          IconButton(
            icon: Icon(_showSkeleton ? Icons.accessibility_new : Icons.accessibility, 
                       color: _showSkeleton ? const Color(0xFF06B6D4) : Colors.grey),
            tooltip: 'Toggle Skeletons',
            onPressed: () => setState(() => _showSkeleton = !_showSkeleton),
          ),
          IconButton(
            icon: Icon(_showBoxes ? Icons.crop_free : Icons.check_box_outline_blank,
                       color: _showBoxes ? const Color(0xFF10B981) : Colors.grey),
            tooltip: 'Toggle Bounding Boxes',
            onPressed: () => setState(() => _showBoxes = !_showBoxes),
          ),
          IconButton(
            icon: Icon(_showTrails ? Icons.timeline : Icons.show_chart,
                       color: _showTrails ? const Color(0xFFFF007F) : Colors.grey),
            tooltip: 'Toggle Motion Trails',
            onPressed: () => setState(() => _showTrails = !_showTrails),
          ),
          if (provider.selectedSport == 'volleyball') ...[
            IconButton(
              icon: const Icon(Icons.refresh, color: Color(0xFFF59E0B)),
              tooltip: 'Reset Rally',
              onPressed: () => provider.resetRally(),
            ),
            const VerticalDivider(width: 20, indent: 12, endIndent: 12),
          ] else if (provider.selectedSport == 'kabaddi') ...[
            IconButton(
              icon: const Icon(Icons.refresh, color: Color(0xFFF59E0B)),
              tooltip: 'Reset Raid',
              onPressed: () => provider.resetRaid(),
            ),
            const VerticalDivider(width: 20, indent: 12, endIndent: 12),
          ] else if (provider.selectedSport == 'kho_kho') ...[
            IconButton(
              icon: const Icon(Icons.refresh, color: Color(0xFFF59E0B)),
              tooltip: 'Reset Turn',
              onPressed: () => provider.resetKhoKhoTurn(),
            ),
            const VerticalDivider(width: 20, indent: 12, endIndent: 12),
          ],
          IconButton(
            icon: const Icon(Icons.analytics, color: Color(0xFF06B6D4)),
            tooltip: 'Match Dashboard & Reports',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const MatchDashboardScreen()),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.replay, color: Color(0xFFA855F7)),
            tooltip: 'Video Replay & Scrubber',
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const VideoReplayScreen()),
            ),
          ),
          IconButton(
            icon: Icon(_showChat ? Icons.chat_bubble : Icons.chat_bubble_outline),
            tooltip: 'Toggle AI Assistant',
            onPressed: () => setState(() => _showChat = !_showChat),
          ),

        ],
      ),
      body: Column(
        children: [
          // Top telemetry bar
          StatsBar(
            fps: provider.fps,
            frameCount: provider.frameCount,
            playerCount: provider.activePlayers.length,
            sport: provider.selectedSport,
            isRunning: provider.isRunning,
          ),
          // Sport match status banners
          if (provider.selectedSport == 'volleyball')
            _buildVolleyballRallyBar(provider),
          if (provider.selectedSport == 'kabaddi')
            _buildKabaddiRaidBar(provider),
          if (provider.selectedSport == 'kho_kho')
            _buildKhoKhoStatusBar(provider),
          // Main layout: Video feed + AI Side Panel
          Expanded(
            child: Row(
              children: [
                // Video & Controls
                Expanded(
                  child: Column(
                    children: [
                      // Video viewport
                      Expanded(
                        child: Stack(
                          children: [
                            CameraView(isRunning: provider.isRunning),
                            // Floating bottom controls
                            Positioned(
                              bottom: 16,
                              left: 16,
                              right: 16,
                              child: Center(
                                child: Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFF0F172A).withOpacity(0.85),
                                    borderRadius: BorderRadius.circular(24),
                                    border: Border.all(color: const Color(0xFF334155)),
                                  ),
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      ElevatedButton.icon(
                                        onPressed: () {
                                          if (provider.isRunning) {
                                            provider.stopAnalysis();
                                          } else {
                                            provider.startAnalysis();
                                          }
                                        },
                                        icon: Icon(provider.isRunning ? Icons.stop : Icons.play_arrow),
                                        label: Text(provider.isRunning ? 'Stop Feed' : 'Start Feed'),
                                        style: ElevatedButton.styleFrom(
                                          backgroundColor: provider.isRunning
                                              ? const Color(0xFFEF4444)
                                              : const Color(0xFF10B981),
                                          foregroundColor: Colors.white,
                                        ),
                                      ),
                                      const SizedBox(width: 12),
                                      IconButton(
                                        icon: Icon(
                                          provider.isPaused ? Icons.play_circle : Icons.pause_circle,
                                          color: Colors.white,
                                        ),
                                        tooltip: provider.isPaused ? 'Resume' : 'Pause',
                                        onPressed: provider.isRunning ? () => provider.togglePause() : null,
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      // Active Violations Warning Ticker
                      if (provider.activeViolations.isNotEmpty)
                        Container(
                          width: double.infinity,
                          color: const Color(0xFF7F1D1D),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                          child: Row(
                            children: [
                              const Icon(Icons.warning_amber_rounded, color: Color(0xFFFCA5A5), size: 18),
                              const SizedBox(width: 8),
                              Expanded(
                                child: Text(
                                  'FOUL: ${provider.activeViolations.first.violationType} | Player #${provider.activeViolations.first.playerId} (${provider.activeViolations.first.team}) — ${provider.activeViolations.first.description}',
                                  style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.bold),
                                  overflow: TextOverflow.ellipsis,
                                ),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                decoration: BoxDecoration(
                                  color: Colors.red.shade900,
                                  borderRadius: BorderRadius.circular(4),
                                  border: Border.all(color: Colors.red.shade400),
                                ),
                                child: Text(
                                  '${provider.activeViolations.first.confidenceLevel} Conf',
                                  style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.bold),
                                ),
                              ),
                            ],
                          ),
                        ),
                      // Bottom active players kinematic cards
                      if (provider.activePlayers.isNotEmpty)
                        Container(
                          height: 84,
                          color: const Color(0xFF1E293B),
                          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                          child: ListView.separated(
                            scrollDirection: Axis.horizontal,
                            itemCount: provider.activePlayers.length,
                            separatorBuilder: (_, __) => const SizedBox(width: 12),
                            itemBuilder: (context, index) {
                              final p = provider.activePlayers[index];
                              final kin = p.kinematics;
                              final isAirborne = kin.movementState == 'airborne';

                              return Container(
                                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                                decoration: BoxDecoration(
                                  color: isAirborne ? const Color(0xFF4C1D95) : const Color(0xFF334155),
                                  borderRadius: BorderRadius.circular(8),
                                  border: Border.all(
                                    color: isAirborne ? const Color(0xFFA855F7) : const Color(0xFF06B6D4),
                                    width: isAirborne ? 2 : 1,
                                  ),
                                ),
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  mainAxisAlignment: MainAxisAlignment.center,
                                  children: [
                                    Row(
                                      children: [
                                        Text(
                                          'ID #${p.playerId}',
                                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
                                        ),
                                        const SizedBox(width: 6),
                                        ConfidenceBadge(confidence: p.confidence),
                                        if (p.team != 'unknown' && p.team.isNotEmpty) ...[
                                          const SizedBox(width: 6),
                                          Container(
                                            padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
                                            decoration: BoxDecoration(
                                              color: (p.team == 'Team A' ? const Color(0xFF2563EB) : const Color(0xFFD97706)).withOpacity(0.25),
                                              borderRadius: BorderRadius.circular(4),
                                              border: Border.all(
                                                color: p.team == 'Team A' ? const Color(0xFF60A5FA) : const Color(0xFFFBBF24),
                                                width: 1,
                                              ),
                                            ),
                                            child: Text(
                                              '${p.team == 'Team A' ? 'T-A' : 'T-B'}${p.courtZone.isNotEmpty ? ' ${p.courtZone.replaceAll("Zone ", "Z")}' : ''}',
                                              style: TextStyle(
                                                color: p.team == 'Team A' ? const Color(0xFF93C5FD) : const Color(0xFFFDE68A),
                                                fontSize: 9,
                                                fontWeight: FontWeight.bold,
                                              ),
                                            ),
                                          ),
                                        ],
                                        const SizedBox(width: 6),
                                        Container(
                                          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                          decoration: BoxDecoration(
                                            color: _getStateColor(kin.movementState).withOpacity(0.25),
                                            borderRadius: BorderRadius.circular(4),
                                          ),
                                          child: Text(
                                            kin.movementState.toUpperCase(),
                                            style: TextStyle(
                                              color: _getStateColor(kin.movementState),
                                              fontSize: 9,
                                              fontWeight: FontWeight.bold,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ),
                                    const SizedBox(height: 4),
                                    Row(
                                      children: [
                                        Text(
                                          'Speed: ${kin.instantSpeedMps.toStringAsFixed(1)} m/s',
                                          style: const TextStyle(color: Color(0xFF06B6D4), fontSize: 11, fontWeight: FontWeight.bold),
                                        ),
                                        const SizedBox(width: 8),
                                        Text(
                                          'Max: ${kin.maxSpeedMps.toStringAsFixed(1)}',
                                          style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                                        ),
                                        const SizedBox(width: 8),
                                        Text(
                                          'Dist: ${kin.totalDistanceM.toStringAsFixed(1)}m',
                                          style: const TextStyle(color: Colors.white70, fontSize: 11),
                                        ),
                                        if (kin.jumpsCount > 0) ...[
                                          const SizedBox(width: 8),
                                          Text(
                                            '🦘 ${kin.jumpsCount} (${kin.highestJumpCm.toStringAsFixed(0)}cm)',
                                            style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 11, fontWeight: FontWeight.bold),
                                          ),
                                        ],
                                      ],
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                        ),
                    ],
                  ),
                ),
                // AI Rules Chat Panel
                if (_showChat) const AIChatPanel(),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Color _getStateColor(String state) {
    switch (state) {
      case 'airborne':
        return const Color(0xFFA855F7); // Purple
      case 'sprinting':
        return const Color(0xFFEF4444); // Red
      case 'running':
        return const Color(0xFFF59E0B); // Amber
      case 'walking':
        return const Color(0xFF10B981); // Emerald
      case 'standing':
      default:
        return const Color(0xFF94A3B8); // Gray
    }
  }

  Widget _buildVolleyballRallyBar(AnalysisProvider provider) {
    final state = provider.rallyState.toUpperCase();
    final stateColor = _getRallyStateColor(state);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      color: const Color(0xFF0F172A),
      child: Row(
        children: [
          // Rally State Pill
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: stateColor.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: stateColor, width: 1.5),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(
                    color: stateColor,
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  state,
                  style: TextStyle(
                    color: stateColor,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                    letterSpacing: 0.5,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          // Serving Team
          if (provider.volleyball?.servingTeam != null) ...[
            Text(
              'Server: ${provider.volleyball!.servingTeam}',
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
            ),
            const SizedBox(width: 14),
          ],
          // Rally Duration
          if (provider.volleyball != null && provider.volleyball!.rallyDurationSeconds > 0) ...[
            Text(
              '⏱ ${provider.volleyball!.rallyDurationSeconds.toStringAsFixed(1)}s',
              style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.w600),
            ),
            const SizedBox(width: 14),
          ],
          // Contacts
          if (provider.volleyball != null && provider.volleyball!.contactsCount > 0) ...[
            Text(
              'Hits: ${provider.volleyball!.contactsCount}',
              style: const TextStyle(color: Color(0xFFA78BFA), fontSize: 12, fontWeight: FontWeight.w600),
            ),
            const SizedBox(width: 14),
          ],
          // Recent Events
          if (provider.recentEvents.isNotEmpty)
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: provider.recentEvents.take(4).map((e) {
                    final isSpike = e.eventType == 'SPIKE';
                    final color = isSpike ? const Color(0xFFEF4444) : const Color(0xFF06B6D4);
                    return Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: color.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: color.withOpacity(0.5)),
                      ),
                      child: Text(
                        '${e.eventType} #${e.playerId}',
                        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Color _getRallyStateColor(String state) {
    switch (state) {
      case 'RALLY_ACTIVE':
        return const Color(0xFF10B981); // Green
      case 'SERVE':
        return const Color(0xFFF59E0B); // Amber
      case 'POINT_SCORED':
        return const Color(0xFF3B82F6); // Blue
      case 'IDLE':
      default:
        return const Color(0xFF64748B); // Slate
    }
  }

  Widget _buildKabaddiRaidBar(AnalysisProvider provider) {
    final kabaddi = provider.kabaddi;
    final state = kabaddi?.raidState ?? 'WAITING';
    Color stateColor;
    switch (state) {
      case 'RAID_ACTIVE':
        stateColor = const Color(0xFF10B981); // Green
        break;
      case 'RAID_COMPLETE':
        stateColor = const Color(0xFF3B82F6); // Blue
        break;
      case 'WAITING':
      default:
        stateColor = const Color(0xFF64748B); // Slate
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      color: const Color(0xFF0F172A),
      child: Row(
        children: [
          // Raid State Pill
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: stateColor.withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: stateColor, width: 1.5),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: BoxDecoration(color: stateColor, shape: BoxShape.circle),
                ),
                const SizedBox(width: 6),
                Text(
                  state,
                  style: TextStyle(color: stateColor, fontSize: 11, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          // Active Raider
          if (kabaddi?.activeRaiderId != null) ...[
            Text(
              'Raider: #${kabaddi!.activeRaiderId} (${kabaddi.raidingTeam ?? ""})',
              style: const TextStyle(color: Color(0xFF38BDF8), fontSize: 12, fontWeight: FontWeight.w600),
            ),
            const SizedBox(width: 14),
          ],
          // Points
          if (kabaddi != null && kabaddi.raidPoints > 0) ...[
            Text(
              'Pts: ${kabaddi.raidPoints}',
              style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 12, fontWeight: FontWeight.bold),
            ),
            const SizedBox(width: 14),
          ],
          // Do or Die Alert Pill
          if (kabaddi?.doOrDieActive == true) ...[
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFFEF4444).withOpacity(0.2),
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: const Color(0xFFEF4444)),
              ),
              child: const Text(
                'DO OR DIE!',
                style: TextStyle(color: Color(0xFFEF4444), fontSize: 10, fontWeight: FontWeight.bold),
              ),
            ),
            const SizedBox(width: 14),
          ],
          // Empty Raids Count
          if (kabaddi != null && kabaddi.consecutiveEmptyRaids.isNotEmpty) ...[
            Text(
              'Empty: A:${kabaddi.consecutiveEmptyRaids["Team A"] ?? 0} B:${kabaddi.consecutiveEmptyRaids["Team B"] ?? 0}',
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
            ),
            const SizedBox(width: 14),
          ],
          // Recent Events
          if (kabaddi != null && kabaddi.events.isNotEmpty)
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: kabaddi.events.reversed.take(4).map((e) {
                    final isTackle = e.eventType.contains('TACKLE');
                    final color = isTackle ? const Color(0xFFEF4444) : const Color(0xFF10B981);
                    return Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: color.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: color.withOpacity(0.5)),
                      ),
                      child: Text(
                        e.eventType,
                        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _buildKhoKhoStatusBar(AnalysisProvider provider) {
    final khoKho = provider.khoKho;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      color: const Color(0xFF0F172A),
      child: Row(
        children: [
          // Active Chaser Pill
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF06B6D4).withOpacity(0.2),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFF06B6D4), width: 1.5),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 7,
                  height: 7,
                  decoration: const BoxDecoration(color: Color(0xFF06B6D4), shape: BoxShape.circle),
                ),
                const SizedBox(width: 6),
                Text(
                  khoKho?.activeChaserId != null
                      ? 'CHASER #${khoKho!.activeChaserId}'
                      : 'NO ACTIVE CHASER',
                  style: const TextStyle(color: Color(0xFF06B6D4), fontSize: 11, fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ),
          const SizedBox(width: 14),
          // Direction
          if (khoKho?.committedDirection != null) ...[
            Text(
              'Direction: ${khoKho!.committedDirection!.toUpperCase()}',
              style: const TextStyle(color: Color(0xFFA78BFA), fontSize: 12, fontWeight: FontWeight.w600),
            ),
            const SizedBox(width: 14),
          ],
          // Runners Remaining
          Text(
            'Runners: ${khoKho?.runnersRemaining ?? 3} / ${khoKho?.runnersInBatch ?? 3}',
            style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 12, fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 14),
          // Recent Events
          if (khoKho != null && khoKho.events.isNotEmpty)
            Expanded(
              child: SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: khoKho.events.reversed.take(4).map((e) {
                    final isTag = e.eventType == 'RUNNER_TAGGED';
                    final color = isTag ? const Color(0xFFEF4444) : const Color(0xFF10B981);
                    return Container(
                      margin: const EdgeInsets.only(right: 8),
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                        color: color.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(color: color.withOpacity(0.5)),
                      ),
                      child: Text(
                        e.eventType,
                        style: TextStyle(color: color, fontSize: 10, fontWeight: FontWeight.bold),
                      ),
                    );
                  }).toList(),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
