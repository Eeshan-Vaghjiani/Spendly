"""Predeclared, train-only staged experiments and locked one-pass legacy benchmark."""


class ExperimentRunner:
    def __init__(self, data, worker, directory, cache, code_hash, device, workers=2, smoke=False,
                 benchmark_role='legacy reused development benchmark'):
        self.data,self.worker,self.directory,self.cache=data,worker,directory,cache
        self.code_hash,self.device,self.workers,self.smoke=code_hash,device,workers,smoke
        self.folds=fixed_folds(data,smoke)
        self.registry=[]; self.fold_metrics=[]; self.runs={}; self.histories=[]
        self.feature_sets={}
        self.benchmark_role=benchmark_role
        self.identity=digest(dict(code=code_hash,smoke=smoke,device=device,benchmark_role=benchmark_role,
            data=hashlib.sha256(pd.util.hash_pandas_object(data,index=True).values.tobytes()).hexdigest(),
            versions={n:importlib.metadata.version(n) for n in ('numpy','pandas','tensorflow','keras','scikit-learn','joblib')}))
        bind_run(directory,self.identity)
        restore_runner(self)

    def bundle(self, config, end=None):
        feature_keys=('lookback','sequence_features','context_features','category_vocabulary','target_transform','scale_method')
        key=digest(dict(config={k:asdict(config)[k] for k in feature_keys},end=end))
        if key not in self.feature_sets:
            data=restrict_history(self.data,pd.Timestamp(end)) if end else self.data
            # Bounded in-memory feature configurations; disk cache remains resumable.
            if len(self.feature_sets)>=4:
                self.feature_sets.pop(next(iter(self.feature_sets)))
            self.feature_sets[key]=features(data,config,self.worker,self.cache,self.code_hash,self.workers)
        return self.feature_sets[key]

    def register(self, name, config, stage, diagnostic=False):
        prior=[r for r in self.registry if r['candidate']==name]
        if prior:
            return
        if not diagnostic and sum(not r['diagnostic'] for r in self.registry)>=14:
            raise ValueError('Predeclared 14-configuration budget exceeded')
        self.registry.append(dict(candidate=name,stage=stage,diagnostic=diagnostic,
            execution_mode='software_smoke' if self.smoke else 'full_development',
            effective_epoch_cap=min(config.max_epochs,2) if self.smoke else config.max_epochs,
            configuration=json.dumps(asdict(config),sort_keys=True),configuration_hash=digest(asdict(config))))
        pd.DataFrame(self.registry).to_csv(self.directory/'experiment_registry.csv',index=False)

    def run(self, name, cfg, stage, seed=42, fraction=1., diagnostic=False):
        key=(name,seed,fraction)
        if key in self.runs:
            if asdict(self.runs[key]['config'])!=asdict(replace(cfg,seed=seed,max_epochs=min(cfg.max_epochs,2) if self.smoke else cfg.max_epochs)):
                raise ValueError('Saved experiment configuration differs')
            print('RESUMED completed experiment:',name,seed,fraction,flush=True)
            return self.runs[key]
        if (self.directory/'configuration_lock.json').exists():
            raise PermissionError('Configuration locked: no further train-fold experiments')
        # An interrupted same-kernel attempt may have appended earlier fold evidence.
        # Replace that attempt rather than counting it twice on retry.
        self.fold_metrics=[r for r in self.fold_metrics if not
            ((r['candidate']==name or r['candidate'].startswith(name+'::')) and
             r['seed']==seed and r['fraction']==fraction)]
        self.histories=[h for h in self.histories if not
            (h.candidate.iloc[0]==name and h.seed.iloc[0]==seed and h.fraction.iloc[0]==fraction)]
        self.register(name,cfg,stage,diagnostic)
        cfg=replace(cfg,seed=seed,max_epochs=min(cfg.max_epochs,2) if self.smoke else cfg.max_epochs)
        records=[]; fits=[]; frames=[]
        for fold in self.folds:
            print(f'{stage}: {name}, seed {seed}, fold {fold["fold"]}, fraction {fraction}',flush=True)
            inner,outer,end=map(pd.Timestamp,(fold['inner'],fold['outer'],fold['end']))
            fit_users=fold['fit_users'][:max(1,int(len(fold['fit_users'])*fraction))]
            refit_users=sorted(set(fit_users)|set(fold['stop_users']))
            resolved=resolve_config(cfg,self.data,fit_users,inner)
            bundle=self.bundle(resolved)
            f=bundle[0]
            common=f.time.ge(self.data.observation_start.min()+pd.Timedelta(weeks=26))
            train=subset(bundle,common&f.user_id.isin(fit_users)&f.end.le(inner))
            stop=subset(bundle,common&f.user_id.isin(fold['stop_users'])&f.time.ge(inner)&f.end.le(outer))
            evaluation=subset(bundle,common&f.user_id.isin(fold['eval_users'])&f.time.ge(outer)&f.end.le(end))
            assert not set(train[0].user_id)&set(stop[0].user_id)
            assert not (set(train[0].user_id)|set(stop[0].user_id))&set(evaluation[0].user_id)
            assert train[0].end.max()<=stop[0].time.min()
            assert stop[0].end.max()<=evaluation[0].time.min()
            folder=self.directory/'experiments'/name/f'seed_{seed}'/f'fold_{fold["fold"]}_fraction_{fraction}'
            chosen=train_model(train,stop,resolved,folder/'stopping',self.device,fit_users,inner)
            self.histories.append(pd.DataFrame(chosen['history']).assign(candidate=name,seed=seed,fold=fold['fold'],fraction=fraction,phase='stopping'))
            refit=subset(bundle,common&f.user_id.isin(refit_users)&f.end.le(outer))
            fitted=train_model(refit,None,resolved,folder/'refit',self.device,refit_users,outer,replay=chosen['rates'])
            prediction,pred_seconds=predict(fitted,evaluation,self.device)
            train_prediction,_=predict(fitted,refit,self.device)
            measured=metrics(evaluation[0],prediction)
            rec=dict(candidate=name,seed=seed,fold=fold['fold'],fraction=fraction,stage=stage,
                **measured,parameters=fitted['parameters'],train_seconds=chosen['seconds']+fitted['seconds'],
                inference_seconds=pred_seconds,best_epoch=chosen['best_epoch'],
                train_WAPE=metrics(refit[0],train_prediction)['WAPE'],gradient_norm=chosen['gradient_norm'])
            records.append(rec); self.fold_metrics.append(rec)
            rows=row_predictions(evaluation[0],prediction,name,fold['fold'],seed)
            subgroup_rows=[]
            for column in ('volatility','activity','recurring_share','zero_fraction'):
                groups=pd.qcut(rows[column],4,duplicates='drop')
                for value,g in rows.groupby(groups,observed=True):
                    subgroup_rows.append(dict(subgroup_feature=column,subgroup=str(value),
                        **metrics(g.rename(columns={'actual':'y','target_week':'time'}),g.prediction)))
            pd.DataFrame(subgroup_rows).to_csv(folder/'causal_subgroup_metrics.csv',index=False)
            frames.append(rows)
            fits.append(dict(rates=chosen['rates'],history=chosen['history'],fold=fold['fold'],parameters=fitted['parameters']))
            for baseline,column in [('recurring_median','robust_recurring'),('recurring_mean','recurring'),('last_week','last'),('mean4','mean4')]:
                self.fold_metrics.append(dict(candidate=name+'::'+baseline,seed=seed,fold=fold['fold'],fraction=fraction,
                    stage=stage,**metrics(evaluation[0],evaluation[0][column]),parameters=0,train_seconds=0.,inference_seconds=0.))
            del chosen,fitted
            pd.DataFrame(self.fold_metrics).to_csv(self.directory/'fold_metrics.csv',index=False)
        result=dict(config=cfg,rows=pd.concat(frames,ignore_index=True),metrics=pd.DataFrame(records),fits=fits,
                    objective=float(np.mean([r['selection_objective'] for r in records])))
        result['rows'].to_csv(self.directory/f'{name}_seed_{seed}_fraction_{fraction}_predictions.csv',index=False)
        self.runs[key]=result
        runner_snapshot(self)
        backup_run(self.directory,'latest_checkpoint')
        return result


