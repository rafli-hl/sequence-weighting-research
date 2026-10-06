"""Read-only historical seed inventory, with no model/binary loading or imports.

Only structured seed fields, source expressions with seed semantics, and explicit
protocol seed declarations create values. Arbitrary counts/losses are excluded.
Safe AST evaluation never executes historical Python. New output is create-only.
"""
import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import time

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
TEXT_SUFFIXES={'.json','.jsonl','.py','.md'}
PLAN_NAMES={'TUNE','CONFIRM','REPS','PANELS'}


def sha_bytes(blob): return hashlib.sha256(blob).hexdigest()
def utc(): return datetime.now(timezone.utc).isoformat()
def integer(x): return isinstance(x,int) and not isinstance(x,bool) and 0<=x<2**64
def seed_key(key):
    key=str(key).lower().replace('-','_')
    return (bool(re.search(r'(^|_)seeds?($|_)',key)) or key in {'preseed','dseed'}) and not any(
        token in key.split('_') for token in ['count','counts','number','num','n','sha256','hash','available','defined','independent'])


def bind(target,value,env):
    if isinstance(target,ast.Name): env[target.id]=value
    elif isinstance(target,(ast.Tuple,ast.List)):
        assert len(target.elts)==len(value)
        for t,v in zip(target.elts,value): bind(t,v,env)
    else: raise ValueError('Unsupported binding')


def literal(node,env):
    """Small bounded evaluator for literal plans and range comprehensions."""
    if isinstance(node,ast.Constant): return node.value
    if isinstance(node,ast.Name): return env[node.id]
    if isinstance(node,(ast.List,ast.Tuple,ast.Set)):
        values=[literal(v,env) for v in node.elts]
        return tuple(values) if isinstance(node,ast.Tuple) else values
    if isinstance(node,ast.Dict): return {literal(k,env):literal(v,env) for k,v in zip(node.keys,node.values)}
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
        value=literal(node.operand,env); return -value if isinstance(node.op,ast.USub) else value
    if isinstance(node,ast.BinOp):
        a,b=literal(node.left,env),literal(node.right,env)
        if isinstance(node.op,ast.Add): return a+b
        if isinstance(node.op,ast.Sub): return a-b
        if isinstance(node.op,ast.Mult):
            assert not isinstance(a,(list,tuple,str)) and not isinstance(b,(list,tuple,str))
            return a*b
        if isinstance(node.op,ast.Pow):
            assert integer(b) and b<=10
            return a**b
    if isinstance(node,ast.Call):
        if isinstance(node.func,ast.Name) and node.func.id=='range':
            values=list(range(*[literal(a,env) for a in node.args])); assert len(values)<=10000
            return values
        if isinstance(node.func,ast.Attribute) and node.func.attr=='values' and not node.args:
            return list(literal(node.func.value,env).values())
    if isinstance(node,ast.ListComp):
        values=[]
        def visit(index,scope):
            if index==len(node.generators):
                values.append(literal(node.elt,scope)); assert len(values)<=10000; return
            gen=node.generators[index]; assert not gen.ifs and not gen.is_async
            for value in literal(gen.iter,scope):
                child=dict(scope); bind(gen.target,value,child); visit(index+1,child)
        visit(0,dict(env)); return values
    raise ValueError('Unsupported/nonliteral expression')


def plan_rows(value):
    if isinstance(value,dict):
        for child in value.values(): yield from plan_rows(child)
    elif isinstance(value,(list,tuple)):
        if len(value)==3 and all(integer(v) for v in value): yield value
        else:
            for child in value: yield from plan_rows(child)


def candidates(config):
    tree=ast.parse(config.read_text(encoding='utf-8-sig')); env={}
    for node in tree.body:
        if isinstance(node,ast.Assign):
            try:
                value=literal(node.value,env)
                for target in node.targets: bind(target,value,env)
            except (ValueError,KeyError,AssertionError,TypeError): pass
    rows=[]
    for phase in ['TUNE','CONFIRM']:
        for i,(d,s,p) in enumerate(env[phase]):
            for role,value in [('adaptation_data',d),('model_weight',s),('pretraining_data',p)]:
                rows.append(dict(phase=phase,row=i,role=role,value=value))
    return rows


