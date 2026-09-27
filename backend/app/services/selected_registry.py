"""Portable selected-model bridge; no TensorFlow or linear regression at serving time."""
import json
from pathlib import Path
from .model_registry import ModelRegistry
from services.aligned_inference.portable import PortableSelectedModel
from services.aligned_inference.features import anomaly_features,utc_to_reporting_time,next_week_features
import pandas as pd


class SelectedModelRegistry(ModelRegistry):
    def __init__(self,model_root,selected_root):
        super().__init__(model_root,'selected-lstm-v6','selected-if-v6',runtime='lightweight')
        self.selected_root=Path(selected_root)
        self.portable=None

    def load(self):
        # Legacy schema is used only for non-model dashboard/budget summaries.
        self.forecast_schema=json.loads((self.model_root/'forecasting/v1/feature_schema.json').read_text())
        self.anomaly_schema=json.loads((self.model_root/'anomaly/v1/feature_schema.json').read_text())
        self.portable=PortableSelectedModel(self.selected_root)
        self.loaded=True

    @staticmethod
    def history(transactions,owner_id):
        rows=[]
        for t in transactions:
            if t.user_id!=owner_id:raise ValueError('Transaction owner mismatch')
            if t.transaction_type=='expense':
                rows.append(dict(user_id=t.user_id,transaction_id=t.id,transaction_timestamp=t.transaction_timestamp,
                    amount=float(t.amount),category=t.category,merchant=t.merchant or ''))
        frame=pd.DataFrame(rows,columns=['user_id','transaction_id','transaction_timestamp','amount','category','merchant'])
        if len(frame):frame['transaction_timestamp']=utc_to_reporting_time(frame.transaction_timestamp)
        return frame.sort_values(['transaction_timestamp','transaction_id']).reset_index(drop=True)

    def forecast_history(self,transactions,owner_id,target,coverage_start):
        self.ensure_loaded()
        frame=self.history(transactions,owner_id)
        context,features=next_week_features(frame,target,observed_through=target,observed_from=coverage_start)
        return float(self.portable.predict_features(features,context.scale,context.recurring)[0])

    def detect_history(self,transactions,owner_id):
        self.ensure_loaded();frame=self.history(transactions,owner_id)
        if frame.empty:return pd.DataFrame(columns=['transaction_id','anomaly_score','is_unusual_spending','decision_threshold','explanation'])
        features=anomaly_features(frame);scores=self.portable.anomaly_scores(features)
        return pd.DataFrame(dict(transaction_id=frame.transaction_id,anomaly_score=scores,
            is_unusual_spending=scores>=self.portable.threshold,decision_threshold=self.portable.threshold,
            explanation='This entry differs from recorded history.'))

    def info(self):
        self.ensure_loaded()
        return dict(forecasting=dict(version=self.forecast_version,main_model='LSTM',runtime='portable',
            baseline_model=None,aggregation_period='weekly',forecast_horizon=1,synthetic_records_used=True,metrics={}),
            anomaly=dict(version=self.anomaly_version,purpose='unusual spending, not fraud',synthetic_records_used=True,metrics={}))