def practical_guardrails(winner_folds, reference_folds):
    """Aggregate the same per-fold chronological thirds used during selection."""
    wm=winner_folds.mean(numeric_only=True)
    rm=reference_folds.mean(numeric_only=True)
    return dict(worst_block=bool(wm.worst_block_WAPE<=rm.worst_block_WAPE+.005),
        bias=bool(abs(wm.bias_percent)<=abs(rm.bias_percent)+2.),
        coverage=bool(wm.within_20_percent>=rm.within_20_percent-.02))


def evidence_decision(material, smoke):
    return bool(material and not smoke)


def stage_experiments(runner):
    saved=runner.directory/'selection_complete'
    if verify_checkpoint(saved,runner.identity):
        verify_outputs(runner.directory,json.loads((saved/'outputs.json').read_text()))
        value=joblib.load(saved/'selection.joblib')
        print('RESUMED completed selection',flush=True)
        return value
    if (runner.directory/'configuration_lock.json').exists():
        raise PermissionError('Locked run lacks verified selection state; do not repeat selection')
    Config=runner.worker.ForecastConfig
    # Same user blocks, chronological boundaries, row coverage and evaluation code.
    # Stage 0 retains V6 val_loss stopping for an honest implementation reference.
    v6=Config(monitor='val_loss',patience=16,min_delta=0.)
    candidates={'v6_reference':v6}
    results={'v6_reference':runner.run('v6_reference',v6,'0 reproduction')}
    corrected=replace(v6,monitor='val_weighted_mae',patience=10,min_delta=1e-4)
    candidates['predictive_stop']=corrected
    results['predictive_stop']=runner.run('predictive_stop',corrected,'0 stopping control')
    median=replace(corrected,target_transform='median_residual')
    robust=replace(median,scale_method='mad')
    for name,cfg in [('median_center',median),('median_mad',robust)]:
        candidates[name]=cfg; results[name]=runner.run(name,cfg,'1 centering')
    choose=lambda names:min(names,key=lambda n:(results[n]['objective'],candidates[n].units,candidates[n].lookback,n))
    winner=choose(['predictive_stop','median_center','median_mad'])
    family=[winner]
    for length in (13,26):
        name=f'lookback_{length}'; cfg=replace(candidates[winner],lookback=length)
        candidates[name]=cfg; results[name]=runner.run(name,cfg,'2 lookback'); family.append(name)
    winner=choose(family)
    compact=replace(candidates[winner],sequence_features=('total','nonrecurring','count','active_days'),
        context_features=candidates[winner].context_features+('rolling_mad','recent_ratio','trend13','week_sin','week_cos','share_PENDING'),
        context_branch=True)
    candidates['compact']=compact; results['compact']=runner.run('compact',compact,'3 compact bundle')
    winner=choose([winner,'compact'])
    # One-factor comparisons rather than a combinatorial grid: total <=14.
    base=candidates[winner]
    for name,cfg in [('units16',replace(base,units=16)),('l2_zero',replace(base,l2=0.)),
                     ('l2_small',replace(base,l2=1e-4)),('lr_fast',replace(base,learning_rate=.001)),
                     ('plateau',replace(base,schedule='plateau'))]:
        candidates[name]=cfg; results[name]=runner.run(name,cfg,'4 capacity/regularization')
    # Predeclared additions; same base and evaluation rows, never legacy-label tuning.
    for name,cfg in [('huber',replace(base,loss='huber')),
                     ('activity_shape',replace(base,sequence_features=tuple(dict.fromkeys(
                         base.sequence_features+('count','active_days','ticket_mean','largest_share','weekend_share')))))]:
        candidates[name]=cfg; results[name]=runner.run(name,cfg,'4b loss/activity')
    ranked=sorted(results,key=lambda n:(results[n]['objective'],candidates[n].units,candidates[n].lookback,n))
    strongest=ranked[:2]
    # Reference seeds are also repeated so every paired comparison has matched seeds.
    repeated=list(dict.fromkeys(strongest+['v6_reference']))
    seed_records=[]
    for name in repeated:
        for seed in (42,123,2026):
            result=runner.run(name,candidates[name],'5 seed confirmation',seed)
            seed_records.append(dict(candidate=name,seed=seed,objective=result['objective'],
                parameters=int(result['metrics'].parameters.max()),
                train_seconds=float(result['metrics'].train_seconds.sum()),
                inference_seconds=float(result['metrics'].inference_seconds.sum()),
                **metrics(result['rows'].rename(columns={'actual':'y','target_week':'time'}),result['rows'].prediction)))
    seed_table=pd.DataFrame(seed_records)
    seed_table.to_csv(runner.directory/'seed_metrics.csv',index=False)
    seed_table.groupby('candidate').agg({c:['mean','std'] for c in ('WAPE','R2','bias_KES','within_20_percent','objective')}).to_csv(runner.directory/'seed_summary.csv')
    winner=min(strongest,key=lambda n:(seed_table.loc[seed_table.candidate.eq(n),'objective'].mean(),candidates[n].units,n))
    paired=[]
    for seed in (42,123,2026):
        paired.append(paired_rows(runner.runs[(winner,seed,1.)]['rows'],runner.runs[('v6_reference',seed,1.)]['rows']))
    all_rows=pd.concat(paired,ignore_index=True)
    interval=bootstrap(all_rows)
    denominator=all_rows.actual.sum()
    improvement=(np.abs(all_rows.reproduced_v6-all_rows.actual).sum()-all_rows.absolute_error.sum())/denominator
    base_improvement=(np.abs(all_rows.recurring_median-all_rows.actual).sum()-all_rows.absolute_error.sum())/denominator
    winner_folds=pd.concat([runner.runs[(winner,s,1.)]['metrics'] for s in (42,123,2026)])
    reference_folds=pd.concat([runner.runs[('v6_reference',s,1.)]['metrics'] for s in (42,123,2026)])
    guards=practical_guardrails(winner_folds,reference_folds)
    material=bool(improvement>=.01 and interval['candidate_minus_v6_pp_95'][1]<0
        and base_improvement>0 and interval['candidate_minus_baseline_pp_95'][1]<0 and all(guards.values()))
    material=evidence_decision(material,runner.smoke)
    selected=winner if material else 'v6_reference'
    decision=dict(provisional_winner=winner,selected=selected,material_improvement_demonstrated=material,
        execution_mode='software_smoke' if runner.smoke else 'full_development',
        evidence_eligible=not runner.smoke,
        WAPE_improvement_pp=100*improvement,baseline_improvement_pp=100*base_improvement,guardrails=guards,
        intervals=interval,selection_source='train-only folds; adaptive staged comparisons, not independent confirmation',
        policy='retain reproduced V6 if material criterion not met; no best-seed selection; final refit uses predeclared seed42')
    write_json(runner.directory/'train_selection_evidence.json',decision)
    saved.mkdir(exist_ok=True)
    joblib.dump((candidates,results,decision),saved/'selection.joblib')
    atomic_json(saved/'outputs.json',seal_outputs(runner.directory,
        ['train_selection_evidence.json','seed_metrics.csv','seed_summary.csv']))
    seal_checkpoint(saved,runner.identity,['selection.joblib','outputs.json'])
    backup_run(runner.directory,'selection_complete')
    return candidates,results,decision


