"""Outcome-independent CPU fixtures for the Stage11 engine. Create-only output."""
import argparse
import hashlib
import json
import math
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
import torch

from config import CAPS, PARAMETERS
from core import exponent
from engine import (data, paired_data, pre_data, support_counts, tie_group_rule,
                    pretraining_objective, weights, validate_weights, orders,
                    tensor_hash, diagnostics, evaluate)
from model import Model

HERE = Path(__file__).resolve().parent
FIXTURE_DATA = 1700101
FIXTURE_PRETRAIN = 1700103
FIXTURE_MODEL = 1700107
SOURCE_NAMES = ['config.py', 'core.py', 'model.py', 'engine.py', 'check_stage11.py']


def source_hashes(names=SOURCE_NAMES):
    return {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in names}


def run_checks():
    torch.set_num_threads(1)
    checks = []
    datasets, metadata = paired_data(FIXTURE_DATA)
    for split, n in [('train', 512), ('validation', 256), ('test', 512)]:
        old, kinds = datasets['G16'][split]
        new, new_kinds = datasets['G1'][split]
        assert old.shape == (n, 41) and kinds.shape == (n, 40)
        assert old.dtype == kinds.dtype == torch.int64
        assert torch.equal(kinds, new_kinds)
        assert all(torch.all((kinds == kind).sum(1) == 4) for kind in range(3))
        allowed = torch.zeros_like(old, dtype=torch.bool)
        allowed[:, 1:] = kinds == 1
        assert torch.equal(old[~allowed], new[~allowed])
        rows, columns = (kinds == 1).nonzero(as_tuple=True)
        groups = old[rows, 1] - 1
        queries = old[rows, columns] - 52
        permutations = torch.tensor(metadata['G16']['group_permutations'])
        assert torch.equal(old[rows, columns + 1], 68 + permutations[groups, queries])
        assert torch.equal(new[rows, columns + 1], 68 + permutations[0, queries])
        assert torch.equal(old[old[:, 1] == 1], new[new[:, 1] == 1])
        changed = old != new
        assert changed.any() and not (changed & ~allowed).any()
        assert torch.equal(changed[:, :-1], old[:, :-1] != new[:, :-1])
        assert torch.equal(changed[:, 1:], old[:, 1:] != new[:, 1:])
        # Every row's group-query support is counted, including finite missing cells.
        s16 = support_counts((old, kinds), 'G16')
        s1 = support_counts((new, kinds), 'G1')
        assert sum(map(sum, s16['rule_query_counts'])) == n * 4
        assert sum(map(sum, s1['rule_query_counts'])) == n * 4
        assert s16['expected_rule_query_count'] == n / 64
        assert s1['expected_rule_query_count'] == n / 4
        assert s16['group_query_counts'] == s1['group_query_counts']
        assert metadata['G16']['tensor_sha256'][split] == tensor_hash(old, kinds)
    checks.append('G1/G16 exact permitted targets/context changes, group0 invariance, mixed counts and support')

    # Explicit hand-built target-position fixture: only the group answer changes.
    tokens = torch.tensor([[0, 3, 17, 17, 17, 50, 52, 68, 49, 53, 70, 51, 54, 75]])
    kinds = torch.tensor([[-1, -1, -1, -1, -1, -1, 1, -1, -1, 0, -1, -1, 2]])
    tied, mask = tie_group_rule((tokens, kinds), list(reversed(range(16))))
    expected = tokens.clone(); expected[0, 7] = 83
    assert torch.equal(tied, expected) and torch.equal(mask, kinds)
    assert tokens[0, 7] == 68
    checks.append('Hand-built group-rule formula and next-token target alignment')

    pre, pm = pre_data(FIXTURE_PRETRAIN)
    all_keys = []
    for source_meta in [metadata['G16'], pm]:
        for values in source_meta['sequence_keys_by_split'].values():
            assert len(values) == len(set(values))
            assert not set(values).intersection(all_keys)
            all_keys.extend(values)
    assert len(pre['train'][0]) == 2048 and len(pre['validation'][0]) == 256
    assert 'test' not in pre
    for condition in ('G16', 'G1'):
        visible, mv = data(FIXTURE_DATA, condition, True)
        hidden, mh = data(FIXTURE_DATA, condition, False)
        assert mv == mh and 'test' not in hidden
        for split in ('train', 'validation'):
            assert all(torch.equal(a, b) for a, b in zip(visible[split], hidden[split]))
            assert all(torch.equal(a, b) for a, b in zip(visible[split], datasets[condition][split]))
    checks.append('Disjoint phase/split keys and complete generation before test visibility')

    w = weights(FIXTURE_MODEL, 'random')
    wu = weights(FIXTURE_MODEL, 'uniform')
    assert w.unique().numel() == 512 and torch.equal(wu, torch.ones(512))
    assert torch.equal(w, weights(FIXTURE_MODEL, 'random'))
    assert abs(float(w.mean()) - 1.) < 2e-7
    for invalid in [torch.tensor([1., 1., 2.]), torch.tensor([0., 1.]), torch.tensor([float('nan'), 1.])]:
        try:
            validate_weights(invalid)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid/tied random weights accepted')
    validate_weights(wu, allow_constant=True)
    order = orders(FIXTURE_MODEL)
    assert order.shape == (30, 512) and torch.equal(order, orders(FIXTURE_MODEL))
    assert all(torch.equal(row.sort().values, torch.arange(512)) for row in order)
    weighted_support = support_counts(datasets['G16']['train'], 'G16', w)
    assert abs(sum(map(sum, weighted_support['rule_query_weight_mass'])) - 4 * sum(w.tolist())) < 1e-9
    checks.append('Saved-dtype random-weight positivity/uniqueness, deliberate ties, uniform guard and paired orders')

    tokens, kinds = (value[:2] for value in pre['train'])
    logits = torch.linspace(-.7, .9, 2 * 40 * 84, dtype=torch.float64).reshape(2, 40, 84).requires_grad_()
    objective = pretraining_objective(logits, tokens, kinds)
    shared = kinds == 0
    auxiliary = (kinds == 1) | (kinds == 2)
    normalization = torch.logsumexp(logits, dim=-1)
    target = logits.gather(-1, tokens[:, 1:, None]).squeeze(-1)
    expected = ((normalization - target) * shared).sum() / shared.sum()
    expected += ((normalization - logits[:, :, 68:84].mean(-1)) * auxiliary).sum() / auxiliary.sum()
    assert abs(float(objective - expected)) < 1e-12
    gradient, = torch.autograd.grad(objective, logits)
    coef = shared.double() / shared.sum() + auxiliary.double() / auxiliary.sum()
    expected_gradient = logits.detach().softmax(-1) * coef[:, :, None]
    shared_target = torch.zeros_like(logits)
    shared_target.scatter_(-1, tokens[:, 1:, None], (shared.double() / shared.sum())[:, :, None])
    expected_gradient -= shared_target
    expected_gradient[:, :, 68:84] -= (auxiliary.double() / (16 * auxiliary.sum()))[:, :, None]
    assert (gradient - expected_gradient).abs().max() < 1e-14
    checks.append('Independent U objective and exact full-vocabulary gradient formula')

    for width, layers in CAPS:
        torch.manual_seed(FIXTURE_MODEL)
        model = Model(width, layers, 40)
        assert sum(p.numel() for p in model.parameters()) == PARAMETERS[width]
    torch.manual_seed(FIXTURE_MODEL)
    model = Model(64, 2, 40).eval()
    tokens, kinds = (value[:2] for value in datasets['G16']['train'])
    altered = tokens[:, :-1].clone(); altered[:, 25:] = (altered[:, 25:] + 1) % 84
    with torch.no_grad():
        baseline_logits = model(tokens[:, :-1])
        altered_logits = model(altered)
    assert torch.equal(baseline_logits[:, :25], altered_logits[:, :25])
    assert not torch.equal(baseline_logits[:, 25:], altered_logits[:, 25:])
    metrics, arrays = evaluate(model, (tokens, kinds), device='cpu')
    assert all(torch.isfinite(value).all() for value in arrays.values())
    assert arrays['loss'].dtype == arrays['component_loss'].dtype == torch.float32
    assert (arrays['loss'] - arrays['component_loss'].mean(1)).abs().max() < 2e-6
    assert math.isfinite(metrics['loss'])
    checks.append('All parameter counts, causal no-future-leakage and component evaluation identities')

    fw = torch.tensor([.1, .3, 1., 3.])
    initial = {'loss': torch.ones(4), 'component_loss': torch.ones(4, 3)}
    current = {'loss': torch.full((4,), 1e-8), 'component_loss': torch.full((4, 3), 1e-8)}
    diagnostic = diagnostics(fw, initial, current)
    assert diagnostic['fit']['guard_total_gain'] == 4.
    assert diagnostic['group_fit']['guard_total_gain'] == sum((initial['component_loss'][:, 1].double() - current['component_loss'][:, 1].double()).tolist())
    assert diagnostic['group_fit']['guard_total_gain'] != diagnostic['fit']['guard_total_gain']
    # Group total exceeds1e-10 but not3e-10; averaged full gain remains guarded.
    component = torch.zeros(4, 3); component[:, 1] = 3e-11
    tiny_initial = {'component_loss': component, 'loss': component.mean(1)}
    tiny_current = {'component_loss': torch.zeros(4, 3), 'loss': torch.zeros(4)}
    near = diagnostics(fw, tiny_initial, tiny_current)
    assert near['fit']['reason'] == 'nonpositive_total_gain'
    assert near['group_fit']['p'] is not None and 1e-10 < near['group_fit']['guard_total_gain'] < 3e-10
    assert exponent(fw.tolist(), [1e-10, 0., 0., 0.])['p'] is None
    assert exponent(fw.tolist(), [math.nextafter(1e-10, math.inf), 0., 0., 0.])['p'] is not None
    unchanged = diagnostics(fw, initial, initial, no_adaptation=True)
    assert unchanged['fit']['reason'] == unchanged['group_fit']['reason'] == 'no_adaptation'
    adapted_zero = diagnostics(fw, initial, initial)
    assert adapted_zero['fit']['reason'] == 'nonpositive_total_gain'
    uniform = diagnostics(torch.ones(4), initial, current)
    assert uniform['fit']['reason'] == 'constant_weights'
    signed_component = torch.tensor([[-.1, .2, .3], [.4, -.2, .1], [.2, .3, -.1], [.1, .1, .1]])
    signed_initial = {'component_loss': torch.ones(4, 3), 'loss': torch.ones(4)}
    sc = signed_initial['component_loss'] - signed_component
    signed = diagnostics(fw, signed_initial, {'component_loss': sc, 'loss': sc.mean(1)})
    assert signed['component_fits']['shared']['negative_gain_fraction'] > 0
    assert signed['component_fits']['instance']['negative_gain_mass'] > 0
    checks.append('Full/component operation order, exact guard sides, 1e-10 versus allocation3e-10, no-adaptation and signed gains')
    return checks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    started = time.perf_counter()
    try:
        checks = run_checks()
        result = {'status': 'PASS', 'checks': checks}
        failed = False
    except Exception:
        result = {'status': 'FAIL', 'error': traceback.format_exc()}
        failed = True
    result.update(utc=datetime.now(timezone.utc).isoformat(), elapsed_seconds=time.perf_counter() - started,
                  fixture_only=True, training=False, device='cpu', source_sha256=source_hashes(),
                  fixture_seeds={'data': FIXTURE_DATA, 'pretraining': FIXTURE_PRETRAIN, 'model': FIXTURE_MODEL})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
        handle.write('\n')
    print(json.dumps({'status': result['status'], 'output': str(args.output), 'elapsed_seconds': result['elapsed_seconds']}))
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
