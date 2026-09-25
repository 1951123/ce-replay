#!/usr/bin/env python3
"""Deterministically build the four frozen PVLDB figures as PDF and SVG."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "results/paper-evaluation-figure-table-data-v0.json").read_text())
ITEM = {x["id"]: x for x in DATA["evaluation_items"]}

BLUE = "#3B6EA8"
ORANGE = "#D88936"
TEAL = "#3A8178"
GRAY = "#666666"
LIGHT_BLUE = "#E6EEF7"
LIGHT_ORANGE = "#F8EAD9"
LIGHT_GRAY = "#F2F2F2"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Linux Libertine O", "Linux Libertine", "Libertine", "DejaVu Serif"],
    "font.size": 7.0,
    "axes.titlesize": 8.0,
    "axes.labelsize": 7.0,
    "xtick.labelsize": 6.4,
    "ytick.labelsize": 6.4,
    "legend.fontsize": 6.4,
    "pdf.fonttype": 42,
    "svg.fonttype": "none",
    "svg.hashsalt": "ce-replay-final-figures-v0",
    "axes.linewidth": 0.6,
})


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.pdf", format="pdf",
                metadata={"Creator": "build_figures.py", "CreationDate": None, "ModDate": None})
    svg_path = OUT / f"{stem}.svg"
    fig.savefig(svg_path, format="svg",
                metadata={"Creator": "build_figures.py", "Date": None})
    # Matplotlib emits trailing spaces in multiline SVG path data. Normalize
    # them so regenerated manuscript assets pass repository whitespace checks.
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text().splitlines()) + "\n")
    plt.close(fig)


def box(ax, xy, wh, text, *, fc=LIGHT_GRAY, ec=GRAY, lw=0.8, fontsize=6.6,
        weight="normal", dashed=False, zorder=2):
    x, y = xy; w, h = wh
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.008,rounding_size=0.012",
                       facecolor=fc, edgecolor=ec, linewidth=lw,
                       linestyle="--" if dashed else "-", zorder=zorder)
    ax.add_patch(p)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fontsize,
            weight=weight, color="#202020", zorder=zorder + 1, linespacing=1.12)
    return p


def arrow(ax, a, b, *, color=GRAY, lw=0.9, style="-", rad=0.0, label=None,
          label_xy=None, mutation=8, zorder=3):
    p = FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=mutation,
                        linewidth=lw, linestyle=style, color=color,
                        connectionstyle=f"arc3,rad={rad}", zorder=zorder)
    ax.add_patch(p)
    if label:
        x, y = label_xy if label_xy else ((a[0]+b[0])/2, (a[1]+b[1])/2)
        ax.text(x, y, label, ha="center", va="center", fontsize=5.8,
                color=color, bbox=dict(facecolor="white", edgecolor="none", pad=0.5), zorder=5)


def build_f1():
    fig, ax = plt.subplots(figsize=(6.6, 2.20))
    fig.subplots_adjust(0, 0, 1, 1); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.add_patch(Rectangle((.012, .51), .976, .47, fill=False, ec="#777", lw=.7))
    ax.add_patch(Rectangle((.012, .02), .976, .43, fill=False, ec="#777", lw=.7))
    ax.text(.025, .955, "FROZEN HYPOTHETICAL-DESIGN LOOP", fontsize=7.2, weight="bold", va="top")
    ax.text(.025, .425, "FRESH DEPLOYMENT & SAME-REALIZATION VALIDATION", fontsize=7.2, weight="bold", va="top")

    box(ax, (.035,.73), (.19,.14), "Fixed workload / CE context\nCandidate definitions + budget", fc=LIGHT_GRAY, fontsize=6.2)
    box(ax, (.035,.54), (.19,.14), "Frozen candidate payloads\n(acquired offline)", fc=LIGHT_BLUE, ec=BLUE, fontsize=6.2)
    box(ax, (.405,.57), (.255,.32), "CE-REPLAY\nSupported PostgreSQL 16.14\nbase-restriction fragment\n\nMCV select → consume → update\nresidual state → FD compose", fc="#EDF3FA", ec=BLUE, lw=1.4, fontsize=6.45, weight="bold")
    box(ax, (.695,.72), (.125,.13), "Objective\nestimates → loss", fc="#E4F1EF", ec=TEAL, fontsize=6.2)
    box(ax, (.695,.55), (.125,.13), "Semantic\ndependencies", fc="#E4F1EF", ec=TEAL, fontsize=6.2)
    box(ax, (.855,.61), (.115,.23), "Maintenance-\nfeasible search\nADD / DROP / SWAP\n(local)", fc=LIGHT_ORANGE, ec=ORANGE, fontsize=6.1)
    arrow(ax,(.225,.80),(.405,.78)); arrow(ax,(.225,.61),(.405,.67))
    arrow(ax,(.66,.79),(.695,.79),color=TEAL); arrow(ax,(.66,.62),(.695,.62),color=TEAL,style="--")
    arrow(ax,(.82,.785),(.855,.785),color=TEAL,label="move objective",label_xy=(.837,.825))
    arrow(ax,(.82,.615),(.855,.665),color=TEAL,style="--",label="invalidation",label_xy=(.84,.59))
    arrow(ax,(.91,.84),(.61,.89),color=ORANGE,rad=.15,label="hypothetical design",label_xy=(.77,.945))

    box(ax, (.055,.12), (.15,.18), "Selected design\n+ recorded order", fc=LIGHT_ORANGE, ec=ORANGE)
    box(ax, (.245,.10), (.16,.22), "Physical deployment\nCREATE statistics\n+ fresh ANALYZE", fc=LIGHT_ORANGE, ec=ORANGE)
    box(ax, (.445,.12), (.13,.18), "Fresh payload\nvalues & availability", fc="#FFF3E5", ec=ORANGE)
    box(ax, (.615,.23), (.13,.13), "CE-Replay\n(fresh payload)", fc=LIGHT_BLUE, ec=BLUE)
    box(ax, (.615,.06), (.13,.13), "Native PostgreSQL\nCE", fc=LIGHT_GRAY, ec=GRAY)
    box(ax, (.79,.11), (.17,.20), "Compare estimates\nsemantic replay error\n≠\nfrozen/fresh drift", fc="#E4F1EF", ec=TEAL, fontsize=6.1)
    ax.plot([.91,.91,.13],[.61,.48,.48],color=ORANGE,lw=1.5,clip_on=False)
    arrow(ax,(.13,.48),(.13,.30),color=ORANGE,lw=1.5,label="selected state",label_xy=(.20,.48)); arrow(ax,(.205,.21),(.245,.21),color=ORANGE,lw=1.5)
    arrow(ax,(.405,.21),(.445,.21),color=ORANGE,lw=1.5); arrow(ax,(.575,.22),(.615,.29),color=GRAY)
    arrow(ax,(.575,.20),(.615,.125),color=GRAY); arrow(ax,(.745,.295),(.79,.245),color=TEAL)
    arrow(ax,(.745,.125),(.79,.175),color=TEAL)
    arrow(ax,(.292,.61),(.325,.32),color=BLUE,style="--",rad=.13,
          label="definitions selected;\npayload equality not assumed",label_xy=(.405,.47))
    ax.text(.495,.535,"design-parametric executable semantics",ha="center",fontsize=6.0,color=BLUE)
    save(fig, "f1-ce-replay-architecture")


def build_f2():
    d = ITEM["F2"]["panels"]
    fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.05))
    fig.subplots_adjust(left=.08,right=.985,bottom=.24,top=.83,wspace=.34)
    specs = [
        (axes[0], "Census · frozen realization", ["Empty","All statistics","Optimized\nsubset"],
         [d["Census_nonmonotonicity_realization"][k] for k in ("empty","all_statistics","optimized_subset")],
         "1,560 / 3,011 harmful additions\n317 improving removals from all"),
        (axes[1], "DMV · frozen baseline realization", ["Empty","All MCV","All FD","All statistics"],
         [d["DMV_baseline_realization"][k] for k in ("empty","all_mcv","all_fd","all_statistics")],
         "30 beneficial / 41 harmful additions\n20 improving removals from all"),
    ]
    for ax,title,labels,vals,note in specs:
        colors=[LIGHT_GRAY, LIGHT_BLUE, LIGHT_ORANGE, "#D8D8D8"][:len(vals)]
        hatches=["", "///", "\\\\", "xx"][:len(vals)]
        bars=ax.bar(range(len(vals)),vals,color=colors,edgecolor=[GRAY,BLUE,ORANGE,GRAY][:len(vals)],linewidth=.8)
        for b,h,v in zip(bars,hatches,vals):
            b.set_hatch(h); ax.text(b.get_x()+b.get_width()/2,v,f"{v:,.0f}",ha="center",va="bottom",fontsize=6.2)
        ax.set_xticks(range(len(vals)),labels); ax.set_title(title,weight="bold",pad=4)
        ax.set_ylabel("Aggregate q-error loss\n(independent scale)")
        ax.set_ylim(0,max(vals)*1.45); ax.grid(axis="y",color="#dddddd",lw=.45); ax.set_axisbelow(True)
        ax.text(.02,.97,note,transform=ax.transAxes,ha="left",va="top",fontsize=6.2,
                bbox=dict(facecolor="white",edgecolor="#aaaaaa",boxstyle="round,pad=.2"))
        ax.spines[["top","right"]].set_visible(False)
    fig.text(.5,.97,"More statistics need not improve the supported CE objective",ha="center",va="top",fontsize=8.2,weight="bold")
    fig.text(.5,.035,"Panels are not cross-workload loss comparisons; “optimized subset” is not a global-optimum claim.",ha="center",fontsize=6.1,color=GRAY)
    save(fig,"f2-cross-workload-nonmonotonicity")


def read_means(path, count_mcv, count_fd, family=None):
    groups=defaultdict(list)
    with path.open() as f:
        for r in csv.DictReader(f):
            if r.get("phase") not in (None,"", "measured"): continue
            key=(int(r[count_mcv]),int(r[count_fd]),r.get(family,"") if family else "")
            groups[key].append(float(r["seconds"])*1000)
    return [(m,f,fam,sum(v)/len(v)) for (m,f,fam),v in groups.items()]


def build_f3():
    meta=ITEM["F3"]["panels"]
    census=read_means(ROOT/"results/census_analyze_cost_model_v0.csv","n_mcv","n_fd","kind")
    fig,ax=plt.subplots(1,1,figsize=(6.6,2.05)); fig.subplots_adjust(left=.09,right=.985,bottom=.22,top=.80)
    for ax,title,rows,base,slopes,note in [
        (ax,"Census environment",census,meta["Census"]["empty_mean_seconds"]*1000,
         (meta["Census"]["mcv_only_slope_ms"],meta["Census"]["fd_only_slope_ms"]),
         "normalized recurring cost: 1 MCV + 1.449 FD   ·   MCV $R^2$=.995   ·   FD $R^2$=.996")]:
        for mech,color,marker,hatch,slope in [("MCV",BLUE,"o","///",slopes[0]),("FD",ORANGE,"s","\\\\",slopes[1])]:
            pts=[]
            for m,f,fam,y in rows:
                pure=(f==0 and m>0) if mech=="MCV" else (m==0 and f>0)
                if pure: pts.append((m if mech=="MCV" else f,y))
            if pts:
                pts=sorted(pts); xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
                ax.scatter(xs,ys,s=18,marker=marker,facecolor="white",edgecolor=color,linewidth=.8,label=f"{mech} measured")
                xx=[0,max(xs)]; ax.plot(xx,[base+slope*x for x in xx],color=color,lw=1.0,ls="-" if mech=="MCV" else "--",label=f"{mech} fit: {slope:.3f} ms/object")
        ax.set_title(title,weight="bold"); ax.set_xlabel("Deployed objects (pure-mechanism configurations)"); ax.set_ylabel("Mean ANALYZE latency (ms)")
        ax.grid(color="#dddddd",lw=.45); ax.set_axisbelow(True); ax.spines[["top","right"]].set_visible(False)
        ax.legend(frameon=False,loc="upper left",ncol=1,handlelength=2.0)
        ax.text(.98,.04,note,transform=ax.transAxes,ha="right",va="bottom",fontsize=6.1,color=GRAY)
    fig.text(.5,.96,"Census first-order recurring maintenance proxy",ha="center",va="top",fontsize=8.2,weight="bold")
    fig.text(.5,.035,"Aggregate environment-specific fit used by the final Census budget; not a universal constant or per-candidate predictor.",ha="center",fontsize=6.1,color=GRAY)
    save(fig,"f3-analyze-maintenance-cost")


def build_f4():
    d=ITEM["F4"]["data"]
    fig=plt.figure(figsize=(6.6,2.15)); gs=fig.add_gridspec(2,2,height_ratios=[.72,1.35],left=.075,right=.985,bottom=.19,top=.91,hspace=.48,wspace=.30)
    flow=fig.add_subplot(gs[0,:]); flow.axis("off"); flow.set_xlim(0,1); flow.set_ylim(0,1)
    box(flow,(.08,.22),(.20,.56),"MCV selection\n+ clause consumption",fc=LIGHT_BLUE,ec=BLUE,fontsize=6.8,weight="bold")
    box(flow,(.40,.22),(.20,.56),"Residual clause /\nsemantic-dimension state",fc=LIGHT_GRAY,ec=GRAY,fontsize=6.8)
    box(flow,(.72,.22),(.20,.56),"FD applicability\n+ selectivity adjustment",fc=LIGHT_ORANGE,ec=ORANGE,fontsize=6.8,weight="bold")
    arrow(flow,(.28,.5),(.40,.5),color=BLUE,lw=1.2,label="consumed clauses",label_xy=(.34,.72))
    arrow(flow,(.60,.5),(.72,.5),color=ORANGE,lw=1.2,label="reachable or suppressed",label_xy=(.66,.72))
    flow.text(.5,.98,"MCV executes before FD",ha="center",va="top",fontsize=8.0,weight="bold")
    axes=[fig.add_subplot(gs[1,0]),fig.add_subplot(gs[1,1])]
    panels=[
        (axes[0],"Census",["Independent","Mixed, fixed order"],[97,54],[25,54]),
        (axes[1],"DMV",["All statistics"],[35],[0])]
    for ax,title,labels,selected,consumed in panels:
        suppressed=[s-c for s,c in zip(selected,consumed)]; x=range(len(labels))
        ax.bar(x,consumed,color=LIGHT_BLUE,edgecolor=BLUE,hatch="///",linewidth=.8,label="Consumed FD")
        ax.bar(x,suppressed,bottom=consumed,color=LIGHT_ORANGE,edgecolor=ORANGE,hatch="\\\\",linewidth=.8,label="Suppressed / unused FD")
        for i,(s,c,u) in enumerate(zip(selected,consumed,suppressed)):
            ax.text(i,s+max(selected)*.035,f"{c}/{s} consumed",ha="center",va="bottom",fontsize=6.2)
        ax.set_xticks(list(x),labels); ax.set_ylabel("Selected or usable FD objects"); ax.set_ylim(0,max(selected)*1.25)
        ax.set_title(title,weight="bold",pad=2); ax.grid(axis="y",color="#ddd",lw=.45); ax.set_axisbelow(True); ax.spines[["top","right"]].set_visible(False)
    axes[0].legend(frameon=False,loc="upper right",ncol=2,bbox_to_anchor=(2.05,-.31),handlelength=1.6)
    axes[1].text(.5,-.20,"Corrected physical validation: 12 MCV + 4 FD, all materialized\n(not a maintenance optimum)",
                 transform=axes[1].transAxes,ha="center",va="top",fontsize=6.0,color=GRAY)
    save(fig,"f4-mcv-fd-composition")


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    build_f1(); build_f2(); build_f3(); build_f4()
    print("built F1-F4 PDF/SVG from frozen repository artifacts")


if __name__ == "__main__":
    main()
