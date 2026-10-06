"""Independent arithmetic cross-checks and prespecified search classifications."""
from decimal import Decimal, localcontext
import search_math as primary_math
import independent_math as reference_math

D=Decimal
FLAGS=['precision_converged','search_objective_agreement','parameter_agreement',
       'original_objective_agreement','original_parameter_agreement',
       'original_better_than_search','weak_neighborhood','unresolved']


def structure(result, denominator, primary):
    """Check complete fixed candidates and all eligible refinement brackets."""
    if result['hp_reason'] is not None:
        assert result['winner'] is None and not result['candidates']
        return
    ps=list(map(D,result['mesh_p'])); js=list(map(D,result['mesh_J']))
    assert ps==[D(i)/denominator for i in range(8*denominator+1)]
    assert len(js)==len(ps) and all(j.is_finite() for j in js)
    if primary:
        ds=list(map(D,result['mesh_derivative']))
        expected=[i for i in range(len(ps)-1) if ds[i]*ds[i+1]<0]
        assert [b['mesh_interval'] for b in result['brackets']]==expected
        assert result['exact_zero_nodes']==[i for i,d in enumerate(ds) if d==0]
    else:
        expected=[i for i in range(1,len(ps)-1) if js[i]<=js[i-1] and js[i]<=js[i+1]
                  and (js[i]<js[i-1] or js[i]<js[i+1])]
        assert [b['mesh_center_index'] for b in result['brackets']]==expected
    assert len(result['candidates'])==len(ps)+len(expected)
    for i,c in enumerate(result['candidates'][:len(ps)]):
        assert c==dict(p=result['mesh_p'][i],J=result['mesh_J'][i],origin='mesh',mesh_index=i)
    for i,(b,c) in enumerate(zip(result['brackets'],result['candidates'][len(ps):])):
        index=expected[i]
        assert D(b['initial']['lo'])==ps[index if primary else index-1]
        assert D(b['initial']['hi'])==ps[index+1]
        if primary:
            assert D(b['initial']['derivative_lo'])==ds[index]
            assert D(b['initial']['derivative_hi'])==ds[index+1]
        else:
            assert D(b['initial']['mesh_center'])==ps[index] and D(b['initial']['J_center'])==js[index]
        lo,hi=D(b['final']['lo']),D(b['final']['hi'])
        assert D(b['initial']['lo'])<=lo<=hi<=D(b['initial']['hi'])
        assert abs(D(b['width'])-(hi-lo))<=D('1e-75')
        assert abs(D(b['p'])-(lo+hi)/2)<=D('1e-75')
        assert b['converged']==(D(b['width'])<=D('1e-12'))
        assert b['iterations']<= (40 if primary else 80)
        assert c['p']==b['p'] and c['bracket_index']==i
        assert c['origin']==('derivative_bracket' if primary else 'objective_bracket')
    assert result['winner']==min(result['candidates'],key=lambda c:(D(c['J']),D(c['p'])))
    assert result['all_brackets_converged']==all(b['converged'] for b in result['brackets'])


def compare(metadata,primary,reference,gains,pcache,rcache,budget=None):
    with localcontext() as ctx:
        ctx.prec=110
        return _compare(metadata,primary,reference,gains,pcache,rcache,budget)


