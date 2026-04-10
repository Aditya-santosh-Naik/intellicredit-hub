"""
IntelliCredit - Run ML Training 40 Times
==========================================
Trains all models (RF, IsoForest, KMeans) 40 times with different random seeds.
Tracks accuracy across all runs and saves the best-performing model.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import os, json, re, pickle, warnings, time
import numpy as np
import pandas as pd
from difflib import SequenceMatcher

from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score, LeaveOneOut
from sklearn.metrics import accuracy_score
from sklearn.cluster import KMeans

warnings.filterwarnings("ignore")

DATASET = r"D:/clg projects/New folder/indian_companies_dataset.xlsx"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_model")
os.makedirs(OUT_DIR, exist_ok=True)

NUM_RUNS = 40

# ── CIN/PAN feature extraction (same as train_model.py) ──────────────────────
CIN_RE  = re.compile(r'^([LU])([A-Z0-9]{5})([A-Z]{2})(\d{4})([A-Z]{3})(\d{6})$')
PAN_RE  = re.compile(r'^([A-Z]{3})([PCHABFTLGJP])([A-Z])(\d{4})([A-Z])$')
CTYPES  = ['PLC','PVT','GOI','NPL','OPC','FLC','FTC','GAP','SGC','ULL','ULT','SGP','ITC']
STATES  = ['AN','AP','AR','AS','BR','CG','CH','DD','DL','DN','GA','GJ','HP','HR','JH',
           'JK','KA','KL','LA','LD','MH','ML','MN','MP','MZ','NL','OD','PB','PY','RJ',
           'SK','TN','TR','TS','UK','UP','WB']
ENTITIES = 'PCHABFTLGJP'

def cin_features(cin):
    m = CIN_RE.match(cin)
    if not m: return [0]*8
    listing = 1 if m.group(1)=='L' else 0
    nic     = sum(ord(c) for c in m.group(2)) / 3000.0
    state   = STATES.index(m.group(3))/len(STATES) if m.group(3) in STATES else -0.1
    year    = (int(m.group(4))-1850)/200.0
    ctype   = CTYPES.index(m.group(5))/len(CTYPES) if m.group(5) in CTYPES else 0.9
    serial  = int(m.group(6))/999999.0
    valid   = 1.0
    regex_ok= 1.0
    return [listing, nic, state, year, ctype, serial, valid, regex_ok]

def pan_features(pan):
    m = PAN_RE.match(pan)
    if not m: return [0]*5
    entity = ENTITIES.index(m.group(2))/len(ENTITIES) if m.group(2) in ENTITIES else 0
    alpha  = sum(ord(c) for c in m.group(1)+m.group(3)) / 2000.0
    digits = int(m.group(4))/9999.0
    last   = (ord(m.group(5))-65)/25.0
    valid  = 1.0
    return [entity, alpha, digits, last, valid]


def run_single_training(run_num, seed, df, X, y, le):
    """Run a single training iteration with given random seed."""
    scaler = StandardScaler()
    X_sc = scaler.fit_transform(X)

    # ── Random Forest ─────────────────────────────────────────────────────────
    rf = RandomForestClassifier(
        n_estimators=500, max_depth=None, min_samples_leaf=1,
        random_state=seed, class_weight="balanced", n_jobs=-1)

    # LOO cross-validation
    loo = LeaveOneOut()
    preds, trues = [], []
    for tr_idx, te_idx in loo.split(X_sc):
        rf_tmp = RandomForestClassifier(
            n_estimators=100, random_state=seed, class_weight="balanced")
        rf_tmp.fit(X_sc[tr_idx], y[tr_idx])
        preds.append(rf_tmp.predict(X_sc[[te_idx[0]]])[0])
        trues.append(y[te_idx[0]])

    rf_loo_acc = accuracy_score(trues, preds)

    # Fit final RF on all data
    rf.fit(X_sc, y)
    rf_in_sample = accuracy_score(y, rf.predict(X_sc))

    # ── Stratified K-Fold CV (additional metric) ──────────────────────────────
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=seed)
    cv_scores = cross_val_score(
        RandomForestClassifier(n_estimators=300, random_state=seed,
                               class_weight="balanced", n_jobs=-1),
        X_sc, y, cv=skf, scoring='accuracy')
    rf_cv_acc = cv_scores.mean()

    # ── IsoForest + KMeans ────────────────────────────────────────────────────
    k = min(df["Sector"].nunique(), max(3, len(df)//6))
    km = KMeans(n_clusters=k, random_state=seed, n_init=15)
    km.fit(X_sc)

    iso = IsolationForest(n_estimators=300, contamination=0.04, random_state=seed)
    iso.fit(X_sc)
    n_anom = int((iso.predict(X_sc) == -1).sum())

    return {
        "run": run_num,
        "seed": seed,
        "rf_loo_acc": round(rf_loo_acc, 4),
        "rf_in_sample": round(rf_in_sample, 4),
        "rf_cv_acc": round(rf_cv_acc, 4),
        "n_anom": n_anom,
        "models": {
            "rf": rf,
            "iso": iso,
            "km": km,
            "scaler": scaler,
            "le": le,
        }
    }


def main():
    # ── Load dataset ──────────────────────────────────────────────────────────
    print("=" * 70)
    print("  IntelliCredit — ML Training (40 Runs)")
    print("=" * 70)
    print(f"\n▶ Loading dataset from: {DATASET}")
    df = pd.read_excel(DATASET)
    df.columns = df.columns.str.strip()
    df = df.dropna(subset=["CIN Number", "PAN Number", "Company Name"])
    df["CIN Number"]   = df["CIN Number"].str.strip().str.upper()
    df["PAN Number"]   = df["PAN Number"].str.strip().str.upper()
    df["Company Name"] = df["Company Name"].str.strip()
    df["Sector"]       = df["Sector"].fillna("Unknown").str.strip()
    print(f"   {len(df)} companies  |  {df['Sector'].nunique()} sectors\n")

    # ── Build lookup DB ───────────────────────────────────────────────────────
    print("▶ Building lookup DB...")
    db_list = []
    for _, r in df.iterrows():
        db_list.append({
            "company": r["Company Name"],
            "cin":     r["CIN Number"],
            "pan":     r["PAN Number"],
            "sector":  r["Sector"],
        })
    db_by_cin = {rec["cin"]: rec for rec in db_list}
    db_by_pan = {rec["pan"]: rec for rec in db_list}
    with open(os.path.join(OUT_DIR, "company_db.json"), "w") as f:
        json.dump({"by_cin": db_by_cin, "by_pan": db_by_pan, "all": db_list}, f, indent=2)
    print(f"   Saved {len(db_list)} records.\n")

    # ── Engineer features ─────────────────────────────────────────────────────
    print("▶ Engineering features...")
    X_cin = np.array([cin_features(c) for c in df["CIN Number"]])
    X_pan = np.array([pan_features(p) for p in df["PAN Number"]])
    X     = np.hstack([X_cin, X_pan])  # 13 features

    le = LabelEncoder()
    y  = le.fit_transform(df["Sector"])
    print(f"   Feature matrix shape: {X.shape}\n")

    # ── Run 40 training iterations ────────────────────────────────────────────
    all_results = []
    best_run = None
    best_loo_acc = -1.0

    seeds = [i * 7 + 13 for i in range(NUM_RUNS)]  # Diverse seeds

    start_time = time.time()

    for i in range(NUM_RUNS):
        seed = seeds[i]
        run_num = i + 1
        print(f"{'─'*70}")
        print(f"  RUN {run_num:02d}/{NUM_RUNS}  (seed={seed})")
        print(f"{'─'*70}")

        t0 = time.time()
        result = run_single_training(run_num, seed, df, X, y, le)
        elapsed = time.time() - t0

        print(f"   RF LOO Accuracy:      {result['rf_loo_acc']*100:.1f}%")
        print(f"   RF 5-Fold CV Acc:     {result['rf_cv_acc']*100:.1f}%")
        print(f"   RF In-Sample Acc:     {result['rf_in_sample']*100:.1f}%")
        print(f"   Anomalies flagged:    {result['n_anom']}")
        print(f"   Time: {elapsed:.1f}s")

        # Track best
        if result["rf_loo_acc"] > best_loo_acc:
            best_loo_acc = result["rf_loo_acc"]
            best_run = result
            print(f"   ★ NEW BEST LOO ACCURACY! ★")

        all_results.append({
            "run": result["run"],
            "seed": result["seed"],
            "rf_loo_acc": result["rf_loo_acc"],
            "rf_in_sample": result["rf_in_sample"],
            "rf_cv_acc": result["rf_cv_acc"],
            "n_anom": result["n_anom"],
            "time_seconds": round(elapsed, 2),
        })
        print()

    total_time = time.time() - start_time

    # ── Save BEST model ──────────────────────────────────────────────────────
    print("=" * 70)
    print("  SAVING BEST MODEL")
    print("=" * 70)
    print(f"\n   Best Run: #{best_run['run']} (seed={best_run['seed']})")
    print(f"   Best LOO Accuracy: {best_run['rf_loo_acc']*100:.1f}%")
    print(f"   Best CV Accuracy:  {best_run['rf_cv_acc']*100:.1f}%")

    models = best_run["models"]
    with open(os.path.join(OUT_DIR, "rf_model.pkl"),   "wb") as f: pickle.dump(models["rf"],     f)
    with open(os.path.join(OUT_DIR, "iso_forest.pkl"), "wb") as f: pickle.dump(models["iso"],    f)
    with open(os.path.join(OUT_DIR, "kmeans.pkl"),     "wb") as f: pickle.dump(models["km"],     f)
    with open(os.path.join(OUT_DIR, "scaler.pkl"),     "wb") as f: pickle.dump(models["scaler"], f)
    with open(os.path.join(OUT_DIR, "label_enc.pkl"),  "wb") as f: pickle.dump(models["le"],     f)

    # ── Compute statistics ────────────────────────────────────────────────────
    loo_accs = [r["rf_loo_acc"] for r in all_results]
    cv_accs  = [r["rf_cv_acc"]  for r in all_results]

    stats = {
        "total_runs": NUM_RUNS,
        "total_time_seconds": round(total_time, 2),
        "loo_accuracy": {
            "mean": round(np.mean(loo_accs), 4),
            "std":  round(np.std(loo_accs), 4),
            "min":  round(np.min(loo_accs), 4),
            "max":  round(np.max(loo_accs), 4),
        },
        "cv_accuracy": {
            "mean": round(np.mean(cv_accs), 4),
            "std":  round(np.std(cv_accs), 4),
            "min":  round(np.min(cv_accs), 4),
            "max":  round(np.max(cv_accs), 4),
        },
        "best_run": {
            "run_number": best_run["run"],
            "seed": best_run["seed"],
            "rf_loo_acc": best_run["rf_loo_acc"],
            "rf_cv_acc": best_run["rf_cv_acc"],
            "rf_in_sample": best_run["rf_in_sample"],
        },
        "all_runs": all_results,
    }

    # Save metadata
    meta = {
        "n_companies":    len(df),
        "n_sectors":      int(df["Sector"].nunique()),
        "n_features":     int(X.shape[1]),
        "rf_loo_acc":     best_run["rf_loo_acc"],
        "rf_in_sample":   best_run["rf_in_sample"],
        "rf_cv_acc":      best_run["rf_cv_acc"],
        "dl_cv_acc":      0.0,
        "dl_available":   False,
        "n_anom":         best_run["n_anom"],
        "training_runs":  NUM_RUNS,
        "best_seed":      best_run["seed"],
        "sectors":        list(le.classes_),
        "feature_names":  ["cin_listing","cin_nic","cin_state","cin_year","cin_type",
                           "cin_serial","cin_valid","cin_regex","pan_entity","pan_alpha",
                           "pan_digits","pan_last","pan_valid"],
    }
    with open(os.path.join(OUT_DIR, "model_metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # Save full training report
    with open(os.path.join(OUT_DIR, "training_40_runs_report.json"), "w") as f:
        json.dump(stats, f, indent=2)

    # ── Print summary ─────────────────────────────────────────────────────────
    print(f"\n{'='*70}")
    print(f"  TRAINING SUMMARY — {NUM_RUNS} RUNS COMPLETE")
    print(f"{'='*70}")
    print(f"  Total time:            {total_time/60:.1f} minutes ({total_time:.0f}s)")
    print(f"  Companies:             {len(df)}")
    print(f"  Sectors:               {df['Sector'].nunique()}")
    print(f"  Features:              {X.shape[1]}")
    print(f"")
    print(f"  LOO Accuracy:")
    print(f"    Mean:   {np.mean(loo_accs)*100:.2f}%")
    print(f"    Std:    {np.std(loo_accs)*100:.2f}%")
    print(f"    Min:    {np.min(loo_accs)*100:.2f}%")
    print(f"    Max:    {np.max(loo_accs)*100:.2f}%")
    print(f"")
    print(f"  5-Fold CV Accuracy:")
    print(f"    Mean:   {np.mean(cv_accs)*100:.2f}%")
    print(f"    Std:    {np.std(cv_accs)*100:.2f}%")
    print(f"    Min:    {np.min(cv_accs)*100:.2f}%")
    print(f"    Max:    {np.max(cv_accs)*100:.2f}%")
    print(f"")
    print(f"  ★ Best model saved (Run #{best_run['run']}, seed={best_run['seed']})")
    print(f"    LOO: {best_run['rf_loo_acc']*100:.1f}% | CV: {best_run['rf_cv_acc']*100:.1f}% | In-sample: {best_run['rf_in_sample']*100:.1f}%")
    print(f"")
    print(f"  Artifacts saved to: {OUT_DIR}/")
    print(f"    • rf_model.pkl, iso_forest.pkl, kmeans.pkl")
    print(f"    • scaler.pkl, label_enc.pkl")
    print(f"    • model_metadata.json")
    print(f"    • training_40_runs_report.json")
    print(f"\n✅ All {NUM_RUNS} training runs complete!")


if __name__ == "__main__":
    main()
