from __future__ import annotations

from pathlib import Path
import sys
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
for path in (ROOT, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from benchmark import _run_suite, load_conversations
from config import load_config


def load_rows():
    config = load_config(Path(__file__).resolve().parent.parent)
    standard = _run_suite(config, load_conversations(config.data_dir / 'conversations.json'), 'standard')
    stress = _run_suite(config, load_conversations(config.data_dir / 'advanced_long_context.json'), 'stress')
    return standard, stress


def add_metric(parent, label, value, row, col):
    box = ttk.Frame(parent, style='Metric.TFrame', padding=12)
    box.grid(row=row, column=col, sticky='nsew', padx=6, pady=6)
    ttk.Label(box, text=label, style='MetricLabel.TLabel').pack(anchor='w')
    ttk.Label(box, text=str(value), style='MetricValue.TLabel').pack(anchor='w', pady=(4, 0))


def add_table(parent, rows):
    cols = ('Agent', 'Tokens', 'Prompt', 'Recall', 'Quality', 'Growth', 'Compactions')
    tree = ttk.Treeview(parent, columns=cols, show='headings', height=3)
    for col in cols:
        tree.heading(col, text=col)
        tree.column(col, anchor='center', width=110)
    for row in rows:
        tree.insert('', 'end', values=(row.agent_name, row.agent_tokens_only, row.prompt_tokens_processed, f'{row.recall_score:.2f}', f'{row.response_quality:.2f}', row.memory_growth_bytes, row.compactions))
    tree.pack(fill='x', expand=True)
    return tree


def build_app():
    standard_rows, stress_rows = load_rows()
    root = tk.Tk()
    root.title('Day 17 Memory Lab Dashboard')
    root.geometry('1180x860')
    root.configure(bg='#0f172a')

    style = ttk.Style(root)
    style.theme_use('clam')
    style.configure('TFrame', background='#0f172a')
    style.configure('Panel.TFrame', background='#111827', relief='flat')
    style.configure('Metric.TFrame', background='#1f2937', relief='flat')
    style.configure('Header.TLabel', background='#0f172a', foreground='#e5e7eb', font=('Segoe UI', 24, 'bold'))
    style.configure('Sub.TLabel', background='#0f172a', foreground='#94a3b8', font=('Segoe UI', 10))
    style.configure('Section.TLabel', background='#0f172a', foreground='#e5e7eb', font=('Segoe UI', 15, 'bold'))
    style.configure('MetricLabel.TLabel', background='#1f2937', foreground='#94a3b8', font=('Segoe UI', 9))
    style.configure('MetricValue.TLabel', background='#1f2937', foreground='#e5e7eb', font=('Segoe UI', 18, 'bold'))
    style.configure('TNotebook', background='#0f172a', borderwidth=0)
    style.configure('TNotebook.Tab', padding=(16, 8), background='#1f2937', foreground='#e5e7eb')
    style.map('TNotebook.Tab', background=[('selected', '#334155')])
    style.configure('Treeview', background='#111827', fieldbackground='#111827', foreground='#e5e7eb', rowheight=28, bordercolor='#334155', borderwidth=0)
    style.configure('Treeview.Heading', background='#1f2937', foreground='#e5e7eb', font=('Segoe UI', 10, 'bold'))

    top = ttk.Frame(root, padding=24, style='TFrame')
    top.pack(fill='x')
    ttk.Label(top, text='Day 17 Memory Lab Dashboard', style='Header.TLabel').pack(anchor='w')
    ttk.Label(top, text='Baseline = thread-only memory. Advanced = User.md + compact memory. Open this app to compare the results visually.', style='Sub.TLabel').pack(anchor='w', pady=(6, 0))

    chips = ttk.Frame(top, style='TFrame')
    chips.pack(anchor='w', pady=(14, 0))
    for text in ['Offline-ready', 'API-compatible', 'Recall vs token cost', 'Compaction']:
        lbl = tk.Label(chips, text=text, bg='#1f2937', fg='#e5e7eb', padx=12, pady=6)
        lbl.pack(side='left', padx=(0, 8))

    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True, padx=20, pady=20)

    for title, rows in [('Standard Benchmark', standard_rows), ('Long-Context Stress Benchmark', stress_rows)]:
        frame = ttk.Frame(notebook, style='TFrame')
        notebook.add(frame, text=title)

        top_row = ttk.Frame(frame, style='Panel.TFrame', padding=16)
        top_row.pack(fill='x', pady=(0, 12))
        top_row.columnconfigure((0, 1, 2, 3), weight=1)

        baseline, advanced = rows
        add_metric(top_row, 'Baseline recall', f'{baseline.recall_score:.2f}', 0, 0)
        add_metric(top_row, 'Advanced recall', f'{advanced.recall_score:.2f}', 0, 1)
        add_metric(top_row, 'Baseline prompt tokens', baseline.prompt_tokens_processed, 0, 2)
        add_metric(top_row, 'Advanced prompt tokens', advanced.prompt_tokens_processed, 0, 3)

        mid_row = ttk.Frame(frame, style='Panel.TFrame', padding=16)
        mid_row.pack(fill='x', pady=(0, 12))
        mid_row.columnconfigure((0, 1, 2, 3), weight=1)
        add_metric(mid_row, 'Baseline memory growth', baseline.memory_growth_bytes, 0, 0)
        add_metric(mid_row, 'Advanced memory growth', advanced.memory_growth_bytes, 0, 1)
        add_metric(mid_row, 'Baseline compactions', baseline.compactions, 0, 2)
        add_metric(mid_row, 'Advanced compactions', advanced.compactions, 0, 3)

        table_frame = ttk.Frame(frame, style='Panel.TFrame', padding=16)
        table_frame.pack(fill='both', expand=True)
        ttk.Label(table_frame, text='Benchmark table', style='Section.TLabel').pack(anchor='w', pady=(0, 10))
        add_table(table_frame, rows)

    return root


if __name__ == '__main__':
    app = build_app()
    app.mainloop()
