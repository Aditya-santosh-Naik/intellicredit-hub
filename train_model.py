"""
IntelliCredit — Company Verifier ML Training Script (v2)
=========================================================
Dataset : D:/clg projects/New folder/indian_companies_dataset.xlsx
153 companies, 21 sectors

Approach:
  • EXACT lookup table      — primary verifier (CIN/PAN → company)
  • Supervised RF           — sector classification from CIN/PAN features
  • Unsupervised IsoForest  — anomaly / spoofed-pattern detection
  • ANN (Dense DL)          — secondary pattern recognition
  • String similarity       — fuzzy company name matching
"""

import os, json, re, pickle, warnings
import numpy as np
import pandas as pd
from difflib import SequenceMatcher

from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score
from sklearn.cluster import KMeans

warnings.filterwarnings("ignore")

DATASET = r"D:/clg projects/New folder/indian_companies_dataset.xlsx"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml_model")
os.makedirs(OUT_DIR, exist_ok=True)

# ── 1. Load ───────────────────────────────────────────────────────────────────
print("▶ Loading dataset...")
df = pd.read_excel(DATASET)
df.columns = df.columns.str.strip()
df = df.dropna(subset=["CIN Number", "PAN Number", "Company Name"])
df["CIN Number"]   = df["CIN Number"].str.strip().str.upper()
df["PAN Number"]   = df["PAN Number"].str.strip().str.upper()
df["Company Name"] = df["Company Name"].str.strip()
df["Sector"]       = df["Sector"].fillna("Unknown").str.strip()
print(f"   {len(df)} companies  |  {df['Sector'].nunique()} sectors")

# ── 2. Exact lookup DB ────────────────────────────────────────────────────────
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
print(f"   Saved {len(db_list)} records.")

# ── 3. Features ───────────────────────────────────────────────────────────────
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

print("▶ Engineering features...")
X_cin = np.array([cin_features(c) for c in df["CIN Number"]])
X_pan = np.array([pan_features(p) for p in df["PAN Number"]])
X     = np.hstack([X_cin, X_pan])  # 13 features

le = LabelEncoder()
y  = le.fit_transform(df["Sector"])

scaler  = StandardScaler()
X_sc    = scaler.fit_transform(X)

# ── 4. Supervised — Random Forest ─────────────────────────────────────────────
print("▶ Training Random Forest...")
rf = RandomForestClassifier(
    n_estimators=500, max_depth=None, min_samples_leaf=1,
    random_state=42, class_weight="balanced", n_jobs=-1)

# Use LeaveOneOut-like CV for small dataset
from sklearn.model_selection import LeaveOneOut
loo = LeaveOneOut()
preds, trues = [], []
for tr_idx, te_idx in loo.split(X_sc):
    rf_tmp = RandomForestClassifier(n_estimators=100, random_state=42, class_weight="balanced")
    rf_tmp.fit(X_sc[tr_idx], y[tr_idx])
    preds.append(rf_tmp.predict(X_sc[[te_idx[0]]])[0])
    trues.append(y[te_idx[0]])

rf_acc = accuracy_score(trues, preds)
print(f"   LOO Accuracy: {rf_acc*100:.1f}%")

# Fit final RF on all data
rf.fit(X_sc, y)
in_sample_acc = accuracy_score(y, rf.predict(X_sc))
print(f"   In-sample accuracy: {in_sample_acc*100:.1f}%")

