# HoneyBadger Machine Learning Project Plan

Here's a plan with three objectives, one per pair. Each objective is a different kind of machine-learning task (supervised classification, anomaly detection without labels, and clustering), so each pair has its own models, its own metrics, and something different to present. All three use the Kaggle dataset you already have and tie back to HoneyBadger.

---

## Shared Part (All 6 Members — Do It Once)

### Business Understanding
* **Context:** HoneyBadger is a honeypot that records SSH and HTTP attacks. Security teams have to decide which traffic is an attack, and then what kind of attack it is.
* **Problem:** Labeling traffic by hand doesn't scale, and real honeypot events have no ground-truth labels.
* **Overall Goal:** Use labeled network data to build and evaluate detection and profiling methods that could later be applied to HoneyBadger's own events.

### Data Understanding *(already in `intrusion_analysis.ipynb`, sections 2–3)*
* `Train_data.csv` has 25,192 rows and 41 features plus the label `class`. `Test_data.csv` has 22,544 rows and the same 41 features, with no labels.
* There are 3 categorical features (`protocol_type`, `service`, `flag`) and 38 numeric ones.
* **Classes:** 13,449 `normal` (53.4%) and 11,743 `anomaly` (46.6%), so they are nearly balanced.
* No missing values. Two columns are constant (`num_outbound_cmds`, `is_host_login`). One pair of identical rows has opposite labels.
* **SSH** has 58 rows, all anomalies. **HTTP** has 8,003 rows: 7,564 normal and 439 anomaly.

### Rules for Every Pair (To Avoid Errors)
1. **Never compute metrics on `Test_data.csv`.** It has no labels, so you can only predict on it.
2. **Use the same validation split as the notebook** (`grouped_stratified_folds`, fold 0). This makes results comparable across pairs and keeps identical rows out of both sides.
3. **Fit every encoder and scaler on the training partition only**, then apply it to the validation data.
4. **Drop the two constant columns.** Never use `class` as an input feature.
5. **Never report accuracy alone.** Always include the confusion matrix and the metrics listed for your objective.
6. **Fix `random_state = 42` everywhere** so results can be reproduced.

---

## Pair 1: Detect Attacks (Supervised Classification)

**Business Question:** Given a labeled connection, can we decide automatically whether it's an attack, while keeping both missed attacks and false alarms low?

### Data Preparation
* One-hot encode the 3 categorical features.
* Apply `StandardScaler` for Logistic Regression only. Tree models don't need scaling; state this in your justification.
* **Class Balance:** The classes are $47/53$ so no resampling is needed. Justify that with the class counts.
* **Feature Selection:** Compare the full feature set with a reduced set chosen by importance.

### Models and Justification
* **Logistic Regression:** A simple baseline you can interpret through its coefficients.
* **Decision Tree:** Its rules are readable by an analyst.
* **Random Forest:** Strong on tabular data and robust to outliers. It already reaches $0.997$ recall in the notebook.
* **Majority-Class Baseline:** Shows the minimum any model must beat.

### Metrics
* **Recall on anomalies:** Missed attacks are the costliest error.
* **Precision:** How many alerts are real attacks, measuring false alarms.
* **F1, ROC-AUC, and PR-AUC**, plus the **confusion matrix**.

> **Extension That Makes It Worth It:** Retrain using only features HoneyBadger could compute from its own events: `service`, `count`, `srv_count`, the `dst_host_*` counts, `num_failed_logins`, and `logged_in`. Then compare with the full model. That answers whether this approach could work on your honeypot.

---

## Pair 2: Detect Attacks Without Labels (Anomaly Detection)

**Business Question:** HoneyBadger has no labels. Can a model trained only on normal traffic flag attacks as "unusual"?

### Data Preparation
* Train only on the `normal` rows of the training partition.
* Apply `log1p` to skewed features (`duration`, `src_bytes`, `dst_bytes`), then `StandardScaler`. These models are sensitive to scale.
* One-hot encode `protocol_type` and `flag`. Group rare `service` values into `"other"` to limit the number of columns.
* Use the labels only for evaluation, never for training.

### Models and Justification
* **Isolation Forest:** Fast and well suited to large tabular data.
* **One-Class SVM:** Learns a boundary around normal traffic. Train it on a sample of about 5,000 normal rows, because it is slow on large data.
* **Local Outlier Factor (`novelty=True`):** A density-based comparison.

> **Watch Out:** Anomalies make up 46.6% of this dataset, but these models assume anomalies are rare. That's exactly why you train on normal traffic only. Explain this in your presentation; it shows you understand the method.

### Metrics
* **ROC-AUC and PR-AUC** on the validation partition.
* **Recall at a fixed false-alarm rate**, for example, the share of attacks caught when only 1% of normal traffic is flagged.
* **F1 and the confusion matrix** at the threshold you choose.
* **Compare with Pair 1's result** to show the cost of having no labels.

---

## Pair 3: Profile Attack Types (Clustering)

**Business Question:** The dataset only says "anomaly". Can we group attacks into families (floods, scans, login attempts) so analysts know what kind of attack they are facing?

### Data Preparation
* Use only the 11,743 `anomaly` rows.
* Apply `log1p` to the skewed features, then `StandardScaler`, and drop the constant columns.
* One-hot encode `protocol_type` and `flag`, and group rare services.
* Use PCA for 2D visualization, and optionally to reduce dimensions before clustering.

### Models and Justification
* **K-Means:** Simple, and its centroids are easy to interpret. Choose $k$ with the elbow method and silhouette scores.
* **Gaussian Mixture:** Allows clusters of different shapes and sizes.
* **DBSCAN:** Finds dense groups and labels outliers, without fixing $k$ in advance.

### Metrics
* **Silhouette score** (computed on a sample to save time), **Davies-Bouldin**, and **Calinski-Harabasz**.
* **Stability:** Rerun with different seeds and check that the clusters stay the same.

> **Interpretation:** Describe each cluster by its average features. For example, high `serror_rate` with flag `S0` looks like a SYN flood; many different services from one host looks like a scan. Map each cluster to a MITRE ATT&CK technique as a hypothesis (`T1595` scanning, `T1110` brute force, `T1499` denial of service). State clearly that this mapping can't be checked against true labels, because the dataset has no attack-type labels.

---

## Splitting Work Inside Each Pair
* **Member A:** Data preparation, with a justification for each choice.
* **Member B:** Modeling and evaluation.
* **Both:** Interpret the results and prepare the slides together, so either one can answer questions about the whole objective.