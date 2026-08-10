class UserProfile {
  const UserProfile({
    required this.id,
    required this.email,
    required this.displayName,
    this.hasRequiredConsents = true,
    this.modelTrainingOptIn = false,
  });

  factory UserProfile.fromJson(Map<String, dynamic> json) => UserProfile(
    id: json['id'] as String,
    email: json['email'] as String,
    displayName: json['display_name'] as String,
    hasRequiredConsents: json['has_required_consents'] as bool? ?? false,
    modelTrainingOptIn: json['model_training_opt_in'] as bool? ?? false,
  );

  final String id;
  final String email;
  final String displayName;
  final bool hasRequiredConsents;
  final bool modelTrainingOptIn;
}

class TransactionRecord {
  const TransactionRecord({
    required this.id,
    required this.timestamp,
    required this.amount,
    required this.category,
    required this.transactionType,
    required this.isRecurring,
    this.merchant,
  });

  factory TransactionRecord.fromJson(Map<String, dynamic> json) =>
      TransactionRecord(
        id: json['id'] as String,
        timestamp: DateTime.parse(json['transaction_timestamp'] as String),
        amount: (json['amount'] as num).toDouble(),
        category: json['category'] as String,
        transactionType: json['transaction_type'] as String,
        merchant: json['merchant'] as String?,
        isRecurring: json['is_recurring'] as bool? ?? false,
      );

  final String id;
  final DateTime timestamp;
  final double amount;
  final String category;
  final String transactionType;
  final String? merchant;
  final bool isRecurring;
}

class BudgetRecord {
  const BudgetRecord({
    required this.id,
    required this.periodStart,
    required this.periodEnd,
    required this.category,
    required this.amount,
  });

  factory BudgetRecord.fromJson(Map<String, dynamic> json) => BudgetRecord(
    id: json['id'] as String,
    periodStart: DateTime.parse(json['period_start'] as String),
    periodEnd: DateTime.parse(json['period_end'] as String),
    category: json['category'] as String,
    amount: (json['amount'] as num).toDouble(),
  );

  final String id;
  final DateTime periodStart;
  final DateTime periodEnd;
  final String category;
  final double amount;
}

class CashflowPoint {
  const CashflowPoint({
    required this.periodStart,
    required this.periodEnd,
    required this.label,
    required this.income,
    required this.expense,
    required this.net,
  });

  factory CashflowPoint.fromJson(Map<String, dynamic> json) => CashflowPoint(
    periodStart: DateTime.parse(json['period_start'] as String),
    periodEnd: DateTime.parse(json['period_end'] as String),
    label: json['label'] as String,
    income: (json['income'] as num).toDouble(),
    expense: (json['expense'] as num).toDouble(),
    net: (json['net'] as num).toDouble(),
  );

  final DateTime periodStart;
  final DateTime periodEnd;
  final String label;
  final double income;
  final double expense;
  final double net;
}

class CashflowSummary {
  const CashflowSummary({
    required this.income,
    required this.expense,
    required this.net,
    required this.cashBalance,
    required this.savingsRate,
    required this.budgeted,
  });

  factory CashflowSummary.fromJson(Map<String, dynamic> json) =>
      CashflowSummary(
        income: (json['income'] as num).toDouble(),
        expense: (json['expense'] as num).toDouble(),
        net: (json['net'] as num).toDouble(),
        cashBalance: (json['cash_balance'] as num).toDouble(),
        savingsRate: (json['savings_rate'] as num).toDouble(),
        budgeted: (json['budgeted'] as num).toDouble(),
      );

  final double income;
  final double expense;
  final double net;
  final double cashBalance;
  final double savingsRate;
  final double budgeted;
}

class CashflowAnalytics {
  const CashflowAnalytics({
    required this.resolution,
    required this.periodStart,
    required this.periodEnd,
    required this.summary,
    required this.series,
  });

  factory CashflowAnalytics.fromJson(Map<String, dynamic> json) =>
      CashflowAnalytics(
        resolution: json['resolution'] as String,
        periodStart: DateTime.parse(json['period_start'] as String),
        periodEnd: DateTime.parse(json['period_end'] as String),
        summary: CashflowSummary.fromJson(
          json['summary'] as Map<String, dynamic>,
        ),
        series: (json['series'] as List<dynamic>)
            .cast<Map<String, dynamic>>()
            .map(CashflowPoint.fromJson)
            .toList(growable: false),
      );

  final String resolution;
  final DateTime periodStart;
  final DateTime periodEnd;
  final CashflowSummary summary;
  final List<CashflowPoint> series;
}

