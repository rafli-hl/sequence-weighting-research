"""Frozen ranking/contrast audit summaries; no new fit or replacement p*."""
import argparse
import csv
import hashlib
import json
import math
import os
import shutil
import statistics as st
import sys
import time
import traceback
import zipfile
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal,localcontext
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
METHODS=['legacy_J','naive_D64','stable_D64']
CATEGORIES=[1.,.1,.01,1e-12,0.,-.01]
METHOD_LABELS={'legacy_J':'Legacy J64','naive_D64':'Naive D64','stable_D64':'Factored D64'}
COLORS={'legacy_J':'#6c568d','naive_D64':'#bb582c','stable_D64':'#2374a6'}
PRECISION=110


def utc(): return datetime.now(timezone.utc).isoformat()


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def write(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,allow_nan=False); stream.write('\n')


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
    return digest.hexdigest()


def d64(value): return Decimal.from_float(float(value))


def fmt(value): return 'undefined' if value is None else format(Decimal(str(value)),'.6g')


def quantile_decimal(values,q):
    if not values: return None
    values=sorted(values); index=Decimal(len(values)-1)*Decimal(str(q)); lo=int(index); hi=min(lo+1,len(values)-1)
    return values[lo]+(values[hi]-values[lo])*(index-lo)


def decimal_stats(values,total=None):
    numbers=[Decimal(v) for v in values if v is not None]
    assert all(v.is_finite() for v in numbers)
    denominator=len(values) if total is None else total
    with localcontext() as ctx:
        ctx.prec=PRECISION
        mean=sum(numbers,Decimal(0))/len(numbers) if numbers else None
        sd=(sum((x-mean)**2 for x in numbers)/(len(numbers)-1)).sqrt() if len(numbers)>1 else None
        result=dict(total=denominator,defined=len(numbers),undefined=denominator-len(numbers),
            conditional_mean=None if mean is None else str(mean),conditional_sd=None if sd is None else str(sd),
            conditional_minimum=str(min(numbers)) if numbers else None,conditional_maximum=str(max(numbers)) if numbers else None,
            conditional_median=None if not numbers else str(quantile_decimal(numbers,.5)),
            unconditional_mean=str(mean) if mean is not None and len(numbers)==denominator else None)
    return result