def diagnostics(runner,candidates,decision):
    name=decision['selected']; cfg=candidates[name]
    # Diagnostic models never become selectable production alternatives.
    for ablation in ('sequence_only','context_only','shuffled'):
        runner.run('diagnostic_'+ablation,replace(cfg,ablation=ablation),'diagnostic ablation',diagnostic=True)
    for fraction in (.25,.5):
        runner.run(name,cfg,'diagnostic learning curve',fraction=fraction,diagnostic=True)
    # Tiny-subset train error is a pipeline capability check, never evidence of generalization.
    fold=runner.folds[0]
    resolved=resolve_config(cfg,runner.data,fold['fit_users'],pd.Timestamp(fold['inner']))
    b=runner.bundle(resolved); f=b[0]
    tiny=subset(b,f.user_id.isin(fold['fit_users'])&f.end.le(pd.Timestamp(fold['inner'])))
    tiny=subset(tiny,np.arange(len(tiny[0]))<min(256,len(tiny[0])))
    tiny_cfg=replace(resolved,l2=0.,learning_rate=.001,max_epochs=2 if runner.smoke else 120)
    fit=train_model(tiny,None,tiny_cfg,runner.directory/'memorization',runner.device,
                    fold['fit_users'],fold['inner'])
    p,_=predict(fit,tiny,runner.device)
    ratio=fit['history']['weighted_mae'][-1]/max(fit['history']['weighted_mae'][0],1e-12)
    write_json(runner.directory/'memorization_diagnostic.json',dict(rows=len(tiny[0]),final_over_initial_error=ratio,
        substantial_reduction=bool(ratio<.5),metrics=metrics(tiny[0],p),
        interpretation='Diagnostic only. If reduction is weak, investigate scaling/order/pipeline/capacity; do not infer an information ceiling.'))
    # Final selected architecture only. If fallback uses val_loss, add a matched
    # predictive-metric120 control rather than confound monitor and cap changes.
    cap_cfg=replace(cfg,monitor='val_weighted_mae',patience=10,min_delta=1e-4)
    if cfg.monitor!='val_weighted_mae':
        original=runner.run('diagnostic_cap120',replace(cap_cfg,max_epochs=120),'diagnostic epoch cap',diagnostic=True)
    else:
        original=runner.runs[(name,42,1.)]
    extended=runner.run('diagnostic_cap160',replace(cap_cfg,max_epochs=160),'diagnostic epoch cap',diagnostic=True)
    stable=[]
    for early,late in zip(original['fits'],extended['fits']):
        h=np.asarray(late['history'][cap_cfg.monitor])
        stable.append(bool(len(h)>120 and len(h[120:])>=3 and
            np.max(h[-3:]) < np.min(h[:120])-cap_cfg.min_delta and late['rates'] and len(late['rates'])>120))
    gain=original['objective']-extended['objective']
    cap=dict(status='120 vs160 train-only sensitivity',objective_improvement=gain,stable_by_fold=stable,
        effective_caps=[2,2] if runner.smoke else [120,160],adopted=False,
        reason='diagnostic only: extension needs repeated-seed confirmation in a future preregistered development run')
    write_json(runner.directory/'epoch_cap_sensitivity.json',cap)
    # Interpretation generated from controlled comparisons, not assumed beforehand.
    full=runner.runs[(name,42,1.)]['objective']
    shuffle=runner.runs[('diagnostic_shuffled',42,1.)]['objective']
    learning=[runner.runs[(name,42,f)]['objective'] for f in (.25,.5,1.)]
    write_json(runner.directory/'diagnostic_interpretation.json',dict(shuffle_minus_full_objective=shuffle-full,
        temporal_structure='not demonstrated by this ablation' if shuffle-full<.01 else 'order-sensitive improvement observed',
        learning_objectives_25_50_100=learning,
        reading='Both poor: possible weak features/noisy target/underfitting. Strong train but weak held-out users: overfitting. '
        'Improvement with more users suggests data limitation. Plateau does not prove an information ceiling. '
        'Shuffling can be redundant with summary context; similar scores do not prove temporal learning.'))


