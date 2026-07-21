# -*- coding: utf-8 -*-
"""
Анализ скважины на основе данных геофизических исследований скважины №17
Расчёт пористости и проницаемости по методам Ларионова и Тимура
Входные данные (LAS): GR (ГК), neutron (ННК), PZ (ПЗ), LLD (LLD)
Глубины 1068-1161.9 м
Выходные данные:
1) Vsh — глинистость по формуле Ларионова (молодые отложения)
2) Kn — эффективная пористость (ННК + поправка за глины)
3) Kпр — проницаемость (формула Тимура, 1968)
Результат: каротажный планшет с 5 треками + CSV с результатами
"""

import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import LogLocator, FuncFormatter


def read_las(path):
    """
    Читает файл LAS 2.0 без сторонних библиотек.
    Возвращает pandas DataFrame с кривыми.
    """
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    sections = re.split(r"(?m)^~", text)
    curves = []
    null_val = -999.25
    data_text = ""

    for sec in sections:
        if not sec.strip():
            continue
        head = sec.strip()[:1].upper()

        # Секция ~Curve
        if head == "C":
            lines = sec.splitlines()
            for line in lines[1:]:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                m = re.match(r"([^\.\s]+)\s*\.", line)
                if m:
                    curves.append(m.group(1))

        # Секция ~Well (поиск NULL)
        elif head == "W":
            m = re.search(r"NULL\s*\.\s*([^\s:]+)", sec, re.IGNORECASE)
            if m:
                try:
                    null_val = float(m.group(1))
                except ValueError:
                    pass

        # Секция ~Ascii (данные)
        elif head == "A":
            data_text = "\n".join(sec.splitlines()[1:])

    rows = []
    for line in data_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            rows.append([float(x) for x in line.split()])
        except ValueError:
            continue

    df = pd.DataFrame(rows, columns=curves if len(curves) == len(rows[0]) else None)
    df = df.replace(null_val, np.nan)
    return df


def calc_vsh_larionov(gr, gr_clean=None, gr_shale=None):
    """
    Расчёт глинистости по формуле Ларионова для молодых отложений.
    """
    if gr_clean is None:
        gr_clean = np.nanpercentile(gr, 5)
    if gr_shale is None:
        gr_shale = np.nanpercentile(gr, 95)

    igr = (gr - gr_clean) / (gr_shale - gr_clean)
    igr = np.clip(igr, 0.0, 1.0)
    vsh = 0.083 * (2.0 ** (3.7 * igr) - 1.0)
    return np.clip(vsh, 0.0, 1.0), gr_clean, gr_shale


def calc_porosity_from_neutron(nlog, vsh, phi_max=0.30, phi_min=0.02, phi_shale=0.30):
    """
    Расчёт эффективной пористости по ННК с поправкой за глины.
    """
    n_min = np.nanpercentile(nlog, 5)
    n_max = np.nanpercentile(nlog, 95)
    
    phi_n = phi_max - (phi_max - phi_min) * (nlog - n_min) / (n_max - n_min)
    phi_n = np.clip(phi_n, phi_min, phi_max)
    phi_eff = phi_n - vsh * phi_shale
    return np.clip(phi_eff, 0.0, phi_max), n_min, n_max


def calc_permeability_timur(phi, swirr=0.25):
    """
    Расчёт проницаемости по эмпирической формуле Тимура (1968).
    """
    phi_safe = np.where(phi > 0, phi, np.nan)
    k_md = (100.0 * (phi_safe  2.25) / swirr)  2
    return k_md


