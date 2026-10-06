"""Pure Stage 11 scientific summaries; no model/data/search execution.

``summarize(records, decisions)`` accepts confirmation scalar checkpoint rows:
condition,width,data_seed,seed,arm,grid_index,epoch; optional status (complete),
train/validation/test metrics {loss, shared/group/instance:{loss,accuracy}},
fit and group_fit {p,reason,...}, clipping, and diagnostic metadata. Canonical
epoch0 rows have grid_index=None and arm=None, with one row per condition/
capacity/corpus/model seed. Adaptation rows use the literal frozen schedule.
The same canonical baseline is referenced by both weighting arms; G1/G16
baselines remain distinct. Failed rows are retained but not treated as metrics.

All planned observations are materialized. Means containing a missing/undefined
value remain null. Only the five equally weighted corpus means form descriptive
between-corpus statistics; the two seeds are nested. No p/fit/test selection.
"""
import math
import statistics
from config import CAPS, CONDITIONS, ARMS, EPOCHS, F_INDEX, CONFIRM
from policies import decision_map, confirmation_schedule

COMPONENTS = ('total', 'shared', 'group', 'instance')
CORPORA = sorted({d for d, _, _ in CONFIRM})
PAIR_IDS = [(d, s) for d, s, _ in CONFIRM]
SEEDS_BY_CORPUS = {d: sorted(s for dd, s, _ in CONFIRM if dd == d) for d in CORPORA}