def choose_refit_schedule(runner,name):
    records=[entry for seed in (42,123,2026) for entry in runner.runs[(name,seed,1.)]['fits']]
    duration=int(np.median([len(v['rates']) for v in records]))
    # Medoid duration, deterministic tie-break: use one actual schedule, no legacy labels.
    representative=min(enumerate(records),key=lambda v:(abs(len(v[1]['rates'])-duration),v[0]))[1]
    return representative['rates']


def lock_and_refit(runner,candidates,decision):
    names=list(dict.fromkeys([decision['selected'],'v6_reference']))
    configurations={n:resolve_config(replace(candidates[n],seed=42),runner.data,
        runner.data.user_id.unique(),runner.data.observation_end.min()) for n in names}
    schedules={n:choose_refit_schedule(runner,n) for n in names}
    lock=dict(protocol='spendly-v7-evidence-v1',configuration={n:asdict(c) for n,c in configurations.items()},
        execution_mode='software_smoke' if runner.smoke else 'full_development',evidence_eligible=not runner.smoke,
        schedules=schedules,decision=decision,training_users_digest=digest(sorted(runner.data.user_id.unique())),
        legacy_validation_role=runner.benchmark_role+'; no further tuning',seed=42)
    lock_path=runner.directory/'configuration_lock.json'
    if lock_path.exists() and json.loads(lock_path.read_text())!=safe_json(lock):
        raise PermissionError('Existing configuration lock differs; refusing overwrite')
    if not lock_path.exists():
        atomic_json(lock_path,safe_json(lock))
    lock_hash=digest(lock)
    fits={}
    consumed=(runner.directory/'legacy_evaluation_started.json').exists()
    for name,cfg in configurations.items():
        bundle=runner.bundle(cfg)
        # Full permitted training history, including early eight-week windows for V6 reproduction.
        fitted=train_model(bundle,None,cfg,runner.directory/'refit'/name,runner.device,
            runner.data.user_id.unique(),runner.data.observation_end.min(),replay=schedules[name],require_completed=consumed)
        fits[name]=fitted
    selected=fits[decision['selected']]
    selected['model'].save(runner.directory/'selected_lstm.keras')
    joblib.dump(selected['scales'],runner.directory/'selected_preprocessing.joblib')
    write_json(runner.directory/'feature_config.json',asdict(selected['config']))
    summary=[]; selected['model'].summary(print_fn=lambda line,**kwargs:summary.append(line))
    (runner.directory/'model_summary.txt').write_text('\n'.join(summary),encoding='utf-8')
    pd.DataFrame(selected['history']).to_csv(runner.directory/'refit_training_history.csv',index=False)
    # Save/reload parity before accessing benchmark outcomes.
    import tensorflow as tf
    loaded=tf.keras.models.load_model(runner.directory/'selected_lstm.keras',compile=False)
    cfg=selected['config']; b=runner.bundle(cfg); probe=subset(b,np.arange(len(b[0]))<32)
    original,_=predict(selected,probe,runner.device)
    reloaded,_=predict(dict(selected,model=loaded),probe,runner.device)
    np.testing.assert_allclose(original,reloaded,atol=.01,rtol=0)
    write_json(runner.directory/'reload_parity.json',dict(passed=True,tolerance_KES=.01))
    return fits,lock_hash


