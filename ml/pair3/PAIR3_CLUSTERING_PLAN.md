# Pair 3: Profile Attack Types (Clustering) — Execution Plan

## Objective
Group the **11,743 anomaly rows** from the Kaggle "Network Intrusion Detection" dataset into attack families (floods, scans, brute-force, etc.) so analysts can understand what kind of attack they're facing. Map each cluster to a MITRE ATT&CK technique as a hypothesis.

---

## 1. Dataset Acquisition (Required First Step)

The Kaggle dataset is **not in the repo**. Download it before starting:

```bash
cd /home/dridi/HoneyBadger

# Option A: Using kagglehub (recommended, works in Colab/local)
python -c "
import kagglehub
path = kagglehub.dataset_download('sampadab17/network-intrusion-detection')
print(f'Downloaded to: {path}')
import shutil
for f in ['Train_data.csv', 'Test_data.csv']:
    shutil.copy(f'{path}/{f}', f'/home/dridi/HoneyBadger/{f}')
    print(f'Copied {f}')
"

# Option B: Direct download (if kagglehub unavailable)
# wget -O dataset.zip "https://www.kaggle.com/api/v1/datasets/download/sampadab17/network-intrusion-detection"
# unzip dataset.zip
```

**Expected files after download:**
- `Train_data.csv` — 25,192 rows, 41 features + `class` label (13,449 normal, 11,743 anomaly)
- `Test_data.csv` — 22,544 rows, 41 features, no labels

**Verify checksums** (from the notebook):
- `Train_data.csv`: SHA256 `1e40eb667611ab507870fc5b5ef0a844201ec094915d78d79f4665937e43b07a`, 2,875,560 bytes
- `Test_data.csv`: SHA256 `a58db8c605e58411f6432dd9ab2fe10e1d768f058f5453e9e279788c7219caf8`, 2,416,180 bytes

---

## 2. Data Preparation (Member A)

### 2.1 Load and Filter
```python
import pandas as pd
import numpy as np

train = pd.read_csv('Train_data.csv')
# Use ONLY anomaly rows for clustering
anomalies = train[train['class'] == 'anomaly'].copy()
print(f"Anomaly rows: {len(anomalies)}")  # Should be 11,743

# Drop the label column and constant columns
features = [c for c in anomalies.columns if c not in ['class', 'num_outbound_cmds', 'is_host_login']]
X = anomalies[features]
```

### 2.2 Preprocessing Pipeline
```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.decomposition import PCA

categorical = ['protocol_type', 'service', 'flag']
numeric = [c for c in features if c not in categorical]

# Skewed numeric features → log1p → StandardScaler
skewed = ['duration', 'src_bytes', 'dst_bytes']  # Add others if highly skewed

preprocess = ColumnTransformer([
    ('cat', OneHotEncoder(handle_unknown='ignore'), categorical),
    ('num_skewed', Pipeline([('log', FunctionTransformer(np.log1p)), ('scale', StandardScaler())]), skewed),
    ('num_regular', StandardScaler(), [c for c in numeric if c not in skewed])
], remainder='passthrough')

X_processed = preprocess.fit_transform(X)
```

### 2.3 PCA for Visualization & Optional Dimensionality Reduction
```python
# For 2D visualization
pca_2d = PCA(n_components=2, random_state=42)
X_2d = pca_2d.fit_transform(X_processed.toarray() if hasattr(X_processed, 'toarray') else X_processed)

# For clustering: keep components explaining ~95% variance
pca_95 = PCA(n_components=0.95, random_state=42)
X_pca = pca_95.fit_transform(X_processed.toarray() if hasattr(X_processed, 'toarray') else X_processed)
print(f"PCA components for 95% variance: {pca_95.n_components_}")
```

### 2.4 Service Grouping (Reduce Cardinality)
- `service` has many rare values → group infrequent ones into `"other"` (threshold: < 100 occurrences)
- This limits one-hot columns and improves clustering stability

---

## 3. Modeling & Evaluation (Member B)

### 3.1 K-Means
```python
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score

# Elbow method + silhouette to choose k
inertias = []
silhouettes = []
K_range = range(2, 15)

for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_pca)
    inertias.append(km.inertia_)
    # Sample for speed (silhouette is O(n^2))
    sample_idx = np.random.choice(len(X_pca), min(5000, len(X_pca)), replace=False)
    sil = silhouette_score(X_pca[sample_idx], labels[sample_idx])
    silhouettes.append(sil)

# Choose k at elbow + high silhouette
```

