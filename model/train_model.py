"""
model/train_model.py — TriageAI GradientBoosting Training Pipeline
===================================================================
Trains a GradientBoostingClassifier to predict patient deterioration risk.

Binary classification task:
  LABEL = 1  →  patient's risk will exceed 7.5 within 60 minutes
  LABEL = 0  →  patient remains stable

The trained model bundle is saved to model/triage_model.pkl and loaded
by rescorer.ModelManager at app startup.

Pipeline:
  1. Generate synthetic training dataset (5000 patients × 15 features)
  2. Engineer additional features (interaction terms, flag columns)
  3. Split train/val/test (70/15/15)
  4. Grid-search hyperparameters with StratifiedKFold cross-validation
  5. Train final GradientBoostingClassifier on full train+val set
  6. Evaluate on held-out test set (precision / recall / F1 / AUC)
  7. Compute global SHAP feature importance summary
  8. Save model bundle (model + scaler + feature names + metadata) → pickle

Run this script once before starting app.py:
  (venv) $ python -m model.train_model


"""

import os
import sys
import pickle
import warnings
import time
from pathlib import Path
from datetime import datetime

import numpy as np

# ── Scikit-learn imports ──────────────────────────────────────
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    cross_val_score,
    GridSearchCV,
)
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score,
    precision_recall_curve,
    average_precision_score,
    f1_score,
)
from sklearn.pipeline import Pipeline

warnings.filterwarnings("ignore")

# ── Project imports ───────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from data.generate_data import (
    generate_training_dataset,
    generate_random_patients,
    generate_demo_patients,
    patient_to_features,
    FEATURE_NAMES,
    SYMPTOM_CATEGORIES,
)
from engine.scorer import compute_training_label, ALERT_THRESHOLD

MODEL_DIR  = PROJECT_ROOT / "model"
MODEL_PATH = MODEL_DIR / "triage_model.pkl"


# ─────────────────────────────────────────────────────────────
# 1. Feature Engineering
# ─────────────────────────────────────────────────────────────

ENGINEERED_FEATURE_NAMES = FEATURE_NAMES + [
    # Interaction features — these are what give GBM an edge over rule-based
    "age_x_time",            # elderly patients × long wait = compounding risk
    "vitals_x_time",         # worsening vitals × wait time
    "age_x_vitals",          # elderly + bad vitals = very high risk
    "hr_bp_ratio",           # tachycardia + hypotension = shock index proxy
    "spo2_rr_risk",          # low O2 + high RR = respiratory failure signal
    "fever_flag",            # binary: temp > 100.4°F
    "hypotension_flag",      # binary: SBP < 90
    "tachycardia_flag",      # binary: HR > 100
    "hypoxia_flag",          # binary: SpO2 < 94
    "gcs_impaired_flag",     # binary: GCS < 15
    "high_risk_category_flag", # binary: category in high-risk set
    "combined_shock_score",  # HR/SBP ratio (modified shock index)
]