def evaluate_legacy(runner,fits,decision,validation,lock_hash):
    lock=json.loads((runner.directory/'configuration_lock.json').read_text())
    if digest(lock)!=lock_hash:
        raise PermissionError('Locked configuration changed')
    complete=runner.directory/'benchmark_complete'
    identity=digest(dict(lock=lock_hash,run=runner.identity,
        fits={name:seal_outputs(runner.directory/'refit'/name,['fitted.keras','preprocessing.joblib']) for name in fits},
        validation=hashlib.sha256(pd.util.hash_pandas_object(validation,index=True).values.tobytes()).hexdigest()))
    if verify_checkpoint(complete,identity):
        verify_outputs(runner.directory,json.loads((complete/'outputs.json').read_text()))
        print('RESUMED benchmark results without re-evaluation',flush=True)
        return joblib.load(complete/'benchmark.joblib')
    marker=runner.directory/'legacy_evaluation_started.json'
    with marker.open('x',encoding='utf-8') as out:
        json.dump(dict(status='consumed once before prediction',lock_hash=lock_hash),out)
    assert not set(validation.user_id)&set(runner.data.user_id)
    start=runner.data.observation_end.min()
    rows={}; measures=[]
    for name,fit in fits.items():
        b=features(validation,fit['config'],runner.worker,runner.cache,runner.code_hash,runner.workers)
        b=subset(b,b[0].time.ge(start))
        p,seconds=predict(fit,b,runner.device)
        rows[name]=row_predictions(b[0],p,name,'legacy',42)
        measures.append(dict(candidate=name,**metrics(b[0],p),parameters=fit['parameters'],
            train_seconds=fit['seconds'],inference_seconds=seconds))
    selected=paired_rows(rows[decision['selected']],rows['v6_reference'])
    for name,column in [('recurring_median','recurring_median'),('recurring_mean','recurring'),('last_week','last'),('mean4','mean4')]:
        frame=selected.rename(columns={'actual':'y','target_week':'time'})
        measures.append(dict(candidate=name,**metrics(frame,selected[column]),parameters=0,train_seconds=0.,inference_seconds=0.))
    interval=bootstrap(selected)
    write_json(runner.directory/'validation_metrics.json',dict(label=runner.benchmark_role,
        independent_confirmation=False,rows=len(selected),metrics=measures,configuration_lock_hash=lock_hash,
        warning='Synthetic development evidence only. R3 validation previously influenced V5/V6; fresh simulator seeds do not establish population generalization. No retuning.'))
    write_json(runner.directory/'bootstrap_confidence_intervals.json',dict(train_only=decision['intervals'],legacy=interval))
    selected.to_csv(runner.directory/'row_level_predictions.csv',index=False)
    complete.mkdir(exist_ok=True)
    joblib.dump((selected,measures),complete/'benchmark.joblib')
    atomic_json(complete/'outputs.json',seal_outputs(runner.directory,
        ['validation_metrics.json','bootstrap_confidence_intervals.json','row_level_predictions.csv']))
    seal_checkpoint(complete,identity,['benchmark.joblib','outputs.json'])
    backup_run(runner.directory,'forecast_complete')
    return selected,measures


