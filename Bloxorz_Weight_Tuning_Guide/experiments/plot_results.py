#!/usr/bin/env python3
"""Standalone Plotting Script for Bloxorz Weight Tuning & Benchmark Results.

This script reads existing CSV and JSON output files generated in `experiments/results/`
and renders publication-quality figures without re-running any search, grid sweep,
or cross-validation.

Usage:
    python experiments/plot_results.py
    python experiments/plot_results.py --results-dir experiments/results --out-dir experiments/results
"""

import argparse
import csv
import json
import os
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

# Ensure Matplotlib cache goes to a writable temp directory
os.environ['MPLCONFIGDIR'] = tempfile.gettempdir()

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    plt = None


def read_csv_sig(filepath: Path) -> list:
    if not filepath.exists():
        return []
    with open(filepath, mode='r', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def read_json(filepath: Path) -> dict:
    if not filepath.exists():
        return {}
    with open(filepath, mode='r', encoding='utf-8') as f:
        return json.load(f)


def plot_ucs_cv_comparison(results_dir: Path, out_dir: Path):
    cv_file = results_dir / 'ucs_grouped_cv.csv'
    rows = read_csv_sig(cv_file)
    if not rows:
        print(f"[Skip] {cv_file.name} not found or empty.")
        return

    fig, ax = plt.subplots(figsize=(8.5, 5.2), dpi=200)
    folds = [int(r['fold']) for r in rows]
    tuned_loss = [float(r['heldout_quality_loss']) for r in rows]
    rubric_loss = [float(r.get('baseline_rubric_heldout_loss', r.get('baseline_heldout_quality_loss', 0.0))) for r in rows]
    
    ax.plot(folds, tuned_loss, marker='o', linewidth=2.4, color='#1f77b4', label='Tuned UCS Weights (Selected)')
    ax.plot(folds, rubric_loss, marker='s', linewidth=2.0, linestyle='--', color='#ff7f0e', label='Baseline 1: Team Rubric (3, 2, 4, 2.5, 3)')
    
    if 'baseline_const1_heldout_loss' in rows[0]:
        const1_loss = [float(r['baseline_const1_heldout_loss']) for r in rows]
        ax.plot(folds, const1_loss, marker='^', linewidth=1.8, linestyle=':', color='#d62728', label='Baseline 2: Const=1 (c = const = 1.0)')
    
    if 'baseline_equal1_heldout_loss' in rows[0]:
        equal1_loss = [float(r['baseline_equal1_heldout_loss']) for r in rows]
        ax.plot(folds, equal1_loss, marker='d', linewidth=1.8, linestyle='-.', color='#2ca02c', label='Baseline 3: Equal=1 (All w = 1.0)')

    ax.set_xlabel('Grouped 6-Fold Cross-Validation Fold', fontsize=11, fontweight='bold', labelpad=8)
    ax.set_ylabel('Mean Rank-Based Quality Loss (lower is better)', fontsize=11, fontweight='bold', labelpad=8)
    ax.set_title('UCS Tuning: Held-out Loss across 6 Folds vs 3 Baselines', fontsize=13, fontweight='bold', pad=12)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xticks(folds)
    ax.legend(frameon=True, facecolor='white', framealpha=0.9, fontsize=9.5, loc='upper right')
    fig.tight_layout()
    
    out_path = out_dir / 'ucs_cv_comparison.png'
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path.name}")