def _compare(metadata,primary,reference,gains,pcache,rcache,budget):
    check=budget or (lambda:None)
    check(); structure(primary,64,True); structure(reference,128,False)
    flags={k:None for k in FLAGS}; flags.update(unresolved=False,reasons=[])
    row=dict(metadata,primary_reason=primary['hp_reason'],reference_reason=reference['hp_reason'],
             classification=flags,values=None,neighborhood=[],point_checks=[],status='guard')
    reasons=flags['reasons']
    if not (primary['hp_reason']==reference['hp_reason']==metadata['expected_guard']
            ==primary['legacy_reason']==reference['legacy_reason']): reasons.append('domain_mismatch')
    if primary['hp_reason'] is not None or reference['hp_reason'] is not None:
        flags['unresolved']=bool(reasons); row['status']='unresolved' if reasons else 'guard'
        return row
    point_checks=row['point_checks']
    def precision_check(label,p,j80,j110):
        tolerance=D('1e-50')*max(D(1),abs(j110))
        gap=j80-j110
        point_checks.append(dict(label=label,p=str(p),evaluated_J=str(j80),reference_J=str(j110),
                                 evaluated_precision=110 if label.startswith('saved_reference') else 80,
                                 signed_gap=str(gap),tolerance=str(tolerance),passed=abs(gap)<=tolerance))
        return j110
    for i,(p,j) in enumerate(zip(primary['mesh_p'],primary['mesh_J'])):
        check(); assert D(p)==D(reference['mesh_p'][2*i])
        precision_check('shared_mesh',D(p),D(j),D(reference['mesh_J'][2*i]))
    def point(label,p):
        check(); j80=primary_math.objective_at(pcache,gains,p)
        check(); j110=reference_math.objective_at(rcache,gains,p)
        return precision_check(label,p,j80,j110)
    pp,rp=D(primary['winner']['p']),D(reference['winner']['p'])
    jp,jr=point('primary_winner',pp),point('reference_winner',rp)
    # Saved values themselves must agree with independent evaluation, too.
    precision_check('saved_primary_winner',pp,D(primary['winner']['J']),jp)
    precision_check('saved_reference_winner',rp,D(reference['winner']['J']),jr)
    op=D.from_float(metadata['original_p']) if metadata['original_p'] is not None else None
    jo=point('original_point',op) if op is not None else None
    if op is not None:
        assert D(primary['original_point']['p'])==D(reference['original_point']['p'])==op
        precision_check('saved_primary_original',op,D(primary['original_point']['J']),jo)
        precision_check('saved_reference_original',op,D(reference['original_point']['J']),jo)
    span=max(map(D,reference['mesh_J']))-min(map(D,reference['mesh_J']))
    scale=max(D(1),span); st=D('1e-18')*scale; ot=D('1e-12')*scale; pt=D('1e-6')
    for p in sorted({max(D(0),rp-D('.001')),min(D(8),rp+D('.001'))}-{rp}):
        j=point('neighborhood',p)
        row['neighborhood'].append(dict(p=str(p),J=str(j),signed_gap=str(j-jr)))
    sg=jp-jr; og=jo-jr if jo is not None else None
    pd=pp-rp; od=op-rp if op is not None else None
    flags.update(precision_converged=all(c['passed'] for c in point_checks),
        search_objective_agreement=abs(sg)<=st,parameter_agreement=abs(pd)<=pt,
        original_objective_agreement=abs(og)<=ot if og is not None else None,
        original_parameter_agreement=abs(od)<=pt if od is not None else None,
        original_better_than_search=og < -ot if og is not None else None,
        weak_neighborhood=all(abs(D(n['signed_gap']))<=ot for n in row['neighborhood']))
    if not flags['precision_converged']: reasons.append('precision_not_converged')
    if not flags['search_objective_agreement']: reasons.append('search_objective_disagreement')
    if not primary['all_brackets_converged']: reasons.append('primary_bracket_not_converged')
    if not reference['all_brackets_converged']: reasons.append('reference_bracket_not_converged')
    if flags['original_better_than_search']: reasons.append('original_better_than_search')
    if any(D(n['signed_gap']) < -st for n in row['neighborhood']): reasons.append('lower_neighbor')
    flags['unresolved']=bool(reasons)
    row.update(status='unresolved' if reasons else 'compared',values=dict(
        primary_p=str(pp),reference_p=str(rp),original_p_exact=str(op) if op is not None else None,
        J_primary_110=str(jp),J_reference_110=str(jr),J_original_110=str(jo) if jo is not None else None,
        search_signed_gap=str(sg),original_signed_gap=str(og) if og is not None else None,
        search_parameter_delta=str(pd),original_parameter_delta=str(od) if od is not None else None,
        reference_mesh_span=str(span),search_objective_tolerance=str(st),
        original_objective_tolerance=str(ot),parameter_tolerance=str(pt)))
    row['arithmetic_summary']=dict(points=len(point_checks),
        maximum_normalized_discrepancy=str(max(abs(D(c['signed_gap']))/D(c['tolerance']) for c in point_checks)))
    check(); return row
