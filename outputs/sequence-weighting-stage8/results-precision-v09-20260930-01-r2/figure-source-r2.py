from analyze_stage8 import *

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
        magnitudes=[10.**e for e in range(-12,31,6) if 10.**e<=high]
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
                if not g['both_defined']: ax.text(i,.5,'unavailable',rotation=90,ha='center',va='center',fontsize=8,transform=ax.get_xaxis_transform())
        rate_values=[g['methods'][name]['pairwise'][metric] for g in cellgroups for name in METHODS
                     for metric in ['float_tie_rate_on_reference_strict','strict_reversal_rate']
                     if g['methods'][name]['pairwise'][metric] is not None]
        maximum=max(rate_values,default=0.)
        if maximum>0:
            axes[r,1].set_ylim(-.03*maximum,1.15*maximum)
            axes[r,1].ticklabel_format(axis='y',style='sci',scilimits=(-3,3))
        axes[r,1].set_ylabel('Fraction of reference-strict pairs')
        low_rate,high_rate=axes[r,1].get_ylim()
        assert all(low_rate<v<high_rate for v in rate_values)
        limits[f'pair_rates_{n}_{p}']=dict(minimum=low_rate,maximum=high_rate,
            points=len(rate_values),all_points_inside=True)
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