def plot_ucs_top15_configs(results_dir: Path, out_dir: Path):
    top_file = results_dir / 'ucs_top_configs.csv'
    grid_file = results_dir / 'ucs_grid_results.csv'
    
    rows = read_csv_sig(top_file)
    if not rows and grid_file.exists():
        grid_rows = read_csv_sig(grid_file)
        agg = defaultdict(list)
        for r in grid_rows:
            agg[int(r['config_id'])].append(float(r['quality_loss']))
        top_ids = sorted(agg, key=lambda cid: sum(agg[cid]) / len(agg[cid]))[:15]
        rows = [{'config_id': str(cid), 'mean_quality_loss': str(sum(agg[cid]) / len(agg[cid]))} for cid in top_ids]

    if not rows:
        print(f"[Skip] {top_file.name} not found or empty.")
        return

    top15 = rows[:15]
    cids = [f"Cfg #{r['config_id']}" for r in top15]
    losses = [float(r['mean_quality_loss']) for r in top15]
    colors = ['#1f77b4'] * len(top15)

    # Highlight baseline configs if tagged
    for i, r in enumerate(top15):
        if str(r.get('is_baseline_rubric', '')).lower() in ('true', '1') or str(r.get('is_original_baseline', '')).lower() in ('true', '1'):
            colors[i] = '#ff7f0e'
            cids[i] += '\n(Rubric)'
        elif str(r.get('is_baseline_const1', '')).lower() in ('true', '1'):
            colors[i] = '#d62728'
            cids[i] += '\n(Const=1)'
        elif str(r.get('is_baseline_equal1', '')).lower() in ('true', '1'):
            colors[i] = '#2ca02c'
            cids[i] += '\n(Equal=1)'

    fig, ax = plt.subplots(figsize=(10.5, 5.2), dpi=200)
    bars = ax.bar(cids, losses, color=colors, width=0.65, edgecolor='black', linewidth=0.6)
    
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.4f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8, fontweight='bold')

    ax.set_xlabel('UCS Configuration ID', fontsize=11, fontweight='bold', labelpad=8)
    ax.set_ylabel('Mean Rank-Based Quality Loss (lower is better)', fontsize=11, fontweight='bold', labelpad=8)
    ax.set_title('Top 15 UCS Configurations across all 18 Levels', fontsize=13, fontweight='bold', pad=12)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.set_ylim(0, max(losses) * 1.18)
    fig.tight_layout()

    out_path = out_dir / 'ucs_top15_configs.png'
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path.name}")


def plot_astar_alpha_tradeoff(results_dir: Path, out_dir: Path):
    summary_file = results_dir / 'astar_alpha_summary.csv'
    rows = read_csv_sig(summary_file)
    if not rows:
        print(f"[Skip] {summary_file.name} not found or empty.")
        return

    alphas = [float(r['alpha']) for r in rows]
    mean_nodes = [float(r['mean_expanded_nodes']) for r in rows]
    search_ms = [float(r['mean_cached_graph_search_ms']) for r in rows]

    fig, ax1 = plt.subplots(figsize=(8.5, 5.0), dpi=200)
    color_node = '#1f77b4'
    ax1.plot(alphas, mean_nodes, marker='o', linewidth=2.5, color=color_node, markersize=8, label='Mean Expanded Nodes')
    ax1.set_xlabel(r'Heuristic Scale Factor $\alpha$', fontsize=11, fontweight='bold', labelpad=8)
    ax1.set_ylabel('Mean Expanded Nodes (18 Levels)', fontsize=11, fontweight='bold', color=color_node, labelpad=8)
    ax1.tick_params(axis='y', labelcolor=color_node)
    ax1.grid(True, linestyle='--', alpha=0.5)

    for a, n in zip(alphas, mean_nodes):
        ax1.annotate(f'{n:.1f}', xy=(a, n), xytext=(0, 6), textcoords="offset points",
                     ha='center', fontsize=9, fontweight='bold', color=color_node)

    # Secondary axis for search time
    ax2 = ax1.twinx()
    color_time = '#d62728'
    ax2.plot(alphas, search_ms, marker='^', linewidth=2.0, linestyle='--', color=color_time, markersize=7, label='Search Time (ms)')
    ax2.set_ylabel('Mean Search Time (ms)', fontsize=11, fontweight='bold', color=color_time, labelpad=8)
    ax2.tick_params(axis='y', labelcolor=color_time)

    plt.title(r'A* Heuristic Scaling ($\alpha$) vs Search Cost (Actual Split-State Heuristic)', fontsize=12, fontweight='bold', pad=12)
    fig.tight_layout()

    out_path = out_dir / 'astar_alpha_expanded_nodes.png'
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path.name}")