class ForecastResult {
  const ForecastResult({
    required this.modelVersion,
    required this.periodStart,
    required this.periodEnd,
    required this.predictedSpending,
    this.baselinePrediction,
    this.historyWeeks = 8,
    this.requiredHistoryWeeks = 8,
    this.dataReadinessPercent = 100,
    this.confidenceLabel = 'Established data',
    this.forecastMethod = 'validated_model_blend',
    this.accuracyPercent,
    this.accuracyNote =
        'Accuracy can be measured after this forecast week ends.',
  });

  factory ForecastResult.fromJson(Map<String, dynamic> json) => ForecastResult(
    modelVersion: json['model_version'] as String,
    periodStart: DateTime.parse(json['period_start'] as String),
    periodEnd: DateTime.parse(json['period_end'] as String),
    predictedSpending: (json['predicted_spending'] as num).toDouble(),
    baselinePrediction: (json['baseline_prediction'] as num?)?.toDouble(),
    historyWeeks: json['history_weeks'] as int? ?? 0,
    requiredHistoryWeeks: json['required_history_weeks'] as int? ?? 8,
    dataReadinessPercent: json['data_readiness_percent'] as int? ?? 0,
    confidenceLabel: json['confidence_label'] as String? ?? 'Very low',
    forecastMethod:
        json['forecast_method'] as String? ?? 'personal_spending_baseline',
    accuracyPercent: (json['accuracy_percent'] as num?)?.toDouble(),
    accuracyNote:
        json['accuracy_note'] as String? ??
        'Accuracy can be measured after this forecast week ends.',
  );

  final String modelVersion;
  final DateTime periodStart;
  final DateTime periodEnd;
  final double predictedSpending;
  final double? baselinePrediction;
  final int historyWeeks;
  final int requiredHistoryWeeks;
  final int dataReadinessPercent;
  final String confidenceLabel;
  final String forecastMethod;
  final double? accuracyPercent;
  final String accuracyNote;
}

class AlertResult {
  const AlertResult({
    required this.isUnusualSpending,
    this.id,
    this.anomalyScore,
    this.explanation,
  });

  factory AlertResult.fromJson(Map<String, dynamic> json) => AlertResult(
    id: json['id'] as String?,
    isUnusualSpending: json['is_unusual_spending'] as bool? ?? false,
    anomalyScore: (json['anomaly_score'] as num?)?.toDouble(),
    explanation: json['explanation'] as String?,
  );

  final String? id;
  final bool isUnusualSpending;
  final double? anomalyScore;
  final String? explanation;
}

class RecommendationResult {
  const RecommendationResult({
    required this.code,
    required this.title,
    required this.message,
    required this.severity,
    required this.reason,
    required this.suggestedAction,
    required this.disclaimer,
  });

  factory RecommendationResult.fromJson(Map<String, dynamic> json) =>
      RecommendationResult(
        code: json['recommendation_code'] as String,
        title: json['title'] as String,
        message: json['message'] as String,
        severity: json['severity'] as String,
        reason: json['reason'] as String? ?? '',
        suggestedAction: json['suggested_action'] as String? ?? '',
        disclaimer: json['disclaimer'] as String? ?? '',
      );

  final String code;
  final String title;
  final String message;
  final String severity;
  final String reason;
  final String suggestedAction;
  final String disclaimer;
}

class AnalysisResult {
  const AnalysisResult({
    required this.id,
    required this.generatedAt,
    required this.forecast,
    required this.alerts,
    required this.recommendations,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    final alertSummary = json['alert_summary'] as Map<String, dynamic>;
    final alertItems = List<Map<String, dynamic>>.from(
      (alertSummary['alerts'] as List<dynamic>? ?? const <dynamic>[])
          .cast<Map<String, dynamic>>(),
    );
    if (alertItems.isEmpty) {
      alertItems.add({
        'is_unusual_spending':
            alertSummary['unusual_spending_detected'] as bool? ?? false,
        'explanation': 'No unusual-spending alert was produced.',
      });
    }
    return AnalysisResult(
      id: json['analysis_run_id'] as String,
      generatedAt: DateTime.parse(json['generated_at'] as String),
      forecast: ForecastResult.fromJson(
        json['forecast'] as Map<String, dynamic>,
      ),
      alerts: alertItems.map(AlertResult.fromJson).toList(growable: false),
      recommendations: (json['recommendations'] as List<dynamic>)
          .cast<Map<String, dynamic>>()
          .map(RecommendationResult.fromJson)
          .toList(growable: false),
    );
  }

  final String id;
  final DateTime generatedAt;
  final ForecastResult forecast;
  final List<AlertResult> alerts;
  final List<RecommendationResult> recommendations;
}