def anomaly_pipeline(runner, calibration, validation, ref):
    """Keep V6's selected single IF excess128 and fixed union as comparators.

    No new IF architecture selection on reused validation. Calibration cohort only
    sets the original 1% FPR budget (0.5% per union component).
    """
    assert not set(calibration.user_id)&(set(runner.data.user_id)|set(validation.user_id))
    with timed('anomaly_detection'):
        stage_started=time.perf_counter()
        from joblib import Parallel,delayed,parallel_config
        def build(data,cohort):
            started=time.perf_counter()
            groups=data.groupby('user_id',sort=True); total=groups.ngroups
            print(f'Anomaly {cohort} features: start, 0/{total} users',flush=True)
            parts=[]
            with parallel_config(backend='loky',n_jobs=runner.workers,inner_max_num_threads=1):
                results=Parallel(return_as='generator',pre_dispatch=runner.workers)(
                    delayed(runner.worker.anomaly_bundle)(g) for _,g in groups)
                for count,part in enumerate(results,1):
                    parts.append(part)
                    if count==1 or count%25==0:
                        print(f'Anomaly {cohort} features: {count}/{total} users; elapsed {time.perf_counter()-started:.1f}s',flush=True)
            result=pd.concat([p[0] for p in parts],ignore_index=True),pd.concat([p[1] for p in parts],ignore_index=True)
            print(f'Anomaly {cohort} features: done, {len(parts)}/{total} users; elapsed {time.perf_counter()-started:.1f}s',flush=True)
            return result
        print('CPU: preserved Isolation Forest fitting and calibration',flush=True)
        a,x=build(runner.data,'train'); ca,cx=build(calibration,'calibration'); va,vx=build(validation,'validation')
        weeks=int((runner.data.observation_end.min()-runner.data.observation_start.min())/pd.Timedelta(weeks=1))
        # runner training history is 120 weeks; calibration/validation begin there.
        boundary=runner.data.observation_start.min()+pd.Timedelta(weeks=weeks)
        cm=ref.event_contained(ca,ca.time.ge(boundary)); vm=va.time.ge(boundary)
        settings=dict(trees=12 if runner.smoke else 300,seed=42)
        specs=[('single',dict(view='excess',samples=128),.01),
               ('union_excess',dict(view='excess',samples=128),.005),
               ('union_rhythm',dict(view='rhythm_only',samples=512),.005)]
        fitted=[]; rows=[]; flags={}
        for name,spec,budget in specs:
            started=time.perf_counter()
            print(f'Anomaly forest {name}: fit start',flush=True)
            fit=ref.fit_forest(spec,x,settings)
            print(f'Anomaly forest {name}: fit complete; elapsed {time.perf_counter()-started:.1f}s',flush=True)
            started=time.perf_counter()
            print(f'Anomaly forest {name}: calibration start',flush=True)
            threshold=ref.calibrate_forest(fit,ca.loc[cm],cx.loc[cm],budget)
            print(f'Anomaly forest {name}: calibration complete; elapsed {time.perf_counter()-started:.1f}s',flush=True)
            fit.update(name=name,threshold=threshold); fitted.append(fit)
        # Companion parameters fixed in source. Calibrate using negatives only,
        # before examining companion benchmark outcomes; no sweep on validation.
        calibrated={name:ref.capped_rule_threshold(cx.loc[cm,'collective_score'],ca.loc[cm,'label'],budget)
                    for name,budget in [('collective_rules',.01),('collective_component',.005)]}
        write_json(runner.directory/'collective_protocol.json',dict(**ref.COLLECTIVE_PROTOCOL,
            thresholds=calibrated,benchmark_role=runner.benchmark_role,
            execution_mode='software_smoke' if runner.smoke else 'full_development',
            adopted=False,reason='predeclared diagnostic; requires a future confirmation protocol to promote'))
        for fit in fitted:
            name=fit['name']; threshold=fit['threshold']
            started=time.perf_counter()
            print(f'Anomaly forest {name}: scoring start',flush=True)
            scores=ref.forest_score(fit,vx.loc[vm]); flags[name]=scores>=threshold['threshold']
            print(f'Anomaly forest {name}: scoring complete; elapsed {time.perf_counter()-started:.1f}s',flush=True)
            rows.append(dict(model=name,cohort='validation',benchmark_role=runner.benchmark_role,**ref.classification_metrics(va.loc[vm,'label'],scores,threshold['threshold'])))
        union=flags['union_excess']|flags['union_rhythm']
        union_metrics=ref.classification_metrics(va.loc[vm,'label'],union.astype(float),.5)
        union_metrics.update(AP=np.nan,ROC_AUC=np.nan)
        rows.append(dict(model='two_if_union',cohort='validation',benchmark_role=runner.benchmark_role,**union_metrics))
        flags['two_if_union']=union
        rule_scores=vx.loc[vm,'collective_score'].to_numpy()
        flags['collective_rules']=rule_scores>=calibrated['collective_rules']['threshold']
        flags['forest_collective_union']=flags['union_excess']|(rule_scores>=calibrated['collective_component']['threshold'])
        for name in ('collective_rules','forest_collective_union'):
            measured=ref.classification_metrics(va.loc[vm,'label'],flags[name].astype(float),.5)
            measured.update(AP=np.nan,ROC_AUC=np.nan)
            rows.append(dict(model=name,cohort='validation',benchmark_role=runner.benchmark_role,**measured))
        families=[]; burden=[]
        for name,predicted in flags.items():
            per_type,daily=ref.collective_diagnostics(va.loc[vm],predicted,name)
            families.extend(per_type); burden.append(daily)
        pd.DataFrame(families).to_csv(runner.directory/'anomaly_per_type_events.csv',index=False)
        write_json(runner.directory/'anomaly_alert_burden.json',burden)
        pd.DataFrame(rows).to_csv(runner.directory/'anomaly_metrics.csv',index=False)
        joblib.dump(fitted,runner.directory/'isolation_forests.joblib')
        write_json(runner.directory/'anomaly_protocol.json',dict(selected='single',view='excess',samples=128,
            architecture_source='frozen V6 selected architecture; no V7 IF search',
            calibration='separate calibration users, original FPR-capped method',
            compatibility_correction='architecture locked before legacy benchmark rather than selected on it again',
            thresholds=[dict(name=f['name'],**f['threshold']) for f in fitted]))
        print(f'Anomaly stage complete: outputs written; elapsed {time.perf_counter()-stage_started:.1f}s',flush=True)


