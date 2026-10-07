import 'package:flutter/material.dart';

/// Dark athletic theme with high-visibility accents for sports tracking
class AppTheme {
  static const Color darkBackground = Color(0xFF0F172A); // Slate 900
  static const Color surfaceColor = Color(0xFF1E293B);    // Slate 800
  static const Color cardColor = Color(0xFF273549);       // Slate 700
  
  // Vibrant accents
  static const Color primaryCyan = Color(0xFF06B6D4);     // Cyan 500
  static const Color accentNeon = Color(0xFF10B981);      // Emerald 500
  static const Color warningOrange = Color(0xFFF59E0B);   // Amber 500
  static const Color dangerRed = Color(0xFFEF4444);       // Red 500

  // Text colors
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  static ThemeData get darkTheme {
    return ThemeData(
      brightness: Brightness.dark,
      scaffoldBackgroundColor: darkBackground,
      primaryColor: primaryCyan,
      cardColor: surfaceColor,
      colorScheme: const ColorScheme.dark(
        primary: primaryCyan,
        secondary: accentNeon,
        surface: surfaceColor,
        error: dangerRed,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: surfaceColor,
        elevation: 0,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: textPrimary,
          fontSize: 18,
          fontWeight: FontWeight.bold,
          letterSpacing: 0.5,
        ),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryCyan,
          foregroundColor: darkBackground,
          textStyle: const TextStyle(fontWeight: FontWeight.bold),
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        ),
      ),
    );
  }
}
