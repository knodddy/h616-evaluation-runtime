from pathlib import Path
from collections import defaultdict
from itertools import combinations
import argparse
import hashlib
import io
import json
import re
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
QA = HERE / "qa"
PARAMETERS = ["S11", "S21", "S12", "S22"]
ORDER = ["IDLE", "NOP", "MOV", "ADD", "AND", "OR", "LSL", "B"]


def load_data():
    records = []
    inventory = []
    for path in sorted(ROOT.rglob("*.s2p")):
        text = path.read_text()
        lines = text.splitlines()
        option = next(line for line in lines if line.startswith("#"))
        assert option.split() == ["#Hz", "S", "RI", "R", "50.000"], (path, option)
        raw = np.loadtxt(io.StringIO("\n".join(
            line for line in lines if line.strip() and not line.startswith(("!", "#"))
        )))
        assert raw.ndim == 2 and raw.shape[1] == 9 and np.isfinite(raw).all(), path
        assert np.all(np.diff(raw[:, 0]) >= 0), path
        complex_values = raw[:, 1::2] + 1j * raw[:, 2::2]
        frequency, inverse, counts = np.unique(raw[:, 0], return_inverse=True, return_counts=True)
        values = np.zeros((len(frequency), 4), dtype=complex)
        np.add.at(values, inverse, complex_values)
        values /= counts[:, None]
        assert np.all(np.abs(values) > 0), path
        match = re.fullmatch(r"([A-Z]+)(\d+)", path.stem)
        workload, repeat = (match[1], int(match[2])) if match else ("UNLABELLED", int(path.stem))
        stamp = next((line[1:].strip() for line in lines if re.match(r"!\w+,", line) and "2026" in line), "")
        duplicate_index = np.flatnonzero(np.diff(raw[:, 0]) == 0)
        record = dict(path=str(path.relative_to(ROOT)), condition=str(path.parent.relative_to(ROOT)),
                      workload=workload, repeat=repeat, timestamp=stamp, frequency=frequency, values=values)
        records.append(record)
        inventory.append({k: record[k] for k in ["path", "condition", "workload", "repeat", "timestamp"]} | {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "rows": len(raw),
            "unique_frequencies": len(frequency), "min_Hz": frequency[0], "max_Hz": frequency[-1],
            "reference_ohm": 50, "calibration": next(line for line in lines if line.startswith("!Calibration")),
            "duplicate_frequency_Hz": ";".join(str(raw[i, 0]) for i in duplicate_index),
            "max_duplicate_complex_jump": float(max((abs(complex_values[i+1]-complex_values[i]).max() for i in duplicate_index), default=0)),
        })
    return records, pd.DataFrame(inventory)


def groups_from(records):
    grouped = defaultdict(list)
    for record in records:
        grouped[(record["condition"], record["workload"])].append(record)
    groups = {}
    for key, group in grouped.items():
        frequency = group[0]["frequency"]
        assert all(np.array_equal(record["frequency"], frequency) for record in group), key
        groups[key] = (frequency, np.stack([record["values"] for record in group]))
    return groups


def average_frequency(values, frequency):
    return np.trapezoid(values, x=frequency, axis=-1) / (frequency[-1] - frequency[0])


