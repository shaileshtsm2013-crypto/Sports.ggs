import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../services/analysis_provider.dart';

/// Screen allowing the user to choose between Volleyball, Kabaddi, and Kho Kho
class SportSelectionScreen extends StatelessWidget {
  const SportSelectionScreen({Key? key}) : super(key: key);

  final List<Map<String, dynamic>> sports = const [
    {
      'id': 'volleyball',
      'name': 'Volleyball',
      'icon': Icons.sports_volleyball,
      'players': '6 vs 6',
      'court': '18m × 9m',
      'desc': 'Rotation tracking, attack line violations, jump height, and rally zones.'
    },
    {
      'id': 'kabaddi',
      'name': 'Kabaddi',
      'icon': Icons.sports_kabaddi,
      'players': '7 vs 7',
      'court': '13m × 10m',
      'desc': 'Baulk line crossing, bonus line detection, tackle formations, and raid timers.'
    },
    {
      'id': 'kho_kho',
      'name': 'Kho Kho',
      'icon': Icons.directions_run,
      'players': '9 vs 9 (3 runners active)',
      'court': '27m × 16m',
      'desc': 'Central lane violations, direction fouls, post turns, and sitting chasers.'
    },
  ];

  @override
  Widget build(BuildContext context) {
    final provider = Provider.of<AnalysisProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Select Sport'),
      ),
      body: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Choose Sport Discipline',
              style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              'Computer vision analyzers and rule enforcement adapt automatically based on your sport.',
              style: TextStyle(color: Color(0xFF94A3B8), fontSize: 14),
            ),
            const SizedBox(height: 24),
            Expanded(
              child: ListView.separated(
                itemCount: sports.length,
                separatorBuilder: (_, __) => const SizedBox(height: 16),
                itemBuilder: (context, index) {
                  final sport = sports[index];
                  final isSelected = provider.selectedSport == sport['id'];

                  return InkWell(
                    onTap: () {
                      provider.setSport(sport['id']);
                      Navigator.pop(context);
                    },
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: const Color(0xFF1E293B),
                        border: Border.all(
                          color: isSelected ? const Color(0xFF06B6D4) : const Color(0xFF334155),
                          width: isSelected ? 2 : 1,
                        ),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(12),
                            decoration: BoxDecoration(
                              color: isSelected ? const Color(0xFF06B6D4).withOpacity(0.2) : const Color(0xFF334155),
                              borderRadius: BorderRadius.circular(8),
                            ),
                            child: Icon(
                              sport['icon'] as IconData,
                              color: isSelected ? const Color(0xFF06B6D4) : Colors.white70,
                              size: 32,
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    Text(
                                      sport['name'],
                                      style: const TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                                    ),
                                    const Spacer(),
                                    if (isSelected)
                                      const Icon(Icons.check_circle, color: Color(0xFF06B6D4), size: 20),
                                  ],
                                ),
                                const SizedBox(height: 4),
                                Row(
                                  children: [
                                    Chip(
                                      label: Text(sport['court'], style: const TextStyle(fontSize: 10)),
                                      visualDensity: VisualDensity.compact,
                                      padding: EdgeInsets.zero,
                                    ),
                                    const SizedBox(width: 6),
                                    Chip(
                                      label: Text(sport['players'], style: const TextStyle(fontSize: 10)),
                                      visualDensity: VisualDensity.compact,
                                      padding: EdgeInsets.zero,
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  sport['desc'],
                                  style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
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