def write_figures(runner,rows,measures,decision):
    # Rebuild mutable exports from verified state, never bless stale/corrupt CSVs.
    pd.DataFrame(runner.registry).to_csv(runner.directory/'experiment_registry.csv',index=False)
    pd.DataFrame(runner.fold_metrics).to_csv(runner.directory/'fold_metrics.csv',index=False)
    for (name,seed,fraction),result in runner.runs.items():
        result['rows'].to_csv(runner.directory/f'{name}_seed_{seed}_fraction_{fraction}_predictions.csv',index=False)
    histories=pd.concat(runner.histories,ignore_index=True)
    histories.to_csv(runner.directory/'training_history.csv',index=False)
    chosen=decision['selected']
    curve=histories.loc[histories.candidate.eq(chosen)&histories.seed.eq(42)&histories.fold.eq(0)&histories.fraction.eq(1)]
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    curve[['loss','val_loss']].reset_index(drop=True).plot(ax=axes[0],title='Loss includes regularization')
    curve[['weighted_mae','val_weighted_mae']].reset_index(drop=True).plot(ax=axes[1],title='Unregularized predictive metric')
    fig.tight_layout(); fig.savefig(runner.directory/'training_history.png',dpi=140); plt.close(fig)
    table=pd.DataFrame(runner.fold_metrics)
    lc=table.loc[table.candidate.eq(chosen)&table.seed.eq(42)].groupby('fraction')[['train_WAPE','WAPE']].mean()
    fig,ax=plt.subplots(figsize=(6,4)); lc.plot(marker='o',ax=ax,title='Fixed user subsets: train-only learning curve')
    ax.set_xlabel('Fraction of fit users (stopping users fixed)'); fig.tight_layout(); fig.savefig(runner.directory/'learning_curve.png',dpi=140); plt.close(fig)
    baseline=pd.DataFrame(measures).set_index('candidate').WAPE*100
    fig,ax=plt.subplots(figsize=(8,4)); baseline.plot.bar(ax=ax,title=runner.benchmark_role)
    ax.set_ylabel('WAPE %'); fig.tight_layout(); fig.savefig(runner.directory/'baseline_comparison.png',dpi=140); plt.close(fig)
    result=rows.copy()
    for col in ('actual','prediction','volatility','activity','recurring_share'):
        # Quantiles are descriptive only, never fed back to preprocessing or selection.
        result[col+'_decile']=pd.qcut(result[col],10,duplicates='drop').astype(str)
    result['time_block']=pd.to_datetime(result.target_week).dt.to_period('Q').astype(str)
    summaries=[]
    for group in ('actual_decile','prediction_decile','volatility_decile','activity_decile','recurring_share_decile','activity_subgroup','time_block'):
        for value,g in result.groupby(group,observed=True):
            summaries.append(dict(diagnostic=group,subgroup=str(value),**metrics(g.rename(columns={'actual':'y','target_week':'time'}),g.prediction)))
    pd.DataFrame(summaries).to_csv(runner.directory/'residual_subgroups.csv',index=False)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    result.groupby('actual_decile',sort=False).residual.mean().plot.bar(ax=axes[0],title='Bias by actual-spending decile')
    result.groupby('volatility_decile',sort=False).residual.mean().plot.bar(ax=axes[1],title='Bias by causal volatility decile')
    fig.tight_layout(); fig.savefig(runner.directory/'residual_diagnostics.png',dpi=140); plt.close(fig)
    pd.concat([result.nsmallest(10,'residual'),result.nlargest(10,'residual')]).drop(columns='user_id').to_csv(runner.directory/'error_examples.csv',index=False)
    baseline_note='Material train-fold improvement demonstrated under the declared criterion.' if decision['material_improvement_demonstrated'] else 'A material improvement was not demonstrated; the reproduced V6 configuration is retained.'
    if runner.smoke:
        baseline_note='SOFTWARE SMOKE ONLY: no predictive-improvement conclusion is eligible. Two-epoch fixture checks are not research performance evidence.'
    (runner.directory/'selection_decision.md').write_text('# Selection decision\n\n'+baseline_note+'\n\n'
        +f"Selected: `{decision['selected']}`. Provisional winner: `{decision['provisional_winner']}`.\n\n"
        +'Selection uses train-user folds and mean results across seeds42,123,2026, not the best seed. '
        +f'The benchmark role is: {runner.benchmark_role}; it did not change the locked configuration. '
        +'Adaptive selection makes internal intervals exploratory. No real-user or final-holdout result is claimed.\n\n'
        +'An MAE objective favours conditional medians. Reduced mean bias can worsen WAPE; no validation-derived offset was added.\n',encoding='utf-8')


