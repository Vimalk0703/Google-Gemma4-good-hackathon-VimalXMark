import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'theme/malaika_theme.dart';
import 'screens/splash_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: MalaikaApp()));
}

class MalaikaApp extends StatelessWidget {
  const MalaikaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Malaika',
      debugShowCheckedModeBanner: false,
      theme: malaikaTheme(),
      home: const SplashScreen(),
    );
  }
}
