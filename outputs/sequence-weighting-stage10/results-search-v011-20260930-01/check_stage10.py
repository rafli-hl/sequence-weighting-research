"""Outcome-independent Stage 10 arithmetic, search and classification fixtures.

No measured model input or objective is loaded. The optional benchmark uses a
fixed synthetic 512-sequence vector and is not part of the numerical experiment.
"""
import argparse
import ast
from copy import deepcopy
from decimal import Decimal, localcontext
from fractions import Fraction
import json
import math
from pathlib import Path
import resource
import sys
import time
from unittest.mock import patch
sys.dont_write_bytecode = True
import numpy as np
import search_math as primary
import independent_math as reference
import audit_stage10 as audit
from common_stage10 import (HERE, ROOT, SOURCES, Budget, BudgetExceeded,
                            array_sha, configuration, read, sha, tensor_array_sha, utc, write)

D = Decimal


def rational_objective(weights, gains, power):
    """Exact rational J at integer powers, independently of either Decimal code."""
    order = sorted(range(len(weights)), key=weights.__getitem__)
    gain = [Fraction.from_float(float(v)) for v in gains]
    mass = [Fraction.from_float(float(v)) ** power for v in weights]
    total_gain, total_mass = sum(gain), sum(mass)
    gsum = qsum = total = Fraction(0)
    for i in order:
        gsum += gain[i]
        qsum += mass[i]
        total += (gsum / total_gain - qsum / total_mass) ** 2
    return total / len(weights)


def metadata(name, original_p, guard=None):
    return dict(source_id='synthetic-' + name, original_p=original_p,
                original_objective=None, original_reason=guard, expected_guard=guard,
                reference_ids=['synthetic-reference'], native_ids=['synthetic-native'])


def evaluate_case(name, weights, gains, original_p, guard=None, caches=None):
    pc, rc = caches or (primary.build_cache(weights), reference.build_cache(weights))
    p = primary.evaluate(weights, gains, original_p, pc)
    r = reference.evaluate(weights, gains, original_p, rc)
    meta = metadata(name, original_p, guard)
    row = audit.compare(meta, p, r, gains, pc, rc)
    return p, r, row, pc, rc


def source_checks():
    assert all((HERE / name).is_file() for name in SOURCES), 'Wait until all frozen sources exist'
    for name in SOURCES:
        if name.endswith('.py'):
            ast.parse((HERE / name).read_text(encoding='utf-8'))
    assert sha(HERE / 'core.py') == sha(ROOT / 'outputs/sequence-weighting-stage9/core.py')
    parent = ast.parse((ROOT / 'outputs/sequence-weighting-stage9/audit_stage9.py').read_text(encoding='utf-8'))
    child = ast.parse((HERE / 'inputs.py').read_text(encoding='utf-8'))
    originals = {node.name: node for node in parent.body if isinstance(node, ast.FunctionDef)}
    for node in child.body:
        if isinstance(node, ast.FunctionDef):
            assert ast.dump(node) == ast.dump(originals[node.name]), node.name
    def designs(tree):
        return next(node for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target,ast.Name) and target.id=='DESIGNS' for target in node.targets))
    assert ast.dump(designs(parent)) == ast.dump(designs(child))
    derivation=read(HERE/'DERIVATION.json')
    for item in derivation['parents']:
        assert sha(ROOT/item['path']) == item['sha256'], item['path']
    assert sha(ROOT/'work/runs'/derivation['parent_run']/'input_manifest.json') == derivation['parent_input_manifest_sha256']
    final_review=derivation['parent_final_review']
    assert sha(ROOT/final_review['path']) == final_review['sha256']
    cfg = configuration('synthetic-fixture')
    assert (cfg['cases'], cfg['policy_references'], cfg['native_checkpoints'], cfg['weight_groups']) == (186, 324, 207, 9)
    assert cfg['shared_numerical_budget_seconds'] == 3600
    assert cfg['primary_precision'] == primary.DPS == 80 and cfg['reference_precision'] == reference.DPS == 110
    assert cfg['primary_mesh_denominator'] == primary.MESH_DENOMINATOR == 64
    assert cfg['reference_mesh_denominator'] == reference.MESH_DENOMINATOR == 128
    assert D(cfg['bracket_width']) == primary.WIDTH_TOLERANCE == reference.WIDTH_TOLERANCE == D('1e-12')
    assert cfg['bisection_max_iterations'] == primary.MAX_STEPS == 40
    assert cfg['golden_max_iterations'] == reference.MAX_STEPS == 80
    assert not cfg['adaptive_precision'] and not cfg['automatic_retry'] and not cfg['global_optimality_certificate']
    # Original subtraction semantics matter even when both inputs were float32.
    initial = np.asarray([1., 2., 3.], dtype=np.float32)
    current = np.asarray([2**-25, 1.5, 4.], dtype=np.float32)
    signed = (initial - current).astype(np.float64)
    assert signed[0] == 1. and signed[2] == -1.
    assert not np.array_equal(signed, initial.astype(np.float64) - current.astype(np.float64))
    assert tensor_array_sha(initial) != tensor_array_sha(initial.astype(np.float64))
    assert array_sha(initial) == array_sha(initial.astype(np.float64))
    expired = Budget(-1)
    try:
        expired.check()
    except BudgetExceeded:
        pass
    else:
        raise AssertionError('Expired common budget was ignored')
    return dict(parsed_source_files=sum(name.endswith('.py') for name in SOURCES),
                historical_core_identical=True, copied_input_provenance_ast_identical=True,
                original_float32_subtraction_preserved=True, common_budget_exhaustion=True)


