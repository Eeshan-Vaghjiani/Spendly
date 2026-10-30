class SmsConsent {
  const SmsConsent({
    this.available = false,
    this.enabled = false,
    this.version,
    this.accountId,
    this.requiredVersion = '2026-10-22',
  });
  factory SmsConsent.fromJson(Map<String, dynamic> json) => SmsConsent(
    available: json['available'] == true,
    enabled: json['enabled'] == true,
    version: json['consent_version'] as String?,
    accountId: json['account_id'] as String?,
    requiredVersion:
        json['required_consent_version'] as String? ?? '2026-10-22',
  );
  final bool available, enabled;
  final String? version;
  final String? accountId;
  final String requiredVersion;
}

class SmsImportStatus {
  const SmsImportStatus({
    this.available = false,
    this.enabled = false,
    this.permission = false,
    this.active = false,
    this.pending = 0,
    this.summary = const {},
    this.lastSync,
    this.error,
    this.historyPending = false,
  });
  factory SmsImportStatus.fromJson(Map<String, dynamic> json) =>
      SmsImportStatus(
        available: json['available'] == true,
        historyPending: json['history_pending'] == true,
        enabled: json['enabled'] == true,
        permission: json['permission'] == true,
        active: json['active'] == true,
        pending: (json['pending'] as num?)?.toInt() ?? 0,
        lastSync: json['last_sync'] is num
            ? DateTime.fromMillisecondsSinceEpoch(
                (json['last_sync'] as num).toInt(),
              )
            : null,
        summary: json['summary'] is Map
            ? Map<String, dynamic>.from(json['summary'] as Map).map(
                (key, value) => MapEntry(key, value is num ? value.toInt() : 0),
              )
            : const {},
        error: json['error'] as String?,
      );
  final bool available, enabled, permission, active;
  final int pending;
  final Map<String, int> summary;
  final DateTime? lastSync;
  final String? error;
  final bool historyPending;
}
