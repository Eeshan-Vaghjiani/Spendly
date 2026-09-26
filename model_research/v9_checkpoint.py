"""Two declared checkpoint policies; no architecture or feature search."""


def v9_candidates(worker):
    reference=worker.ForecastConfig(monitor='val_loss',patience=16,min_delta=0.)
    # patience exceeds the cap: collect all120 stopping epochs and restore the
    # best unregularized predictive checkpoint rather than stopping at a plateau.
    predictive=replace(reference,monitor='val_weighted_mae',patience=121,min_delta=0.)
    return dict(v6_reference=reference,predictive_full_budget=predictive)


def checkpoint_diagnostics(runner,decision):
    rows=[]
    for name in v9_candidates(runner.worker):
        for seed in (42,123,2026):
            result=runner.runs[(name,seed,1.)]
            for fit in result['fits']:
                h=fit['history']; cfg=result['config']
                rows.append(dict(candidate=name,seed=seed,fold=fit['fold'],
                    trained_epochs=len(h['loss']),restored_epoch=len(fit['rates']),
                    checkpoint_metric=cfg.monitor,
                    restored_metric=float(h[cfg.monitor][len(fit['rates'])-1]),
                    final_metric=float(h[cfg.monitor][-1]),
                    mode='software_smoke' if runner.smoke else 'full_development'))
    pd.DataFrame(rows).to_csv(runner.directory/'checkpoint_comparison.csv',index=False)
    write_json(runner.directory/'checkpoint_interpretation.json',dict(selected=decision['selected'],
        interpretation='Restored-epoch comparisons are diagnostics. Held-out fold metrics and paired seed evidence determine selection.',
        scope='Checkpoint policy comparison, not an isolated monitor or patience effect; no960epoch training'))
