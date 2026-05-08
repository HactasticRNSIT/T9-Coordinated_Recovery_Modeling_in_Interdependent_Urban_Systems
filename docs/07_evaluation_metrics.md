# Evaluation Metrics

## ML Model Metrics

### Cascade GNN

| Metric | Formula | Target | Interpretation |
|---|---|---|---|
| **AUC-ROC** | Area under ROC curve | > 0.85 | Overall discrimination ability |
| **F1 Score** | 2×P×R / (P+R) | > 0.75 | Balance of precision and recall |
| **Precision@K** | TP in top-K predictions / K | > 0.80 | Quality of top cascade predictions |
| **Recall** | TP / (TP + FN) | > 0.70 | Fraction of actual cascades caught |

**Why AUC-ROC as primary:** Cascade failures are rare events (class imbalance). AUC-ROC is threshold-independent and robust to imbalance.

### Recovery LSTM + XGBoost

| Metric | Formula | Target | Interpretation |
|---|---|---|---|
| **MAE** | mean(|y_pred - y_true|) | < 2 hours | Average prediction error in hours |
| **RMSE** | sqrt(mean((y_pred - y_true)²)) | < 4 hours | Penalizes large errors more |
| **MAPE** | mean(|y_pred - y_true| / y_true) × 100 | < 20% | Relative error percentage |
| **PI Coverage** | % of true values in 80% PI | 75–85% | Calibration of uncertainty bounds |

**Why MAE as primary:** Recovery time errors are roughly symmetric and we care equally about over/under-estimation. RMSE would over-penalize rare long-recovery events.

### Resilience XGBoost

| Metric | Formula | Target | Interpretation |
|---|---|---|---|
| **MAE** | mean(|y_pred - y_true|) | < 0.05 | Score error on 0–1 scale |
| **R²** | 1 - SS_res/SS_tot | > 0.80 | Variance explained |
| **Pearson r** | Correlation coefficient | > 0.85 | Linear correlation with ground truth |
| **SHAP Coverage** | Top-5 features explain > 70% variance | — | Model interpretability |

### Scenario Engine

| Metric | Formula | Target | Interpretation |
|---|---|---|---|
| **Strategy Ranking Accuracy** | % correct rank of best strategy | > 80% | Does simulation pick the right strategy? |
| **Bottleneck Detection Rate** | TP bottlenecks / actual bottlenecks | > 75% | Identifies real recovery blockers |
| **Runtime (100 runs)** | Wall clock time | < 30 seconds | Usability for interactive planning |
| **Distribution Calibration** | KS test p-value | > 0.05 | MC distribution matches historical |

---

## System Performance Metrics

| Metric | Target | Measurement Method |
|---|---|---|
| API response time (p50) | < 200ms | Load test with k6 |
| API response time (p95) | < 500ms | Load test with k6 |
| API response time (p99) | < 1000ms | Load test with k6 |
| Dashboard initial load | < 2 seconds | Lighthouse |
| Map render time (20 districts) | < 1 second | Browser DevTools |
| WebSocket latency | < 100ms | Manual measurement |
| Concurrent users supported | 50 | Load test |
| Database query time (spatial) | < 100ms | EXPLAIN ANALYZE |

---

## Resilience Score Validation

The composite resilience score is validated against:

1. **Historical correlation**: Compare predicted scores with actual recovery outcomes from the 50 synthetic incidents. Target Pearson r > 0.85.

2. **Cross-validation**: 5-fold CV on the XGBoost model. Target CV MAE < 0.06.

3. **Sensitivity analysis**: Perturb each input feature by ±10% and measure score change. Verify monotonicity (higher severity → lower score, more backup nodes → higher score).

4. **Rank consistency**: For the same incident, districts with more resources should consistently rank higher. Measure Spearman rank correlation between resource count and resilience score. Target > 0.70.

---

## Dashboard UX Metrics

| Metric | Target | Tool |
|---|---|---|
| Lighthouse Performance | > 85 | Lighthouse CI |
| Lighthouse Accessibility | > 90 | Lighthouse CI |
| First Contentful Paint | < 1.5s | Lighthouse |
| Time to Interactive | < 3.0s | Lighthouse |
| WCAG 2.1 AA compliance | Pass | axe-core |

---

## Hackathon Judging Criteria Alignment

| Criterion | How UrbanSync AI Addresses It |
|---|---|
| **Innovation** | First system to combine GNN cascade detection + LSTM recovery + MC simulation in one platform |
| **Technical Depth** | 4 distinct ML models, PostGIS spatial queries, real-time WebSocket, heterogeneous graph |
| **Practical Impact** | Directly usable by city emergency managers; quantified improvement in recovery time |
| **Scalability** | Docker + cloud deployment; designed for real smart-city data integration |
| **Presentation** | Interactive dashboard with live simulation, map, and charts |
| **Completeness** | End-to-end: data → ML → API → frontend → deployment |