### 3.2 Gaussian Mixture Model (GMM)
```python
from sklearn.mixture import GaussianMixture

# Try same k range, use BIC/AIC for selection
bics = []
for k in K_range:
    gmm = GaussianMixture(n_components=k, random_state=42, n_init=5)
    gmm.fit(X_pca)
    bics.append(gmm.bic(X_pca))
# Lowest BIC = best k
```

### 3.3 DBSCAN
```python
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors

# Estimate eps via k-distance plot (k = n_components + 1)
neighbors = NearestNeighbors(n_neighbors=pca_95.n_components_ + 1)
neighbors_fit = neighbors.fit(X_pca)
distances, _ = neighbors_fit.kneighbors(X_pca)
distances = np.sort(distances[:, -1])
# Plot distances to find "knee" → eps

# Run DBSCAN
dbscan = DBSCAN(eps=chosen_eps, min_samples=pca_95.n_components_ + 1)
db_labels = dbscan.fit_predict(X_pca)
n_clusters = len(set(db_labels)) - (1 if -1 in db_labels else 0)
n_outliers = np.sum(db_labels == -1)
```

### 3.4 Stability Analysis (Required)
```python
# Rerun best model with different seeds, compute Adjusted Rand Index
from sklearn.metrics import adjusted_rand_index

base_labels = best_model.fit_predict(X_pca)
ari_scores = []
for seed in range(10):
    model = type(best_model)(**best_model.get_params(), random_state=seed)
    labels = model.fit_predict(X_pca)
    ari_scores.append(adjusted_rand_index(base_labels, labels))
print(f"Stability (ARI): mean={np.mean(ari_scores):.3f}, std={np.std(ari_scores):.3f}")
```

### 3.5 Metrics to Report
| Metric | Purpose |
|--------|---------|
| **Silhouette Score** (sampled) | Cohesion vs separation |
| **Davies-Bouldin** | Lower = better separation |
| **Calinski-Harabasz** | Higher = better defined clusters |
| **Stability (ARI across seeds)** | Robustness of cluster assignment |
| **Cluster sizes** | Distribution, detect degenerate clusters |

---

## 4. Interpretation & MITRE ATT&CK Mapping

### 4.1 Profile Each Cluster
For each cluster, compute mean/median of key features:
```python
cluster_profiles = anomalies.assign(cluster=best_labels).groupby('cluster').agg({
    'duration': 'median', 'src_bytes': 'median', 'dst_bytes': 'median',
    'flag': lambda x: x.mode().iloc[0], 'service': lambda x: x.mode().iloc[0],
    'protocol_type': lambda x: x.mode().iloc[0],
    'count': 'median', 'srv_count': 'median', 'serror_rate': 'mean',
    'rerror_rate': 'mean', 'same_srv_rate': 'mean', 'diff_srv_rate': 'mean',
    'dst_host_count': 'median', 'dst_host_srv_count': 'median',
    'dst_host_same_srv_rate': 'mean', 'dst_host_diff_srv_rate': 'mean',
    'num_failed_logins': 'median', 'logged_in': 'mean',
    'is_guest_login': 'mean', 'num_compromised': 'median',
    'root_shell': 'mean', 'su_attempted': 'mean', 'num_root': 'median',
    'num_file_creations': 'median', 'num_shells': 'median',
    'num_access_files': 'median', 'num_outbound_cmds': 'median',
    'is_host_login': 'mean', 'hot': 'median', 'num_failed_logins': 'median'
})
```

### 4.2 Hypothesis Mapping to MITRE ATT&CK
| Cluster Profile | Likely Attack Type | MITRE Technique (Hypothesis) |
|-----------------|-------------------|------------------------------|
| High `serror_rate`, flag `S0`, many `count`/`srv_count` | SYN Flood / DoS | **T1499** (Endpoint DoS) / **T1498** (Network DoS) |
| High `num_failed_logins`, low `logged_in`, SSH/HTTP service | Brute Force / Credential Stuffing | **T1110** (Brute Force) / **T1110.004** (Credential Stuffing) |
| Many distinct `service` from one source, low bytes | Port/Service Scanning | **T1595** (Active Scanning) / **T1046** (Network Service Scanning) |
| High `root_shell`, `su_attempted`, `num_shells` | Exploit / Privilege Escalation | **T1190** (Exploit Public-Facing App) / **T1068** (Exploitation for Privilege Escalation) |
| High `num_file_creations`, `num_access_files` | Payload Deployment / Tool Transfer | **T1105** (Ingress Tool Transfer) / **T1059** (Command & Scripting) |