def plot_gbfs_cv_comparison(results_dir: Path, out_dir: Path):
    cv_file = results_dir / 'gbfs_grouped_cv.csv'
    rows = read_csv_sig(cv_file)
    if not rows:
        print(f"[Skip] {cv_file.name} not found or empty.")
        return

    folds = [int(r['fold']) for r in rows]
    tuned = [float(r['heldout_quality_loss']) for r in rows]
    base = [float(r['baseline_heldout_quality_loss']) for r in rows]

    fig, ax = plt.subplots(figsize=(8.5, 5.0), dpi=200)
    ax.plot(folds, tuned, marker='o', linewidth=2.4, color='#2ca02c', label='Tuned GBFS Heuristic')
    ax.plot(folds, base, marker='s', linewidth=2.0, linestyle='--', color='#7f7f7f', label='Baseline GBFS (1, 1, 0, 0)')

    ax.set_xlabel('Grouped CV Fold', fontsize=11, fontweight='bold', labelpad=8)
    ax.set_ylabel('Mean Rank-Based Quality Loss (lower is better)', fontsize=11, fontweight='bold', labelpad=8)
    ax.set_title('GBFS Heuristic Tuning: Held-Out Performance per Fold', fontsize=13, fontweight='bold', pad=12)
    ax.grid(True, linestyle='--', alpha=0.5)
    ax.set_xticks(folds)
    ax.legend(frameon=True, facecolor='white', framealpha=0.9, fontsize=10)
    fig.tight_layout()

    out_path = out_dir / 'gbfs_cv_comparison.png'
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path.name}")


def plot_baselines_vs_tuned_summary(results_dir: Path, out_dir: Path):
    summary_file = results_dir / 'ucs_tuning_summary.json'
    d = read_json(summary_file)
    if not d or 'baseline_configurations' not in d:
        print(f"[Skip] {summary_file.name} missing baseline_configurations.")
        return

    b_meta = d['baseline_configurations']
    labels = [
        'Baseline Const=1\n(c=1.0, w=0)',
        'Baseline Equal=1\n(All w=1.0)',
        'Baseline Rubric\n(3, 2, 4, 2.5, 3)',
        'UCS Tuned\n(Selected)'
    ]
    mean_losses = [
        b_meta['baseline_const_1']['mean_quality_loss'],
        b_meta['baseline_equal_1']['mean_quality_loss'],
        b_meta['baseline_rubric']['mean_quality_loss'],
        d['chosen_weights'] and d['baseline_mean_rank_loss'],  # Matches chosen rubric
    ]
    heldout_losses = [
        b_meta['baseline_const_1']['mean_cv_heldout_loss'],
        b_meta['baseline_equal_1']['mean_cv_heldout_loss'],
        b_meta['baseline_rubric']['mean_cv_heldout_loss'],
        d['baseline_mean_rank_loss'],
    ]

    fig, ax = plt.subplots(figsize=(9.2, 5.2), dpi=200)
    x = list(range(len(labels)))
    width = 0.35

    bars1 = ax.bar([i - width/2 for i in x], mean_losses, width, label='Full Data Quality Loss', color='#4a7bb0', edgecolor='black', linewidth=0.5)
    bars2 = ax.bar([i + width/2 for i in x], heldout_losses, width, label='Mean 6-Fold Held-out Loss', color='#e88848', edgecolor='black', linewidth=0.5)

    for bar in list(bars1) + list(bars2):
        height = bar.get_height()
        ax.annotate(f'{height:.4f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.5, fontweight='bold')

    ax.set_ylabel('Quality Loss (lower is better)', fontsize=11, fontweight='bold', labelpad=8)
    ax.set_title('Comparative Analysis: 3 Baselines vs Tuned Cost Model', fontsize=13, fontweight='bold', pad=12)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5, fontweight='bold')
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.set_ylim(0, max(mean_losses + heldout_losses) * 1.18)
    ax.legend(frameon=True, facecolor='white', framealpha=0.9, fontsize=10)
    fig.tight_layout()

    out_path = out_dir / 'baselines_vs_tuned_comparison.png'
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path.name}")