def bracket_checks():
    with localcontext() as ctx:
        ctx.prec = 110
        mesh = [D(i) / 2 for i in range(7)]
        derivative = lambda p: (p-D('.4'))*(p-D('1.4'))*(p-D('2.4'))
        brackets = primary.bisect_sign_changes(mesh, [derivative(p) for p in mesh], derivative)
        assert [b['mesh_interval'] for b in brackets] == [0, 2, 4]
        assert all(b['converged'] for b in brackets)
        for b, root in zip(brackets, [D('.4'), D('1.4'), D('2.4')]):
            assert D(b['final']['lo']) <= root <= D(b['final']['hi'])
        limited = primary.bisect_sign_changes(mesh, [derivative(p) for p in mesh], derivative, max_steps=0)
        assert len(limited) == 3 and all(not b['converged'] and b['status'] == 'iteration_limit' for b in limited)
        assert primary.bisect_sign_changes(mesh, [D(0)]*len(mesh), lambda p:D(0)) == []
        exact = primary.bisect_sign_changes([D(0), D(1)], [D(-1), D(1)], lambda p:p-D('.5'))
        assert exact[0]['p'] == '0.5' and D(exact[0]['width']) == 0
        objective = lambda p:(p-D('.4'))**2*(p-D('2.4'))**2
        golden = reference.golden_brackets(mesh, [objective(p) for p in mesh], objective)
        assert [b['mesh_center_index'] for b in golden] == [1, 5]
        for b, root in zip(golden, [D('.4'), D('2.4')]):
            assert b['converged'] and abs(D(b['p'])-root) <= D('1e-12')
        limited = reference.golden_brackets(mesh, [objective(p) for p in mesh], objective, max_steps=0)
        assert len(limited) == 2 and all(not b['converged'] for b in limited)
        assert reference.golden_brackets(mesh, [D(1)]*len(mesh), lambda p:D(1)) == []
        # Equal neighboring minima satisfy the frozen <= both, < at least one rule.
        plateau = reference.golden_brackets([D(i) for i in range(4)], [D(1),D(0),D(0),D(1)], lambda p:D(0))
        assert [b['mesh_center_index'] for b in plateau] == [1,2]
    return dict(all_sign_changes_including_maximum=True, exact_zero_preserved=True,
                multiple_objective_brackets=True, equal_neighbor_brackets=True,
                flat_mesh_no_false_brackets=True, iteration_limits_retained=True)


