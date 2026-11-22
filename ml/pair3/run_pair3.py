#!/usr/bin/env python3
"""
Pair 3 Clustering — Quick Start Script

Run this to execute the full clustering pipeline non-interactively.
The notebook (pair3_clustering.ipynb) is for interactive exploration.
"""

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.decomposition import PCA
from sklearn.cluster import KMeans, DBSCAN
from sklearn.mixture import GaussianMixture
from sklearn.metrics import (
    silhouette_score,
    davies_bouldin_score,
    calinski_harabasz_score,
    adjusted_rand_score
)
from sklearn.neighbors import NearestNeighbors
from sklearn.pipeline import Pipeline
import json

SEED = 42
np.random.seed(SEED)

print("=" * 60)
print("PAIR 3: Profile Attack Types (Clustering)")
print("=" * 60)

# 1. Load data
print("\n[1/8] Loading data...")
train = pd.read_csv('Train_data.csv')
anomalies = train[train['class'] == 'anomaly'].copy()
print(f"    Anomaly rows: {len(anomalies):,}")

# 2. Preprocessing
print("\n[2/8] Preprocessing...")
constant_cols = ['num_outbound_cmds', 'is_host_login']
features = [c for c in anomalies.columns if c not in ['class'] + constant_cols]
X = anomalies[features].copy()

categorical = ['protocol_type', 'service', 'flag']
numeric = [c for c in features if c not in categorical]

# Group rare services
service_counts = X['service'].value_counts()
rare_services = service_counts[service_counts < 100].index.tolist()
X['service_grouped'] = X['service'].replace(rare_services, 'other')

categorical_grouped = ['protocol_type', 'service_grouped', 'flag']
numeric = [c for c in features if c not in categorical]
skewed = ['duration', 'src_bytes', 'dst_bytes']
numeric_regular = [c for c in numeric if c not in skewed]

preprocess = ColumnTransformer([
    ('cat', OneHotEncoder(handle_unknown='ignore', sparse_output=False), categorical_grouped),
    ('num_skewed', Pipeline([
        ('log', FunctionTransformer(np.log1p, validate=False)),
        ('scale', StandardScaler())
    ]), skewed),
    ('num_regular', StandardScaler(), numeric_regular)
], remainder='drop')

X_processed = preprocess.fit_transform(X)
print(f"    Processed shape: {X_processed.shape}")

# 3. PCA
print("\n[3/8] PCA dimensionality reduction...")
pca_95 = PCA(n_components=0.95, random_state=SEED)
X_pca = pca_95.fit_transform(X_processed)
print(f"    Components for 95% variance: {pca_95.n_components_}")

# 4. K-Means selection
print("\n[4/8] K-Means elbow & silhouette...")
K_range = range(2, 16)
inertias = []
silhouettes = []
sample_idx = np.random.choice(len(X_pca), min(5000, len(X_pca)), replace=False)
X_sample = X_pca[sample_idx]

for k in K_range:
    km = KMeans(n_clusters=k, random_state=SEED, n_init=10)
    labels = km.fit_predict(X_pca)
    inertias.append(km.inertia_)
    sil = silhouette_score(X_sample, labels[sample_idx])
    silhouettes.append(sil)

# Find elbow (max curvature) and best silhouette
import numpy as np
# Simple elbow: max difference in differences
diff2 = np.diff(inertias, 2)
elbow_k = K_range[np.argmax(diff2) + 2] if len(diff2) > 0 else 6
best_sil_k = K_range[np.argmax(silhouettes)]
print(f"    Elbow k: {elbow_k}, Best silhouette k: {best_sil_k}")

CHOSEN_K = elbow_k  # Use elbow method

# 5. GMM BIC
print("\n[5/8] GMM BIC selection...")
bics = []
for k in K_range:
    gmm = GaussianMixture(n_components=k, random_state=SEED, n_init=5)
    gmm.fit(X_pca)
    bics.append(gmm.bic(X_pca))
best_bic_k = K_range[np.argmin(bics)]
print(f"    Best BIC k: {best_bic_k}")

# 6. DBSCAN eps estimation
print("\n[6/8] DBSCAN eps estimation...")
k_neighbors = pca_95.n_components_ + 1
neighbors = NearestNeighbors(n_neighbors=k_neighbors).fit(X_pca)
distances, _ = neighbors.kneighbors(X_pca)
distances = np.sort(distances[:, -1])
# Use 90th percentile as eps
CHOSEN_EPS = np.percentile(distances, 90)
min_samples = k_neighbors
print(f"    k-NN distance 90th percentile (eps): {CHOSEN_EPS:.3f}")

# 7. Final models
print("\n[7/8] Running final models...")

# K-Means
kmeans = KMeans(n_clusters=CHOSEN_K, random_state=SEED, n_init=10)
km_labels = kmeans.fit_predict(X_pca)

# GMM
gmm = GaussianMixture(n_components=CHOSEN_K, random_state=SEED, n_init=5)
gmm.fit(X_pca)
gmm_labels = gmm.predict(X_pca)

# DBSCAN
dbscan = DBSCAN(eps=CHOSEN_EPS, min_samples=min_samples)
db_labels = dbscan.fit_predict(X_pca)
db_n_clusters = len(set(db_labels)) - (1 if -1 in db_labels else 0)

