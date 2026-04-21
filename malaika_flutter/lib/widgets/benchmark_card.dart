import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import '../theme/malaika_theme.dart';
import '../core/tool_call_tracker.dart';

/// Benchmark summary card — shows aggregate tool call metrics at end of
/// assessment. Real numbers from on-device Gemma 4 E2B execution.
class BenchmarkCard extends StatelessWidget {
  final BenchmarkSummary summary;
  const BenchmarkCard({super.key, required this.summary});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8),
      child: Container(
        decoration: BoxDecoration(
          color: MalaikaColors.surface,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: MalaikaColors.primary.withValues(alpha: 0.2)),
          boxShadow: [
            BoxShadow(
              color: MalaikaColors.primary.withValues(alpha: 0.06),
              blurRadius: 12,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Header
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: MalaikaColors.primaryLight,
                borderRadius: const BorderRadius.only(
                  topLeft: Radius.circular(20),
                  topRight: Radius.circular(20),
                ),
              ),
              child: Column(
                children: [
                  const Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.speed_rounded,
                          size: 20, color: MalaikaColors.primary),
                      SizedBox(width: 8),
                      Text(
                        'Agentic Tool Call Benchmark',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.w700,
                          color: MalaikaColors.primary,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: MalaikaColors.primary.withValues(alpha: 0.08),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Text(
                      'Gemma 4 E2B  |  Fully Offline  |  On-Device GPU',
                      style: TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w600,
                        color: MalaikaColors.primaryDark,
                        letterSpacing: 0.3,
                      ),
                    ),
                  ),
                ],
              ),
            ),

            // Top-level metrics
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
              child: Row(
                children: [
                  _MetricTile(
                    label: 'Tool Calls',
                    value: '${summary.totalToolCalls}',
                    icon: Icons.build_rounded,
                  ),
                  _MetricTile(
                    label: 'Avg Latency',
                    value: '${summary.avgLatencyMs.round()}ms',
                    icon: Icons.timer_rounded,
                  ),
                  _MetricTile(
                    label: 'Success',
                    value: '${(summary.successRate * 100).round()}%',
                    icon: Icons.check_circle_rounded,
                  ),
                ],
              ),
            ),

            Padding(
              padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
              child: Row(
                children: [
                  _MetricTile(
                    label: 'LLM Calls',
                    value: '${summary.llmCallCount}',
                    subtitle: '${summary.llmTotalMs}ms total',
                    icon: Icons.psychology_rounded,
                  ),
                  _MetricTile(
                    label: 'Vision Calls',
                    value: '${summary.visionCallCount}',
                    subtitle: '${summary.visionTotalMs}ms total',
                    icon: Icons.visibility_rounded,
                  ),
                  _MetricTile(
                    label: 'Deterministic',
                    value: '${summary.deterministicCallCount}',
                    subtitle: '${summary.deterministicTotalMs}ms total',
                    icon: Icons.verified_rounded,
                  ),
                ],
              ),
            ),

            // Skill breakdown
            if (summary.bySkill.isNotEmpty) ...[
              const Padding(
                padding: EdgeInsets.fromLTRB(16, 16, 16, 8),
                child: Text(
                  'Skill Breakdown',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: MalaikaColors.textSecondary,
                  ),
                ),
              ),
              ...summary.bySkill.entries.map((e) => _SkillRow(
                    name: e.key,
                    count: e.value.toMap()['count'] as int,
                    avgMs: e.value.toMap()['avgMs'] as int,
                  )),
            ],

            // Copy JSON button
            Padding(
              padding: const EdgeInsets.all(16),
              child: SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  onPressed: () {
                    final json = summary.toMap().toString();
                    Clipboard.setData(ClipboardData(text: json));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text('Benchmark data copied to clipboard'),
                        duration: Duration(seconds: 2),
                      ),
                    );
                  },
                  icon: const Icon(Icons.copy_rounded, size: 14),
                  label: const Text('Copy Benchmark Data',
                      style: TextStyle(fontSize: 12)),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: MalaikaColors.primary,
                    side: BorderSide(
                        color: MalaikaColors.primary.withValues(alpha: 0.3)),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(12)),
                    padding: const EdgeInsets.symmetric(vertical: 10),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Single metric tile in the top grid.
class _MetricTile extends StatelessWidget {
  final String label;
  final String value;
  final String? subtitle;
  final IconData icon;

  const _MetricTile({
    required this.label,
    required this.value,
    this.subtitle,
    required this.icon,
  });

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
        decoration: BoxDecoration(
          color: MalaikaColors.surfaceAlt,
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          children: [
            Icon(icon, size: 16, color: MalaikaColors.primary),
            const SizedBox(height: 4),
            Text(
              value,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w800,
                color: MalaikaColors.text,
              ),
            ),
            Text(
              label,
              style: const TextStyle(
                fontSize: 9,
                color: MalaikaColors.textMuted,
                fontWeight: FontWeight.w500,
              ),
            ),
            if (subtitle != null)
              Text(
                subtitle!,
                style: const TextStyle(
                  fontSize: 8,
                  color: MalaikaColors.textMuted,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

/// Single skill row in the breakdown section.
class _SkillRow extends StatelessWidget {
  final String name;
  final int count;
  final int avgMs;

  const _SkillRow({
    required this.name,
    required this.count,
    required this.avgMs,
  });

  @override
  Widget build(BuildContext context) {
    final displayName = name
        .replaceAll('_', ' ')
        .split(' ')
        .map((w) => w.isEmpty ? w : '${w[0].toUpperCase()}${w.substring(1)}')
        .join(' ');

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 3),
      child: Row(
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: MalaikaColors.primary.withValues(alpha: 0.4),
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              displayName,
              style: const TextStyle(
                fontSize: 11,
                color: MalaikaColors.text,
              ),
            ),
          ),
          Text(
            '${count}x',
            style: const TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: MalaikaColors.textSecondary,
            ),
          ),
          const SizedBox(width: 12),
          SizedBox(
            width: 50,
            child: Text(
              avgMs < 1000 ? '${avgMs}ms' : '${(avgMs / 1000).toStringAsFixed(1)}s',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: MalaikaColors.primary,
              ),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }
}