def rank_info(values,grid):
    minimum=min(values); indices=[i for i,value in enumerate(values) if value==minimum]
    return dict(argmin_index=indices[0],argmin_p=grid[indices[0]],exact_minimum_indices=indices,
                exact_minimum_count=len(indices),raw_exact_ties_all_pairs=sum(n*(n-1)//2 for n in Counter(values).values()))


def pairwise_counts(reference,methods,tau):
    total=len(reference)*(len(reference)-1)//2
    result=dict(total_pairs=total,reference_exact_ties=0,reference_nonexact_near_ties=0,reference_strict_pairs=0,
        methods={name:dict(raw_exact_ties_all_pairs=0,strict_agreements=0,strict_reversals=0,
            float_ties_against_reference_strict=0,float_strict_on_reference_nonstrict=0,
            float_ties_on_reference_nonstrict=0) for name in methods})
    for i in range(len(reference)):
        for j in range(i+1,len(reference)):
            difference=reference[i]-reference[j]
            strict=abs(difference)>tau
            if strict: result['reference_strict_pairs']+=1
            elif difference==0: result['reference_exact_ties']+=1
            else: result['reference_nonexact_near_ties']+=1
            for name,values in methods.items():
                counts=result['methods'][name]; comparison=(values[i]>values[j])-(values[i]<values[j])
                if comparison==0: counts['raw_exact_ties_all_pairs']+=1
                if strict:
                    if comparison==0: counts['float_ties_against_reference_strict']+=1
                    elif (comparison>0)==(difference>0): counts['strict_agreements']+=1
                    else: counts['strict_reversals']+=1
                elif comparison==0: counts['float_ties_on_reference_nonstrict']+=1
                else: counts['float_strict_on_reference_nonstrict']+=1
    assert result['reference_exact_ties']+result['reference_nonexact_near_ties']+result['reference_strict_pairs']==total
    for counts in result['methods'].values():
        assert counts['strict_agreements']+counts['strict_reversals']+counts['float_ties_against_reference_strict']==result['reference_strict_pairs']
        assert counts['float_strict_on_reference_nonstrict']+counts['float_ties_on_reference_nonstrict']==total-result['reference_strict_pairs']
    return result


def normalized_error(error,contrast_scale,span):
    return dict(max_abs_error=str(error),relative_to_contrast_scale=str(error/contrast_scale),
                relative_to_contrast_span=str(error/span) if span>0 else None)


def profile_metrics(row,grid,classification=None):
    with localcontext() as ctx:
        ctx.prec=PRECISION
        legacy_defined=row['legacy_reason'] is None; reference_defined=row['hp_reason'] is None
        assert all((row[name] is not None)==legacy_defined for name in METHODS)
        assert all((row[name] is not None)==reference_defined for name in ['hp_J','hp_D'])
        result={key:row.get(key) for key in ['source_id','source_array_index','block_id','n','replicate','generator_p','c','truth_p',
            'seed_weights','seed_noise','weights_sha256','gains_sha256','original_p','original_reason','original_objective',
            'legacy_reason','hp_reason','total_gain_legacy','total_gain_fsum','total_gain_hp','hp_dps','hp_identity_max_abs_error']}
        assert row['hp_dps']==80
        hp_total=Decimal(row['total_gain_hp'])
        legacy_difference=d64(row['total_gain_legacy'])-hp_total
        fsum_difference=d64(row['total_gain_fsum'])-hp_total
        result['normalization_difference']=dict(legacy_minus_hp=str(legacy_difference),fsum_minus_hp=str(fsum_difference),
            legacy_relative_to_hp=str(abs(legacy_difference)/abs(hp_total)) if hp_total else None,
            fsum_relative_to_hp=str(abs(fsum_difference)/abs(hp_total)) if hp_total else None)
        result.update(legacy_defined=legacy_defined,reference_defined=reference_defined,
            both_defined=legacy_defined and reference_defined,domain_mismatch=legacy_defined!=reference_defined,
            reference_validation=classification or {},reference_classification_unresolved=bool((classification or {}).get('unresolved',False)),
            reference=None,methods={},pairwise=None,original_point=None)
        method_values={}
        if legacy_defined:
            for name in METHODS:
                values=row[name]; assert len(values)==len(grid) and all(math.isfinite(v) for v in values)
                method_values[name]=values
                result['methods'][name]=dict(available=True,**rank_info(values,grid),exact_argmin_agreement=None,
                    reference_minset_agreement=None,reference_regret=None,reference_regret_excess_over_tau=None,
                    error=None,pairwise=None)
        else:
            result['methods']={name:dict(available=False,argmin_index=None,argmin_p=None,exact_minimum_indices=None,
                exact_minimum_count=None,raw_exact_ties_all_pairs=None,exact_argmin_agreement=None,reference_minset_agreement=None,
                reference_regret=None,reference_regret_excess_over_tau=None,error=None,pairwise=None) for name in METHODS}
        if reference_defined:
            ref=[Decimal(value) for value in row['hp_D']]; ref_J=[Decimal(value) for value in row['hp_J']]
            assert len(ref)==len(ref_J)==len(grid) and all(v.is_finite() for v in ref+ref_J)
            scale=max(Decimal(1),max(abs(value) for value in ref)); tau=Decimal('2e-50')*scale
            minimum=min(ref); span=max(ref)-minimum; sorted_values=sorted(ref)
            minset=[i for i,value in enumerate(ref) if value<=minimum+tau]
            info=rank_info(ref,grid)
            result['reference']=dict(**info,minimum_D=str(minimum),contrast_scale=str(scale),contrast_span=str(span),
                top_two_gap=str(sorted_values[1]-sorted_values[0]),tau=str(tau),minimum_set_indices=minset,
                minimum_set_size=len(minset),ranking_reference='Decimal80 D grid, independently validated at Decimal110',
                strict_order_is_resolution_limited=True)
            pairs=pairwise_counts(ref,method_values,tau)
            result['pairwise']={key:value for key,value in pairs.items() if key!='methods'}
            for name,values in method_values.items():
                info=result['methods'][name]; chosen=info['argmin_index']; regret=ref[chosen]-minimum
                assert regret>=0
                reference_for_error=ref_J if name=='legacy_J' else ref
                maximum=max(abs(d64(value)-target) for value,target in zip(values,reference_for_error))
                info.update(exact_argmin_agreement=chosen==result['reference']['argmin_index'],
                    reference_minset_agreement=chosen in minset,reference_regret=str(regret),
                    reference_regret_excess_over_tau=str(max(Decimal(0),regret-tau)),
                    error=normalized_error(maximum,scale,span),pairwise=pairs['methods'][name])
                assert info['raw_exact_ties_all_pairs']==info['pairwise']['raw_exact_ties_all_pairs']
            if row['original_point'] is not None and row['original_point']['hp_D'] is not None:
                point=row['original_point']; assert point['p']==row['original_p']
                hp_D=Decimal(point['hp_D']); hp_J=Decimal(point['hp_J'])
                point_errors={}
                for name in METHODS:
                    value=point[name]
                    point_errors[name]=None if value is None else normalized_error(abs(d64(value)-(hp_J if name=='legacy_J' else hp_D)),scale,span)
                result['original_point']=dict(p=point['p'],hp_D=str(hp_D),signed_HP_gap_vs_grid_min=str(hp_D-minimum),
                    lower_than_grid_min=hp_D<minimum,point_errors=point_errors,
                    interpretation='Signed diagnostic gap for the stored continuous estimate; not a continuous optimum or grid candidate')
        return result


def _counts(values): return dict(sorted(Counter(values).items(),key=lambda item:str(item[0])))


def summarize_cell(profiles,expected_replicates=64):
    assert len(profiles)==expected_replicates and len({p['replicate'] for p in profiles})==expected_replicates
    cell={k:profiles[0][k] for k in ['n','generator_p','c','truth_p']}
    assert all({k:p[k] for k in cell}==cell for p in profiles)
    both=[p for p in profiles if p['both_defined']]; refs=[p for p in profiles if p['reference_defined']]
    result=dict(condition=cell,total=len(profiles),legacy_defined=sum(p['legacy_defined'] for p in profiles),
        reference_defined=len(refs),both_defined=len(both),domain_mismatches=sum(p['domain_mismatch'] for p in profiles),
        legacy_undefined_reasons=_counts(p['legacy_reason'] for p in profiles if not p['legacy_defined']),
        hp_undefined_reasons=_counts(p['hp_reason'] for p in profiles if not p['reference_defined']),
        reference_classification_unresolved=sum(p['reference_classification_unresolved'] for p in profiles),
        reference_argmin_frequencies=_counts(p['reference']['argmin_index'] for p in refs),
        reference_exact_minimum_tie_profiles=sum(p['reference']['exact_minimum_count']>1 for p in refs),
        reference_band_minimum_tie_profiles=sum(p['reference']['minimum_set_size']>1 for p in refs),
        reference_exact_pair_ties=sum(p['pairwise']['reference_exact_ties'] for p in refs),
        reference_nonexact_near_pair_ties=sum(p['pairwise']['reference_nonexact_near_ties'] for p in refs),
        reference_strict_pairs=sum(p['pairwise']['reference_strict_pairs'] for p in refs),
        methods={},source_ids=[p['source_id'] for p in sorted(profiles,key=lambda p:p['replicate'])])
    for metric in ['contrast_scale','contrast_span','top_two_gap','tau']:
        result['reference_'+metric]=decimal_stats([p['reference'][metric] if p['reference'] else None for p in profiles])
    result['normalization_difference']={metric:decimal_stats([p['normalization_difference'][metric] for p in profiles])
        for metric in ['legacy_minus_hp','fsum_minus_hp','legacy_relative_to_hp','fsum_relative_to_hp']}
    signed=[p['original_point']['signed_HP_gap_vs_grid_min'] if p['original_point'] else None for p in profiles]
    result['original_point_signed_gap']=decimal_stats(signed)
    result['original_point_below_grid_count']=sum(Decimal(x)<0 for x in signed if x is not None)
    result['original_point_equal_grid_count']=sum(Decimal(x)==0 for x in signed if x is not None)
    for name in METHODS:
        available=[p['methods'][name] for p in profiles if p['methods'][name]['available']]
        comparisons=[p['methods'][name] for p in both]
        pairs={field:sum(p['methods'][name]['pairwise'][field] for p in both) for field in
            ['raw_exact_ties_all_pairs','strict_agreements','strict_reversals','float_ties_against_reference_strict',
             'float_strict_on_reference_nonstrict','float_ties_on_reference_nonstrict']}
        denominator=sum(p['pairwise']['reference_strict_pairs'] for p in both)
        exact=sum(x['exact_argmin_agreement'] for x in comparisons); tolerant=sum(x['reference_minset_agreement'] for x in comparisons)
        result['methods'][name]=dict(available=len(available),comparable=len(comparisons),
            argmin_frequencies=_counts(x['argmin_index'] for x in available),
            exact_minimum_tie_profiles=sum(x['exact_minimum_count']>1 for x in available),
            raw_exact_ties_all_pairs_available=sum(x['raw_exact_ties_all_pairs'] for x in available),
            exact_argmin_agreements=exact,reference_minset_agreements=tolerant,
            exact_argmin_agreement_rate_conditional=exact/len(comparisons) if comparisons else None,
            reference_minset_agreement_rate_conditional=tolerant/len(comparisons) if comparisons else None,
            any_strict_reversal_profiles=sum(x['pairwise']['strict_reversals']>0 for x in comparisons),
            any_float_tie_on_reference_strict_profiles=sum(x['pairwise']['float_ties_against_reference_strict']>0 for x in comparisons),
            pairwise=dict(reference_strict_denominator=denominator,possible_pairs=sum(p['pairwise']['total_pairs'] for p in both),
                float_tie_rate_on_reference_strict=pairs['float_ties_against_reference_strict']/denominator if denominator else None,
                strict_reversal_rate=pairs['strict_reversals']/denominator if denominator else None,**pairs),
            reference_regret=decimal_stats([p['methods'][name]['reference_regret'] for p in profiles]),
            reference_regret_excess_over_tau=decimal_stats([p['methods'][name]['reference_regret_excess_over_tau'] for p in profiles]),
            error={metric:decimal_stats([p['methods'][name]['error'][metric] if p['methods'][name]['error'] else None for p in profiles])
                   for metric in ['max_abs_error','relative_to_contrast_scale','relative_to_contrast_span']})
    return result


def summarize(profiles,expected_replicates=64):
    groups=defaultdict(list)
    for p in profiles: groups[p['n'],p['generator_p'],p['c']].append(p)
    return [summarize_cell(groups[key],expected_replicates) for key in sorted(groups)]


def flatten(value,prefix=''):
    result={}
    for key,item in value.items():
        label=f'{prefix}_{key}' if prefix else str(key)
        if isinstance(item,dict): result.update(flatten(item,label))
        elif isinstance(item,list): result[label]=json.dumps(item,allow_nan=False)
        else: result[label]=item
    return result


def csvwrite(path,rows):
    with path.open('x',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(dict.fromkeys(key for row in rows for key in row)))
        writer.writeheader(); writer.writerows(rows)


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(str,row))+' |' for row in rows])