class Inventory:
    def __init__(self):
        self.records=defaultdict(set); self.files=[]; self.omissions=[]; self.expressions=[]
        self.model_contexts=defaultdict(list); self.data_contexts=defaultdict(set)
        self.code_seen={}; self.json_seen={}; self.markdown_seen={}

    def add(self,value,role,path,location):
        if integer(value): self.records[value,role].add((path,location))
        elif isinstance(value,(list,tuple)):
            for i,v in enumerate(value): self.add(v,role,path,f'{location}[{i}]')

    def structured(self,obj,path,location='$'):
        if isinstance(obj,dict):
            # Actual saved model metadata supplies inherited RNG derivations.
            s=obj.get('seed'); is_model=integer(s) and any(k in obj for k in ['width','layers','weighting','learning_rate'])
            if is_model:
                epochs=obj.get('epochs',obj.get('max_epochs'))
                if not integer(epochs):
                    history=obj.get('history',[])
                    epochs=max([h.get('epoch',0) for h in history if isinstance(h,dict) and integer(h.get('epoch'))] or [0])
                if epochs<=10000:
                    self.model_contexts[s].append(dict(path=path,location=location,epochs=epochs,
                        weighting=obj.get('weighting',obj.get('arm'))))
            for key,value in obj.items():
                child=f'{location}.{key}'
                if seed_key(key):
                    self.add(value,'structured:'+str(key),path,child)
                    if integer(value) and ('data' in key.lower() or 'pretrain' in key.lower() or key in ['dseed','preseed']):
                        self.data_contexts[value].add((path,child))
                    if key=='seed' and integer(value) and ('ntrain' in obj or 'group_permutations' in obj):
                        self.data_contexts[value].add((path,child))
                self.structured(value,path,child)
        elif isinstance(obj,list):
            for i,value in enumerate(obj): self.structured(value,path,f'{location}[{i}]')

    def python(self,text,path):
        tree=ast.parse(text); env={}
        for node in tree.body:
            if not isinstance(node,ast.Assign): continue
            try:
                value=literal(node.value,env)
                for target in node.targets: bind(target,value,env)
            except (ValueError,KeyError,AssertionError,TypeError): continue
            for target in node.targets:
                if not isinstance(target,ast.Name): continue
                name=target.id
                if name in PLAN_NAMES:
                    for i,row in enumerate(plan_rows(value)):
                        for role,item in zip(['adaptation_data','model_weight','pretraining_data'],row):
                            self.add(item,'source_plan:'+role,path,f'{name}[{i}]@{node.lineno}')
                elif seed_key(name): self.add(value,'source_assignment:'+name,path,str(node.lineno))
        for node in ast.walk(tree):
            if isinstance(node,ast.Call):
                func=node.func.attr if isinstance(node.func,ast.Attribute) else node.func.id if isinstance(node.func,ast.Name) else None
                if func in ['Random','manual_seed','manual_seed_all','default_rng','seed'] and node.args:
                    try: value=literal(node.args[0],env)
                    except (ValueError,KeyError,AssertionError,TypeError):
                        self.expressions.append(dict(path=path,line=node.lineno,kind=func,expression=ast.unparse(node.args[0])))
                    else: self.add(value,'source_rng_call:'+func,path,str(node.lineno))
                for keyword in node.keywords:
                    if keyword.arg and seed_key(keyword.arg):
                        try: self.add(literal(keyword.value,env),'source_keyword:'+keyword.arg,path,str(node.lineno))
                        except (ValueError,KeyError,AssertionError,TypeError): pass
                if func=='add_argument' and node.args and isinstance(node.args[0],ast.Constant) and seed_key(str(node.args[0].value).lstrip('-')):
                    for k in node.keywords:
                        if k.arg=='default':
                            try: self.add(literal(k.value,env),'source_cli_default:'+node.args[0].value,path,str(node.lineno))
                            except (ValueError,KeyError,AssertionError,TypeError): pass
            if isinstance(node,ast.Dict):
                for key,value in zip(node.keys,node.values):
                    if isinstance(key,ast.Constant) and seed_key(key.value):
                        try: self.add(literal(value,env),'source_dict:'+str(key.value),path,str(node.lineno))
                        except (ValueError,KeyError,AssertionError,TypeError): pass
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
                for arg,default in zip(node.args.args[-len(node.args.defaults):],node.args.defaults):
                    if seed_key(arg.arg):
                        try: self.add(literal(default,env),'source_default:'+arg.arg,path,str(node.lineno))
                        except (ValueError,KeyError,AssertionError,TypeError): pass

    def markdown(self,text,path):
        headers=None
        for number,line in enumerate(text.splitlines(),1):
            if line.strip().startswith('|'):
                cells=[s.strip().strip('`') for s in line.strip().strip('|').split('|')]
                if any(re.search(r'\bseed',s,re.I) for s in cells) and not any(re.search(r'\d',s) for s in cells):
                    headers=cells; continue
                if headers and len(cells)==len(headers):
                    for header,value in zip(headers,cells):
                        if re.search(r'\bseeds?\b',header,re.I) and re.fullmatch(r'[\d ,/]+',value):
                            for token in re.findall(r'\d+',value): self.add(int(token),'protocol_table:'+header,path,str(number))
            else: headers=None
            for match in re.finditer(r'\b((?:data|pretrain(?:ing)?|model|weight|training)[ _/-]*)?seeds?\s*[:=]\s*([\[{]?[\d, /]+)',line,re.I):
                for token in re.findall(r'\d+',match.group(2)):
                    self.add(int(token),'protocol_assignment:'+match.group(0).split(':')[0].split('=')[0],path,str(number))

    def examine(self,path):
        rel=path.relative_to(ROOT).as_posix(); blob=path.read_bytes(); digest=sha_bytes(blob)
        row=dict(path=rel,sha256=digest,bytes=len(blob),format=path.suffix)
        self.files.append(row)
        try: text=blob.decode('utf-8-sig')
        except UnicodeDecodeError as exc:
            self.omissions.append(dict(path=rel,reason='text_decode_failure',detail=str(exc))); row['status']='unparsed'; return
        try:
            if path.suffix=='.json':
                if digest in self.json_seen:
                    row.update(status='identical_content_alias',parsed_source=self.json_seen[digest]); return
                self.json_seen[digest]=rel; self.structured(json.loads(text),rel)
            elif path.suffix=='.jsonl':
                if digest in self.json_seen:
                    row.update(status='identical_content_alias',parsed_source=self.json_seen[digest]); return
                self.json_seen[digest]=rel
                for i,line in enumerate(text.splitlines(),1):
                    if line.strip(): self.structured(json.loads(line),rel,f'$line{i}')
            elif path.suffix=='.py':
                if digest in self.code_seen:
                    row.update(status='identical_content_alias',parsed_source=self.code_seen[digest]); return
                self.code_seen[digest]=rel; self.python(text,rel)
            elif path.suffix=='.md':
                if digest in self.markdown_seen:
                    row.update(status='identical_content_alias',parsed_source=self.markdown_seen[digest]); return
                self.markdown_seen[digest]=rel; self.markdown(text,rel)
            row['status']='parsed'
        except (ValueError,SyntaxError,TypeError,KeyError,AssertionError) as exc:
            self.omissions.append(dict(path=rel,reason='parse_failure',detail=repr(exc))); row['status']='unparsed'


