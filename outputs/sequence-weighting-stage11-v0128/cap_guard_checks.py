"""Focused 180-second guard correctness fixtures; no timing benchmark/model."""
import time
START=time.perf_counter()
import copy,json,math,sys
from pathlib import Path
import preparation as p
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OUT=ROOT/'work/runs/cap-guard-v0128-20261001-01'
def main():
    OUT.mkdir(parents=True,exist_ok=False);checks=[]
    def record(name,ok):
        value=dict(name=name,status='PASS' if ok else 'FAILED');checks.append(value)
        p.write_json(OUT/('CHECK-'+name+'.json'),value)
        if not ok:raise AssertionError(name)
    def make(name,limit=180):
        root=OUT/name;root.mkdir();(root/'source').mkdir();clock=[0.,0.]
        guard=p.Preparation(root,0.,0.,limit=limit,monotonic=lambda:clock[0],wall=lambda:clock[1],source_root=root/'source',evidence_root=root)
        return root,guard,clock
    def rejects(fn):
        try:fn()
        except (RuntimeError,ValueError,OSError):return True
        return False
    r,g,c=make('boundaries');c[:]=[180.,179.]
    record('exact_180_monotonic',g.check('at180')['elapsed_seconds']==180.)
    c[:]=[179.,180.];record('exact_180_utc',g.check('at180utc')['elapsed_seconds']==180.)
    c[:]=[180.001,0.];record('over_180_monotonic',rejects(lambda:g.check('overmono')))
    c[:]=[0.,180.001];record('over_180_utc',rejects(lambda:g.check('overutc')))
    for name,limit in [('zero',0.),('negative',-1.),('above180',181.),('infinity',float('inf')),('nan',float('nan'))]:
        root=OUT/('limit-'+name);root.mkdir()
        rejected=rejects(lambda:p.Preparation(root,0.,0.,limit=limit,monotonic=lambda:0.,wall=lambda:0.))
        # Strict durable JSON cannot serialize nonfinite failure metadata.
        # Missing terminal records must still fail closed; do not weaken writer.
        marker_ok=(root/'PREPARATION_FAILURE.json').exists() if math.isfinite(limit) else rejects(lambda:p.assert_launchable(root))
        record('reject_limit_'+name,rejected and marker_ok)
    r,g,c=make('lower-explicit',60);c[:]=[61.,61.]
    record('lower_explicit_cap_retained',rejects(lambda:g.check('lowercap')))
    # The default itself is180, independently of explicitly supplied limits.
    root=OUT/'default';root.mkdir();default=p.Preparation(root,0.,0.,monotonic=lambda:0.,wall=lambda:0.)
    record('default_180',default.limit==180)
    r,g,c=make('complete');g.metadata_capture_complete=True;c[:]=[180.,180.]
    receipt=g.finish(dict(fixture_only=True))
    frozen,accepted=p.assert_launchable(r,source_root=r/'source',evidence_root=r)
    record('durable_180_receipt_admitted',receipt['limit_seconds']==180 and accepted['elapsed_seconds']==180 and not (r/'PREPARATION_IN_PROGRESS.json').exists())
    originals=[p.read_json(r/n) for n in p.TERMINAL_ARTIFACTS]
    def replace_records(change,hostile_nonfinite=False):
        frozen,receipt,checkpoint=copy.deepcopy(originals)
        for value in (frozen['preparation'],receipt,checkpoint):change(value)
        def fixture_write(path,value):
            if hostile_nonfinite:
                # Deliberately forge nonstandard JSON only in this isolated
                # fixture; production write_json must remain strict.
                path.write_text(json.dumps(value,allow_nan=True),encoding='utf-8')
            else:p.write_json(path,value)
        fixture_write(r/'FREEZE.json',frozen);h=p.file_sha256(r/'FREEZE.json')
        receipt['freeze_sha256']=h;fixture_write(r/'PREPARATION_COMPLETE.json',receipt)
        checkpoint['freeze_sha256']=h;checkpoint['completion_sha256']=p.file_sha256(r/'PREPARATION_COMPLETE.json')
        fixture_write(r/'PREPARATION_CHECKPOINT.json',checkpoint)
    replace_records(lambda v:v.update(limit_seconds=181))
    record('launch_rejects_limit181',rejects(lambda:p.assert_launchable(r,source_root=r/'source',evidence_root=r)))
    replace_records(lambda v:v.update(monotonic_elapsed_seconds=180.001,utc_elapsed_seconds=180.001,elapsed_seconds=180.001))
    record('launch_rejects_late_receipts',rejects(lambda:p.assert_launchable(r,source_root=r/'source',evidence_root=r)))
    replace_records(lambda v:v.update(monotonic_elapsed_seconds=float('nan')),hostile_nonfinite=True)
    record('launch_rejects_nonfinite_clock',rejects(lambda:p.assert_launchable(r,source_root=r/'source',evidence_root=r)))
    replace_records(lambda v:None)
    p.write_json(r/'PREPARATION_FAILURE.json',dict(fixture=True))
    record('failure_marker_blocks_launch',rejects(lambda:p.assert_launchable(r,source_root=r/'source',evidence_root=r)))
    r,g,c=make('late-write');g.metadata_capture_complete=True;c[:]=[180.,180.]
    def late_write(path,value):
        p.write_json(path,value)
        if path.name=='FREEZE.json':c[:]=[180.001,180.001]
    g.writer=late_write
    record('late_write_persists_failure',rejects(lambda:g.finish(dict(fixture_only=True))) and (r/'PREPARATION_FAILURE.json').exists() and (r/'PREPARATION_IN_PROGRESS.json').exists())
    record('late_write_blocks_launch',rejects(lambda:p.assert_launchable(r,source_root=r/'source',evidence_root=r)))
    result=dict(status='PASS',checks=checks,count=len(checks),elapsed_seconds=time.perf_counter()-START,
        no_model_preparation_training=True,scope='Synthetic guard fixtures only; no research preparation or performance estimate')
    p.write_json(OUT/'RESULT.json',result);print(json.dumps(dict(status='PASS',count=len(checks),result=str(OUT/'RESULT.json'))),flush=True)
if __name__=='__main__':
    try:main()
    except BaseException as exc:
        if OUT.exists():p.write_json(OUT/'CHECK_FAILURE.json',dict(error=repr(exc),elapsed_seconds=time.perf_counter()-START))
        raise