# ── 5. Unsupervised — IsoForest + KMeans ──────────────────────────────────────
print("▶ Training IsoForest + KMeans...")
k = min(df["Sector"].nunique(), max(3, len(df)//6))
km  = KMeans(n_clusters=k, random_state=42, n_init=15)
km.fit(X_sc)

iso = IsolationForest(n_estimators=300, contamination=0.04, random_state=42)
iso.fit(X_sc)
n_anom = (iso.predict(X_sc) == -1).sum()
print(f"   KMeans k={k}  |  Anomalies flagged: {n_anom}")

# ── 6. Deep Learning — ANN ───────────────────────────────────────────────────
dl_available = False
dl_acc = 0.0
try:
    import tensorflow as tf
    from tensorflow import keras

    print("▶ Training ANN (Deep Learning)...")
    n_cls = len(le.classes_)
    y_cat = keras.utils.to_categorical(y, n_cls)

    def build_model(input_dim, n_cls):
        inp = keras.Input(shape=(input_dim,))
        x   = keras.layers.Dense(256, activation='relu')(inp)
        x   = keras.layers.BatchNormalization()(x)
        x   = keras.layers.Dropout(0.35)(x)
        x   = keras.layers.Dense(128, activation='relu')(x)
        x   = keras.layers.BatchNormalization()(x)
        x   = keras.layers.Dropout(0.25)(x)
        x   = keras.layers.Dense(64, activation='relu')(x)
        out = keras.layers.Dense(n_cls, activation='softmax')(x)
        return keras.Model(inp, out)

    # K-Fold cross-validation for DNN
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    fold_accs = []
    for fold, (tr, te) in enumerate(skf.split(X_sc, y)):
        m = build_model(X_sc.shape[1], n_cls)
        m.compile('adam', 'categorical_crossentropy', ['accuracy'])
        m.fit(X_sc[tr], y_cat[tr], epochs=60, batch_size=16, verbose=0,
              callbacks=[keras.callbacks.EarlyStopping(patience=8, restore_best_weights=True)])
        _, vacc = m.evaluate(X_sc[te], y_cat[te], verbose=0)
        fold_accs.append(vacc)
        print(f"   Fold {fold+1}: {vacc*100:.1f}%")

    dl_acc = float(np.mean(fold_accs))
    print(f"   DNN 5-Fold mean accuracy: {dl_acc*100:.1f}%")

    # Final model trained on all data
    final_model = build_model(X_sc.shape[1], n_cls)
    final_model.compile('adam', 'categorical_crossentropy', ['accuracy'])
    final_model.fit(X_sc, y_cat, epochs=80, batch_size=16, verbose=0,
                    callbacks=[keras.callbacks.EarlyStopping(patience=10, restore_best_weights=True)])
    dl_path = os.path.join(OUT_DIR, "dnn_model.keras")
    final_model.save(dl_path)
    dl_available = True
    print(f"   Saved DNN → {dl_path}")
except Exception as e:
    print(f"   [WARN] TF/Keras not available — skipping DNN: {e}")

# ── 7. Save artefacts ─────────────────────────────────────────────────────────
print("▶ Saving artefacts...")
with open(os.path.join(OUT_DIR, "rf_model.pkl"),   "wb") as f: pickle.dump(rf,     f)
with open(os.path.join(OUT_DIR, "iso_forest.pkl"), "wb") as f: pickle.dump(iso,    f)
with open(os.path.join(OUT_DIR, "kmeans.pkl"),     "wb") as f: pickle.dump(km,     f)
with open(os.path.join(OUT_DIR, "scaler.pkl"),     "wb") as f: pickle.dump(scaler, f)
with open(os.path.join(OUT_DIR, "label_enc.pkl"),  "wb") as f: pickle.dump(le,     f)

meta = {
    "n_companies":    len(df),
    "n_sectors":      int(df["Sector"].nunique()),
    "n_features":     int(X_sc.shape[1]),
    "rf_loo_acc":     round(rf_acc, 4),
    "rf_in_sample":   round(in_sample_acc, 4),
    "dl_cv_acc":      round(dl_acc, 4),
    "dl_available":   dl_available,
    "n_anom":         int(n_anom),
    "sectors":        list(le.classes_),
    "feature_names":  ["cin_listing","cin_nic","cin_state","cin_year","cin_type",
                       "cin_serial","cin_valid","cin_regex","pan_entity","pan_alpha",
                       "pan_digits","pan_last","pan_valid"],
}
with open(os.path.join(OUT_DIR, "model_metadata.json"), "w") as f:
    json.dump(meta, f, indent=2)

print("\n✅ Training complete!")
print(json.dumps(meta, indent=2))