def figures(out,profiles,cells):
    mpl=ROOT/'work/.matplotlib'; mpl.mkdir(parents=True,exist_ok=True); os.environ['MPLCONFIGDIR']=str(mpl)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FixedLocator,FuncFormatter,NullLocator
    plt.rcParams.update({'font.size':9,'figure.dpi':160,'axes.spines.top':False,'axes.spines.right':False})
    rowkeys=[(n,p) for n in [128,512] for p in [.2,1.]]; x=np.arange(6); limits={}
    labels=['1','0.1','0.01','1e-12','0','−0.01']
    def groups(n,p): return [next(g for g in cells if (g['condition']['n'],g['condition']['generator_p'],g['condition']['c'])==(n,p,c)) for c in CATEGORIES]
    def category_axis(ax,n,p,title):
        ax.set_xlim(-.35,5.35); ax.set_xticks(x,labels); ax.set_xlabel('Signal c (categories; spacing not numeric)')
        ax.set_title(f'n={n}, generating p={p:g} — {title}',fontsize=9)
        ax.axvspan(3.5,5.35,color='#eeeeee',alpha=.5,zorder=-1)
    def symlog_axis(ax,values,key,signed=False):
        finite=[float(v) for v in values if v is not None]; assert all(math.isfinite(v) for v in finite)
        lin=1e-18; high=max(lin,max((abs(v) for v in finite),default=0.))*1.35
        low=-high if signed else -lin*.2
        ax.set_yscale('symlog',linthresh=lin); ax.set_ylim(low,high)
        magnitudes=[10.**e for e in range(-18,31,6) if 10.**e<=high]
        ticks=([-v for v in reversed(magnitudes)] if signed else [])+[0.]+magnitudes
        ax.yaxis.set_major_locator(FixedLocator(ticks)); ax.yaxis.set_minor_locator(NullLocator())
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v,pos:'0' if v==0 else ('−' if v<0 else '')+'$10^{'+str(int(round(math.log10(abs(v)))))+'}$'))
        assert all(low<v<high for v in finite)
        limits[key]=dict(minimum=low,maximum=high,points=len(finite),all_points_inside=True)
    fig,axes=plt.subplots(4,2,figsize=(14,12),layout='constrained')
    for r,(n,p) in enumerate(rowkeys):
        cellgroups=groups(n,p)
        for name in METHODS:
            exact=[g['methods'][name]['exact_argmin_agreement_rate_conditional'] for g in cellgroups]
            ties=[g['methods'][name]['pairwise']['float_tie_rate_on_reference_strict'] for g in cellgroups]
            reversals=[g['methods'][name]['pairwise']['strict_reversal_rate'] for g in cellgroups]
            axes[r,0].plot(x,[np.nan if v is None else v for v in exact],'-o',ms=4,color=COLORS[name],label=METHOD_LABELS[name])
            axes[r,1].plot(x,[np.nan if v is None else v for v in ties],'-o',ms=4,color=COLORS[name])
            axes[r,1].plot(x,[np.nan if v is None else v for v in reversals],'--s',ms=3,color=COLORS[name])
        for col,title in enumerate(['Exact first-argmin agreement / comparable profiles','Pairwise float ties (solid) / reversals (dashed)']):
            ax=axes[r,col]; category_axis(ax,n,p,title); ax.set_ylim(-.03,1.03); ax.set_ylabel('Descriptive fraction')
            for i,g in enumerate(cellgroups):
                if not g['both_defined']: ax.text(i,.5,'unavailable',rotation=90,ha='center',va='center',fontsize=8)
        axes[r,0].text(.01,.04,'Comparable profiles by category: '+','.join(str(g['both_defined'])+'/64' for g in cellgroups),
            transform=axes[r,0].transAxes,fontsize=7)
    handles=[Line2D([0],[0],color=COLORS[name],marker='o',label=METHOD_LABELS[name]) for name in METHODS]
    fig.legend(handles=handles,loc='outside lower center',ncol=3,frameon=False)
    fig.suptitle('Grid ranking diagnostics — reference strict pairs satisfy |Dᵢ−Dⱼ| > frozen τ; paired counts are not IID trials')
    fig.savefig(out/'grid-ranking.png'); plt.close(fig)
    fig,axes=plt.subplots(4,3,figsize=(17,12),layout='constrained')
    for r,(n,p) in enumerate(rowkeys):
        for col,name in enumerate(METHODS):
            ax=axes[r,col]; points=[]; medians=[]
            for i,c in enumerate(CATEGORIES):
                group=[z for z in profiles if (z['n'],z['generator_p'],z['c'])==(n,p,c) and z['methods'][name]['error'] is not None]
                values=[float(z['methods'][name]['error']['max_abs_error']) for z in group]; points.extend(values)
                ax.scatter(np.full(len(values),i)+np.linspace(-.07,.07,len(values)),values,s=8,alpha=.3,color=COLORS[name])
                medians.append(st.median(values) if values else np.nan)
            ax.plot(x,medians,'-o',ms=3,color=COLORS[name]); category_axis(ax,n,p,METHOD_LABELS[name]+': maximum absolute grid error')
            ax.set_ylabel('Error vs Decimal80 reference (symlog)'); symlog_axis(ax,points,f'error_{n}_{p}_{name}')
    fig.suptitle('Every defined profile error shown — J64 vs reference J; both D64 methods vs reference D; line is median')
    fig.savefig(out/'contrast-errors.png'); plt.close(fig)
    fig,axes=plt.subplots(4,3,figsize=(17,12),layout='constrained')
    for r,(n,p) in enumerate(rowkeys):
        regrets=[]; variations=[]; original_gaps=[]
        for index,name in enumerate(METHODS):
            medians=[]
            for i,c in enumerate(CATEGORIES):
                values=[float(z['methods'][name]['reference_regret']) for z in profiles if (z['n'],z['generator_p'],z['c'])==(n,p,c) and z['methods'][name]['reference_regret'] is not None]
                regrets.extend(values); medians.append(st.median(values) if values else np.nan)
                axes[r,0].scatter(np.full(len(values),i)+(index-1)*.09+np.linspace(-.025,.025,len(values)),values,s=7,alpha=.25,color=COLORS[name])
            axes[r,0].plot(x+(index-1)*.09,medians,'-o',ms=3,color=COLORS[name])
        for field,color in [('contrast_span','#276c67'),('top_two_gap','#b78a1f')]:
            medians=[]
            for i,c in enumerate(CATEGORIES):
                values=[float(z['reference'][field]) for z in profiles if (z['n'],z['generator_p'],z['c'])==(n,p,c) and z['reference']]
                variations.extend(values); medians.append(st.median(values) if values else np.nan)
                axes[r,1].scatter(np.full(len(values),i)+np.linspace(-.06,.06,len(values)),values,s=7,alpha=.25,color=color)
            axes[r,1].plot(x,medians,'-o',ms=3,color=color,label='Reference span' if field=='contrast_span' else 'Top-two grid gap')
        medians=[]
        for i,c in enumerate(CATEGORIES):
            values=[float(z['original_point']['signed_HP_gap_vs_grid_min']) for z in profiles if
                (z['n'],z['generator_p'],z['c'])==(n,p,c) and z['original_point']]
            original_gaps.extend(values); medians.append(st.median(values) if values else np.nan)
            axes[r,2].scatter(np.full(len(values),i)+np.linspace(-.07,.07,len(values)),values,s=8,alpha=.3,color='#64588d')
        axes[r,2].plot(x,medians,'-o',ms=3,color='#64588d'); axes[r,2].axhline(0,color='black',lw=.7)
        for col,title in enumerate(['HP regret at each method’s grid choice','Reference profile span and top-two gap','Stored continuous p: signed HP gap vs grid min']):
            category_axis(axes[r,col],n,p,title); axes[r,col].set_ylabel('Reference D units (symlog)')
        symlog_axis(axes[r,0],regrets,f'regret_{n}_{p}'); symlog_axis(axes[r,1],variations,f'variation_{n}_{p}')
        symlog_axis(axes[r,2],original_gaps,f'original_gap_{n}_{p}',signed=True)
    handles+=[Line2D([0],[0],color='#276c67',marker='o',label='Reference span'),Line2D([0],[0],color='#b78a1f',marker='o',label='Top-two gap')]
    fig.legend(handles=handles,loc='outside lower center',ncol=5,frameon=False)
    fig.suptitle('Grid regret is nonnegative; original continuous-point gaps may be negative and do not establish a continuous optimum')
    fig.savefig(out/'reference-regret.png'); plt.close(fig)
    write(out/'PLOT_CHECKS.json',dict(status='PASS',limits=limits,visual_review='pending',
        categorical_c=CATEGORIES,individual_profiles_shown=True,median_lines_are_display_only=True))