**Critical Disclaimer**: The dataset has **no attack-type labels**. This mapping is a *hypothesis* based on feature patterns, not ground truth. State this clearly in presentations.

---

## 5. Visualization Deliverables

1. **PCA 2D scatter** colored by cluster (matplotlib/seaborn)
2. **Elbow plot** (inertia vs k) + **Silhouette vs k**
3. **BIC/AIC curves** for GMM
4. **Cluster profile heatmap** (features × clusters, normalized)
5. **DBSCAN outlier count** if applicable
6. **Stability boxplot** (ARI across seeds)

---

## 6. Connection to HoneyBadger

### How This Relates to the Honeypot
- HoneyBadger captures **SSH (port 8022)** and **HTTP (port 8081)** attacks
- The Kaggle dataset has **58 SSH rows (all anomaly)** and **8,003 HTTP rows (7,564 normal, 439 anomaly)**
- Cluster profiles using `service`, `num_failed_logins`, `logged_in`, `count`, `srv_count`, `dst_host_*` counts are the closest overlap

### Features HoneyBadger Can Actually Compute
| Kaggle Feature | HoneyBadger Equivalent |
|----------------|------------------------|
| `service` | `RawEvent.service` (`ssh`/`http`) |
| `num_failed_logins` | Derived from `login_info` + `technique_id` (T1110) |
| `logged_in` | SSH always accepts; HTTP login POST → `technique_id` T1078 contextual |
| `count`, `srv_count` | Aggregations on `source_ip` + time windows (not stored, computable) |
| `dst_host_*` counts | Not captured (no server-side view) |
| `flag`, `serror_rate`, TCP fields | **Not captured** (SSH sensor only gets client version) |
| `duration`, `src_bytes`, `dst_bytes` | **Not captured** |

**Conclusion**: A model trained on full Kaggle features **cannot be directly applied** to HoneyBadger events. The clustering exercise validates the *approach* (grouping by behavioral patterns), not a deployable model.

---

## 7. Work Split (Per Project Plan)

| Member | Responsibility |
|--------|----------------|
| **Member A** | Data prep: load, filter anomalies, preprocessing (log1p, scaling, encoding, PCA), service grouping, justification doc |
| **Member B** | Modeling: K-Means (elbow/silhouette), GMM (BIC), DBSCAN (eps selection), stability analysis, metrics computation |
| **Both** | Interpretation: cluster profiles, MITRE mapping hypothesis, visualizations, slides, joint Q&A prep |

---

## 8. Reproducibility Checklist

- [ ] `random_state = 42` everywhere (KMeans, GMM, PCA, train/test splits)
- [ ] Same validation fold as notebook (`grouped_stratified_folds`, fold 0) — **but for clustering we use ALL anomaly rows, no holdout needed**
- [ ] Encoders/scalers fit on anomaly subset only
- [ ] Constant columns dropped (`num_outbound_cmds`, `is_host_login`)
- [ ] No `class` column used as feature
- [ ] Silhouette computed on sample (≤5000) for speed
- [ ] Stability tested with ≥10 seeds
- [ ] All visualizations saved as PNG + code in notebook

---

## 9. Timeline Estimate

| Phase | Duration |
|-------|----------|
| Dataset download & verification | 15 min |
| Data prep & preprocessing | 1–2 hours |
| K-Means + elbow/silhouette | 1 hour |
| GMM + BIC/AIC | 1 hour |
| DBSCAN + eps tuning | 1 hour |
| Stability analysis | 30 min |
| Cluster profiling & MITRE mapping | 1–2 hours |
| Visualizations & slides | 1–2 hours |
| **Total** | **~6–9 hours** |

---

## 10. Files to Produce

1. `pair3_clustering.ipynb` — Complete notebook with all code, outputs, visualizations
2. `pair3_cluster_profiles.csv` — Cluster feature summaries
3. `pair3_mitre_mapping.md` — Hypothesis mapping table with justification
4. `pair3_slides.pdf` — 5–7 slides: objective, data prep, method, results, interpretation, limitations, HoneyBadger relevance

---

## 11. Key References

- **Project Plan**: `/home/dridi/HoneyBadger/honeybadger_machine_learning_project_plan.md` (Pair 3 section)
- **Notebook**: `/home/dridi/HoneyBadger/intrusion_analysis.ipynb` (data loading, validation design, feature descriptions)
- **Kaggle Dataset**: https://www.kaggle.com/datasets/sampadab17/network-intrusion-detection
- **MITRE ATT&CK**: https://attack.mitre.org/techniques/enterprise/