def plot_well(df, out_png):
    """
    Строит каротажный планшет (5 треков) с результатами интерпретации.
    """
    depth = df["DEPT"].values
    gr = df["GR"].values
    nlog = df["neutron"].values
    pz = df["PZ"].values
    lld = df["LLD"].values
    vsh = df["Vsh"].values
    kp = df["Kn"].values
    kpr = df["Kпр"].values

    fig, axes = plt.subplots(
        nrows=1, ncols=5, sharey=True,
        figsize=(15, 11),
        gridspec_kw={"wspace": 0.08},
    )
    
    fig.suptitle("Скважина №17 | Расчёт пористости и проницаемости", fontsize=14, fontweight="bold", y=0.995)

    # Трек 1: ГК + Vsh
    ax1 = axes[0]
    ax1.plot(gr, depth, color="#3498db", lw=0.9, label="ГК")
    ax1.set_xlabel("ГК, р.е.", color="#3498db", labelpad=4)
    ax1.tick_params(axis="x", colors="#3498db", labelsize=8)
    ax1.set_xlim(np.floor(np.nanmin(gr)), np.ceil(np.nanmax(gr)))
    
    ax1b = ax1.twiny()
    ax1b.plot(vsh, depth, color="#e74c3c", lw=0.9, label="Vsh")
    ax1b.spines["top"].set_position(("outward", 36))
    ax1b.set_xlabel("Vsh, д.ед.", color="#e74c3c", labelpad=4)
    ax1b.tick_params(axis="x", colors="#e74c3c", labelsize=8)
    ax1b.set_xlim(0, 1)

    # Трек 2: ННК
    ax2 = axes[1]
    ax2.plot(nlog, depth, color="#f39c12", lw=0.9)
    ax2.set_xlabel("ННК, р.е.", color="#f39c12", labelpad=4)
    ax2.tick_params(axis="x", colors="#f39c12", labelsize=8)
    ax2.set_xlim(np.nanmin(nlog) * 0.95, np.nanmax(nlog) * 1.02)

    # Трек 3: ПЗ + LLD (логарифмическая шкала)
    ax3 = axes[2]
    ax3.plot(pz, depth, color="#27ae60", lw=0.9, label="ПЗ")
    ax3.set_xlabel("ПЗ, Ом·м", color="#27ae60", labelpad=4)
    ax3.tick_params(axis="x", colors="#27ae60", labelsize=8)
    ax3.set_xscale("log")
    ax3.set_xlim(1, 1000)
    ax3.xaxis.set_major_locator(LogLocator(base=10, numticks=4))
    ax3.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))

    ax3b = ax3.twiny()
    ax3b.plot(lld, depth, color="#2980b9", lw=0.9, label="LLD")
    ax3b.spines["top"].set_position(("outward", 36))
    ax3b.set_xlabel("LLD, Ом·м", color="#2980b9", labelpad=4)
    ax3b.tick_params(axis="x", colors="#2980b9", labelsize=8)
    ax3b.set_xscale("log")

    # Трек 4: Эффективная пористость
    ax4 = axes[3]
    ax4.plot(kp * 100, depth, color="#9b59b6", lw=1.0)
    ax4.fill_betweenx(depth, 0, kp * 100, where=~np.isnan(kp), color="#9b59b6", alpha=0.15)
    ax4.set_xlabel("Кп, %", color="#9b59b6", labelpad=4)
    ax4.tick_params(axis="x", colors="#9b59b6", labelsize=8)
    ax4.set_xlim(0, 30)
    ax4.set_xticks([0, 10, 20, 30])

    # Трек 5: Проницаемость
    ax5 = axes[4]
    ax5.plot(kpr, depth, color="#e67e22", lw=1.0)
    ax5.set_xscale("log")
    ax5.set_xlabel("Кпр, мД", color="#e67e22", labelpad=4)
    ax5.tick_params(axis="x", colors="#e67e22", labelsize=8)
    ax5.set_xlim(1e-2, 1e3)
    ax5.xaxis.set_major_locator(LogLocator(base=10, numticks=6))
    ax5.xaxis.set_major_formatter(FuncFormatter(lambda x, _: f"{x:g}"))

    # Оформление осей
    for i, ax in enumerate(axes):
        ax.invert_yaxis()
        ax.grid(True, which="both", ls=":", lw=0.4, color="grey", alpha=0.6)
        ax.xaxis.set_label_position("top")
        ax.xaxis.tick_top()
        ax.tick_params(axis="x", labelsize=8)
        if i == 0:
            ax.set_ylabel("Глубина, м", fontsize=11)

    axes[0].set_ylim(depth.max(), depth.min())
    plt.subplots_adjust(top=0.88, bottom=0.04, left=0.06, right=0.985)
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    plt.close()


def main():
    las_path = "17.las"
    out_dir = "."
    os.makedirs(out_dir, exist_ok=True)

    df = read_las(las_path)
    print(f"Прочитан LAS-файл: {df.shape[0]} измерений, {df.shape[1]} кривых")
    print(f"Глубины: {df['DEPT'].min():.1f} - {df['DEPT'].max():.1f} м")
    print(f"Кривые: {', '.join(df.columns.tolist())}\n")

    vsh, _, _ = calc_vsh_larionov(df["GR"].values)
    df["Vsh"] = vsh
    print("Расчёт глинистости (формула Ларионова) выполнен")

    kp, _, _ = calc_porosity_from_neutron(df["neutron"].values, vsh)
    df["Kn"] = kp
    print("Расчёт эффективной пористости выполнен")

    df["Kпр"] = calc_permeability_timur(kp, swirr=0.25)
    print("Расчёт проницаемости (формула Тимура, 1968) выполнен\n")

    out_csv = os.path.join(out_dir, "well_17_results.csv")
    df.to_csv(out_csv, index=False, sep=";", float_format="%.4f")
    print(f"Результаты сохранены в CSV: {out_csv}")

    out_png = os.path.join(out_dir, "well_17_logplot.png")
    plot_well(df, out_png)
    print(f"Планшет ГИС сохранён в PNG: {out_png}")

    print("\nСтатистика результатов:")
    print(f"Глинистость (Vsh): мин={vsh.min():.2%}, макс={vsh.max():.2%}")
    print(f"Пористость (Кп): мин={kp.min():.2%}, макс={kp.max():.2%}")
    kpr_nonzero = df["Kпр"][df["Kпр"] > 0]
    if len(kpr_nonzero) > 0:
        print(f"Проницаемость (Кпр): мин={kpr_nonzero.min():.2f} мД, макс={kpr_nonzero.max():.2f} мД")


if name == "__main__":
    main()