def inherited_derivations(inv):
    """Expand observed model/data contexts under inspected historical formulas.

    These formulas are explicitly source-bound; no seed is inferred from file
    names or from arbitrary numeric outcomes. Epoch intervals are conservative
    if a config declares a duration but the saved run stopped before completion.
    """
    engine=ROOT/'outputs/sequence-weighting-stage2/stage2.py'
    mechanism=ROOT/'outputs/sequence-weighting-pilot/mechanism.py'
    pilot=ROOT/'outputs/sequence-weighting-pilot/pilot.py'
    for p in [engine,mechanism,pilot]:
        code=p.read_text(encoding='utf-8'); assert '1000' in code and '999' in code
    schemes=[]
    for seed,contexts in sorted(inv.model_contexts.items()):
        maximum=max(c['epochs'] for c in contexts)
        if maximum:
            source=min(contexts,key=lambda c:(-c['epochs'],c['path'],c['location']))
            schemes.append(dict(role='batch_order',base_seed=seed,formula='999 + seed + epoch',
                epoch_range=[1,maximum],values=list(range(1000+seed,1000+seed+maximum)),
                context=source,coverage='Declared duration; conservative if interrupted'))
        random_contexts=[c for c in contexts if c['weighting']=='random']
        if random_contexts:
            schemes.append(dict(role='weight_assignment',base_seed=seed,formula='1000 + seed',
                values=[1000+seed],context=min(random_contexts,key=lambda c:(c['path'],c['location'])),
                coverage='Saved random-arm model config/result'))
    for seed,contexts in sorted(inv.data_contexts.items()):
        schemes.append(dict(role='synthetic_key_sampling',base_seed=seed,formula='seed + 77',values=[seed+77],
            context=dict(zip(['path','location'],min(contexts))),
            coverage='Conservative for data-role records: applicable to synthetic corrected key samplers'))
    return schemes, {p.relative_to(ROOT).as_posix():sha_bytes(p.read_bytes()) for p in [engine,mechanism,pilot]}


