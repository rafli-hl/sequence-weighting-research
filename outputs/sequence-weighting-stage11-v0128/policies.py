"""Pure Stage 11 schedules and validation-only selection.

No filesystem, model, p*, or test value is consulted. ``select`` takes scalar
rows with condition,width,data_seed,seed,grid_index,arm,epoch,validation_nll.
All 432 nonzero tuning rows are required. Epoch-zero rows may be one canonical
row (grid_index=arm=None) per condition/capacity/pair, trajectory copies, or
both; every supplied copy must be exactly equal and each pair must be present.
Extra diagnostic keys are ignored, never selection criteria.
"""
import math
from config import CAPS, CONDITIONS, ARMS, EPOCHS, GRID, F_INDEX, TUNE, CONFIRM


def _config(phase, condition, width, layers, data_seed, seed, pretrain_seed, index, arm):
    prefix = 'tune' if phase == 'tuning' else 'confirm'
    return dict(name=f'{prefix}-{condition}-w{width}-d{data_seed}-s{seed}-g{index:02d}-{arm}',
                phase=phase, condition=condition, width=width, layers=layers,
                data_seed=data_seed, seed=seed, pretrain_seed=pretrain_seed,
                grid_index=index, arm=arm, **GRID[index])


def tuning_schedule():
    return [_config('tuning', c, w, l, d, s, p, i, a)
            for c in CONDITIONS for w, l in CAPS for d, s, p in TUNE
            for i in range(len(GRID)) for a in ARMS]


def decision_map(decisions):
    """Accept the selector result or its ``decisions`` mapping; validate all six."""
    mapping = decisions.get('decisions', decisions)
    if set(mapping) != set(CONDITIONS):
        raise ValueError('Decision conditions differ from frozen design')
    for c in CONDITIONS:
        if set(mapping[c]) != {str(w) for w, _ in CAPS}:
            raise ValueError('Decision capacities differ from frozen design')
        for w, _ in CAPS:
            item = mapping[c][str(w)]
            e, i = item['epoch'], item['grid_index']
            if type(e) is not int or e not in [0] + EPOCHS:
                raise ValueError('Invalid selected epoch')
            if item.get('condition', c) != c or item.get('width', w) != w:
                raise ValueError('Decision identity mismatch')
            if e == 0:
                if i is not None or any(item.get(k) is not None for k in ('lr', 'wd', 'clip')):
                    raise ValueError('Epoch zero must have null optimizer fields')
            else:
                if type(i) is not int or i not in range(len(GRID)):
                    raise ValueError('Invalid selected grid index')
                for k, v in GRID[i].items():
                    if k in item and item[k] != v:
                        raise ValueError('Selected optimizer disagrees with frozen grid')
    return mapping


def confirmation_schedule(decisions):
    mapping = decision_map(decisions)
    result = []
    for c in CONDITIONS:
        for w, l in CAPS:
            item = mapping[c][str(w)]
            indices = {F_INDEX}
            if item['epoch']:
                indices.add(item['grid_index'])
            for d, s, p in CONFIRM:
                for i in sorted(indices):
                    for a in ARMS:
                        result.append(_config('confirmation', c, w, l, d, s, p, i, a))
    if len({x['name'] for x in result}) != len(result):
        raise AssertionError('Duplicate confirmation trajectory')
    return result


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
        raise ValueError('Selection requires finite numeric validation NLL')
    return float(value)


def selection_key(candidate):
    return candidate['score'], candidate['epoch'], (candidate['lr'] or 0.)


def select(inputs):
    schedule = tuning_schedule()
    expected = {(r['condition'], r['width'], r['data_seed'], r['seed'],
                 r['grid_index'], r['arm'], e) for r in schedule for e in EPOCHS}
    pair_ids = {(c, w, d, s) for c in CONDITIONS for w, _ in CAPS for d, s, _ in TUNE}
    measured, initial, row_ids = {}, {}, set()
    for row in inputs:
        c, w, d, s = (row[k] for k in ('condition', 'width', 'data_seed', 'seed'))
        i, a, e = (row[k] for k in ('grid_index', 'arm', 'epoch'))
        if any(type(x) is not int for x in (w, d, s, e)):
            raise ValueError('Selection identifiers/epoch must be integers')
        key = (c, w, d, s, i, a, e)
        if key in row_ids:
            raise ValueError(f'Duplicate selection row: {key}')
        row_ids.add(key)
        score = _finite(row['validation_nll'])
        if (c, w, d, s) not in pair_ids:
            raise ValueError('Unexpected tuning pair')
        if e == 0:
            if not ((i is None and a is None) or
                    (type(i) is int and i in range(len(GRID)) and a in ARMS)):
                raise ValueError('Invalid epoch-zero copy identity')
            pair = (c, w, d, s)
            if pair in initial and initial[pair] != score:
                raise ValueError('Nonidentical initial validation copies')
            initial[pair] = score
        else:
            if type(i) is not int or key not in expected:
                raise ValueError('Unexpected tuning measurement')
            measured[key] = score
    if set(measured) != expected or set(initial) != pair_ids:
        raise ValueError('Incomplete tuning measurements; refusing partial selection')
    decisions, all_scores = {}, {}
    for c in CONDITIONS:
        decisions[c], all_scores[c] = {}, {}
        for w, _ in CAPS:
            candidates = []
            for i, e in [(None, 0)] + [(i, e) for i in range(len(GRID)) for e in EPOCHS]:
                pair_scores = [dict(data_seed=d, seed=s,
                    validation_nll=initial[c, w, d, s] if e == 0 else
                    measured[c, w, d, s, i, 'random', e]) for d, s, _ in TUNE]
                candidate = dict(condition=c, width=w, epoch=e, grid_index=i,
                    score=math.fsum(x['validation_nll'] for x in pair_scores) / len(TUNE),
                    pair_scores=pair_scores,
                    **(dict(lr=None, wd=None, clip=None) if e == 0 else GRID[i]))
                candidates.append(candidate)
            assert len(candidates) == 19
            all_scores[c][str(w)] = candidates
            decisions[c][str(w)] = min(candidates, key=selection_key).copy()
    result = dict(decisions=decisions, all_scores=all_scores,
                  selector='R: mean random-arm validation NLL over two tuning pairs',
                  tie_rule=['full_precision_score', 'earliest_epoch', 'ascending_lr'],
                  canonical_initial_pairs=len(initial), nonzero_rows=len(measured),
                  supplied_initial_copies=len(row_ids) - len(measured),
                  candidate_count=19 * len(CONDITIONS) * len(CAPS))
    decision_map(result)
    return result