def engineer_features(X_raw: list, feature_names: list = FEATURE_NAMES) -> np.ndarray:
    """
    Augment the base 15-feature vector with 12 additional engineered features.
    
    Input:  X_raw — list of base feature vectors (n_samples × 15)
    Output: np.ndarray of shape (n_samples × 27)
    
    Interaction and flag features are the bridge between clinical intuition
    and ML signal: the GBM can learn that the combination of elderly + bad
    vitals + long wait is worse than any individual factor alone.
    """
    X = np.array(X_raw, dtype=float)

    idx = {name: i for i, name in enumerate(feature_names)}

    age         = X[:, idx["age"]]
    vitals_s    = X[:, idx["vitals_score"]]
    minutes     = X[:, idx["minutes_in_ed"]]
    hr          = X[:, idx["heart_rate"]]
    sbp         = X[:, idx["bp_systolic"]]
    spo2        = X[:, idx["spo2"]]
    rr          = X[:, idx["respiratory_rate"]]
    temp        = X[:, idx["temperature"]]
    gcs         = X[:, idx["gcs"]]
    base_risk   = X[:, idx["base_risk"]]

    # ── Interaction terms ──────────────────────────────────────
    age_x_time    = (age / 100.0) * (minutes / 120.0) * 10.0   # normalized
    vitals_x_time = vitals_s * (minutes / 60.0)
    age_x_vitals  = (age / 100.0) * vitals_s

    # ── Shock index proxy (HR / SBP) ──────────────────────────
    # Normal < 0.7. Shock index > 1.0 = high mortality risk.
    hr_bp_ratio = np.where(sbp > 0, hr / np.maximum(sbp, 1), 2.0)

    # ── Respiratory failure signal ─────────────────────────────
    # Low SpO2 + high RR = impending respiratory failure. Nonlinear interaction.
    spo2_norm  = np.clip((100 - spo2) / 15.0, 0, 1)   # 0=normal, 1=critical
    rr_norm    = np.clip((rr - 12) / 28.0, 0, 1)       # 0=normal, 1=critical
    spo2_rr_risk = spo2_norm * rr_norm * 10.0

    # ── Binary flag features (clinical decision rules) ─────────
    fever_flag          = (temp > 100.4).astype(float)
    hypotension_flag    = (sbp < 90).astype(float)
    tachycardia_flag    = (hr > 100).astype(float)
    hypoxia_flag        = (spo2 < 94).astype(float)
    gcs_impaired_flag   = (gcs < 15).astype(float)

    # High-risk category: base_risk > 6.0
    high_risk_category_flag = (base_risk > 6.0).astype(float)

    # ── Modified shock index (MSI = HR / (2 × SBP)) ───────────
    combined_shock_score = np.where(
        sbp > 0,
        hr / np.maximum(2.0 * sbp, 1),
        2.0
    )

    # ── Stack all engineered features ─────────────────────────
    engineered = np.column_stack([
        X,                     # original 15 features
        age_x_time,            # 16
        vitals_x_time,         # 17
        age_x_vitals,          # 18
        hr_bp_ratio,           # 19
        spo2_rr_risk,          # 20
        fever_flag,            # 21
        hypotension_flag,      # 22
        tachycardia_flag,      # 23
        hypoxia_flag,          # 24
        gcs_impaired_flag,     # 25
        high_risk_category_flag, # 26
        combined_shock_score,  # 27
    ])

    return engineered


# ─────────────────────────────────────────────────────────────
# 2. Extended Dataset Generator
# ─────────────────────────────────────────────────────────────

def generate_extended_dataset(
    n_base: int = 5000,
    n_augmented: int = 2000,
    random_state: int = 42,
) -> tuple:
    """
    Build a rich training dataset with:
      - n_base synthetic patients from generate_training_dataset()
      - n_augmented patients at various stages of their ED stay
      - Deliberate over-sampling of high-acuity (positive class) cases
        to address class imbalance (deterioration is rarer than stability)

    Returns:
      X (np.ndarray), y (np.ndarray), feature_names (list)
    """
    np.random.seed(random_state)

    print(f"[DataGen] Generating {n_base} base samples...")
    X_base, y_base, names = generate_training_dataset(n_base)

    # ── Augmented samples: patients deep into their ED stay ───
    print(f"[DataGen] Generating {n_augmented} augmented (late-stay) samples...")
    X_aug, y_aug = [], []
    from data.generate_data import generate_patient
    import random

    for _ in range(n_augmented):
        # Bias toward longer waits (60–180 min) — where deterioration happens
        minutes_waited = random.choices(
            [random.randint(60, 120), random.randint(90, 180), random.randint(10, 60)],
            weights=[0.5, 0.3, 0.2], k=1
        )[0]

        p = generate_patient(arrival_minutes_ago=minutes_waited)
        feats = patient_to_features(p)
        label = compute_training_label(p, horizon_minutes=60)
        X_aug.append(feats)
        y_aug.append(label)

    # ── Combine ───────────────────────────────────────────────
    X_all = np.array(X_base + X_aug, dtype=float)
    y_all = np.array(y_base + y_aug, dtype=int)

    pos_rate = y_all.sum() / len(y_all) * 100
    print(f"[DataGen] Total samples: {len(X_all)} | "
          f"Positive (deterioration): {y_all.sum()} ({pos_rate:.1f}%)")

    # ── Feature engineering ───────────────────────────────────
    print("[DataGen] Engineering interaction features...")
    X_engineered = engineer_features(X_all.tolist())

    return X_engineered, y_all, ENGINEERED_FEATURE_NAMES


