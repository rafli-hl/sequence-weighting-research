"""Outcome-independent rational and signed-gain precision fixtures."""
import argparse
import ast
from decimal import Decimal, localcontext
from fractions import Fraction
import math
import sys
sys.dont_write_bytecode = True
from core import exponent
from precision_math import GRID, evaluate
from audit_stage8 import independent_decimal_profile, compare_references
from stage8 import HERE, ROOT, SOURCES, configuration, sha, write, utc


def check_convergence(low, high):
    assert low['hp_reason'] == high['hp_reason']
    if high['hp_reason'] is not None:
        assert low['hp_J'] is high['hp_J'] is None
        return
    with localcontext() as ctx:
        ctx.prec = 110
        js = [Decimal(v) for v in high['hp_J']]
        ds = [Decimal(v) for v in high['hp_D']]
        scale = max(Decimal(1), max(abs(v) for v in ds))
        for a,b in zip(low['hp_J'],js):
            assert abs(Decimal(a)-b) <= Decimal('1e-50')*max(Decimal(1),abs(b))
        for a,b in zip(low['hp_D'],ds):
            assert abs(Decimal(a)-b) <= Decimal('1e-50')*scale
        if high['original_point'] is not None:
            for key in ['hp_J','hp_D']:
                a,b=Decimal(low['original_point'][key]),Decimal(high['original_point'][key])
                s=max(Decimal(1),abs(b)) if key=='hp_J' else scale
                assert abs(a-b)<=Decimal('1e-50')*s


def rational_objective(w,g,p):
    order=sorted(range(len(w)),key=w.__getitem__)
    gains=[Fraction.from_float(float(v)) for v in g]
    weights=[Fraction.from_float(float(v))**p for v in w]
    gt,wt=sum(gains),sum(weights)
    cumulative=Fraction(0); objective=Fraction(0)
    for i in order:
        cumulative+=gains[i]/gt-weights[i]/wt
        objective+=cumulative*cumulative
    return objective/len(w)


def checks():
    for name in SOURCES:
        if name.endswith('.py'): ast.parse((HERE/name).read_text(encoding='utf-8'))
    assert sha(HERE/'core.py')==sha(ROOT/'outputs/sequence-weighting-stage7/core.py')
    assert GRID==[i/20 for i in range(161)] and len(GRID)==161
    cfg=configuration('fixture')
    assert len(cfg['ns'])*len(cfg['generator_ps'])*len(cfg['cs'])*len(cfg['replicates'])==1536
    with localcontext() as ctx:
        ctx.prec=110
        promoted=Decimal.from_float(.2)
        numerator,denominator=(.2).as_integer_ratio()
        assert promoted==Decimal(numerator)/Decimal(denominator) and promoted!=Decimal('0.2')
    fixtures=[([.125,.5,1.,2.,8.],[.2,-.125,.3,-.025,.75]),
              ([.1,.5,2.,9.],[1.,-1.,1.,-1.+2e-10])]
    for w,g in fixtures:
        old=exponent(w,g)
        low=evaluate(w,g,old['p'])
        high=independent_decimal_profile(w,g,GRID,old['p'])
        assert low['legacy_reason'] is None and low['original_point']['legacy_J']==old['objective']
        check_convergence(low,high)
        evidence, classification=compare_references(low,high,'fixture')
        assert evidence['eligible'] and evidence['grid_points']==161
        assert classification['source_id']=='fixture'
        with localcontext() as ctx:
            ctx.prec=110
            for power in [0,1,2]:
                exact=rational_objective(w,g,power)
                wanted=Decimal(exact.numerator)/Decimal(exact.denominator)
                assert abs(Decimal(low['hp_J'][20*power])-wanted)<=Decimal('1e-50')*max(Decimal(1),abs(wanted))
            assert Decimal(low['hp_D'][0])==0 and low['naive_D64'][0]==low['stable_D64'][0]==0
        assert all(math.isfinite(v) for name in ['legacy_J','naive_D64','stable_D64'] for v in low[name])
    for w,g,reason in [([.1,.2,1.,3.],[0.]*4,'nonpositive_total_gain'),
                       ([.1,.2,1.,3.],[1e-11]*4,'nonpositive_total_gain'),
                       ([.1,.2,1.,3.],[-1.]*4,'nonpositive_total_gain'),
                       ([1.]*4,[1.]*4,'constant_weights')]:
        low=evaluate(w,g); high=independent_decimal_profile(w,g,GRID)
        assert low['legacy_reason']==low['hp_reason']==reason
        assert all(low[name] is None for name in ['legacy_J','naive_D64','stable_D64','hp_J','hp_D'])
        check_convergence(low,high)
        evidence, classification=compare_references(low,high,'guard-fixture')
        assert not evidence['eligible'] and classification['status']=='domain_not_comparable'
    return dict(status='PASS',utc=utc(),measured_objective_profiles_read_or_computed=False,
        source_sha256={name:sha(HERE/name) for name in SOURCES},checks=[
            'all source syntax and exact historical core hash',
            '1536 design-selected cases; binary64 161-point grid',
            'Decimal promotion equals exact binary rational, not decimal label',
            'legacy objective at original fitted point equals unchanged estimator',
            '80-digit objectives agree with exact rational fixtures at integer powers',
            'independent 110-digit profiles agree at frozen tolerance on signed fixtures',
            'anchor contrast zero and full finite profiles',
            'uniform/zero/negative/small-positive guard outcomes remain null'])


if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--output',required=True); a=p.parse_args()
    value=checks(); write(ROOT/a.output,value); print(value['status'],flush=True)