def report(root,out,grid,profiles,cells,audit,complete):
    defined=sum(p['both_defined'] for p in profiles); unresolved=sum(p['reference_classification_unresolved'] for p in profiles)
    text='# Stage 8 v0.9 — objective ranking precision on preserved signed gains\n\n'
    text+=f'Run `{root.name}` evaluates **{len(profiles):,} preserved Stage7 cancellation profiles** from 128 shared blocks, in **24 cells × 64 replicates**. '
    text+=f'**{defined:,} profiles** have both legacy and high-precision objectives; all other profiles and guard outcomes remain recorded. '
    text+='No gains, training runs, fits or p* replacements were generated for this study.\n\n'
    text+='## Measured results\n\n'
    text+=f"All {audit['eligible_grid_points']:,} eligible grid points and {audit['original_points_verified']:,} stored-p points passed the frozen 80/110-digit convergence bounds. "
    text+=f"Legacy and high-precision guards disagree in {sum(p['domain_mismatch'] for p in profiles)} of {len(profiles)} cases. "
    text+='The following counts compare grid choices on the same profiles; the final column counts profiles with at least one reference-strict pair reversed.\n\n'
    result_rows=[]
    for label,chosen in [('All comparable', [p for p in profiles if p['both_defined']]),
                         ('c=1e-12 comparable', [p for p in profiles if p['both_defined'] and p['c']==1e-12])]:
        for name in METHODS:
            methods=[p['methods'][name] for p in chosen]
            result_rows.append([label,METHOD_LABELS[name],len(methods),
                sum(m['exact_argmin_agreement'] for m in methods),
                sum(m['reference_minset_agreement'] for m in methods),
                sum(m['exact_minimum_count']>1 for m in methods),
                sum(m['pairwise']['strict_reversals']>0 for m in methods)])
    text+=table(['Profiles','Method','Comparable','Exact argmin matches','Reference-band matches','Tied method minima','Any reversed pair'],result_rows)+'\n\n'
    text+='These are numerical fidelity results for reused inputs. Grid agreement does not measure recovery of the generating exponent, validate continuous optimization, or identify the cause of Stage7 recovery error.\n\n'
    text+='## Question and fixed comparisons\n\n'
    text+='Does binary64 arithmetic preserve grid rankings and objective contrasts of the unchanged signed-gain objective? '
    text+=f'The diagnostic grid has {len(grid)} exact saved binary64 values i/20, i=0..160, and anchor p=0. '
    text+='Legacy J64 follows the original operation order. Naive D64 subtracts J64(0); factored D64 evaluates the algebraic contrast using sequential prefixes and math.fsum of products, '
    text+='with the original Python sum gain denominator. Decimal80 reference arrays use the exact binary64 inputs and a high-precision sum/log/exp evaluation.\n\n'
    text+='The factored route changes algebra and accumulation, so its differences cannot be assigned solely to removal of a common offset. '
    text+='The high-precision route changes precision throughout the pipeline and is a checked numerical reference to saved rounded inputs, not unknown unrounded data.\n\n'
    text+='The independent auditor reconstructs Decimal110 objectives and direct contrasts. Preregistered convergence bounds are '
    text+='1e-50·max(1,abs(J110)) for J and 1e-50·max(1,max(abs(D110))) for D. Ranking reference remains D80, with '
    text+='τ = 2e-50·max(1,max(abs(D80))). Reference minimum-set membership is D80≤min(D80)+τ; a reference pair is strict only if its absolute difference exceeds τ.\n\n'
    text+=f'**{unresolved} profiles** have an 80-vs-110 classification difference or lie near a classification boundary relative to the observed precision drift. Such cases are retained and labelled unresolved; '
    text+='tolerance-aware counts use the declared D80 reference and do not assert a fully resolved ordering beyond the checked precision.\n\n'
    text+='## Availability and all-cell ranking counts\n\n'
    text+='Each row below has 64 independently drawn blocks at its n. Conditions on the same block share weights/noise; neither cells nor the 12,880 grid pairs within a profile are independent trials. '
    text+='“Exact” means the same first-index strict argmin as D80. “Band” accepts any index within the frozen reference minimum set. Counts are conditional on both objectives being available; the available count is explicit.\n\n'
    text+=table(['n','Generator p','c','Legacy /64','HP /64','Both /64','Domain mismatch','Unresolved','Legacy exact/band','Naive exact/band','Factored exact/band'],[
        [g['condition']['n'],g['condition']['generator_p'],g['condition']['c'],g['legacy_defined'],g['reference_defined'],g['both_defined'],
         g['domain_mismatches'],g['reference_classification_unresolved']]+[
         f"{g['methods'][name]['exact_argmin_agreements']}/{g['methods'][name]['reference_minset_agreements']}" for name in METHODS]
        for g in cells])+'\n\n'
    text+='The first index resolves raw exact method ties deterministically. Exact ties, near-ties under τ, float ties against reference-strict pairs and strict reversals are counted separately. '
    text+='Unavailable cells have null comparisons rather than zero error. All per-profile tie index sets and metrics are preserved in `profile-metrics.jsonl`.\n\n![Ranking](grid-ranking.png)\n\n'
    text+='## Errors, reference variation and regret\n\n'
    text+='Binary64 values are promoted with Decimal.from_float. Error subtraction, normalization and summaries are computed with Decimal precision110 and stored as strings; '
    text+='conversion to binary64 is used only for plotting. Each profile records maximum absolute J error, naive/factored D error, and both error/max(1,max|D80|) and error/reference-span. '
    text+='Span normalization is null when span is zero. Decimal strings preserve small differences before any display conversion.\n\n'
    text+=table(['n','Generator p','c','Both /64','Max J error','Max naive D error','Max factored D error','Max naive regret','Max factored regret','Median ref span','Median top-two gap'],[
        [g['condition']['n'],g['condition']['generator_p'],g['condition']['c'],g['both_defined']]+[
         fmt(g['methods'][name]['error']['max_abs_error']['conditional_maximum']) for name in METHODS]+[
         fmt(g['methods'][name]['reference_regret']['conditional_maximum']) for name in ['naive_D64','stable_D64']]+[
         fmt(g['reference_contrast_span']['conditional_median']),fmt(g['reference_top_two_gap']['conditional_median'])] for g in cells])+'\n\n'
    text+='“Max” is over available profiles in that cell, without excluding poor objectives or ranks. Conditional mean/SD/min/max/median and unconditional means '
    text+='(null if any required profile is unavailable) are in `summaries.json` and `summaries.csv`; pairwise counts also retain their resolved-reference denominator.\n\n![Contrast errors](contrast-errors.png)\n\n'
    text+='Grid regret is D80 at a method’s selected grid index minus the grid minimum, so it is nonnegative. The tolerance-aware excess is max(0,regret−τ), '
    text+='while exact agreement and raw regret are also retained. A small absolute objective error does not itself certify a ranking if the relevant gap is smaller. '
    text+='Conversely, a large common objective offset need not change the ranking.\n\n'
    text+='The original stored continuous p* is evaluated separately and is never added to the grid candidate set. Its signed reference contrast minus the grid minimum can be negative. '
    text+='That comparison neither locates a continuous global optimum nor replaces the historical p*.\n\n![Reference regret and profiles](reference-regret.png)\n\n'
    text+='## Guard controls and precision limits\n\n'
    text+=table(['n','Generator p','c','Legacy undefined reasons','HP undefined reasons','Original-point defined','Original-point below grid','Max relative total error: legacy vs HP'],[
        [g['condition']['n'],g['condition']['generator_p'],g['condition']['c'],json.dumps(g['legacy_undefined_reasons'],sort_keys=True),
         json.dumps(g['hp_undefined_reasons'],sort_keys=True),g['original_point_signed_gap']['defined'],g['original_point_below_grid_count'],
         fmt(g['normalization_difference']['legacy_relative_to_hp']['conditional_maximum'])] for g in cells])+'\n\n'
    text+='Domain eligibility uses each route’s declared denominator/guard, without retrospective filtering. Exact input preservation does not mean arithmetic routes share the same denominator rounding; '
    text+='the legacy sum, math.fsum and high-precision total are retained. Classification differences between the two precision references are reported rather than removed.\n\n'
    text+='Stage7 already showed that all c=1e-12 cases could be defined while recovery error remained large. '
    text+='This study diagnoses numerical objective/ranking fidelity on those same draws; agreement with a high-precision profile is not accuracy, identifiability, useful adaptation, '
    text+='or a validated sequence-weighting mechanism. Changes in c also change signal-to-noise ratio. No fit-quality threshold, exclusion rule, new target exponent, novelty claim or publication guarantee is introduced.\n\n'
    text+='## Audit and provenance\n\n'
    text+=f"Independent audit status: **{audit['status']}**. Reference-classification evidence and original profiles are included in the raw archive. "
    text+='Three scientific figures use categorical c spacing and include every defined plotted profile within explicit axes. Visual review is recorded separately.\n\n'
    text+='Recorded completion metadata:\n\n```json\n'+json.dumps(complete,indent=2,allow_nan=False)+'\n```\n\n'
    text+=f"Protocol SHA256: `{sha(HERE/'PROTOCOL_STAGE8.md')}`. Profile SHA256: `{sha(root/'profiles.jsonl')}`. "
    text+='All frozen sources, raw arrays/profiles, checks, numerical summaries and figure files are preserved in a CRC/SHA-checked archive. '
    text+='No model training, cloud execution, upload or publication was performed.\n'
    (out/'REPORT.md').write_text(text,encoding='utf-8')


