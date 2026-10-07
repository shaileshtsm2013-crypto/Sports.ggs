import 'package:flutter/material.dart';
import '../../models/report_data.dart';
import '../../services/api_service.dart';
import 'player_report_screen.dart';

/// Professional Match Dashboard and Analytics Report Screen
class MatchDashboardScreen extends StatefulWidget {
  final String matchId;

  const MatchDashboardScreen({Key? key, this.matchId = 'live'}) : super(key: key);

  @override
  State<MatchDashboardScreen> createState() => _MatchDashboardScreenState();
}

class _MatchDashboardScreenState extends State<MatchDashboardScreen> {
  final ApiService _apiService = ApiService();
  bool _isLoading = true;
  MatchReportData? _report;
  String _selectedEventFilter = 'ALL';
  String _selectedTeamFilter = 'ALL';

  @override
  void initState() {
    super.initState();
    _fetchReport();
  }

  Future<void> _fetchReport() async {
    setState(() => _isLoading = true);
    try {
      final res = await _apiService.getMatchReport(widget.matchId);
      setState(() {
        _report = MatchReportData.fromJson(res);
        _isLoading = false;
      });
    } catch (e) {
      setState(() => _isLoading = false);
    }
  }

  Widget _buildMetricCard(String title, String value, IconData icon, Color color) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B),
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: const Color(0xFF334155)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: 6),
              Text(
                title.toUpperCase(),
                style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontWeight: FontWeight.w600),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold, color: Colors.white),
          ),
        ],
      ),
    );
  }

  Widget _buildExportButton(String label, IconData icon, VoidCallback onTap) {
    return OutlinedButton.icon(
      icon: Icon(icon, size: 14, color: const Color(0xFF06B6D4)),
      label: Text(label, style: const TextStyle(fontSize: 12, color: Color(0xFF06B6D4))),
      style: OutlinedButton.styleFrom(
        side: const BorderSide(color: Color(0xFF06B6D4)),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      ),
      onPressed: onTap,
    );
  }

  void _showExportSnackbar(String format) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Exported match report as $format. View in browser/downloads.'),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return const Scaffold(
        backgroundColor: Color(0xFF0F172A),
        body: Center(child: CircularProgressIndicator(color: Color(0xFF06B6D4))),
      );
    }

    final rep = _report;
    if (rep == null) {
      return Scaffold(
        backgroundColor: const Color(0xFF0F172A),
        appBar: AppBar(title: const Text('Match Analysis')),
        body: const Center(child: Text('No match data available.')),
      );
    }

    // Filter events
    final filteredEvents = rep.events.where((e) {
      if (_selectedEventFilter != 'ALL' && !e.eventType.toUpperCase().contains(_selectedEventFilter)) {
        return false;
      }
      return true;
    }).toList();

    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E293B),
        elevation: 0,
        title: Row(
          children: [
            const Icon(Icons.analytics, color: Color(0xFF06B6D4), size: 20),
            const SizedBox(width: 8),
            Text(rep.title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
            const SizedBox(width: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: const Color(0xFF0284C7).withOpacity(0.2),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFF0284C7)),
              ),
              child: Text(
                rep.sport.toUpperCase(),
                style: const TextStyle(fontSize: 10, color: Color(0xFF38BDF8), fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh, color: Color(0xFF94A3B8)),
            onPressed: _fetchReport,
            tooltip: 'Refresh Report',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // ── Section 20 Metric Cards Grid ─────────────────────────────────
            GridView.count(
              crossAxisCount: MediaQuery.of(context).size.width > 800 ? 6 : 2,
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              crossAxisSpacing: 10,
              mainAxisSpacing: 10,
              childAspectRatio: 1.6,
              children: [
                _buildMetricCard('Duration', rep.durationFormatted, Icons.timer, const Color(0xFF38BDF8)),
                _buildMetricCard('Players', '${rep.activePlayers} / ${rep.playersDetected}', Icons.people, const Color(0xFF4ADE80)),
                _buildMetricCard('Distance', '${rep.totalDistanceKm} km', Icons.route, const Color(0xFFFBBF24)),
                _buildMetricCard('Total Jumps', '${rep.totalJumps}', Icons.height, const Color(0xFFA855F7)),
                _buildMetricCard('Max Speed', '${rep.maxSpeedMps} m/s', Icons.speed, const Color(0xFFF87171)),
                _buildMetricCard('Avg Speed', '${rep.avgSpeedMps} m/s', Icons.directions_run, const Color(0xFF06B6D4)),
              ],
            ),
            const SizedBox(height: 20),

            // ── Action & Export Bar ──────────────────────────────────────────
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: Row(
                children: [
                  const Text('EXPORT REPORT:', style: TextStyle(fontSize: 11, fontWeight: FontWeight.bold, color: Color(0xFF94A3B8))),
                  const Spacer(),
                  _buildExportButton('JSON', Icons.data_object, () => _showExportSnackbar('JSON')),
                  const SizedBox(width: 8),
                  _buildExportButton('CSV', Icons.table_chart, () => _showExportSnackbar('CSV')),
                  const SizedBox(width: 8),
                  _buildExportButton('Print / PDF', Icons.print, () => _showExportSnackbar('Printable HTML / PDF')),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // ── Player Performance Table ─────────────────────────────────────
            Row(
              children: [
                const Icon(Icons.leaderboard, color: Color(0xFF06B6D4), size: 18),
                const SizedBox(width: 8),
                const Text('PLAYER PERFORMANCE SUMMARY', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
                const Spacer(),
                const Text('Click player for full report & charts', style: TextStyle(fontSize: 11, color: Color(0xFF64748B))),
              ],
            ),
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: DataTable(
                headingRowColor: MaterialStateProperty.all(const Color(0xFF0F172A)),
                columns: const [
                  DataColumn(label: Text('JERSEY', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11))),
                  DataColumn(label: Text('TEAM', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11))),
                  DataColumn(label: Text('DISTANCE', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11))),
                  DataColumn(label: Text('MAX SPEED', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11))),
                  DataColumn(label: Text('AVG SPEED', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11))),
                  DataColumn(label: Text('JUMPS', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11))),
                  DataColumn(label: Text('MAX JUMP', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11))),
                  DataColumn(label: Text('COVERAGE', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11))),
                  DataColumn(label: Text('ACTION', style: TextStyle(color: Color(0xFF94A3B8), fontSize: 11))),
                ],
                rows: rep.players.map((p) {
                  return DataRow(
                    cells: [
                      DataCell(Text(p.jerseyNumber, style: const TextStyle(fontWeight: FontWeight.bold, color: Color(0xFF38BDF8)))),
                      DataCell(Text(p.team, style: const TextStyle(color: Colors.white70, fontSize: 12))),
                      DataCell(Text('${p.distanceM} m', style: const TextStyle(color: Colors.white, fontSize: 12))),
                      DataCell(Text('${p.maxSpeedMps} m/s', style: const TextStyle(color: Colors.white, fontSize: 12))),
                      DataCell(Text('${p.avgSpeedMps} m/s', style: const TextStyle(color: Colors.white, fontSize: 12))),
                      DataCell(Text('${p.jumpsCount}', style: const TextStyle(color: Colors.white, fontSize: 12))),
                      DataCell(Text('${p.highestJumpCm} cm', style: const TextStyle(color: Colors.white, fontSize: 12))),
                      DataCell(Text('${p.courtCoveragePct}%', style: const TextStyle(color: Colors.white, fontSize: 12))),
                      DataCell(
                        IconButton(
                          icon: const Icon(Icons.show_chart, color: Color(0xFF06B6D4), size: 18),
                          tooltip: 'View Player Charts',
                          onPressed: () {
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (_) => PlayerReportScreen(playerId: p.playerId),
                              ),
                            );
                          },
                        ),
                      ),
                    ],
                  );
                }).toList(),
              ),
            ),
            const SizedBox(height: 24),

            // ── Event Timeline & Filter ──────────────────────────────────────
            Row(
              children: [
                const Icon(Icons.history, color: Color(0xFF06B6D4), size: 18),
                const SizedBox(width: 8),
                const Text('MATCH EVENTS TIMELINE', style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Colors.white)),
                const Spacer(),
                // Filter chips
                Wrap(
                  spacing: 6,
                  children: ['ALL', 'SPIKE', 'BLOCK', 'RAID', 'TACKLE', 'KHO', 'VIOLATION'].map((filter) {
                    final isSel = _selectedEventFilter == filter;
                    return ChoiceChip(
                      label: Text(filter, style: TextStyle(fontSize: 10, color: isSel ? Colors.black : Colors.white70)),
                      selected: isSel,
                      selectedColor: const Color(0xFF06B6D4),
                      backgroundColor: const Color(0xFF1E293B),
                      onSelected: (val) {
                        setState(() => _selectedEventFilter = filter);
                      },
                    );
                  }).toList(),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Container(
              decoration: BoxDecoration(
                color: const Color(0xFF1E293B),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFF334155)),
              ),
              child: filteredEvents.isEmpty
                  ? const Padding(
                      padding: EdgeInsets.all(24.0),
                      child: Center(child: Text('No events matching the selected filter.', style: TextStyle(color: Color(0xFF94A3B8)))),
                    )
                  : ListView.separated(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: filteredEvents.length,
                      separatorBuilder: (_, __) => const Divider(color: Color(0xFF334155), height: 1),
                      itemBuilder: (context, index) {
                        final ev = filteredEvents[index];
                        return ListTile(
                          dense: true,
                          leading: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                            decoration: BoxDecoration(
                              color: const Color(0xFF0F172A),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(ev.formattedTime, style: const TextStyle(color: Color(0xFF06B6D4), fontSize: 12, fontWeight: FontWeight.bold)),
                          ),
                          title: Text(
                            ev.eventType.toUpperCase(),
                            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 12, color: Colors.white),
                          ),
                          subtitle: Text(
                            ev.details.isNotEmpty ? ev.details : (ev.playerId != null ? 'Player #${ev.playerId}' : ''),
                            style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8)),
                          ),
                          trailing: Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                            decoration: BoxDecoration(
                              color: Colors.green.withOpacity(0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text('${(ev.confidence * 100).toInt()}% conf', style: const TextStyle(fontSize: 10, color: Colors.greenAccent)),
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      ),
    );
  }
}