def _number(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError('Metrics must be finite numbers or explicit nulls')
    return float(value)


def _mean(values):
    return None if not values or any(x is None for x in values) else math.fsum(values) / len(values)


def _and(values):
    return None if any(v is None for v in values) else all(values)


def _difference(a, b):
    return None if a is None or b is None else a - b


def _stats(values):
    mean = _mean(values)
    available = [x for x in values if x is not None]
    return dict(total=len(values), defined=len(available), undefined=len(values) - len(available),
        positive=sum(x > 0 for x in available), negative=sum(x < 0 for x in available),
        zero=sum(x == 0 for x in available), mean=mean,
        sd=None if mean is None or len(values) < 2 else statistics.stdev(values),
        minimum=None if mean is None else min(values), maximum=None if mean is None else max(values))


def paired_summary(entries):
    """Entries need every declared pair exactly once: data_seed,seed,value."""
    values = {}
    for row in entries:
        key = row['data_seed'], row['seed']
        if key not in PAIR_IDS or key in values:
            raise ValueError('Unexpected or duplicate confirmation pair')
        values[key] = _number(row['value'])
    if set(values) != set(PAIR_IDS):
        raise ValueError('A paired summary must materialize every planned pair')
    pairs = [dict(data_seed=d, seed=s, value=values[d, s]) for d, s in PAIR_IDS]
    corpora = []
    for d in CORPORA:
        nested = [values[d, s] for s in SEEDS_BY_CORPUS[d]]
        corpora.append(dict(data_seed=d, seeds=SEEDS_BY_CORPUS[d], values=nested,
                            mean=_mean(nested), within_corpus=_stats(nested)))
    means = [r['mean'] for r in corpora]
    complete = all(x is not None for x in means)
    return dict(pairs=pairs, all_pairs=_stats([r['value'] for r in pairs]),
                corpora=corpora, between_corpora=_stats(means),
                all_corpus_means_positive=all(x > 0 for x in means) if complete else None,
                all_corpus_means_nonnegative=all(x >= 0 for x in means) if complete else None)


def _metric(row, split, component='total', field='loss'):
    if row is None or row.get('status', 'complete') != 'complete':
        return None
    block = row.get(split)
    if block is None:
        return None
    if component != 'total':
        block = block.get(component)
    return None if block is None else _number(block.get(field))


def _fit(row, key, arm, epoch):
    if row is None or row.get('status', 'complete') != 'complete':
        return dict(p=None, reason='missing_or_failed_checkpoint')
    if epoch == 0:
        return dict(p=None, reason='no_adaptation', uniform_unidentifiable=arm == 'uniform')
    value = row.get(key)
    if value is None:
        return dict(p=None, reason='missing_fit')
    p = _number(value.get('p'))
    if p is not None and (not 0 <= p <= 8 or arm == 'uniform'):
        raise ValueError('Inconsistent bounded/uniform fit')
    if p is None and not value.get('reason'):
        raise ValueError('Undefined fit requires its reason')
    return dict(value, p=p)


def _key(row):
    return tuple(row[k] for k in ('condition', 'width', 'data_seed', 'seed', 'grid_index', 'arm', 'epoch'))


def _planned(decisions):
    rows = []
    for c in CONDITIONS:
        for w, _ in CAPS:
            for d, s, _ in CONFIRM:
                rows.append(dict(condition=c, width=w, data_seed=d, seed=s,
                                 grid_index=None, arm=None, epoch=0))
    for r in confirmation_schedule(decisions):
        for e in EPOCHS:
            rows.append({k: r[k] for k in ('condition', 'width', 'data_seed', 'seed', 'grid_index', 'arm')} | {'epoch': e})
    return rows


def _policy_row(index, c, w, d, s, a, i, e, branch):
    initial = index.get((c, w, d, s, None, None, 0))
    current = initial if e == 0 else index.get((c, w, d, s, i, a, e))
    missing = [name for name, row in [('initial', initial), ('current', current)]
               if row is None or row.get('status', 'complete') != 'complete']
    gains = {split: {component: _difference(_metric(initial, split, component),
                                             _metric(current, split, component))
                     for component in COMPONENTS} for split in ('train', 'validation', 'test')}
    return dict(branch=branch, condition=c, width=w, data_seed=d, seed=s, arm=a,
                grid_index=i, epoch=e, status='missing_or_failed' if missing else 'complete',
                missing=missing, initial=initial, current=current, gains=gains,
                fit=_fit(current, 'fit', a, e), group_fit=_fit(current, 'group_fit', a, e),
                clipping=None if e == 0 or current is None or current.get('status', 'complete') != 'complete'
                else _number(current.get('clipping')))


def _summary(rows, function):
    return paired_summary([dict(data_seed=r['data_seed'], seed=r['seed'], value=function(r)) for r in rows])


def _loss_summary(rows, location, split, component='total', field='loss'):
    return _summary(rows, lambda r: _metric(r[location], split, component, field))


def _fit_counts(rows, key):
    reasons = {}
    for row in rows:
        reason = row[key].get('reason') if row[key]['p'] is None else 'defined'
        reasons[reason] = reasons.get(reason, 0) + 1
    return dict(total=len(rows), reasons=reasons,
                at_lower_bound=sum(r[key]['p'] is not None and r[key]['p'] <= .001 for r in rows),
                at_upper_bound=sum(r[key]['p'] is not None and r[key]['p'] >= 7.999 for r in rows))


def _cell(rows):
    e = rows[0]['epoch']
    delta_test = _summary(rows, lambda r: r['gains']['test']['total'])
    delta_validation = _summary(rows, lambda r: r['gains']['validation']['total'])
    checks = dict(nonzero_updates=e > 0,
                  all_corpora_test_positive=delta_test['all_corpus_means_positive'],
                  all_corpora_validation_nonnegative=delta_validation['all_corpus_means_nonnegative'])
    return dict(epoch=e, grid_index=rows[0]['grid_index'],
                delta_test=delta_test, delta_validation=delta_validation,
                utility=dict(**checks, met=_and(list(checks.values()))),
                losses={split: {comp: {loc: _loss_summary(rows, loc, split, comp)
                                      for loc in ('initial', 'current')}
                                for comp in COMPONENTS} for split in ('train', 'validation', 'test')},
                train_accuracy={comp: _loss_summary(rows, 'current', 'train', comp, 'accuracy')
                                for comp in COMPONENTS if comp != 'total'},
                p=_summary(rows, lambda r: r['fit']['p']),
                group_p=_summary(rows, lambda r: r['group_fit']['p']),
                fit_counts=_fit_counts(rows, 'fit'), group_fit_counts=_fit_counts(rows, 'group_fit'),
                objective=_summary(rows, lambda r: _number(r['fit'].get('objective'))),
                group_objective=_summary(rows, lambda r: _number(r['group_fit'].get('objective'))),
                clipping=_summary(rows, lambda r: r['clipping']))


def _direction(summary):
    vals = [r['mean'] for r in summary['corpora']]
    if any(x is None for x in vals):
        return 'unavailable'
    if all(x > 0 for x in vals):
        return 'positive_in_all_corpora'
    if all(x <= 0 for x in vals):
        return 'nonpositive_in_all_corpora'
    return 'mixed'


def summarize(records, decisions):
    mapping = decision_map(decisions)
    planned = _planned(mapping)
    expected = {_key(row) for row in planned}
    index = {}
    for row in records:
        key = _key(row)
        if key not in expected or key in index:
            raise ValueError('Unexpected or duplicate confirmation checkpoint')
        if row.get('phase', 'confirmation') != 'confirmation':
            raise ValueError('Analysis accepts confirmation records only')
        index[key] = row
    materialized = [dict(identity=row, status=index[_key(row)].get('status', 'complete'),
                         record=index[_key(row)]) if _key(row) in index else
                    dict(identity=row, status='not_run', record=None) for row in planned]
    policy_rows = []
    row_groups = {}
    for branch, fixed_e in [('F' + str(e), e) for e in EPOCHS] + [('R', None)]:
        for c in CONDITIONS:
            for a in ARMS:
                for w, _ in CAPS:
                    selection = mapping[c][str(w)]
                    e = selection['epoch'] if branch == 'R' else fixed_e
                    i = selection['grid_index'] if branch == 'R' else F_INDEX
                    rows = [_policy_row(index, c, w, d, s, a, i, e, branch) for d, s in PAIR_IDS]
                    row_groups[branch, c, a, w] = rows
                    policy_rows.extend(rows)
    cells = {branch: {c: {a: {str(w): _cell(row_groups[branch, c, a, w]) for w, _ in CAPS}
                                  for a in ARMS} for c in CONDITIONS}
             for branch in ['F' + str(e) for e in EPOCHS] + ['R']}
    matched = {}
    for e in EPOCHS:
        branch = 'F' + str(e)
        matched[str(e)] = {}
        for a in ARMS:
            matched[str(e)][a] = {}
            for w, _ in CAPS:
                left, right = row_groups[branch, 'G1', a, w], row_groups[branch, 'G16', a, w]
                contrast = {comp: paired_summary([dict(data_seed=d, seed=s,
                    value=_difference(l['gains']['test'][comp], r['gains']['test'][comp]))
                    for (d, s), l, r in zip(PAIR_IDS, left, right)]) for comp in COMPONENTS}
                group_p = paired_summary([dict(data_seed=d, seed=s,
                    value=_difference(r['group_fit']['p'], l['group_fit']['p']))
                    for (d, s), l, r in zip(PAIR_IDS, left, right)])
                matched[str(e)][a][str(w)] = dict(test_gain_G1_minus_G16=contrast,
                    G1_absolute_group_test_gain=_summary(left, lambda r: r['gains']['test']['group']),
                    group_p_G16_minus_G1=group_p)
    peaks = {}
    scaling = {}
    for branch in cells:
        peaks[branch], scaling[branch] = {}, {}
        for c in CONDITIONS:
            peaks[branch][c], scaling[branch][c] = {}, {}
            for a in ARMS:
                triples = [row_groups[branch, c, a, w] for w, _ in CAPS]
                entries = []
                for j, (d, s) in enumerate(PAIR_IDS):
                    ps = [rows[j]['fit']['p'] for rows in triples]
                    entries.append(dict(data_seed=d, seed=s,
                        value=None if any(p is None for p in ps) else ps[1] - max(ps[0], ps[2])))
                peaks[branch][c][a] = paired_summary(entries)
                corpus_checks = []
                for k, d in enumerate(CORPORA):
                    tests = [cells[branch][c][a][str(w)]['losses']['test']['total']['current']['corpora'][k]['mean']
                             for w, _ in CAPS]
                    vals = [cells[branch][c][a][str(w)]['delta_validation']['corpora'][k]['mean'] for w, _ in CAPS]
                    decrease = None if any(x is None for x in tests) else all(tests[j] > tests[j+1] for j in range(2))
                    val_ok = None if any(x is None for x in vals) else all(x >= 0 for x in vals)
                    corpus_checks.append(dict(data_seed=d, test_nll=tests,
                        validation_gain=vals, test_strictly_decreases=decrease,
                        validation_nonnegative=val_ok, met=_and([decrease, val_ok])))
                scaling[branch][c][a] = dict(corpora=corpus_checks,
                    met=_and([r['met'] for r in corpus_checks]))
    primary = matched['10']['random']['128']
    relative = primary['test_gain_G1_minus_G16']['group']
    absolute = primary['G1_absolute_group_test_gain']
    middle_utility = cells['R']['G1']['random']['128']['utility']['met']
    global_utility = {c: {a: _and([cells['R'][c][a][str(w)]['utility']['met'] for w, _ in CAPS])
                          for a in ARMS} for c in CONDITIONS}
    ready = _and([relative['all_corpus_means_positive'], absolute['all_corpus_means_positive'], middle_utility])
    readiness = dict(relative_response_positive=relative['all_corpus_means_positive'],
        absolute_G1_group_gain_positive=absolute['all_corpus_means_positive'],
        selected_G1_middle_utility=middle_utility, mechanism_ready=ready,
        G1_global_utility=global_utility['G1']['random'],
        capacity_ready=_and([ready, global_utility['G1']['random']]),
        relative_response_direction=_direction(relative), automatic_next_run=False,
        uses_p_or_fit_for_decision=False)
    statuses = {}
    for row in materialized:
        statuses[row['status']] = statuses.get(row['status'], 0) + 1
    return dict(schema_version='stage11-analysis-v1', decisions=mapping,
        counting_units=dict(confirmation_corpora=5, nested_seeds_per_corpus=2,
            planned_native_checkpoints=len(planned), observed_native_checkpoints=len(index),
            policy_references=len(policy_rows), status_counts=statuses),
        native_records=materialized, policy_rows=policy_rows, cells=cells,
        matched_F=matched, K=peaks, scaling=scaling, selected_global_utility=global_utility,
        primary_F10_group_contrast=relative, primary_F10_G1_absolute_group_gain=absolute,
        readiness=readiness,
        scope='Five corpus draws; two nested seeds. Undefined propagates. F matched; R selected total policy. No significance/global-optimality claim.')