# ─────────────────────────────────────────────────────────────
# 3. Hyperparameter Grid
# ─────────────────────────────────────────────────────────────

# Fast grid for hackathon demo — good enough, not exhaustive.
# GBM key knobs: n_estimators (more = better but slower), learning_rate
# (lower + more estimators = better generalisation), max_depth (3-5 is sweet spot).
PARAM_GRID = {
    "n_estimators":  [100, 200, 300],
    "learning_rate": [0.05, 0.10, 0.15],
    "max_depth":     [3, 4, 5],
    "min_samples_split": [10, 20],
    "subsample":     [0.8, 1.0],    # stochastic GBM — helps generalisation
}

# Best params found from prior experimentation (used as default for speed)
BEST_PARAMS_DEFAULT = {
    "n_estimators":    200,
    "learning_rate":   0.10,
    "max_depth":       4,
    "min_samples_split": 15,
    "subsample":       0.85,
    "max_features":    "sqrt",   # random subset of features per split
    "random_state":    42,
    "n_iter_no_change": 15,      # early stopping on validation loss
    "validation_fraction": 0.1,
    "tol":             1e-4,
}


# ─────────────────────────────────────────────────────────────
# 4. Training Function
# ─────────────────────────────────────────────────────────────

def train(
    n_samples: int = 7000,
    run_grid_search: bool = False,   # set True for full optimization (slower)
    verbose: bool = True,
) -> dict:
    """
    Full training pipeline. Returns the model bundle dict.

    Args:
        n_samples:       Total training samples (base + augmented)
        run_grid_search: If True, run 5-fold CV grid search (takes ~3-5 min)
        verbose:         Print progress and metrics

    Returns:
        bundle: {
            "model":          trained GradientBoostingClassifier,
            "scaler":         fitted StandardScaler,
            "feature_names":  list of feature names,
            "metrics":        {accuracy, auc, f1, ...},
            "feature_importance": dict of feature → importance,
            "trained_at":     ISO timestamp,
            "n_train_samples": int,
            "params":         model hyperparameters,
        }
    """
    t0 = time.time()

    # ── Step 1: Generate data ─────────────────────────────────
    n_base = int(n_samples * 0.7)
    n_aug  = int(n_samples * 0.3)
    X, y, feature_names = generate_extended_dataset(n_base=n_base, n_augmented=n_aug)

    # ── Step 2: Train / val / test split ─────────────────────
    # Stratified to preserve class ratio in all splits
    X_trainval, X_test, y_trainval, y_test = train_test_split(
        X, y, test_size=0.15, stratify=y, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_trainval, y_trainval, test_size=0.15/(1-0.15), stratify=y_trainval, random_state=42
    )

    if verbose:
        print(f"\n[Train] Dataset split:")
        print(f"  Train:      {len(X_train):5d} samples ({y_train.sum():4d} positive)")
        print(f"  Validation: {len(X_val):5d} samples ({y_val.sum():4d} positive)")
        print(f"  Test:       {len(X_test):5d} samples ({y_test.sum():4d} positive)")

    # ── Step 3: Scale features ────────────────────────────────
    # GBM is tree-based and doesn't strictly need scaling, but it helps
    # when features have very different magnitudes (age 1-100 vs rate 0.005-0.15)
    scaler = StandardScaler()
    X_train_sc  = scaler.fit_transform(X_train)
    X_val_sc    = scaler.transform(X_val)
    X_test_sc   = scaler.transform(X_test)

    # ── Step 4: Class weight for imbalanced labels ────────────
    # Positive class (deterioration) is typically 30-40% — not extreme,
    # but weighting helps precision, which matters in clinical context
    # (false positives = unnecessary escalation; false negatives = death).
    pos_count = y_train.sum()
    neg_count = len(y_train) - pos_count
    class_weight_pos = neg_count / max(pos_count, 1)  # upweight positives

    if verbose:
        print(f"\n[Train] Class balance: {pos_count} pos / {neg_count} neg | "
              f"pos_weight = {class_weight_pos:.2f}")

    # ── Step 5: Grid search or use defaults ───────────────────
    if run_grid_search:
        if verbose:
            print(f"\n[Train] Running GridSearchCV (this takes a few minutes)...")

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        base_model = GradientBoostingClassifier(
            random_state=42,
            subsample=0.85,
        )
        grid = GridSearchCV(
            base_model,
            PARAM_GRID,
            cv=cv,
            scoring="roc_auc",
            n_jobs=-1,     # use all CPU cores
            verbose=1 if verbose else 0,
            refit=True,
        )
        grid.fit(X_train_sc, y_train)
        best_params = grid.best_params_
        model = grid.best_estimator_

        if verbose:
            print(f"[Train] Best params: {best_params}")
            print(f"[Train] Best CV AUC: {grid.best_score_:.4f}")
    else:
        # Use pre-validated best params for demo speed
        if verbose:
            print(f"\n[Train] Using pre-validated hyperparameters (skip grid search)...")

        model = GradientBoostingClassifier(**BEST_PARAMS_DEFAULT)
        model.fit(
            X_train_sc,
            y_train,
            # Pass val set for early stopping monitor
        )
        best_params = BEST_PARAMS_DEFAULT

    # ── Step 6: Cross-validation on training set ──────────────
    if verbose:
        print("\n[Train] 5-fold cross-validation on training set...")

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_auc_scores = cross_val_score(
        GradientBoostingClassifier(**BEST_PARAMS_DEFAULT),
        X_train_sc, y_train, cv=cv, scoring="roc_auc", n_jobs=-1
    )
    cv_f1_scores = cross_val_score(
        GradientBoostingClassifier(**BEST_PARAMS_DEFAULT),
        X_train_sc, y_train, cv=cv, scoring="f1", n_jobs=-1
    )

    if verbose:
        print(f"  AUC:  {cv_auc_scores.mean():.4f} ± {cv_auc_scores.std():.4f}")
        print(f"  F1:   {cv_f1_scores.mean():.4f} ± {cv_f1_scores.std():.4f}")

    # ── Step 7: Retrain on full train+val set ─────────────────
    # Standard practice: once hyperparams are chosen, retrain on all available data
    if verbose:
        print(f"\n[Train] Retraining on train+val combined ({len(X_trainval)} samples)...")

    X_trainval_sc = scaler.transform(X_trainval)
    final_model = GradientBoostingClassifier(**best_params)
    final_model.fit(X_trainval_sc, y_trainval)

    # ── Step 8: Test set evaluation ───────────────────────────
    if verbose:
        print("\n[Eval] Test set evaluation:")

    y_pred_proba = final_model.predict_proba(X_test_sc)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)

    auc   = roc_auc_score(y_test, y_pred_proba)
    ap    = average_precision_score(y_test, y_pred_proba)
    f1    = f1_score(y_test, y_pred)
    acc   = (y_pred == y_test).mean()
    cm    = confusion_matrix(y_test, y_pred)

    tn, fp, fn, tp = cm.ravel()
    sensitivity = tp / max(tp + fn, 1)    # recall for positive class (critical: catches deteriorations)
    specificity = tn / max(tn + fp, 1)    # recall for negative class (avoids false alarms)
    ppv         = tp / max(tp + fp, 1)    # precision for positive class

    metrics = {
        "test_auc":        round(auc, 4),
        "test_ap":         round(ap, 4),
        "test_f1":         round(f1, 4),
        "test_accuracy":   round(acc, 4),
        "sensitivity":     round(sensitivity, 4),   # true positive rate
        "specificity":     round(specificity, 4),   # true negative rate
        "ppv":             round(ppv, 4),
        "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        "cv_auc_mean":     round(cv_auc_scores.mean(), 4),
        "cv_auc_std":      round(cv_auc_scores.std(), 4),
        "cv_f1_mean":      round(cv_f1_scores.mean(), 4),
        "n_test_samples":  len(X_test),
    }

    if verbose:
        print(f"  AUC-ROC:       {auc:.4f}")
        print(f"  Avg Precision: {ap:.4f}")
        print(f"  F1 Score:      {f1:.4f}")
        print(f"  Accuracy:      {acc:.4f}")
        print(f"  Sensitivity:   {sensitivity:.4f}  (catches {tp}/{tp+fn} deteriorations)")
        print(f"  Specificity:   {specificity:.4f}  (avoids {tn}/{tn+fp} false alarms)")
        print(f"  PPV:           {ppv:.4f}  (precision of positive class)")
        print(f"\n  Confusion Matrix:")
        print(f"             Predicted")
        print(f"             Stable  Detn")
        print(f"  True Stable  {tn:5d}  {fp:4d}")
        print(f"  True Detn    {fn:5d}  {tp:4d}")
        print(f"\n{classification_report(y_test, y_pred, target_names=['Stable', 'Deterioration'])}")

    # ── Step 9: Feature importance ────────────────────────────
    importances  = final_model.feature_importances_
    feat_importance = dict(sorted(
        zip(feature_names, importances),
        key=lambda x: x[1],
        reverse=True,
    ))

    if verbose:
        print("  Top 10 Feature Importances:")
        for feat, imp in list(feat_importance.items())[:10]:
            bar = "█" * int(imp * 200)
            print(f"    {feat:30s}: {imp:.4f}  {bar}")

    # ── Step 10: SHAP global summary ─────────────────────────
    shap_summary = None
    try:
        import shap
        if verbose:
            print("\n[SHAP] Computing global feature importance (TreeExplainer)...")

        explainer = shap.TreeExplainer(final_model)

        # Use a sample of test set for SHAP summary (full set is slow)
        sample_size = min(300, len(X_test_sc))
        X_shap = X_test_sc[:sample_size]
        shap_values = explainer.shap_values(X_shap)

        # For binary GBM, shap_values is a list [class0, class1]; use class1
        if isinstance(shap_values, list):
            shap_vals_class1 = shap_values[1]
        else:
            shap_vals_class1 = shap_values

        # Mean |SHAP| per feature = global importance
        mean_abs_shap = np.abs(shap_vals_class1).mean(axis=0)
        shap_summary = dict(sorted(
            zip(feature_names, mean_abs_shap),
            key=lambda x: x[1],
            reverse=True,
        ))

        if verbose:
            print("  Top 10 SHAP Feature Importances (mean |SHAP value|):")
            for feat, sv in list(shap_summary.items())[:10]:
                bar = "█" * int(sv * 500)
                print(f"    {feat:30s}: {sv:.4f}  {bar}")

    except ImportError:
        if verbose:
            print("[SHAP] ⚠️  SHAP not installed. pip install shap — skipping SHAP summary.")
    except Exception as e:
        if verbose:
            print(f"[SHAP] ⚠️  SHAP computation failed: {e}")

    elapsed = time.time() - t0

    # ── Step 11: Assemble bundle ──────────────────────────────
    bundle = {
        "model":                final_model,
        "scaler":               scaler,
        "feature_names":        feature_names,
        "n_features":           len(feature_names),
        "metrics":              metrics,
        "feature_importance":   feat_importance,
        "shap_summary":         shap_summary,
        "trained_at":           datetime.now().isoformat(),
        "training_time_sec":    round(elapsed, 1),
        "n_train_samples":      len(X_trainval),
        "params":               best_params,
        "alert_threshold":      ALERT_THRESHOLD,
        "label_description":    "1=deterioration risk >7.5 in 60min, 0=stable",
    }

    return bundle


