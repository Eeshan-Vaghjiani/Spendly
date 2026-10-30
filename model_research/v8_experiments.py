"""Five fixed income-information candidates; separate forecast-only V8 experiment."""


def resolve_config(config, data, users, end):
    if not any(n.startswith('category_') for n in config.sequence_features):
        return config
    vocab=fit_vocabulary(data.loc[data.transaction_type.eq('expense')],users,end)
    channels=tuple(n for n in config.sequence_features if not n.startswith('category_'))+tuple('category_'+v for v in vocab)
    return replace(config,category_vocabulary=vocab,sequence_features=channels)


def v8_candidates(worker):
    reference=worker.ForecastConfig(monitor='val_loss',patience=16,min_delta=0.)
    control=replace(reference,monitor='val_weighted_mae',patience=10,min_delta=1e-4)
    income=replace(control,context_features=control.context_features+worker.V8_INCOME_CONTEXT)
    sequence=replace(income,sequence_features=income.sequence_features+worker.V8_INCOME_SEQUENCE)
    category=replace(sequence,sequence_features=sequence.sequence_features+('category_PENDING',))
    return dict(v6_reference=reference,predictive_control=control,income_context=income,
                income_sequence=sequence,income_category=category)


def v8_search(runner):
    saved=runner.directory/'v8_selection_complete'
    if verify_checkpoint(saved,runner.identity):
        verify_outputs(runner.directory,json.loads((saved/'outputs.json').read_text()))
        return joblib.load(saved/'selection.joblib')
    if (runner.directory/'configuration_lock.json').exists():
        raise PermissionError('Locked V8 run cannot repeat model selection')
    candidates=v8_candidates(runner.worker)
    records=[]
    for name,cfg in candidates.items():
        for seed in (42,123,2026):
            result=runner.run(name,cfg,'V8 observed information',seed)
            records.append(dict(candidate=name,seed=seed,objective=result['objective'],
                **metrics(result['rows'].rename(columns={'actual':'y','target_week':'time'}),result['rows'].prediction)))
    table=pd.DataFrame(records)
    table.to_csv(runner.directory/'seed_metrics.csv',index=False)
    table.groupby('candidate').agg({n:['mean','std'] for n in ('WAPE','MAE_KES','bias_KES','within_20_percent','objective')}).to_csv(runner.directory/'seed_summary.csv')
    provisional=min(candidates,key=lambda n:(table.loc[table.candidate.eq(n),'objective'].mean(),n!='v6_reference',n))
    comparisons=[]
    for name in candidates:
        pairs=pd.concat([paired_rows(runner.runs[(name,s,1.)]['rows'],runner.runs[('v6_reference',s,1.)]['rows']) for s in (42,123,2026)],ignore_index=True)
        interval=bootstrap(pairs)
        improvement=float((np.abs(pairs.reproduced_v6-pairs.actual).sum()-pairs.absolute_error.sum())/pairs.actual.sum())
        baseline_gain=float((np.abs(pairs.recurring_median-pairs.actual).sum()-pairs.absolute_error.sum())/pairs.actual.sum())
        candidate_folds=pd.concat([runner.runs[(name,s,1.)]['metrics'] for s in (42,123,2026)])
        reference_folds=pd.concat([runner.runs[('v6_reference',s,1.)]['metrics'] for s in (42,123,2026)])
        guards=practical_guardrails(candidate_folds,reference_folds)
        material=evidence_decision(improvement>=.01 and interval['candidate_minus_v6_pp_95'][1]<0
            and baseline_gain>0 and interval['candidate_minus_baseline_pp_95'][1]<0 and all(guards.values()),runner.smoke)
        comparisons.append(dict(candidate=name,material=material,improvement_pp=100*improvement,
            baseline_gain_pp=100*baseline_gain,intervals=interval,guardrails=guards))
    result=next(r for r in comparisons if r['candidate']==provisional)
    decision=dict(provisional_winner=provisional,selected=provisional if result['material'] else 'v6_reference',
        material_improvement_demonstrated=result['material'],execution_mode='software_smoke' if runner.smoke else 'full_development',
        evidence_eligible=not runner.smoke,intervals=result['intervals'],guardrails=result['guardrails'],
        WAPE_improvement_pp=result['improvement_pp'],comparisons=comparisons,
        policy='five fixed configurations; all three seeds; internal adaptive selection; no population/final-test claim')
    write_json(runner.directory/'train_selection_evidence.json',decision)
    saved.mkdir(exist_ok=True)
    joblib.dump((candidates,decision),saved/'selection.joblib')
    atomic_json(saved/'outputs.json',seal_outputs(runner.directory,['seed_metrics.csv','seed_summary.csv','train_selection_evidence.json']))
    seal_checkpoint(saved,runner.identity,['selection.joblib','outputs.json'])
    backup_run(runner.directory,'selection_complete')
    return candidates,decision
