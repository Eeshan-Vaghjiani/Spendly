"""Scalable synthetic finance histories with explicit diagnostic truth separation.

Assumptions are declared in R3_DATA_PROTOCOL.md, not empirically fitted to real users.
No model, threshold or feature implementation is imported into this generator.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import calendar
import numpy as np
import pandas as pd

VERSION = 'spendly-synthetic-r3-v1'
EAT = timezone(timedelta(hours=3))
START = datetime(2021, 1, 4, tzinfo=EAT)
COHORTS = {'train': (306173, 600, False), 'validation': (417239, 100, False),
           'calibration': (528307, 100, False), 'test': (639373, 100, False),
           'test_shifted': (740419, 100, True)}
CATEGORIES = ('Food', 'Transport', 'Shopping', 'Entertainment', 'Education', 'Healthcare')
TICKET = np.array([.0035, .0025, .007, .0045, .008, .007])
ACTIVITY_HOURS = np.array([1,8,12,17,20,23])
ACTIVITY_WEIGHTS = np.array([.02,.12,.28,.3,.23,.05])


def payment_effect(at, pay_dates):
    earlier = [paid for paid in pay_dates if paid <= at]
    age = (at-earlier[-1]).total_seconds()/86400 if earlier else 30.
    return age, .82 + .40*np.exp(-age/8.)


def month_starts(start, end):
    current = start.replace(day=1, hour=0, minute=0, second=0)
    while current < end:
        yield current
        current = current.replace(year=current.year + 1, month=1) if current.month == 12 else current.replace(month=current.month + 1)


def generate_user(seed, index, cohort, weeks=156, shifted=False, inject=True):
    if weeks < 24 or index < 0:
        raise ValueError('At least 24 weeks and a nonnegative user index required')
    streams = [np.random.default_rng(np.random.SeedSequence([seed, index, k])) for k in (1, 11, 23, 37, 53, 97)]
    profile_rng, rng, bills_rng, income_rng, benign_rng, anomaly_rng = streams
    uid = f'r3_{cohort}_{seed}_{index:05d}'
    end = START + timedelta(weeks=weeks)
    profile = str(profile_rng.choice(['salaried', 'irregular', 'student'], p=[.5, .3, .2]))
    typical_income = {'salaried': 55000, 'irregular': 42000, 'student': 22000}[profile]
    income = float(profile_rng.lognormal(np.log(typical_income), .42))
    income_day = int(profile_rng.choice([1, 15, 25, 28]))
    rate = float(profile_rng.uniform(4, 12))
    if profile_rng.random() < .12:
        rate *= .35
    preferences = profile_rng.dirichlet([6, 5, 2, 2, 1.5 if profile == 'student' else .6, .7])
    rho = float(profile_rng.uniform(.45, .85))
    state_noise = float(profile_rng.uniform(.08, .2))
    ticket_noise = float(profile_rng.uniform(.30, .65))
    habit_day = int(profile_rng.integers(7))
    weekend_boost = float(profile_rng.uniform(1.1, 1.65))
    seasonal = float(profile_rng.uniform(.05, .2))
    trend = float(profile_rng.uniform(-.08, .2))
    rent_day, utility_day, subscription_day = [int(profile_rng.integers(1, 29)) for _ in range(3)]
    utility_noise = float(profile_rng.uniform(.08, .22))
    anomaly_rate = float(profile_rng.uniform(.035, .095))
    rows, annotations, diagnostics = [], [], []

    def add(t, amount, category, merchant, suffix, kind='expense', event=None, family=None, source='ordinary'):
        if not START <= t < end:
            return
        tid = f'{uid}_{suffix}'
        rows.append(dict(transaction_id=tid, user_id=uid, transaction_timestamp=t.isoformat(),
            amount=round(max(.01, float(amount)), 2), category=category, merchant=merchant,
            transaction_type=kind, currency='KES', is_anomaly=int(event is not None), event_id=event,
            anomaly_type=family, observation_start=START.isoformat(), observation_end=end.isoformat(),
            source_dataset=VERSION, is_synthetic=True))
        annotations.append(dict(transaction_id=tid, diagnostic_origin=source))

    # Observable income transactions; generator profile parameters stay outside model CSV.
    pay_dates = []
    for m, month in enumerate(month_starts(START, end)):
        if income_rng.random() < (.10 if profile == 'irregular' else .015):
            continue
        delay = int(income_rng.integers(-2, 8 if shifted else 5)) if profile == 'irregular' else 0
        day = min(income_day, calendar.monthrange(month.year, month.month)[1])
        paid = month.replace(day=day) + timedelta(days=delay, hours=8)
        pay_dates.append(paid)
        amount = income * income_rng.lognormal(0, .25 if profile == 'irregular' else .04)
        add(paid, amount, 'Income', 'payer', f'income{m}', kind='income', source='income')
    pay_dates.sort()
    state = 0.
    for w in range(weeks):
        left = START + timedelta(weeks=w)
        state = rho * state + rng.normal(0, state_noise * (1.35 if shifted else 1.))
        state = float(np.clip(state, -1, 1))
        scale = np.exp(state) * (1 + trend * w / max(1, weeks-1))
        if shifted and w >= weeks // 2:
            scale *= 1.2
        expected_week, actual_week = 0., 0.
        for day in range(7):
            date = left + timedelta(days=day)
            effects = [payment_effect(date+timedelta(hours=int(hour)), pay_dates) for hour in ACTIVITY_HOURS]
            hourly_pay = np.array([effect[1] for effect in effects])
            payfactor = float(np.dot(ACTIVITY_WEIGHTS, hourly_pay))
            age, _ = payment_effect(date+timedelta(hours=12), pay_dates)
            weekfactor = weekend_boost if day >= 5 else 1.
            catseason = np.ones(len(CATEGORIES))
            if date.month in (11, 12):
                catseason *= 1 + seasonal
            if date.month in (1, 8):
                catseason[CATEGORIES.index('Education')] *= 1.4
            intensity = rate / 7 * weekfactor * payfactor
            factors = income * TICKET * scale * catseason
            # Exact conditional mean for ordinary draws, before Poisson/ticket randomness;
            # no deterministic bills in this diagnostic noise denominator.
            expected = intensity * np.dot(preferences, factors) * np.exp(ticket_noise**2 / 2)
            count = int(rng.poisson(intensity))
            actual = 0.
            for j in range(count):
                c = int(rng.choice(len(CATEGORIES), p=preferences))
                amount = float(factors[c] * rng.lognormal(0, ticket_noise))
                t = date + timedelta(hours=int(rng.choice(ACTIVITY_HOURS, p=ACTIVITY_WEIGHTS*hourly_pay/payfactor)), minutes=int(rng.integers(60)))
                merchant = f'{CATEGORIES[c]}_{rng.integers(5 if shifted and w >= weeks//2 else 3)}'
                add(t, amount, CATEGORIES[c], merchant, f'n{w}_{day}_{j}')
                actual += round(max(.01, amount), 2)
            diagnostics.append(dict(user_id=uid, week=w, day=day, month=date.month, profile=profile,
                expected_ordinary=expected, ordinary_actual=actual, count=count,
                unit_expected=float(np.dot(preferences, factors) * np.exp(ticket_noise**2/2)),
                season_neutral_expected=float(intensity*np.dot(preferences,income*TICKET*scale)*np.exp(ticket_noise**2/2)),
                income=income, pay_age=age, payfactor=payfactor, weekend_factor=weekfactor,
                seasonal_factor=float(np.dot(preferences, catseason)), state=state))
            expected_week += expected
            actual_week += actual
        if rng.random() < .85:
            t = left + timedelta(days=habit_day, hours=10)
            add(t, income * .014 * scale * rng.lognormal(0, .22), 'Food', 'grocery', f'habit{w}', source='habit')
        if benign_rng.random() < .08:
            t = left + timedelta(days=int(benign_rng.integers(7)), hours=16)
            amount = income * benign_rng.uniform(.002, .015)
            for j in range(2):
                add(t+timedelta(minutes=j*5), amount, 'Food', 'Food_0', f'bd{w}_{j}', source='benign_duplicate')
        if benign_rng.random() < .06:
            t = left + timedelta(days=5, hours=21)
            for j in range(int(benign_rng.integers(3, 7))):
                add(t+timedelta(minutes=j*7), income*benign_rng.uniform(.002,.008), 'Entertainment', 'Entertainment_0', f'bb{w}_{j}', source='benign_burst')
        if benign_rng.random() < .025:
            add(left+timedelta(days=3,hours=14), income*benign_rng.uniform(.08,.45), 'Shopping', 'Shopping_0', f'bl{w}', source='benign_large')
    # No bill is globally constant: utility variation and legitimate persistent changes.
    rent_fraction = float(bills_rng.uniform(.12,.28))
    for m, month in enumerate(month_starts(START, end)):
        for category, day, fraction, sigma in [('Rent',rent_day,rent_fraction,.015), ('Utilities',utility_day,.035,utility_noise),
                                              ('Subscriptions',subscription_day,.009,.025)]:
            delay = int(bills_rng.integers(-2,3)) if shifted else 0
            t = month.replace(day=min(day, calendar.monthrange(month.year, month.month)[1])) + timedelta(days=delay,hours=18)
            change = 1.08 if m >= 18 else 1.
            add(t, income*fraction*change*bills_rng.lognormal(0,sigma), category,
                category+('_new' if m >= 18 else '_old'), f'bill{m}_{category}', source='bill')
    if inject:
        for e in range(int(anomaly_rng.poisson(weeks*anomaly_rate*(.7 if shifted else 1.)))):
            family = str(anomaly_rng.choice(['large','burst','duplicate','recurring_increase','split']))
            w = int(anomaly_rng.integers(8,weeks-1))
            t = START+timedelta(weeks=w,days=int(anomaly_rng.integers(7)),hours=14)
            event = f'{uid}_event{e}'
            if family == 'recurring_increase':
                affected = [r for r in rows if r['category']=='Rent' and r['transaction_timestamp']>=t.isoformat() and not r['is_anomaly']]
                if affected:
                    row = min(affected, key=lambda r:r['transaction_timestamp'])
                    row.update(amount=round(row['amount']*anomaly_rng.uniform(1.35,1.9),2), is_anomaly=1, event_id=event, anomaly_type=family)
                continue
            n = {'large':1,'burst':int(anomaly_rng.integers(5,10)), 'duplicate':3,'split':5}[family]
            amount = income*anomaly_rng.uniform(.10,.4)
            for j in range(n):
                delta = timedelta(days=j) if family=='split' else timedelta(minutes=j*4)
                add(t+delta, amount if family in ('large','duplicate') else amount/n, 'Shopping',
                    f'Shopping_{j%3}' if family=='split' else 'Shopping_0', f'a{e}_{j}', event=event, family=family, source='injected')
    frame = pd.DataFrame(rows).sort_values(['transaction_timestamp','transaction_id']).reset_index(drop=True)
    for c in ('event_id','anomaly_type'):
        frame[c] = frame[c].astype('string')
    info = dict(user_id=uid, profile=profile, income=income, income_day=income_day, rho=rho,
                state_noise=state_noise, ticket_noise=ticket_noise, rate=rate, utility_noise=utility_noise)
    validate_user(frame, uid, end)
    return frame, pd.DataFrame([info]), pd.DataFrame(diagnostics), pd.DataFrame(annotations)


def validate_user(frame, uid, end):
    if frame.empty or not frame.transaction_id.is_unique or set(frame.user_id) != {uid}:
        raise ValueError('Invalid generated identity')
    if not np.isfinite(frame.amount).all() or frame.amount.le(0).any() or not frame.is_anomaly.isin([0,1]).all():
        raise ValueError('Invalid numeric/label values')
    times = pd.to_datetime(frame.transaction_timestamp, utc=True)
    if times.lt(START).any() or times.ge(end).any():
        raise ValueError('Coverage violation')
    if not frame.event_id.notna().equals(frame.is_anomaly.eq(1)):
        raise ValueError('Event/label mismatch')


def audit_user(frame, profile, daily, origins):
    expense = frame.loc[frame.transaction_type.eq('expense')]
    normal = expense.loc[expense.is_anomaly.eq(0)]
    week = daily.groupby('week')[['expected_ordinary','ordinary_actual']].sum()
    residual = (week.ordinary_actual-week.expected_ordinary).abs().sum()
    noise_ratio = residual/max(week.ordinary_actual.sum(),1.)
    marks = origins.set_index('transaction_id').diagnostic_origin
    pay_near = daily.pay_age.le(3)
    pay_late = daily.pay_age.between(20,29)
    # Exposure-adjusted counts retain actual draws, not just unit tests of helper factors.
    expected_pay_neutral = daily.expected_ordinary / daily.payfactor / daily.unit_expected
    pay_near_ratio = daily.loc[pay_near,'count'].sum()/max(expected_pay_neutral.loc[pay_near].sum(),1.)
    pay_late_ratio = daily.loc[pay_late,'count'].sum()/max(expected_pay_neutral.loc[pay_late].sum(),1.)
    weekend = daily.day.ge(5)
    exposure = daily.expected_ordinary/daily.weekend_factor/daily.unit_expected
    weekend_ratio = daily.loc[weekend,'count'].sum()/max(exposure.loc[weekend].sum(),1.)
    weekday_ratio = daily.loc[~weekend,'count'].sum()/max(exposure.loc[~weekend].sum(),1.)
    utilities = normal.loc[normal.category.eq('Utilities'),'amount']
    bill_cv = float(utilities.std()/utilities.mean()) if len(utilities)>1 else 0.
    observed_dates=pd.to_datetime(expense.transaction_timestamp,utc=True).dt.tz_convert('Africa/Nairobi').dt.date.nunique()
    holiday = daily.month.isin([11,12])
    holiday_ratio=daily.loc[holiday,'ordinary_actual'].sum()/max(daily.loc[holiday,'season_neutral_expected'].sum(),1.)
    nonholiday_ratio=daily.loc[~holiday,'ordinary_actual'].sum()/max(daily.loc[~holiday,'season_neutral_expected'].sum(),1.)
    return dict(user_id=profile['user_id'], profile=profile['profile'], rows=len(frame), expense_rows=len(expense),
        anomaly_transactions=int(expense.is_anomaly.sum()), events=int(expense.event_id.nunique()),
        zero_ordinary_days=int(daily['count'].eq(0).sum()), days=len(daily),
        zero_expense_days=int(len(daily)-observed_dates),
        conditional_ordinary_noise_ratio=float(noise_ratio), utilities_cv=bill_cv,
        realized_payday_ratio=float(pay_near_ratio/max(pay_late_ratio,1e-9)),
        realized_weekend_ratio=float(weekend_ratio/max(weekday_ratio,1e-9)),
        realized_holiday_ratio=float(holiday_ratio/max(nonholiday_ratio,1e-9)),
        benign_duplicate=int(normal.transaction_id.map(marks).eq('benign_duplicate').sum()),
        benign_burst=int(normal.transaction_id.map(marks).eq('benign_burst').sum()),
        benign_large=int(normal.transaction_id.map(marks).eq('benign_large').sum()))