# ─────────────────────────────────────────────────────────────
# 5. Save & Load Helpers
# ─────────────────────────────────────────────────────────────

def save_model(bundle: dict, path: Path = MODEL_PATH) -> None:
    """Serialize model bundle to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(bundle, f, protocol=pickle.HIGHEST_PROTOCOL)
    size_kb = path.stat().st_size / 1024
    print(f"\n✅ Model saved → {path}  ({size_kb:.1f} KB)")


def load_model(path: Path = MODEL_PATH) -> dict:
    """Deserialize model bundle from disk. Returns bundle dict."""
    if not path.exists():
        raise FileNotFoundError(f"Model not found at {path}. Run train_model.py first.")
    with open(path, "rb") as f:
        return pickle.load(f)


# ─────────────────────────────────────────────────────────────
# 6. Model Smoke Test (validates the saved model end-to-end)
# ─────────────────────────────────────────────────────────────

def smoke_test(bundle: dict) -> bool:
    """
    Validate the saved model against the 10 demo patients.
    Ensures the model produces sensible predictions on known cases.
    Returns True if all checks pass.
    """
    print("\n[SmokeTest] Running demo patient predictions...")
    model   = bundle["model"]
    scaler  = bundle["scaler"]
    names   = bundle["feature_names"]

    demo = generate_demo_patients()
    all_pass = True

    for p in demo:
        # Build base features + engineer
        base_feats = patient_to_features(p)
        feats_eng  = engineer_features([base_feats])[0]
        feats_sc   = scaler.transform([feats_eng])[0].reshape(1, -1)

        proba = model.predict_proba(feats_sc)[0][1]
        label = 1 if proba >= 0.5 else 0

        # Sanity check: ESI-1/2 should predict deterioration, ESI-4/5 should not
        esi = p["esi_level"]
        if esi <= 2 and proba < 0.3:
            print(f"  ⚠️  FAIL: {p['name']} (ESI-{esi}) has low deterioration prob {proba:.2f}")
            all_pass = False
        elif esi >= 4 and proba > 0.7:
            print(f"  ⚠️  FAIL: {p['name']} (ESI-{esi}) has high deterioration prob {proba:.2f}")
            all_pass = False
        else:
            icon = "✅" if (proba > 0.5) == (esi <= 2) else "⚠️"
            print(
                f"  {icon} {p['name']:20s} | ESI {esi} | "
                f"Deterioration P={proba:.2f} | {'HIGH RISK' if label else 'STABLE'}"
            )

    return all_pass


# ─────────────────────────────────────────────────────────────
# 7. Threshold Calibration (for demo tuning)
# ─────────────────────────────────────────────────────────────

def find_optimal_threshold(bundle: dict, target_sensitivity: float = 0.85) -> float:
    """
    Find the probability threshold that achieves the target sensitivity.
    Higher sensitivity = catches more deteriorations (fewer missed cases).
    In ED triage, we prefer sensitivity over specificity (missing is worse than false alarm).

    Returns the optimal probability threshold (default model uses 0.5).
    """
    from data.generate_data import generate_training_dataset

    print(f"\n[Calibration] Finding threshold for sensitivity ≥ {target_sensitivity}...")

    # Generate a calibration set
    X_cal, y_cal, _ = generate_training_dataset(1000)
    X_cal_eng = engineer_features(X_cal)
    X_cal_sc  = bundle["scaler"].transform(X_cal_eng)
    y_cal = np.array(y_cal)

    y_proba = bundle["model"].predict_proba(X_cal_sc)[:, 1]

    # Sweep thresholds from strict (high threshold) to lenient (low threshold)
    # Start at 0.9 and work down to find first threshold meeting sensitivity
    best_threshold = 0.5
    thresholds_to_try = np.arange(0.9, 0.05, -0.01)

    for thresh in thresholds_to_try:
        y_pred = (y_proba >= thresh).astype(int)

        pos_mask = y_cal == 1
        neg_mask = y_cal == 0

        if pos_mask.sum() == 0 or neg_mask.sum() == 0:
            continue

        recall_pos = (y_pred[pos_mask] == 1).mean()   # sensitivity

        if recall_pos >= target_sensitivity:
            best_threshold = float(thresh)
            break

    # Final evaluation at best_threshold
    y_pred_final = (y_proba >= best_threshold).astype(int)
    pos_mask = y_cal == 1
    neg_mask = y_cal == 0

    actual_sensitivity = float((y_pred_final[pos_mask] == 1).mean()) if pos_mask.sum() > 0 else 0.0
    actual_specificity = float((y_pred_final[neg_mask] == 0).mean()) if neg_mask.sum() > 0 else 0.0
    f1 = f1_score(y_cal, y_pred_final, zero_division=0)

    print(f"  Optimal threshold: {best_threshold:.3f}")
    print(f"  Sensitivity: {actual_sensitivity:.3f} | Specificity: {actual_specificity:.3f} | F1: {f1:.3f}")

    return best_threshold



# ─────────────────────────────────────────────────────────────
# 8. Main Entry Point
# ─────────────────────────────────────────────────────────────

def main():
    print("=" * 65)
    print("  TriageAI — GradientBoosting Triage Risk Model Training")
    print("=" * 65)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Model will be saved to: {MODEL_PATH}")
    print()

    # Parse simple CLI args
    run_grid_search = "--grid-search" in sys.argv
    n_samples = 7000

    for arg in sys.argv[1:]:
        if arg.startswith("--samples="):
            try:
                n_samples = int(arg.split("=")[1])
            except ValueError:
                pass

    print(f"  Samples:     {n_samples}")
    print(f"  Grid search: {'Yes (slow)' if run_grid_search else 'No (using pre-validated params)'}")
    print()

    # ── Train ──────────────────────────────────────────────────
    bundle = train(
        n_samples=n_samples,
        run_grid_search=run_grid_search,
        verbose=True,
    )

    # ── Threshold calibration ──────────────────────────────────
    optimal_threshold = find_optimal_threshold(bundle, target_sensitivity=0.85)
    bundle["optimal_threshold"] = optimal_threshold

    # ── Save model ────────────────────────────────────────────
    save_model(bundle)

    # ── Smoke test ────────────────────────────────────────────
    print("\n[SmokeTest] Validating saved model...")
    loaded_bundle = load_model()
    all_pass = smoke_test(loaded_bundle)

    # ── Summary ───────────────────────────────────────────────
    m = bundle["metrics"]
    print("\n" + "=" * 65)
    print("  📊 Training Complete")
    print("=" * 65)
    print(f"  {'AUC-ROC:':<25} {m['test_auc']:.4f}")
    print(f"  {'Avg Precision:':<25} {m['test_ap']:.4f}")
    print(f"  {'F1 Score:':<25} {m['test_f1']:.4f}")
    print(f"  {'Sensitivity:':<25} {m['sensitivity']:.4f}  ← catches deteriorations")
    print(f"  {'Specificity:':<25} {m['specificity']:.4f}  ← avoids false alarms")
    print(f"  {'CV AUC (5-fold):':<25} {m['cv_auc_mean']:.4f} ± {m['cv_auc_std']:.4f}")
    print(f"  {'Training time:':<25} {bundle['training_time_sec']:.1f}s")
    print(f"  {'Optimal threshold:':<25} {optimal_threshold:.3f}")
    print(f"  {'Smoke test:':<25} {'✅ PASS' if all_pass else '⚠️  CHECK WARNINGS'}")
    print(f"\n  Model saved → {MODEL_PATH.name}")
    print("=" * 65)

    if all_pass:
        print("\n🚀 Model ready!")
    else:
        print("\n⚠️  Some smoke tests failed — check predictions above.")

    return bundle


if __name__ == "__main__":
    bundle = main()
