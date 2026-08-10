# System Architecture

```mermaid
flowchart LR
    U["Flutter mobile user"] -->|"JWT + JSON/CSV"| API["Flask /api/v1"]
    API --> V["Request validation and user scope"]
    V --> DB[("MySQL")]
    API --> ORCH["Analysis orchestration"]
    ORCH --> FE["Weekly and transaction feature preparation"]
    FE --> LSTM["LSTM v1"]
    FE --> LR["Linear Regression baseline v1"]
    FE --> IF["Isolation Forest v1"]
    LSTM --> RULES["Transparent recommendation engine"]
    IF --> RULES
    DB --> FE
    RULES --> DB
    DB --> API
    API --> U
```

## Boundaries

- Flutter contains no model-training logic.
- Flask routes validate and delegate; machine-learning logic lives in services.
- Model artefacts load once when Flask starts.
- API requests perform inference only and never retrain.
- SQLAlchemy repositories enforce user ownership.
- Alembic manages the MySQL schema.
- The LSTM is the main forecast; Linear Regression remains an internal
  comparison.
- Isolation Forest produces unusual-spending review prompts, not fraud labels.

## Stored entities

Users, transactions, budgets, analysis runs, forecasts, anomaly alerts,
recommendations, and model versions.
