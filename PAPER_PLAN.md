# Paper Plan

**Working title:** Forecasting Rare Public Operational Actions from Auditable Event Streams  
**Target venue:** ICLR (workshop/full-paper decision deferred)  
**Type:** Empirical diagnostic study  
**Date:** 2026-07-28  
**Page budget:** 9 pages through conclusion  
**Review mode:** Single-session plan review; no external reviewer MCP was available.

## Claims–Evidence Matrix

| Claim | Evidence | Status | Section |
| --- | --- | --- | --- |
| A public-action forecasting problem can be represented as leakage-controlled person-period data. | 41 accepted announcements; 315 daily and 1260 six-hour periods; explicit `(start,end]` boundaries. | Supported | §3 |
| A strong recent-rate baseline changes the historical conclusion. | Rolling-30 daily Brier 0.119664 versus M2 0.125443; six-hour M2 remains 0.036443. | Historically supported; prospective test pending | §4 |
| Official-incident features do not yet show stable incremental value. | Daily M3-lite 0.127800; six-hour 0.037029; paired block intervals cross zero. | Supported as a null/uncertain finding | §4–5 |
| Immutable prospective evaluation is feasible and auditable. | Hash-locked bundles including adaptive baselines, independent outcomes, exclusions, missed-run registry, Windows scheduler, 8/8 fault drills. | Infrastructure supported; performance pending | §3, §5 |
| Public application reports reveal heterogeneous mechanisms but cannot estimate failure prevalence. | 20 reports: 13 clean/unspecified arrival, 4 mechanism mismatch, 3 failures; only one exact delay. | Descriptively supported | §5 |
| Any claim of prospective superiority must wait. | Amended stopping rule: at least 180 scheduled days and 20 positives; currently 0 scheduled runs. | Needs future evidence | §6 |

## Structure

### §0 Abstract (180–220 words)

Problem, auditable event-stream formulation, 41-event historical study, M2/M3-lite result, and
prospective protocol. State plainly that prospective performance is not yet available.

### §1 Introduction (1.3 pages)

Motivate rare public operational actions as a forecasting target. Contrast auditable behavioral
events with psychological profiling. Contributions: dataset, leakage controls, historical
diagnostics, immutable prospective system, and null result for incident features.

### §2 Related Work (1.0 pages)

Proper probabilistic scoring; rolling evaluation and leakage; event-system/organizational attention;
concept drift and rare-event temporal prediction. Position the work as a single-stream,
audit-centered diagnostic rather than a general model benchmark.

### §3 Data and Prospective Protocol (1.8 pages)

Define announcement event, daily/6h windows, source hierarchy, context visibility, M0/M2/M3-lite,
locked forecasts, missing runs, revisions, and stopping rule. Include a compact pipeline figure
later; until then use a textual flow.

### §4 Historical Experiments (2.2 pages)

Daily common-window table, six-hour table, lag ablation, block bootstrap. Emphasize development-stage
status and avoid significance claims.

### §5 Operational and Application Audits (1.2 pages)

Fault drills, evidence grades, application mechanisms, data limitations, and dashboard state.

### §6 Prospective Evaluation Plan (0.8 pages)

Primary comparisons, stopping rule, calibration, missed-run accounting, revision sensitivity, and
explicit empty result state.

### §7 Limitations, Ethics, and Conclusion (0.7 pages)

Small single-stream sample, dependent windows, discovery-layer dependency, self-selected application
reports, reflexivity, and no inference about private motives.

## Figure and Table Plan

| ID | Type | Description | Data source | Priority |
| --- | --- | --- | --- | --- |
| Fig. 1 | Pipeline | Discovery → primary verification → gold → context snapshots → locked forecasts → independent scoring/revision | repository schema | High |
| Fig. 2 | Timeline | 41 announcements with official incidents and policy regime | processed CSVs | Medium |
| Table 1 | Main results | Daily M0–M3-lite Brier/Log Loss | `model_comparison_v1.md` | High |
| Table 2 | Main results | Six-hour M0–M3-lite plus bootstrap intervals | `model_comparison_6h_v1.md` | High |
| Table 3 | Audit | Application evidence and quality breakdown | task 9/12 reports | Medium |

Hero figure caption draft: “Audit-preserving forecasting pipeline. Discovery sources can propose
candidates, but only verified gold events update labels; predictions and later revisions are stored
in separate append-only layers.”

## Citation Plan

- Introduction/evaluation: Brier (1950), Gneiting and Raftery (2007), Tashman (2000).
- Leakage and reproducibility: Kapoor and Narayanan (2023).
- Event context: Morgeson et al. (2015), Ocasio (1997).
- Drift: Gama et al. (2014).

All entries must be drawn from verified DOI metadata or the existing research bibliography.

## Single-Session Review

The main risk is premature paper framing before prospective outcomes mature. Minimum fix: label the
manuscript as a protocol-and-historical-diagnostic draft, keep prospective results explicitly empty,
and prevent the abstract from implying real-time superiority. A second risk is over-generalization
from one public action stream; the limitations section must constrain the scope.

## Next Steps

- Generate the anonymous LaTeX protocol-and-results draft.
- Add figures only after the visual pipeline and timeline are generated.
- Compile and review after the prospective result table contains mature scheduled observations.
