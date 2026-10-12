import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:cross_file/cross_file.dart';

void main() => runApp(const MaterialApp(home: Survey()));

class Survey extends StatefulWidget {
  const Survey({super.key});
  @override
  State<Survey> createState() => _SurveyState();
}

class _SurveyState extends State<Survey> with WidgetsBindingObserver {
  final endpoint = TextEditingController(text: 'http://192.168.1.10:8765');
  bool running = false, busy = false;
  int generation = 0, count = 0;
  String status = 'Connect an SDR bridge to start.', reading = '—';
  File? file;
  Timer? timer;
  final points = <Offset>[];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state != AppLifecycleState.resumed && running) stop();
  }

  void stop() {
    timer?.cancel();
    generation++;
    if (mounted) setState(() { running = false; status = 'Stopped. $count points saved.'; });
  }

  Future<void> start() async {
    if (busy) return;
    busy = true;
    final token = ++generation;
    try {
      final uri = Uri.parse(endpoint.text.trim());
      if (!['http', 'https'].contains(uri.scheme) || uri.host.isEmpty) {
        throw Exception('Enter an HTTP or HTTPS bridge address');
      }
      if (!await Geolocator.isLocationServiceEnabled()) throw Exception('Enable phone location');
      var permission = await Geolocator.checkPermission();
      if (permission == LocationPermission.denied) permission = await Geolocator.requestPermission();
      if (permission == LocationPermission.denied || permission == LocationPermission.deniedForever) {
        throw Exception('Location permission is required');
      }
      final dir = await getApplicationDocumentsDirectory();
      if (!mounted || token != generation) return;
      file = File('${dir.path}/kermit2go_${DateTime.now().millisecondsSinceEpoch}.csv');
      await file!.writeAsString('timestamp,signal_strength_db,signal_strength_s_unit,latitude,longitude,elevation,band_power_dbfs,input_power_dbm,field_strength_v_m,measurement_status,center_frequency_hz,bandwidth_hz,gps_timestamp,gps_accuracy_m\n');
      if (!mounted || token != generation) return;
      setState(() { count = 0; points.clear(); running = true; status = 'Survey running'; });
      timer = Timer.periodic(const Duration(seconds: 1), (_) => sample(uri));
    } catch (e) {
      if (mounted) setState(() => status = e.toString());
    } finally {
      busy = false;
      if (mounted) setState(() {});
    }
  }

  Future<void> sample(Uri base) async {
    if (!running || busy) return;
    busy = true;
    final token = generation;
    try {
      // Fetch a fresh fix for each reading; never silently reuse a cached fix.
      final gps = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(accuracy: LocationAccuracy.high, timeLimit: Duration(seconds: 8)));
      final response = await http.get(base.resolve('/measurement')).timeout(const Duration(seconds: 5));
      if (response.statusCode != 200) throw Exception('Bridge returned ${response.statusCode}');
      final data = jsonDecode(response.body) as Map<String, dynamic>;
      if (!mounted || !running || token != generation) return;
      final power = data['band_power_dbfs'];
      if (power is! num || !power.isFinite) throw Exception('Invalid bridge power');
      final measuredAt = DateTime.parse(data['timestamp'] as String);
      if (DateTime.now().toUtc().difference(measuredAt.toUtc()).inSeconds.abs() > 15) {
        throw Exception('Stale reading or bridge clock mismatch');
      }
      if (measuredAt.toUtc().difference(gps.timestamp.toUtc()).inSeconds.abs() > 15) {
        throw Exception('GPS fix is too old for this RF reading');
      }
      final field = data['field_strength_v_m'];
      if (field != null && (field is! num || !field.isFinite || field < 0 || data['measurement_status'] != 'calibrated_estimate')) {
        throw Exception('Invalid calibrated field');
      }
      String cell(dynamic value) => '"${(value ?? '').toString().replaceAll('"', '""')}"';
      final row = [data['timestamp'], power, '', gps.latitude, gps.longitude, gps.altitude,
        power, data['input_power_dbm'], field, data['measurement_status'],
        data['center_frequency_hz'], data['bandwidth_hz'], gps.timestamp.toUtc().toIso8601String(), gps.accuracy];
      await file!.writeAsString('${row.map(cell).join(',')}\n', mode: FileMode.append, flush: true);
      if (!mounted || token != generation) return;
      setState(() {
        count++;
        points.add(Offset(gps.longitude, gps.latitude));
        reading = field == null ? '${power.toStringAsFixed(1)} dBFS' : '${(field as num).toStringAsPrecision(4)} V/m';
        status = '${data['measurement_status']} · GPS ±${gps.accuracy.toStringAsFixed(0)} m · $count points';
      });
    } catch (e) {
      if (mounted && running && token == generation) setState(() { reading = '—'; status = 'No point saved: $e'; });
    } finally {
      busy = false;
      if (mounted) setState(() {});
    }
  }

  Future<void> export() async {
    try {
      if (file != null) await SharePlus.instance.share(ShareParams(files: [XFile(file!.path)]));
    } catch (e) { if (mounted) setState(() => status = 'Export failed: $e'); }
  }

  @override
  void dispose() {
    generation++;
    timer?.cancel();
    endpoint.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Kermit2Go')),
    body: Padding(padding: const EdgeInsets.all(24), child: Column(
      crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        TextField(controller: endpoint, enabled: !running, decoration: const InputDecoration(labelText: 'SDR bridge address')),
        const SizedBox(height: 24),
        Text(reading, style: Theme.of(context).textTheme.displaySmall),
        Text(status),
        const Text('RMS level in the tuned SDR band. V/m requires calibration.'),
        const SizedBox(height: 16),
        FilledButton(onPressed: running ? stop : start, child: Text(running ? 'Stop survey' : 'Start survey')),
        OutlinedButton(onPressed: file != null && !running && !busy ? export : null, child: const Text('Export CSV')),
        const SizedBox(height: 16),
        const Text('Survey track (relative coordinates)'),
        Expanded(child: CustomPaint(painter: Track(List.of(points)), child: const SizedBox.expand())),
      ])),
  );
}

class Track extends CustomPainter {
  final List<Offset> points;
  Track(this.points);
  @override
  void paint(Canvas canvas, Size size) {
    if (points.isEmpty) return;
    double minX = points.first.dx, maxX = minX, minY = points.first.dy, maxY = minY;
    for (final p in points) {
      if (p.dx < minX) minX = p.dx; if (p.dx > maxX) maxX = p.dx;
      if (p.dy < minY) minY = p.dy; if (p.dy > maxY) maxY = p.dy;
    }
    final dx = (maxX - minX).clamp(0.0001, 360.0), dy = (maxY - minY).clamp(0.0001, 180.0);
    final path = Path();
    final paint = Paint()..color = Colors.green..strokeWidth = 3..style = PaintingStyle.stroke;
    for (var i = 0; i < points.length; i++) {
      final p = points[i];
      final x = 12 + (p.dx - minX) / dx * (size.width - 24);
      final y = size.height - 12 - (p.dy - minY) / dy * (size.height - 24);
      if (i == 0) { path.moveTo(x, y); } else { path.lineTo(x, y); }
      canvas.drawCircle(Offset(x, y), 3, Paint()..color = Colors.green);
    }
    canvas.drawPath(path, paint);
  }
  @override
  bool shouldRepaint(covariant Track oldDelegate) => true;
}