def proposal_check(rows,historical,derivations,model_replacements=None):
    if model_replacements:
        mapping=dict(zip(sorted({r['value'] for r in rows if r['role']=='model_weight'}),model_replacements))
        rows=[dict(r,value=mapping[r['value']]) if r['role']=='model_weight' else dict(r) for r in rows]
    checks=[]
    for value in sorted({r['value'] for r in rows}):
        prior=[dict(role=role,evidence=[dict(path=p,location=l) for p,l in sorted(evidence)[:5]],
                    provenance_locations=len(evidence)) for (old,role),evidence in historical.items() if old==value]
        derived=[d for d in derivations if value in d['values']]
        checks.append(dict(value=value,proposed_roles=sorted({r['role'] for r in rows if r['value']==value}),
            base_or_literal_collisions=prior,derived_stream_collisions=derived,clear=not prior and not derived))
    old_values={v for v,_ in historical}|{v for d in derivations for v in d['values']}
    new_derived=[]
    for seed in sorted({r['value'] for r in rows if r['role']=='model_weight'}):
        weights={1000+seed}; batch=set(range(1000+seed,1030+seed)); pretrain=set(range(1000+seed,1004+seed))
        new_derived.append(dict(base_seed=seed,weight_seed=1000+seed,batch_seeds=sorted(batch),
            pretraining_batch_seeds=sorted(pretrain),historical_collisions=sorted((weights|batch|pretrain)&old_values)))
    new_data_derived=[dict(base_seed=seed,key_sampling_seed=seed+77,historical_collision=seed+77 in old_values)
        for seed in sorted({r['value'] for r in rows if r['role'] in ['adaptation_data','pretraining_data']})]
    across=[]
    for i,a in enumerate(new_derived):
        for b in new_derived[i+1:]:
            common=set(a['batch_seeds'])&set(b['batch_seeds'])
            if common: across.append(dict(model_seeds=[a['base_seed'],b['base_seed']],shared_batch_seeds=sorted(common)))
    tune={r['value'] for r in rows if r['phase']=='TUNE'}; confirm={r['value'] for r in rows if r['phase']=='CONFIRM'}
    return dict(proposed_rows=rows,checks=checks,new_model_streams=new_derived,new_data_streams=new_data_derived,
        tuning_confirmation_base_overlap=sorted(tune&confirm),cross_model_batch_stream_overlaps=across,
        base_values_clear=all(c['clear'] for c in checks),
        model_derived_streams_clear=all(not d['historical_collisions'] for d in new_derived),
        data_derived_streams_clear=all(not d['historical_collision'] for d in new_data_derived))


