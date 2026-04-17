import 'package:flutter/material.dart';
import 'theme/malaika_theme.dart';
import 'screens/home_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const MalaikaApp());
}

class MalaikaApp extends StatelessWidget {
  const MalaikaApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Malaika',
      debugShowCheckedModeBanner: false,
      theme: malaikaTheme(),
      home: const HomeScreen(),
    );
  }
}
