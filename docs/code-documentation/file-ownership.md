# File Ownership — Python Modules

Auto-generated table. Fill **Owner**, **Reviewer**, **Demo explained**, and **Commenting complete**.

Regenerate skeleton: `py scripts/audit_python_docs.py`

| File | Author tag | Owner | Reviewer | Demo explained | Commenting complete |
|------|------------|-------|----------|----------------|---------------------|
| `src/__init__.py` | TODO - Team Member Name | Team | Team | Rehearsal | Yes |
| `src/api/__init__.py` | TODO - Team Member Name | Team | Team | Rehearsal | Yes |
| `src/api/architecture_page.py` | Presentation layer — interactive architecture dashboard | Sana (Member C) | Team | Rehearsal | Review |
| `src/api/config.py` | TODO - Team Member Name | Team | Team | Rehearsal | Yes |
| `src/api/demo_pipeline.py` | Member D — local demo pipeline runner | Fazal (Member D) | Team | Rehearsal | Review |
| `src/api/drift_service.py` | Member D — drift API service | Fazal (Member D) | Team | Rehearsal | Review |
| `src/api/inference.py` | TODO - Team Member Name | Team | Team | Rehearsal | Yes |
| `src/api/local_dashboard.py` | Member D — local dev hub | Fazal (Member D) | Team | Rehearsal | Review |
| `src/api/main.py` | Member C — FastAPI inference service | Sana (Member C) | Team | Rehearsal | Review |
| `src/api/openrouter_service.py` | Member D — OpenRouter API service | Fazal (Member D) | Team | Rehearsal | Review |
| `src/api/schemas.py` | TODO - Team Member Name | Team | Team | Rehearsal | Review |
| `src/api/swagger_ui.py` | Member C — API documentation presentation | Sana (Member C) | Team | Rehearsal | Review |
| `src/api/system_status.py` | Member D — dashboard system status | Fazal (Member D) | Team | Rehearsal | Review |
| `src/api/url_check_history.py` | Member D — URL check history persistence | Fazal (Member D) | Team | Rehearsal | Review |
| `src/api/url_checker.py` | Member D — public URL metrics probe | Fazal (Member D) | Team | Rehearsal | Review |
| `src/data/__init__.py` | TODO - Team Member Name | Team | Team | Rehearsal | Yes |
| `src/data/load_data.py` | Member A — data ingestion stage | Ameer (Member A) | Team | Rehearsal | Yes |
| `src/data/preprocess.py` | Member A — data preprocessing stage | Ameer (Member A) | Team | Rehearsal | Yes |
| `src/data/validate_data.py` | Member A — data validation module | Ameer (Member A) | Team | Rehearsal | Yes |
| `src/features/__init__.py` | TODO - Team Member Name | Team | Team | Rehearsal | Yes |
| `src/features/build_features.py` | Member B — feature preparation stage | Bakhtiyar (Member B) | Team | Rehearsal | Yes |
| `src/models/__init__.py` | TODO - Team Member Name | Team | Team | Rehearsal | Yes |
| `src/models/evaluate.py` | Member B — model evaluation stage | Bakhtiyar (Member B) | Team | Rehearsal | Review |
| `src/models/registry.py` | Member B — model registry stage | Bakhtiyar (Member B) | Team | Rehearsal | Review |
| `src/models/train.py` | Member B — model training stage | Bakhtiyar (Member B) | Team | Rehearsal | Review |
| `src/monitoring/__init__.py` | Member D — monitoring package | Fazal (Member D) | Team | Rehearsal | Yes |
| `src/monitoring/drift.py` | Member D — Evidently data drift detection | Fazal (Member D) | Team | Rehearsal | Review |
| `src/monitoring/llm_prompts.py` | Member D — OpenRouter prompt templates | Fazal (Member D) | Team | Rehearsal | Review |
| `src/monitoring/observations.py` | Member D — demo production observation log | Fazal (Member D) | Team | Rehearsal | Review |
| `src/monitoring/telemetry.py` | Member D — Application Insights telemetry | Fazal (Member D) | Team | Rehearsal | Review |
| `src/utils/__init__.py` | TODO - Team Member Name | Team | Team | Rehearsal | Yes |
| `src/utils/config.py` | Team — shared utility module | Team | Team | Rehearsal | Review |
| `src/utils/secrets.py` | Team — shared utility module | Team | Team | Rehearsal | Yes |
| `scripts/audit_python_docs.py` | Member D — documentation audit tooling | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/build_image.py` | Member C — Docker image build helper | Sana (Member C) | Team | Rehearsal | Review |
| `scripts/check_local.py` | TODO - Team Member Name | Team | Team | Rehearsal | Review |
| `scripts/collect_local_evidence.py` | Member D — submission evidence collector | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/evaluate_model.py` | Member B — evaluation script | Bakhtiyar (Member B) | Team | Rehearsal | Review |
| `scripts/generate_sample_data.py` | Member A — data generation script | Ameer (Member A) | Team | Rehearsal | Yes |
| `scripts/ingest_data.py` | Member A — data ingestion script | Ameer (Member A) | Team | Rehearsal | Yes |
| `scripts/investigate_drift.py` | Member D — drift investigation | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/openrouter_report.py` | Member D — OpenRouter LLM reporting | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/refresh_drift_baseline.py` | Member D — baseline refresh after retrain | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/register_model.py` | Member B — model registry script | Bakhtiyar (Member B) | Team | Rehearsal | Review |
| `scripts/render_architecture_diagrams.py` | Member D — architecture diagram renderer | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/run_drift_check.py` | Member D — drift check CLI | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/run_drift_remediation.py` | Member D — post-drift remediation pipeline | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/run_local.py` | Member D — single local dev server | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/run_submission_rehearsal.py` | Member D — submission rehearsal runner | Fazal (Member D) | Team | Rehearsal | Review |
| `scripts/setup_dvc.py` | Member A — DVC setup script | Ameer (Member A) | Team | Rehearsal | Yes |
| `scripts/train_model.py` | Member B — training script | Bakhtiyar (Member B) | Team | Rehearsal | Review |
| `scripts/verify_member_d.py` | Member D — verification helper | Fazal (Member D) | Team | Rehearsal | Review |
| `infra/deploy_aci.py` | Member C — ACI staging deployment | Sana (Member C) | Team | Rehearsal | Review |
| `infra/deploy_aks.py` | Member D — AKS production deployment | Fazal (Member D) | Team | Rehearsal | Review |
| `infra/setup_alerts.py` | Member D — Azure Monitor alert provisioning | Fazal (Member D) | Team | Rehearsal | Review |
| `tests/test_api.py` | Member C — API tests | Sana (Member C) | Team | Rehearsal | Review |
| `tests/test_architecture_page.py` | Presentation layer tests | Sana (Member C) | Team | Rehearsal | Review |
| `tests/test_dashboard_demo.py` | Member D — dashboard demo workflow tests | Fazal (Member D) | Team | Rehearsal | Review |
| `tests/test_data_ingestion.py` | Member A — unit tests for data ingestion pipeline | Ameer (Member A) | Team | Rehearsal | Review |
| `tests/test_drift_api.py` | TODO - Team Member Name | Team | Team | Rehearsal | Review |
| `tests/test_member_d_scripts.py` | TODO - Team Member Name | Team | Team | Rehearsal | Review |
| `tests/test_monitoring.py` | TODO - Team Member Name | Team | Team | Rehearsal | Review |
| `tests/test_observations.py` | TODO - Team Member Name | Team | Team | Rehearsal | Review |
| `tests/test_openrouter_api.py` | TODO - Team Member Name | Team | Team | Rehearsal | Review |
| `tests/test_training.py` | Member B — unit tests for training, evaluation, and registry | Bakhtiyar (Member B) | Team | Rehearsal | Review |
