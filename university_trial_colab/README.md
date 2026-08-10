# University model-training trial

This folder is a separate teaching copy. It does not change the data or trained
artifacts used by the mobile application.

## Files

- `combined_finance_raw.csv` — one transaction per row, left-joined with the
  user profile, matching monthly/category budget, and any controlled anomaly
  label. Blank merchants, budgets, and labels are intentionally preserved so
  you can demonstrate cleaning.
- `Spending_Model_Trial.ipynb` — a Google Colab-ready walkthrough for data
  inspection, cleaning, visualisation, Isolation Forest anomaly detection,
  weekly spending forecasting, an optional LSTM, evaluation, and artifact
  export.
- `build_combined_csv.py` — reproducibly rebuilds the CSV from the synthetic
  Parquet source files in this project.
- `requirements.txt` — packages used by the notebook.

## Run in Google Colab

1. Open [Google Colab](https://colab.research.google.com/).
2. Upload `Spending_Model_Trial.ipynb`.
3. In the Colab Files panel, upload `combined_finance_raw.csv` when the notebook
   asks for it.
4. Choose **Runtime > Run all**. The LSTM section is optional and takes longer.

The dataset is entirely synthetic. Amounts use KES and the records represent
synthetic Kenyan young-adult finance scenarios; they are not real people or
real banking records.

## Rebuild locally

From the project root:

```powershell
python university_trial_colab/build_combined_csv.py
```