def plot_benchmark_algorithms_comparison(results_dir: Path, out_dir: Path):
    summary_file = results_dir / 'final_selected_weights_summary.csv'
    rows = read_csv_sig(summary_file)
    if not rows:
        print(f"[Skip] {summary_file.name} not found or empty.")
        return

    # Aggregate by algorithm
    algo_data = defaultdict(lambda: {'nodes': [], 'times': [], 'rolls': []})
    for r in rows:
        a = r['algorithm']
        if r['mean_expanded_nodes']:
            algo_data[a]['nodes'].append(float(r['mean_expanded_nodes']))
        if r['median_search_time_ms']:
            algo_data[a]['times'].append(float(r['median_search_time_ms']))
        if r['median_solution_length_rolls']:
            algo_data[a]['rolls'].append(float(r['median_solution_length_rolls']))

    preferred_order = [
        ('UCS_Baseline_Const1', 'UCS Const=1'),
        ('UCS_Baseline_Equal1', 'UCS Equal=1'),
        ('UCS_Baseline_Rubric', 'UCS Rubric'),
        ('UCS_Tuned', 'UCS Tuned'),
        ('AStar_Tuned', 'A* Tuned'),
        ('GBFS_Tuned', 'GBFS Tuned'),
    ]
    algos = [k for k, _ in preferred_order if k in algo_data]
    display_names = [v for k, v in preferred_order if k in algo_data]

    mean_nodes = [sum(algo_data[k]['nodes']) / len(algo_data[k]['nodes']) for k in algos]
    median_times = [sum(algo_data[k]['times']) / len(algo_data[k]['times']) for k in algos]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.0), dpi=200)

    # Plot 1: Expanded Nodes
    bars1 = ax1.bar(display_names, mean_nodes, color=['#7f7f7f', '#2ca02c', '#ff7f0e', '#1f77b4', '#9467bd', '#8c564b'], edgecolor='black', linewidth=0.6)
    for bar in bars1:
        h = bar.get_height()
        ax1.annotate(f'{h:.1f}', xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
    ax1.set_ylabel('Mean Expanded Nodes across 18 Levels', fontsize=10.5, fontweight='bold')
    ax1.set_title('Search Efficiency: Expanded Nodes (18 Levels)', fontsize=12, fontweight='bold')
    ax1.grid(axis='y', linestyle='--', alpha=0.5)
    ax1.tick_params(axis='x', rotation=25)
    ax1.set_ylim(0, max(mean_nodes) * 1.15)

    # Plot 2: Search Time
    bars2 = ax2.bar(display_names, median_times, color=['#7f7f7f', '#2ca02c', '#ff7f0e', '#1f77b4', '#9467bd', '#8c564b'], edgecolor='black', linewidth=0.6)
    for bar in bars2:
        h = bar.get_height()
        ax2.annotate(f'{h:.2f}ms', xy=(bar.get_x() + bar.get_width() / 2, h),
                     xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=8.5, fontweight='bold')
    ax2.set_ylabel('Mean Search Time per Level (ms)', fontsize=10.5, fontweight='bold')
    ax2.set_title('Runtime Comparison (Direct Repeated Harness)', fontsize=12, fontweight='bold')
    ax2.grid(axis='y', linestyle='--', alpha=0.5)
    ax2.tick_params(axis='x', rotation=25)
    ax2.set_ylim(0, max(median_times) * 1.15)

    fig.suptitle('Bloxorz Benchmark: Baselines vs Tuned Solvers (Repeated x3 on 18 Levels)', fontsize=13, fontweight='bold', y=1.02)
    fig.tight_layout()

    out_path = out_dir / 'benchmark_algorithms_comparison.png'
    fig.savefig(out_path, bbox_inches='tight')
    plt.close(fig)
    print(f"Generated: {out_path.name}")


def plot_astar_heuristic_verification(results_dir: Path, out_dir: Path):
    checks_file = results_dir / 'astar_heuristic_checks.csv'
    rows = read_csv_sig(checks_file)
    if not rows:
        print(f"[Skip] {checks_file.name} not found or empty.")
        return

    levels = [r['level_id'].replace('level_', 'L') for r in rows]
    total_nodes = [int(r['nodes']) for r in rows]
    split_nodes = [int(r['split_nodes']) for r in rows]
    adm_viols = [int(r['admissibility_violations']) for r in rows]
    cons_viols = [int(r['base_cost_consistency_violations']) for r in rows]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7.5), dpi=200, sharex=True)

    # Subplot 1: Total vs Split Nodes
    x = range(len(levels))
    ax1.bar(x, total_nodes, label='Total Reachable States', color='#aec7e8', edgecolor='black', linewidth=0.5)
    ax1.bar(x, split_nodes, label='Split States (2x 1x1x1 cubes)', color='#1f77b4', edgecolor='black', linewidth=0.5)
    ax1.set_ylabel('Augmented State Count', fontsize=10.5, fontweight='bold')
    ax1.set_title('Reachability & Split-Mechanic Distribution across 18 Levels', fontsize=12, fontweight='bold')
    ax1.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.9)
    ax1.grid(axis='y', linestyle='--', alpha=0.5)

    # Subplot 2: Violations
    w = 0.35
    ax2.bar([i - w/2 for i in x], adm_viols, width=w, label='Admissibility Violations', color='#d62728', edgecolor='black', linewidth=0.5)
    ax2.bar([i + w/2 for i in x], cons_viols, width=w, label='Consistency Violations', color='#ff7f0e', edgecolor='black', linewidth=0.5)
    ax2.set_ylabel('Violation Count', fontsize=10.5, fontweight='bold')
    ax2.set_xlabel('Level ID', fontsize=11, fontweight='bold', labelpad=8)
    ax2.set_title('Admissibility & Consistency Check of Actual Codebase Heuristic', fontsize=12, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(levels, rotation=45, fontsize=9, fontweight='bold')
    ax2.legend(loc='upper left', frameon=True, facecolor='white', framealpha=0.9)
    ax2.grid(axis='y', linestyle='--', alpha=0.5)

    fig.tight_layout()
    out_path = out_dir / 'astar_heuristic_verification.png'
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Generated: {out_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Plot Bloxorz Tuning & Benchmark Results from saved files.")
    default_dir = Path(__file__).resolve().parent / 'results'
    parser.add_argument('--results-dir', type=Path, default=default_dir, help="Directory containing CSV/JSON outputs.")
    parser.add_argument('--out-dir', type=Path, default=default_dir, help="Directory to save generated PNG plots.")
    args = parser.parse_args()

    if not HAS_MATPLOTLIB:
        print("[Error] matplotlib is required for plotting, but is not installed in current Python environment.")
        print("Please install matplotlib via: pip install matplotlib")
        sys.exit(1)

    results_dir = args.results_dir.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading experiment data from: {results_dir}")
    print(f"Saving figures to:           {out_dir}")
    print("-" * 60)

    plot_ucs_cv_comparison(results_dir, out_dir)
    plot_ucs_top15_configs(results_dir, out_dir)
    plot_astar_alpha_tradeoff(results_dir, out_dir)
    plot_gbfs_cv_comparison(results_dir, out_dir)
    plot_baselines_vs_tuned_summary(results_dir, out_dir)
    plot_benchmark_algorithms_comparison(results_dir, out_dir)
    plot_astar_heuristic_verification(results_dir, out_dir)

    print("-" * 60)
    print("All figures generated successfully!")


if __name__ == '__main__':
    main()