print(f"    K-Means: {CHOSEN_K} clusters")
print(f"    GMM:     {CHOSEN_K} clusters")
print(f"    DBSCAN:  {db_n_clusters} clusters, {np.sum(db_labels == -1):,} outliers")

# 8. Metrics
print("\n[8/8] Computing metrics...")

def compute_metrics(X, labels, name):
    valid = labels >= 0
    if valid.sum() < 2:
        return {'method': name, 'n_clusters': 0}
    X_valid = X[valid]
    labels_valid = labels[valid]
    sample_size = min(5000, len(X_valid))
    idx = np.random.choice(len(X_valid), sample_size, replace=False)
    return {
        'method': name,
        'n_clusters': len(np.unique(labels_valid)),
        'silhouette': silhouette_score(X_valid[idx], labels_valid[idx]),
        'davies_bouldin': davies_bouldin_score(X_valid, labels_valid),
        'calinski_harabasz': calinski_harabasz_score(X_valid, labels_valid)
    }

metrics = []
metrics.append(compute_metrics(X_pca, km_labels, 'K-Means'))
metrics.append(compute_metrics(X_pca, gmm_labels, 'GMM'))
metrics.append(compute_metrics(X_pca, db_labels, 'DBSCAN'))

metrics_df = pd.DataFrame(metrics)
print(metrics_df.round(4).to_string(index=False))

# Stability
print("\n[Stability] Adjusted Rand Index across 10 seeds...")
def stability_analysis(model_class, model_params, X, n_runs=10):
    base_model = model_class(**model_params, random_state=SEED)
    base_labels = base_model.fit_predict(X)
    ari_scores = []
    for seed in range(n_runs):
        model = model_class(**model_params, random_state=seed)
        labels = model.fit_predict(X)
        ari_scores.append(adjusted_rand_score(base_labels, labels))
    return np.array(ari_scores)

km_ari = stability_analysis(KMeans, {'n_clusters': CHOSEN_K, 'n_init': 10}, X_pca)
gmm_ari = stability_analysis(GaussianMixture, {'n_components': CHOSEN_K, 'n_init': 5}, X_pca)
print(f"    K-Means ARI: mean={km_ari.mean():.4f} std={km_ari.std():.4f}")
print(f"    GMM ARI:     mean={gmm_ari.mean():.4f} std={gmm_ari.std():.4f}")

# Save results
print("\n[Save] Writing output files...")

# Choose best model (highest silhouette)
best_method = metrics_df.loc[metrics_df['silhouette'].idxmax(), 'method']
best_labels = km_labels if best_method == 'K-Means' else gmm_labels
print(f"    Best model: {best_method}")

# Cluster assignments
output_df = anomalies[['protocol_type', 'service', 'flag', 'src_bytes', 'dst_bytes']].copy()
output_df['cluster'] = best_labels
output_df.to_csv('pair3_cluster_assignments.csv', index=False)

# Cluster profiles
anomalies_labeled = anomalies.copy()
anomalies_labeled['cluster'] = best_labels

profile_features = [
    'duration', 'src_bytes', 'dst_bytes', 'protocol_type', 'service', 'flag',
    'count', 'srv_count', 'serror_rate', 'rerror_rate', 'same_srv_rate', 'diff_srv_rate',
    'dst_host_count', 'dst_host_srv_count', 'dst_host_same_srv_rate', 'dst_host_diff_srv_rate',
    'num_failed_logins', 'logged_in', 'is_guest_login', 'num_compromised',
    'root_shell', 'su_attempted', 'num_root', 'num_file_creations',
    'num_shells', 'num_access_files', 'hot'
]

numeric_profile = [f for f in profile_features if f in anomalies_labeled.select_dtypes(include='number').columns]
categorical_profile = [f for f in profile_features if f in anomalies_labeled.select_dtypes(exclude='number').columns]

cluster_profiles = anomalies_labeled.groupby('cluster').agg({
    **{f: 'median' for f in numeric_profile},
    **{f: lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else 'N/A' for f in categorical_profile}
})
cluster_profiles.to_csv('pair3_cluster_profiles.csv')

# MITRE mapping template
mitre_mapping = {
    str(c): {
        'attack_type': 'TODO: Interpret from cluster profile',
        'mitre_technique': 'TODO: Map to MITRE ATT&CK',
        'key_indicators': 'TODO: List distinguishing features',
        'confidence': 'Low'
    } for c in sorted(np.unique(best_labels[best_labels >= 0]))
}
with open('pair3_mitre_mapping.json', 'w') as f:
    json.dump(mitre_mapping, f, indent=2)

print("\n" + "=" * 60)
print("DONE! Output files:")
print("  - pair3_cluster_assignments.csv")
print("  - pair3_cluster_profiles.csv")
print("  - pair3_mitre_mapping.json (TEMPLATE - fill in)")
print("=" * 60)
print("\nNext steps:")
print("1. Open pair3_cluster_profiles.csv to interpret clusters")
print("2. Fill in pair3_mitre_mapping.json with your hypotheses")
print("3. Use pair3_clustering.ipynb for visualizations & detailed analysis")