def arithmetic_checks():
    weights = [1., 2.]
    caches = primary.build_cache(weights), reference.build_cache(weights)
    outcomes = []
    with localcontext() as ctx:
        ctx.prec = 110
        expected_root = D(3).ln()/D(2).ln()
        fixtures = [
            ('interior', [1.,3.], float(expected_root), None, expected_root),
            ('zero', [1.,1.], 0., None, D(0)),
            ('eight', [1.,256.], 8., None, D(8)),
            ('below_interval', [4.,1.], 0., None, D(0)),
            ('above_interval', [1.,1024.], 8., None, D(8)),
            ('signed_upper', [-1.,2.], 8., None, D(8)),
            ('zero_gain', [0.,0.], None, 'nonpositive_total_gain', None),
            ('negative_total', [-1.,0.], None, 'nonpositive_total_gain', None),
            ('tiny_positive_guard', [0.,1e-10], None, 'nonpositive_total_gain', None),
            ('small_positive_defined', [0.,2e-10], 8., None, D(8)),
        ]
        for name, gains, op, guard, optimum in fixtures:
            p,r,row,pc,rc = evaluate_case(name, weights, gains, op, guard, caches)
            assert p['hp_reason'] == r['hp_reason'] == guard
            assert not row['classification']['unresolved'], (name,row['classification'])
            if optimum is None:
                assert row['values'] is None and row['status'] == 'guard'
            else:
                assert row['classification']['precision_converged'] and row['classification']['search_objective_agreement']
                assert abs(D(p['winner']['p'])-optimum) <= D('1e-12')
                assert abs(D(r['winner']['p'])-optimum) <= D('1e-12')
                for power in [0,1,2,8]:
                    exact = rational_objective(weights, gains, power)
                    wanted = D(exact.numerator)/D(exact.denominator)
                    for method, cache in [(primary,pc),(reference,rc)]:
                        assert abs(method.objective_at(cache,gains,D(power))-wanted) <= D('1e-50')*max(D(1),abs(wanted))
            outcomes.append(dict(name=name,status=row['status'],primary_p=None if p['winner'] is None else p['winner']['p'],reference_p=None if r['winner'] is None else r['winner']['p']))
            if name == 'interior':
                interior = (metadata(name,op,guard),p,r,row)
                changed = primary.evaluate(weights,gains,7.123,pc)
                changed_ref = reference.evaluate(weights,gains,7.123,rc)
                assert changed['candidates'] == p['candidates'] and changed['brackets'] == p['brackets']
                assert changed_ref['candidates'] == r['candidates'] and changed_ref['brackets'] == r['brackets']
        p,r,row,_,_ = evaluate_case('uniform',[1.,1.],[1.,2.],None,'constant_weights')
        assert row['status'] == 'guard' and not row['classification']['unresolved']
        outcomes.append(dict(name='uniform',status='guard'))
        # Exact fractional power has a known interior root without rounding the gains.
        w,g = [1.,4.,9.,16.],[1.,8.,27.,64.]
        p,r,row,pc,rc = evaluate_case('fractional',w,g,1.5)
        assert abs(D(p['winner']['p'])-D('1.5')) <= D('1e-12')
        assert abs(D(r['winner']['p'])-D('1.5')) <= D('1e-12')
        assert not row['classification']['unresolved']
        # Signed, unsorted rational data exercises sorting and negative prefix values.
        w,g = [8.,.125,2.,1.,.5],[.75,.2,-.025,.3,-.125]
        pc,rc = primary.build_cache(w),reference.build_cache(w)
        for power in [0,1,2,8]:
            exact = rational_objective(w,g,power)
            wanted = D(exact.numerator)/D(exact.denominator)
            assert abs(primary.objective_at(pc,g,D(power))-wanted) <= D('1e-50')
            assert abs(reference.objective_at(rc,g,D(power))-wanted) <= D('1e-50')
        h,power = D('1e-20'),D('1.2345')
        central = (primary.objective_at(pc,g,power+h)-primary.objective_at(pc,g,power-h))/(2*h)
        analytic = primary.derivative_at(pc,g,power)
        assert abs(central-analytic) < D('1e-35')
        power = D('1.250000000000000000000000000001')
        assert primary.decimal_p(power) == reference.decimal_p(power) == power
        assert primary.objective_at(pc,g,power) != primary.objective_at(pc,g,D('1.25'))
        assert reference.objective_at(rc,g,power) != reference.objective_at(rc,g,D('1.25'))
        assert primary.decimal_p(.2) == reference.decimal_p(.2) == D.from_float(.2) != D('.2')
        # Guard arithmetic disagreement is retained rather than silently harmonized.
        p,r,row,_,_ = evaluate_case('threshold_rounding',[1.,2.],[1e-10,1e-30],None,None,caches)
        assert p['hp_reason'] is None and p['legacy_reason'] == 'nonpositive_total_gain'
        assert 'domain_mismatch' in row['classification']['reasons']
    # Independent administrative replay is a separate, optional pre-freeze check.
    replay = HERE/'verify_stage10_final.py'
    if replay.exists():
        from verify_stage10_final import inspect_search, inspect_comparison
        with localcontext() as ctx:
            ctx.prec = 110
            meta,p,r,row = interior
            inspect_search(p,64,True); inspect_search(r,128,False)
            inspect_comparison(meta,p,r,row)
    return dict(fixtures=outcomes,exact_rational_powers=True,analytic_derivative_finite_difference=True,
                original_excluded_from_candidates=True,decimal_p_not_coerced_to_float=True,
                cancellation_domain_mismatch_retained=True,independent_saved_record_replay=sha(replay) if replay.exists() else None)


