"""Outcome-independent fixtures for Stage7; no measured outcomes are read."""
import argparse
import ast
import math
import sys
sys.dont_write_bytecode = True
from stage7 import HERE, ROOT, SOURCES, NS, REPLICATES, configs, draw, generate, response, metrics, sha, write, utc
from core import exponent
from audit_stage7 import condition_schedule, independent_draw, independent_gain


def checks():
    for name in SOURCES:
        if name.endswith('.py'):
            ast.parse((HERE/name).read_text(encoding='utf-8'))
    assert sha(HERE/'core.py') == sha(ROOT/'outputs/sequence-weighting-stage6/core.py')
    assert len(configs()) == 65 and len(NS)*REPLICATES*65 == 8320
    assert condition_schedule() == configs()
    # Fixture seeds are separate from every measured base draw.
    weights = [.01, .03, .2, .7, 1.1, 2.3, 4.2, 9.]
    for p in [0., .2, 1., 4., 8.]:
        gains = response(weights, p)
        fit = exponent(weights, gains)
        assert abs(fit['p']-p) < 1e-6 and fit['objective'] < 1e-14
        scaled = exponent(weights, [v*1e-8 for v in gains])
        assert abs(fit['p']-scaled['p']) < 1e-6
        assert exponent(weights, [v*1e-14 for v in gains])['p'] is None
    assert exponent(weights, response(weights, 10.))['at_upper_bound']
    assert exponent([1.]*8, [1.]*8)['reason'] == 'constant_weights'
    assert exponent(weights, [0.]*8)['reason'] == 'nonpositive_total_gain'
    assert exponent(weights, [-1.]*8)['p'] is None
    assert exponent(weights, [1e-11]*8)['p'] is None
    assert exponent(weights, [2e-11]*8)['p'] is not None
    # Regeneration tests do not fit or inspect experimental outcomes.
    for n in NS:
        first = draw(n, 1000)
        assert first == draw(n, 1000) and first != draw(n, 1001)
        assert independent_draw(n, 1000) == first
        w, z, centered, sw, sn = first
        assert sw != sn and abs(sum(w)/n-1.) < 1e-14
        assert abs(math.fsum(centered)) < 1e-12
        assert abs(math.fsum(e*e for e in centered)/n-1.) < 1e-14
        for config in configs():
            ww, gg = generate(w, z, centered, config)
            assert independent_gain(w, z, centered, config) == (ww, gg)
            assert len(ww) == len(gg) == n and all(math.isfinite(v) for v in gg)
            if config['family']=='cancellation':
                assert math.isclose(math.fsum(gg), n*config['c'], abs_tol=1e-12, rel_tol=1e-12)
            if config['control'] != 'uniform_weights':
                assert ww == w
    fixture = metrics(weights, [1., -1., 2., -2., 1., -1., 2., -2.])
    assert fixture['p'] is None and fixture['cancellation_ratio'] == 0
    return dict(status='PASS', utc=utc(), measured_estimates_inspected=False,
                source_sha256={name:sha(HERE/name) for name in SOURCES},
                checks=['unchanged estimator byte hash', 'all source syntax', '8320-cell schedule',
                        'exact powers and constrained boundaries', 'positive-scale invariance and absolute guard',
                        'uniform/zero/negative undefined', 'deterministic paired arrays and separate streams',
                        'centered noise RMS and signed total', 'signed cancellation preserved',
                        'independent audit reconstruction matches separate fixture streams'])


if __name__ == '__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    args=parser.parse_args(); result=checks(); write(ROOT/args.output, result)
    print(result['status'])