def summarize(records, groups):
    pairs, repeatability, peaks = [], [], []
    conditions = sorted({key[0] for key in groups if key[1] != "UNLABELLED"})
    for condition in conditions:
        labels = [label for label in ORDER if (condition, label) in groups]
        for label in labels:
            frequency, values = groups[condition, label]
            for j, parameter in enumerate(PARAMETERS):
                data = values[:, :, j]
                magnitude_db = 20 * np.log10(np.abs(data))
                variance = np.var(data, axis=0, ddof=1) if len(data) > 1 else np.full(len(frequency), np.nan)
                repeatability.append(dict(condition=condition, workload=label, parameter=parameter, n=len(data),
                    complex_repeat_sd_rms=float(np.sqrt(average_frequency(variance, frequency))),
                    db_repeat_sd_rms=float(np.sqrt(average_frequency(np.var(magnitude_db, axis=0, ddof=1), frequency))) if len(data)>1 else np.nan,
                    minimum_db=float(magnitude_db.min()), maximum_db=float(magnitude_db.max())))
        for left, right in combinations(labels, 2):
            frequency, a = groups[condition, left]
            other_frequency, b = groups[condition, right]
            assert np.array_equal(frequency, other_frequency)
            for j, parameter in enumerate(PARAMETERS):
                aa, bb = a[:, :, j], b[:, :, j]
                delta = aa.mean(axis=0) - bb.mean(axis=0)
                distance = np.sqrt(average_frequency(abs(delta)**2, frequency))
                variance = (np.var(aa, axis=0, ddof=1) + np.var(bb, axis=0, ddof=1))/2 if min(len(aa),len(bb))>1 else np.full(len(frequency), np.nan)
                noise = np.sqrt(average_frequency(variance, frequency))
                db_delta = 20*np.log10(abs(aa)).mean(axis=0)-20*np.log10(abs(bb)).mean(axis=0)
                index = np.argmax(abs(db_delta))
                pairs.append(dict(condition=condition, a=left, b=right, parameter=parameter,
                    n_a=len(aa), n_b=len(bb), complex_distance_rms=float(distance),
                    pooled_repeat_sd_rms=float(noise), separation_to_repeat_sd=float(distance/noise),
                    db_difference_rms=float(np.sqrt(average_frequency(db_delta**2, frequency))),
                    max_abs_db_difference=float(abs(db_delta[index])), max_db_difference_MHz=float(frequency[index]/1e6)))
                for low, high in [(5, 100), (100, 300)]:
                    take=(frequency>=low*1e6)&(frequency<=high*1e6)
                    peaks.append(dict(condition=condition, a=left, b=right, parameter=parameter,
                        band_MHz=f"{low}-{high}", complex_distance_rms=float(np.sqrt(average_frequency(abs(delta[take])**2, frequency[take])))))
    pd.DataFrame(pairs).to_csv(HERE / "pairwise_comparisons.csv", index=False)
    pd.DataFrame(repeatability).to_csv(HERE / "repeatability.csv", index=False)
    pd.DataFrame(peaks).to_csv(HERE / "band_comparisons.csv", index=False)
    usb_rows = []
    for label in ORDER:
        frequency, a = groups["power-on/none/PS", label]
        other_frequency, b = groups["power-on/usb/PS", label]
        assert np.array_equal(frequency, other_frequency)
        delta = 20*np.log10(abs(b[:,:,1])).mean(0) - 20*np.log10(abs(a[:,:,1])).mean(0)
        usb_rows.append(dict(workload=label, n_no_usb=len(a), n_usb=len(b),
            S21_db_difference_rms=float(np.sqrt(average_frequency(delta**2, frequency))),
            S21_difference_at_5MHz_db=float(delta[0])))
    pd.DataFrame(usb_rows).to_csv(HERE / "usb_comparisons.csv", index=False)
    return pd.DataFrame(pairs), pd.DataFrame(repeatability)