def package_results(directory,code_hash):
    import tensorflow as tf
    memory={}
    try:
        import resource
        memory['peak_process_rss_platform_units']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory['units']='KiB on Linux; bytes on macOS; main process excludes workers'
    except ImportError:
        memory['peak_rss']='unavailable on this platform'
    try:
        memory['tensorflow_gpu0_bytes']=tf.config.experimental.get_memory_info('GPU:0')
    except (ValueError,RuntimeError):
        pass
    for name in ('data_loading','feature_generation','model_training','prediction','evaluation','anomaly_detection'):
        TIMINGS.setdefault(name,0.)
    TIMINGS['total_execution']=time.perf_counter()-STARTED
    timing=dict(seconds=dict(TIMINGS),memory=memory,
        resume_attempt=globals().get('RESUME_ATTEMPT_ID'),
        note='This process/session only; skipped recovered stages are not measured again. Total excludes final ZIP compression.')
    if (directory/'timings.json').exists():
        write_json(directory/('resume_timings_'+str(time.time_ns())+'.json'),timing)
    else:
        write_json(directory/'timings.json',timing)
    # Fit schedules preserve measured work even when the process-level timer restarted.
    schedules=[json.loads(p.read_text()) for p in directory.glob('**/schedule.json')]
    write_json(directory/'persisted_fit_costs.json',dict(completed_fits=len(schedules),
        training_seconds=sum(s['train_seconds'] for s in schedules),
        scope='Sum of preserved completed-fit costs; excludes failed/incomplete attempts, features and anomaly work.'))
    write_json(directory/'input_access_log.json',ACCESSES)
    assert all(e['cohort'] in ALLOWED_COHORTS for e in ACCESSES)
    required=['v6_audit.json','gpu_evidence.json','runtime_environment.json','data_split_manifest.json',
        'feature_config.json','experiment_registry.csv','fold_metrics.csv','seed_metrics.csv','validation_metrics.json',
        'row_level_predictions.csv','bootstrap_confidence_intervals.json','model_summary.txt','training_history.csv',
        'learning_curve.png','residual_diagnostics.png','baseline_comparison.png','training_history.png',
        'selected_preprocessing.joblib','selected_lstm.keras','selection_decision.md']
    missing=[name for name in required if not (directory/name).is_file()]
    if missing:
        raise ValueError('Incomplete results: '+str(missing))
    files={p.relative_to(directory).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
           for p in directory.rglob('*') if p.is_file() and p.name!='artifact_manifest.json'}
    write_json(directory/'artifact_manifest.json',dict(protocol='spendly-v7-evidence-v1',code_hash=code_hash,
        execution_mode=json.loads((directory/'configuration_lock.json').read_text())['execution_mode'],
        evidence_eligible=json.loads((directory/'configuration_lock.json').read_text())['evidence_eligible'],
        files=files,holdouts_accessed=False,raw_transactions_included=False,
        scope='development research only; not API-compatible automatically'))
    archive=directory.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(directory.rglob('*')):
            if p.is_file():
                z.write(p,p.relative_to(directory).as_posix())
    print('Evidence ZIP:',archive)
    return archive