def fixtures():
    assert seed_key('seed_noise') and seed_key('pretraining_seed') and not seed_key('seed_count')
    inv=Inventory(); inv.structured(dict(loss=1501,count=1401,seed=42,training_seeds=[43,44],seed_count=1502),'fixture')
    assert {v for v,_ in inv.records}=={42,43,44}
    env={'PANELS':{'P1':[(1,2,3)]}}
    assert literal(ast.parse('[row for rows in PANELS.values() for row in rows]',mode='eval').body,env)==[(1,2,3)]
    assert literal(ast.parse('[(d,s,p) for d,p in [(11,12)] for s in range(21,23)]',mode='eval').body,{})==[(11,21,12),(11,22,12)]
    inv.markdown('| Role | Data seed | Model/weight seed |\n| --- | --- | --- |\n| T | 77 | 88, 89 |','fixture')
    assert {77,88,89}<={v for v,_ in inv.records}
    return dict(arbitrary_loss_and_count_values_excluded=True,seed_fields_and_lists=True,
                safe_literal_comprehensions=True,seed_table_columns=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--check-against',type=Path,
                        help='Rebind current config to a preserved inventory without rescanning history')
    parser.add_argument('--candidate-model-seeds',type=int,nargs=4,default=[140101,140201,150101,150201])
    args=parser.parse_args(); assert not args.output.exists(),'Preserve existing inventory evidence'
    if args.check_against:
        started=time.perf_counter()
        old=json.loads(args.check_against.read_text(encoding='utf-8'))
        assert old['status'] in ['PASS','COLLISIONS'] and not old['omissions']
        historical={(r['value'],r['role']):{(p['path'],p['location']) for p in r['provenance']}
                    for r in old['seed_records']}
        rows=candidates(HERE/'config.py')
        proof=proposal_check(rows,historical,old['derived_streams'])
        assert proof['base_values_clear'] and proof['model_derived_streams_clear'] and proof['data_derived_streams_clear']
        assert not proof['tuning_confirmation_base_overlap'] and not proof['cross_model_batch_stream_overlaps']
        assert rows==old['alternative_model_seed_candidate']['proposed_rows'], 'Revised rows differ from reviewed replacement proposal'
        result=dict(status='PASS',utc=utc(),review='Revised Stage11 seed identities and derived streams',
            config_sha256=sha_bytes((HERE/'config.py').read_bytes()),
            inventory_source_sha256=sha_bytes(Path(__file__).read_bytes()),
            inventory_binding=dict(path=args.check_against.resolve().relative_to(ROOT).as_posix(),
                sha256=sha_bytes(args.check_against.read_bytes()),bytes=args.check_against.stat().st_size),
            historical_inventory_source_sha256=old['inventory_source_sha256'],
            historical_files_examined=old['files_examined_count'],historical_seed_values=old['distinct_recorded_seed_values'],
            original_colliding_proposal=[c for c in old['current_proposal']['checks'] if not c['clear']],
            replacement_proof=proof,no_historical_rescan=True,no_model_outcomes=True,
            limitations=old['limitations'],elapsed_seconds=time.perf_counter()-started)
        with args.output.open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2,allow_nan=False); stream.write('\n')
        print(json.dumps(dict(status='PASS',review=str(args.output),historical_files=result['historical_files_examined'],
                             elapsed_seconds=result['elapsed_seconds'])),flush=True)
        return
    start=time.perf_counter(); started=utc(); fixture=fixtures(); inv=Inventory()
    excluded=[]; ignored=Counter(); paths=[]
    for base in [ROOT/'outputs',ROOT/'work/runs']:
        for path in sorted(base.rglob('*')):
            if not path.is_file(): continue
            rel=path.relative_to(ROOT).as_posix()
            if ('sequence-weighting-stage11' in path.parts or 'sequence-weighting-paper-track-v1' in path.parts
                    or any(part.startswith(('rule-sharing-v012-','rule-tying-v012-')) for part in path.parts)
                    or '__pycache__' in path.parts):
                excluded.append(rel); continue
            if path.suffix in TEXT_SUFFIXES: paths.append(path)
            else: ignored[path.suffix or '<none>']+=1
    for index,path in enumerate(paths):
        inv.examine(path)
        if (index+1)%2000==0: print(json.dumps(dict(examined=index+1,total=len(paths))),flush=True)
    derived,formula_sources=inherited_derivations(inv)
    proposed=candidates(HERE/'config.py')
    current=proposal_check(proposed,inv.records,derived)
    alternative=proposal_check(proposed,inv.records,derived,args.candidate_model_seeds)
    records=[dict(value=value,role=role,provenance=[dict(path=p,location=l) for p,l in sorted(evidence)])
             for (value,role),evidence in sorted(inv.records.items())]
    omissions=inv.omissions
    status='INCOMPLETE' if omissions else 'PASS' if current['base_values_clear'] else 'COLLISIONS'
    result=dict(status=status,started_utc=started,finished_utc=utc(),elapsed_seconds=time.perf_counter()-start,
        inventory_source_sha256=sha_bytes(Path(__file__).read_bytes()),config_sha256=sha_bytes((HERE/'config.py').read_bytes()),
        historical_roots=['outputs','work/runs'],files_examined=inv.files,files_examined_count=len(inv.files),
        format_counts=dict(Counter(p.suffix for p in paths)),excluded_new_stage_or_proposal_or_cache=excluded,
        binary_archive_and_other_formats_not_loaded=dict(ignored),seed_records=records,
        distinct_recorded_seed_values=len({r['value'] for r in records}),derived_streams=derived,
        source_bound_derivation_formulas=formula_sources,nonliteral_rng_expressions=inv.expressions,
        omissions=omissions,current_proposal=current,alternative_model_seed_candidate=alternative,fixtures=fixture,
        claims=dict(historical_model_outcomes_not_recomputed=True,source_files_not_executed=True,
            metadata_and_source_hashes_saved=True,no_gpu_or_training=True),
        limitations=[
            'Identical file-content aliases share the canonical parsed seed provenance; every alias path and SHA256 is retained.',
            'Inventory covers historical saved JSON/JSONL, literal Python configurations/RNG constants and explicit Markdown seed declarations under both roots.',
            'Binary tensors/checkpoints and zip archives were not loaded; their expanded metadata and frozen source are inventoried. Historical deleted or unsaved seeds cannot be reconstructed.',
            'Nonliteral RNG expressions are retained. Runtime seed instances are reconstructed from saved configuration roles for the inherited weight/order/key formulas, while simulation weight/noise seeds come from structured records.',
            'Declared epoch ranges and applying key-seed offsets to data-role metadata can be conservative; a derived collision carries its evidence and role.',
            'The same integer in different PRNG engines/roles is a seed-identifier collision, not by itself evidence of identical datasets or contamination.',
            'Within one model seed, inherited weight RNG seed and first batch-order seed coincide numerically across different PRNG engines; this documented pairing is intentional.',
            'All proposals and replacement candidates are prospective; this script never edits config, protocols or historical records.'
        ])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream: json.dump(result,stream,indent=2,allow_nan=False); stream.write('\n')
    print(json.dumps(dict(status=status,output=str(args.output),files=len(paths),distinct_seeds=result['distinct_recorded_seed_values'],
        omissions=len(omissions),current_collisions=[c['value'] for c in current['checks'] if not c['clear']],
        alternative_base_clear=alternative['base_values_clear'],alternative_model_streams_clear=alternative['model_derived_streams_clear'],
        alternative_data_streams_clear=alternative['data_derived_streams_clear'],elapsed_seconds=result['elapsed_seconds'])),flush=True)


if __name__=='__main__': main()