def classification_checks():
    """Controlled point callbacks isolate classification branches from solvers.

    Structure is deliberately bypassed only in these unit fixtures; all real
    synthetic searches above pass the complete production structure checks.
    """
    cases = {}
    with localcontext() as ctx:
        ctx.prec = 110
        def fixture(name,pp,rp,op,objective,offset=D(0),pconverged=True,rconverged=True):
            p = dict(hp_reason=None,legacy_reason=None,mesh_p=[str(D(i)/64) for i in range(513)],
                     mesh_J=['0']*513,winner=dict(p=str(pp),J=str(objective(pp))),
                     original_point=dict(p=str(D.from_float(op)),J=str(objective(D.from_float(op)))),
                     all_brackets_converged=pconverged)
            r = dict(hp_reason=None,legacy_reason=None,mesh_p=[str(D(i)/128) for i in range(1025)],
                     mesh_J=['0']*1025,winner=dict(p=str(rp),J=str(objective(rp))),
                     original_point=dict(p=str(D.from_float(op)),J=str(objective(D.from_float(op)))),
                     all_brackets_converged=rconverged)
            with patch.object(audit,'structure',lambda *a:None), \
                 patch.object(primary,'objective_at',lambda c,g,p:objective(p)+offset), \
                 patch.object(reference,'objective_at',lambda c,g,p:objective(p)):
                row = audit.compare(metadata(name,op),p,r,[],None,None)
            cases[name] = row['classification']
            return row
        row = fixture('search_disagreement',D(1),D(2),2.,lambda p:(p-D(2))**2)
        assert row['classification']['reasons'] == ['search_objective_disagreement']
        row = fixture('original_better',D(2),D(2),1.,lambda p: D(0) if p==1 else D(1))
        assert row['classification']['reasons'] == ['original_better_than_search']
        assert D(row['values']['original_signed_gap']) == -1
        row = fixture('lower_neighbor',D(2),D(2),2.,lambda p:D(0) if p==D('2.001') else D(1))
        assert row['classification']['reasons'] == ['lower_neighbor']
        row = fixture('precision_failure',D(2),D(2),2.,lambda p:(p-D(2))**2,offset=D('1e-20'))
        assert row['classification']['reasons'] == ['precision_not_converged']
        row = fixture('weak_parameter_difference',D(1),D(2),3.,lambda p:D(1))
        assert not row['classification']['unresolved'] and row['classification']['weak_neighborhood']
        assert row['classification']['search_objective_agreement'] and not row['classification']['parameter_agreement']
        assert row['classification']['original_objective_agreement'] and not row['classification']['original_parameter_agreement']
        row = fixture('bracket_limits',D(2),D(2),2.,lambda p:(p-D(2))**2,pconverged=False,rconverged=False)
        assert row['classification']['reasons'] == ['primary_bracket_not_converged','reference_bracket_not_converged']
    return cases


def benchmark():
    weights = [float(i+1)/512 for i in range(512)]
    gains = [w*w for w in weights]
    timer = Budget(600)
    first=time.perf_counter(); pc=primary.build_cache(weights,budget=timer.check); ptime=time.perf_counter()-first
    first=time.perf_counter(); rc=reference.build_cache(weights,budget=timer.check); rtime=time.perf_counter()-first
    first=time.perf_counter(); p=primary.evaluate(weights,gains,2.,pc,budget=timer.check); peval=time.perf_counter()-first
    first=time.perf_counter(); r=reference.evaluate(weights,gains,2.,rc,budget=timer.check); reval=time.perf_counter()-first
    first=time.perf_counter(); row=audit.compare(metadata('benchmark',2.),p,r,gains,pc,rc,budget=timer.check); comparison=time.perf_counter()-first
    assert not row['classification']['unresolved']
    assert abs(D(p['winner']['p'])-2) <= D('1e-12') and abs(D(r['winner']['p'])-2) <= D('1e-12')
    elapsed,wall=timer.check()
    return dict(n=512,synthetic_only=True,weights_formula='(i+1)/512',gains_formula='weight**2',
                primary_cache_seconds=ptime,reference_cache_seconds=rtime,primary_evaluate_seconds=peval,
                reference_evaluate_seconds=reval,comparison_seconds=comparison,elapsed_seconds=elapsed,
                utc_elapsed_seconds=wall,peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,
                rough_9_cache_186_case_seconds=9*(ptime+rtime)+186*(peval+reval+comparison),
                extrapolation_limitation='Only an outcome-independent synthetic timing; brackets and host load may differ.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=HERE/'CHECKS.json')
    parser.add_argument('--benchmark',action='store_true')
    args=parser.parse_args()
    assert not args.output.exists(),'Preserve previous check evidence; choose another output'
    started=time.perf_counter()
    result=dict(status='PASS',utc=utc(),source=source_checks(),brackets=bracket_checks(),
                arithmetic=arithmetic_checks(),classification=classification_checks(),
                actual_model_objectives_computed=False)
    if args.benchmark:
        print(json.dumps(dict(status='FIXTURES_PASS',benchmark='starting')),flush=True)
        result['synthetic_benchmark']=benchmark()
    result.update(source_sha256={name:sha(HERE/name) for name in SOURCES},elapsed_seconds=time.perf_counter()-started)
    write(args.output,result)
    print(json.dumps(dict(status='PASS',output=str(args.output),elapsed_seconds=result['elapsed_seconds'],
                          synthetic_benchmark=result.get('synthetic_benchmark'))),flush=True)


if __name__=='__main__':
    main()