def plot_results(groups, pairs):
    import matplotlib as mpl
    mpl.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LogNorm

    mpl.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans"],
        "font.size": 8, "axes.titlesize": 9,
        "axes.labelsize": 8, "xtick.labelsize": 7, "ytick.labelsize": 7,
        "legend.fontsize": 7, "svg.fonttype": "none", "pdf.fonttype": 42,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.linewidth": .7, "legend.frameon": False,
    })
    colors = dict(zip(ORDER, ["#555555", "#000000", "#9B59B6", "#D55E00",
                              "#0072B2", "#56B4E9", "#009E73", "#A56A12"]))
    source_rows = []

    def finish(fig, name, axes, note, exclude_axes=()):
        QA.mkdir(exist_ok=True)
        for letter, ax in zip("abcdefghijklmnopqrstuvwxyz", np.asarray(axes).ravel()):
            ax.annotate(letter, (0, 1), xycoords="axes fraction", xytext=(-19, 7),
                        textcoords="offset points", fontsize=9, fontweight="bold")
        fig.text(.5, .025, note, ha="center", va="bottom", fontsize=7)
        fig.canvas.draw()
        try:
            from audit_panel_alignment import require_matplotlib_panel_alignment
        except ImportError:
            print("Alignment auditor not on PYTHONPATH; exporting without an alignment audit.")
        else:
            require_matplotlib_panel_alignment(fig, json_out=QA / f"{name}.alignment.json",
                tolerance_pt=1.5, gutter_tolerance_pt=1.5, strict=True, exclude_axes=list(exclude_axes))
        fig.savefig(HERE / f"{name}.png", dpi=300)
        fig.savefig(HERE / f"{name}.pdf")
        fig.savefig(HERE / f"{name}.svg")
        plt.close(fig)

    def curves(ax, condition, workload, parameter=1, color=None, label=None, style="-", xlim=None):
        f, values = groups[condition, workload]
        db = 20*np.log10(abs(values[:, :, parameter]))
        mean, low, high = db.mean(0), db.min(0), db.max(0)
        color = color or colors[workload]
        visible = (f >= xlim[0]*1e6) & (f <= xlim[1]*1e6) if xlim else np.ones(len(f), dtype=bool)
        ax.fill_between(f[visible]/1e6, low[visible], high[visible], color=color, alpha=.15, linewidth=0)
        ax.plot(f[visible]/1e6, mean[visible], color=color, label=label or workload, linestyle=style, linewidth=1)
        ax.set(xlabel="Frequency (MHz)", ylabel=f"{PARAMETERS[parameter]} magnitude (dB)")
        ax.grid(axis="y", alpha=.17)
        if xlim:
            ax.set_xlim(xlim)
        for hz, m, lo, hi in zip(f, mean, low, high):
            source_rows.append(dict(condition=condition, workload=workload, parameter=PARAMETERS[parameter],
                frequency_Hz=hz, mean_db=m, min_db=lo, max_db=hi, n=len(values)))

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.3))
    fig.subplots_adjust(left=.09, right=.98, bottom=.23, top=.77, wspace=.3)
    for ax, limits, title in zip(axes, [(5, 300), (130, 165)], ["Full measured band", "Exploratory zoom: 130–165 MHz"]):
        for workload in ORDER:
            curves(ax, "power-on/none/PS", workload, xlim=limits)
        ax.set_title(title, pad=11)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.52, .91), ncol=8, columnspacing=1)
    fig.suptitle("PS rail, no USB device: recorded workload spectra", y=.99, fontsize=11)
    finish(fig, "01_ps_spectra", axes, "Lines: mean in dB; bands: observed min–max. Three consecutive sweeps per workload, one run each.")

    conditions = ["power-on/none/PS", "power-on/usb/PS", "power-on/none/cpu"]
    titles = ["PS · no USB", "PS · USB attached", "VDDCPU · no USB"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.6))
    fig.subplots_adjust(left=.075, right=.98, bottom=.32, top=.78, wspace=.35)
    cmap = mpl.colormaps["viridis"].copy()
    cmap.set_bad("#eeeeee")
    for ax, condition, title in zip(axes, conditions, titles):
        matrix = np.full((len(ORDER), len(ORDER)), np.nan)
        rows = pairs[(pairs.condition == condition) & (pairs.parameter == "S21")]
        for row in rows.itertuples():
            matrix[ORDER.index(row.b), ORDER.index(row.a)] = row.separation_to_repeat_sd
        im = ax.imshow(matrix, cmap=cmap, norm=LogNorm(vmin=1, vmax=100), aspect="auto")
        ax.set_xticks(range(len(ORDER)), ORDER, rotation=90)
        ax.set_yticks(range(len(ORDER)), ORDER)
        ax.tick_params(length=0, pad=3)
        ax.set_title(title, pad=12)
        for i in range(len(ORDER)):
            for j in range(i):
                value = matrix[i,j]
                ax.text(j, i, f"{value:.0f}" if value>=10 else f"{value:.1f}" if np.isfinite(value) else "–",
                    ha="center", va="center", fontsize=6, color="white" if value<10 else "black")
    color_ax = fig.add_axes([.35, .15, .35, .025])
    fig.colorbar(im, cax=color_ax, orientation="horizontal", ticks=[1, 3, 10, 30, 100])
    color_ax.set_xticks([1, 3, 10, 30, 100], ["1", "3", "10", "30", "100"])
    color_ax.set_xlabel("Complex S21 separation / within-run repeat SD", fontsize=7, labelpad=3)
    fig.suptitle("Recorded differences versus short-term repeat variation", y=.96, fontsize=11)
    finish(fig, "02_separation", axes,
        "Descriptive full-band ratio, not a significance test. Dashes: insufficient repeats (CPU NOP, MOV, OR).",
        exclude_axes=[color_ax])

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 5.5), sharex=True, sharey=True)
    fig.subplots_adjust(left=.09, right=.98, bottom=.16, top=.84, wspace=.22, hspace=.38)
    for ax, workload in zip(axes.ravel(), ["NOP", "MOV", "ADD", "OR"]):
        curves(ax, "power-on/none/PS", workload, color="#555555", label="No USB", xlim=(5,300))
        curves(ax, "power-on/usb/PS", workload, color="#0072B2", label="USB attached", style="--")
        ax.set_title(workload, pad=10)
    handles, labels = axes[0,0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.5,.93), ncol=2)
    fig.suptitle("USB-associated changes are not a uniform offset", y=.99, fontsize=11)
    finish(fig, "03_usb_comparison", axes,
        "PS rail. Lines: mean in dB; bands: min–max of 3 consecutive sweeps, not confidence intervals.")

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4), sharey=True)
    fig.subplots_adjust(left=.09, right=.98, bottom=.23, top=.77, wspace=.26)
    for ax, (condition, workload, title) in zip(axes, [
        ("power-on/usb/PS", "B", "B · PS · USB attached"),
        ("power-on/none/cpu", "IDLE", "IDLE · VDDCPU · no USB"),
    ]):
        frequency, values = groups[condition, workload]
        db=20*np.log10(abs(values[:,:,0]))
        for i, (color, style) in enumerate(zip(["#0072B2", "#D55E00", "#009E73"], ["-", "--", ":"])):
            ax.plot(frequency/1e6, db[i], color=color, linestyle=style, linewidth=1.2, label=f"Sweep {i+1}")
        ax.set(xlim=(180,195), xlabel="Frequency (MHz)", ylabel="S11 magnitude (dB)", title=title)
        ax.grid(axis="y", alpha=.17)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.5,.9), ncol=3)
    fig.suptitle("Deep reflection notches vary between consecutive sweeps", y=.99, fontsize=11)
    finish(fig, "04_repeat_variation", axes,
        "Individual S11 sweeps, exploratory 180–195 MHz zoom. No sweep removed; no averaging or smoothing.")
    pd.DataFrame(source_rows).drop_duplicates().to_csv(HERE / "plotted_spectra.csv", index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse H616 VNA workload sweeps.")
    parser.add_argument("data_dir", type=Path, help="Directory containing power-on/ and no-power/ measurements")
    parser.add_argument("--plot", action="store_true", help="Regenerate the figures")
    args = parser.parse_args()
    ROOT = args.data_dir.resolve()
    if not ROOT.is_dir():
        parser.error(f"Measurement directory does not exist: {ROOT}")
    records, inventory = load_data()
    if not records:
        parser.error(f"No .s2p measurements found in {ROOT}")
    inventory["included_in_workload_comparisons"] = inventory.workload != "UNLABELLED"
    inventory.to_csv(HERE / "inventory.csv", index=False)
    metadata = {
        "python": sys.version, "numpy": np.__version__, "pandas": pd.__version__,
        "input_s2p_count": len(records), "labelled_s2p_count": int((inventory.workload != "UNLABELLED").sum()),
        "unnamed_files": inventory.loc[inventory.workload == "UNLABELLED", "path"].tolist(),
        "unparsed_instrument_state_files": [str(p.relative_to(ROOT)) for p in sorted(ROOT.rglob("*.cst"))],
        "duplicate_frequency_rule": "Complex arithmetic mean of the two 100 MHz segment endpoints, within each trace.",
        "frequency_summary_rule": "Trapezoidal integral divided by total bandwidth; squared quantities integrated before taking square root.",
        "magnitude_plot_rule": "20 log10(abs(S)) per sweep, then arithmetic mean and observed min/max across sweeps.",
        "repeat_type": "Consecutive technical sweeps of one run; not independent reset/provision cycles.",
        "impedance_conversion": "Not performed: probe topology and calibration reference plane unverified.",
    }
    (HERE / "analysis_metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    groups = groups_from(records)
    pairs, repeatability = summarize(records, groups)
    for condition in sorted(pairs.condition.unique()):
        print(condition)
        for parameter in PARAMETERS:
            rows = pairs[(pairs.condition == condition) & (pairs.parameter == parameter)]
            print(parameter, "median separation/repeat SD", rows.separation_to_repeat_sd.median(),
                  "range", rows.separation_to_repeat_sd.min(), rows.separation_to_repeat_sd.max())
            print(rows.nsmallest(2, "separation_to_repeat_sd")[["a", "b", "separation_to_repeat_sd", "db_difference_rms"]].to_string(index=False))
    print("traces",len(records), "instrument states",len(list(ROOT.rglob('*.cst'))))
    if args.plot:
        plot_results(groups, pairs)
