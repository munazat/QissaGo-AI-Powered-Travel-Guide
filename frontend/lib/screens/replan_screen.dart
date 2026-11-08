import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/app_state.dart';
import '../core/models.dart';
import '../widgets/common.dart';

class ReplanScreen extends StatefulWidget {
  const ReplanScreen({super.key, required this.itinerary});

  final Itinerary itinerary;

  @override
  State<ReplanScreen> createState() => _ReplanScreenState();
}

class _ReplanScreenState extends State<ReplanScreen> {
  final _input = TextEditingController();
  bool _busy = false;
  String? _error;
  ReplanResult? _result;
  List<Map<String, dynamic>> _suggestions = [];
  List<Map<String, dynamic>> _versions = [];

  @override
  void initState() {
    super.initState();
    _loadSuggestions();
    _loadVersions();
  }

  @override
  void dispose() {
    _input.dispose();
    super.dispose();
  }

  Future<void> _loadSuggestions() async {
    try {
      final values = await context.read<AppState>().api.weatherSuggestions(widget.itinerary.id);
      if (mounted) setState(() => _suggestions = values);
    } catch (_) {}
  }

  Future<void> _loadVersions() async {
    try {
      final values = await context.read<AppState>().api.versions(widget.itinerary.id);
      if (mounted) setState(() => _versions = values);
    } catch (_) {}
  }

  Future<void> _submit() async {
    final text = _input.text.trim();
    if (text.isEmpty || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final api = context.read<AppState>().api;
      final preview = await api.previewReplan(widget.itinerary.id, text);
      if (!mounted) return;
      final affected = (preview.diff['affected_days'] as List? ?? []).join(', ');
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Apply this change?'),
          content: Text('This will rebuild the remaining schedule for day(s) $affected. Completed stops stay locked.'),
          actions: [
            TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
            FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Apply')),
          ],
        ),
      );
      if (confirmed != true) return;
      final result = await api.replan(widget.itinerary.id, text);
      if (mounted) setState(() => _result = result);
      await _loadVersions();
    } catch (e) {
      if (mounted) setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _restore(int version) async {
    try {
      await context.read<AppState>().api.restoreVersion(widget.itinerary.id, version);
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) showError(context, e);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Update your plan')),
      body: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 760),
          child: ListView(
            padding: const EdgeInsets.all(20),
            children: [
              const Text('Describe a change', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700)),
              const SizedBox(height: 8),
              const Text('Try: “remove stop lhr_fort on day 1” or “start later by 60 minutes on day 2”.'),
              const SizedBox(height: 16),
              TextField(
                controller: _input,
                maxLines: 3,
                decoration: const InputDecoration(border: OutlineInputBorder(), hintText: 'What should change?'),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _busy ? null : _submit,
                icon: const Icon(Icons.refresh),
                label: Text(_busy ? 'Updating...' : 'Apply change'),
              ),
              if (_error != null) ...[
                const SizedBox(height: 16),
                ErrorRetry(message: _error!, onRetry: _submit),
              ],
              if (_result != null) ...[
                const SizedBox(height: 20),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.check_circle_outline),
                    title: Text('Version ${_result!.version} created'),
                    subtitle: Text('Affected days: ${(_result!.diff['affected_days'] as List? ?? []).join(', ')}'),
                  ),
                ),
              ],
              if (_suggestions.isNotEmpty) ...[
                const SizedBox(height: 24),
                const Text('Weather suggestions', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                for (final suggestion in _suggestions)
                  Card(
                    child: ListTile(
                      title: Text('${suggestion['stop_name']} · Day ${suggestion['day']}'),
                      subtitle: Text('${suggestion['message']}'),
                      trailing: suggestion['suggested_place_id'] == null
                          ? null
                          : IconButton(
                              tooltip: 'Use suggestion',
                              icon: const Icon(Icons.arrow_forward),
                              onPressed: () =>
                                  _input.text = 'remove stop ${suggestion['stop_id']} on day ${suggestion['day']}',
                            ),
                    ),
                  ),
              ],
              if (_versions.isNotEmpty) ...[
                const SizedBox(height: 24),
                const Text('Previous versions', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
                for (final version in _versions)
                  ListTile(
                    title: Text('Version ${version['version']}'),
                    subtitle: Text('${version['reason'] ?? ''}'),
                    trailing: TextButton(
                      onPressed: () => _restore(version['version'] as int),
                      child: const Text('Restore'),
                    ),
                  ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
