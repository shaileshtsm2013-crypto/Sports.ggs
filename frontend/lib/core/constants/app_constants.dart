/// Application wide constants for Sports Analyzer AI.
class AppConstants {
  static const String appName = 'Sports Analyzer AI';
  static const String appVersion = '1.0.0';

  // Network URLs (configurable for localhost / emulator / LAN)
  static const String defaultHost = '127.0.0.1';
  static const int defaultPort = 8000;
  static const String baseApiUrl = 'http://$defaultHost:$defaultPort/api';
  static const String baseWsUrl = 'ws://$defaultHost:$defaultPort/api/analysis/ws/live';
  static const String mjpegStreamUrl = 'http://$defaultHost:$defaultPort/api/analysis/feed/mjpeg';

  // Sports identifiers
  static const String sportVolleyball = 'volleyball';
  static const String sportKabaddi = 'kabaddi';
  static const String sportKhoKho = 'kho_kho';

  static const List<String> supportedSports = [
    sportVolleyball,
    sportKabaddi,
    sportKhoKho,
  ];

  // Refresh intervals
  static const int telemetryPollingIntervalMs = 33; // ~30 fps
  static const int statusCheckIntervalSec = 2;
}