def main():
    start=time.perf_counter(); started=datetime.now(timezone.utc)
    parser=argparse.ArgumentParser(); parser.add_argument('--run-id',required=True); args=parser.parse_args()
    assert args.run_id and args.run_id not in ['.','..'] and '/' not in args.run_id and '\\' not in args.run_id
    raw=ROOT/'work/runs'/args.run_id; out=HERE/f'results-{args.run_id}'
    assert not out.exists(),'Preserve completed or partial analysis'
    complete=read(raw/'COMPLETE.json'); audit=read(raw/'AUDIT.json'); assert audit['status']=='PASS'
    source=read(raw/'source_manifest.json'); assert audit['source_sha256']==source
    assert {'analyze_stage8.py','analysis_checks.py','PROTOCOL_STAGE8.md'}<=set(source)
    for name,digest in source.items(): assert sha(HERE/name)==sha(raw/'source'/name)==digest,name
    assert sha(raw/'profiles.jsonl')==complete['profiles_sha256']==audit['profiles_sha256']
    classification_file=raw/audit['classification_evidence_file']
    assert classification_file.resolve().parent==raw.resolve()
    assert sha(classification_file)==audit['classification_evidence_sha256']
    classifications=read(classification_file)['cases']; by_id={c['source_id']:c for c in classifications}
    config=read(raw/'config.json'); grid=config['grid']; assert grid==[i/20 for i in range(161)]
    rows=[json.loads(line) for line in (raw/'profiles.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    assert len(rows)==1536 and len({r['source_id'] for r in rows})==1536
    assert set(by_id)=={r['source_id'] for r in rows} and len(classifications)==1536
    out.mkdir()
    try:
        profiles=[profile_metrics(row,grid,by_id[row['source_id']]) for row in rows]
        assert sum(p['reference_classification_unresolved'] for p in profiles)==audit['unresolved_reference_count']
        cells=summarize(profiles); assert len(cells)==24
        with (out/'profile-metrics.jsonl').open('x',encoding='utf-8') as f:
            for profile in profiles: f.write(json.dumps(profile,allow_nan=False)+'\n')
        write(out/'summaries.json',dict(replication='24 cells x64; conditions paired within128 shared blocks; grid pairs not independent',cells=cells))
        csvwrite(out/'summaries.csv',[flatten(cell) for cell in cells])
        write(out/'SUMMARY_AUDIT.json',dict(status='PASS',utc=utc(),profiles=len(profiles),cells=len(cells),grid_points=len(grid),
            grid_pairs_per_profile=len(grid)*(len(grid)-1)//2,original_p_preserved=True,
            decimal_calculation_precision=PRECISION,reference='D80 with frozen tau; independently checked at110',
            classification_unresolved=sum(p['reference_classification_unresolved'] for p in profiles),
            no_filter_or_replacement=True))
        figures(out,profiles,cells); report(raw,out,grid,profiles,cells,audit,complete)
        for name in source: shutil.copy2(raw/'source'/name,out/name)
        shutil.copy2(raw/'AUDIT.json',out/'AUDIT.json')
        write(out/'analysis-provenance.json',dict(utc=utc(),source_sha256=source,profiles_sha256=audit['profiles_sha256'],
            classification_evidence_sha256=audit['classification_evidence_sha256'],visual_review='pending'))
        write(out/'ANALYSIS_RUNTIME.json',dict(utc=utc(),pre_archive_elapsed_seconds=time.perf_counter()-start,
            pre_archive_utc_elapsed_seconds=(datetime.now(timezone.utc)-started).total_seconds(),
            full_runtime_location='ARCHIVE_CHECK.json'))
        manifest={str(p.relative_to(raw)):sha(p) for p in sorted(raw.rglob('*')) if p.is_file()}
        write(out/'raw-manifest.json',manifest); archive=out/'run-records.zip'
        with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
            for path in sorted(raw.rglob('*')):
                if path.is_file(): z.write(path,'raw/'+str(path.relative_to(raw)))
            for path in sorted(out.iterdir()):
                if path.is_file() and path!=archive: z.write(path,'report/'+path.name)
        with zipfile.ZipFile(archive) as z: assert z.testzip() is None
        digest=sha(archive)
        write(out/'ARCHIVE_CHECK.json',dict(status='PASS',crc='PASS',utc=utc(),sha256=digest,bytes=archive.stat().st_size,
            raw_files=len(manifest),analysis_elapsed_seconds=time.perf_counter()-start,
            analysis_utc_elapsed_seconds=(datetime.now(timezone.utc)-started).total_seconds()))
        print(json.dumps(dict(output=str(out),profiles=len(profiles),cells=len(cells),audit='PASS',archive='PASS')),flush=True)
    except BaseException as exc:
        write(out/'ANALYSIS_FAILURE.json',dict(status='FAILED',utc=utc(),error=repr(exc),traceback=traceback.format_exc(),
            instruction='Preserve partial analysis; any scientific repair requires a new version.'))
        raise


if __name__=='__main__': main()
