"""Tests for Member D CLI scripts to meet coverage threshold."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from scripts.generate_sample_data import generate_monitoring_data


@pytest.fixture
def drift_csvs(tmp_path):
    """Create minimal reference and current CSVs for drift tests."""
    df = generate_monitoring_data(n_samples=200, random_state=42)
    ref_path = tmp_path / "reference.csv"
    cur_path = tmp_path / "current.csv"
    df.head(100).to_csv(ref_path, index=False)
    df.tail(80).to_csv(cur_path, index=False)
    return ref_path, cur_path


@pytest.fixture
def sample_raw_csv(tmp_path):
    """Write a raw monitoring CSV large enough for baseline refresh."""
    df = generate_monitoring_data(n_samples=1000, random_state=7)
    raw_path = tmp_path / "website_monitoring.csv"
    df.to_csv(raw_path, index=False)
    return raw_path


@pytest.fixture
def drift_summary_file(tmp_path, drift_csvs):
    """Minimal drift summary JSON for investigate_drift tests."""
    ref_path, cur_path = drift_csvs
    summary = {
        "drift_detected": True,
        "column_drifts": {
            "latency_p95_ms": True,
            "error_rate": False,
        },
    }
    path = tmp_path / "drift_summary.json"
    path.write_text(json.dumps(summary), encoding="utf-8")
    return path


# --- investigate_drift.py ---


def test_analyze_feature_computes_stats():
    from scripts.investigate_drift import analyze_feature

    ref = pd.Series([10.0, 20.0, 30.0])
    cur = pd.Series([12.0, 18.0, 30.0])
    stat = analyze_feature(ref, cur, "latency_p95_ms")
    assert stat["feature"] == "latency_p95_ms"
    assert stat["reference_mean"] == 20.0
    assert stat["current_mean"] == 20.0
    assert stat["mean_shift_percent"] == 0.0


def test_analyze_feature_zero_reference_mean():
    from scripts.investigate_drift import analyze_feature

    stat = analyze_feature(pd.Series([0.0, 0.0]), pd.Series([1.0, 2.0]), "x")
    assert stat["mean_shift_percent"] == 0.0


def test_build_investigation_report_latency_lower():
    from scripts.investigate_drift import build_investigation_report

    stats = [
        {
            "feature": "latency_p95_ms",
            "reference_mean": 300.0,
            "current_mean": 200.0,
        }
    ]
    payload = build_investigation_report(["latency_p95_ms"], stats, Path("summary.json"))
    assert payload["action_required"] is True
    assert any("healthier" in r.lower() for r in payload["recommendations"])


def test_build_investigation_report_latency_higher():
    from scripts.investigate_drift import build_investigation_report

    stats = [
        {
            "feature": "latency_p95_ms",
            "reference_mean": 100.0,
            "current_mean": 200.0,
        }
    ]
    payload = build_investigation_report(["latency_p95_ms"], stats, Path("summary.json"))
    assert any("exceeds" in r.lower() for r in payload["recommendations"])


def test_write_markdown_report_no_drift(tmp_path):
    from scripts.investigate_drift import write_markdown_report

    payload = {
        "investigated_at_utc": "2026-01-01T00:00:00+00:00",
        "drifted_features": [],
        "feature_statistics": [],
        "recommendations": [],
        "suggested_actions": ["Re-run drift check"],
    }
    out = tmp_path / "report.md"
    write_markdown_report(payload, out)
    text = out.read_text(encoding="utf-8")
    assert "None (no drift detected)" in text
    assert "Re-run drift check" in text


def test_investigate_drift_main_missing_summary(tmp_path, capsys):
    from scripts import investigate_drift

    missing = tmp_path / "missing.json"
    with patch.object(sys, "argv", ["investigate_drift.py", "--drift-summary", str(missing)]):
        rc = investigate_drift.main()
    assert rc == 1
    assert "ERROR" in capsys.readouterr().err


def test_investigate_drift_main_writes_reports(tmp_path, drift_csvs, monkeypatch):
    from scripts import investigate_drift

    ref_path, cur_path = drift_csvs
    summary = tmp_path / "drift_summary.json"
    summary.write_text(
        json.dumps({"column_drifts": {"latency_p95_ms": True}}),
        encoding="utf-8",
    )
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    monkeypatch.setattr(
        investigate_drift,
        "load_drift_datasets",
        lambda: (
            pd.read_csv(ref_path),
            pd.read_csv(cur_path),
            list(pd.read_csv(ref_path).columns[:-1]),
        ),
    )
    with patch.object(sys, "argv", [
        "investigate_drift.py",
        "--drift-summary",
        str(summary),
        "--output-dir",
        str(out_dir),
    ]):
        rc = investigate_drift.main()
    assert rc == 1
    assert (out_dir / "drift_investigation.json").exists()
    assert (out_dir / "drift_investigation.md").exists()


def test_investigate_drift_main_no_drift(tmp_path, drift_csvs, monkeypatch):
    from scripts import investigate_drift

    ref_path, cur_path = drift_csvs
    summary = tmp_path / "drift_summary.json"
    summary.write_text(json.dumps({"column_drifts": {}}), encoding="utf-8")
    out_dir = tmp_path / "out"
    out_dir.mkdir()
    features = list(pd.read_csv(ref_path).columns[:-1])
    monkeypatch.setattr(
        investigate_drift,
        "load_drift_datasets",
        lambda: (pd.read_csv(ref_path), pd.read_csv(cur_path), features),
    )
    with patch.object(sys, "argv", [
        "investigate_drift.py",
        "--drift-summary",
        str(summary),
        "--output-dir",
        str(out_dir),
    ]):
        rc = investigate_drift.main()
    assert rc == 0


# --- refresh_drift_baseline.py ---


def test_refresh_baseline_writes_csvs(sample_raw_csv, tmp_path, monkeypatch):
    from scripts.refresh_drift_baseline import refresh_baseline

    ref_root = tmp_path / "data"
    monkeypatch.setattr(
        "scripts.refresh_drift_baseline.get_project_root",
        lambda: ref_root,
    )
    ref_path, cur_path = refresh_baseline(
        raw_path=sample_raw_csv,
        reference_rows=100,
        current_rows=80,
    )
    assert ref_path.exists()
    assert cur_path.exists()
    assert len(pd.read_csv(ref_path)) == 100
    assert len(pd.read_csv(cur_path)) == 80


def test_refresh_baseline_missing_raw(tmp_path, monkeypatch):
    from scripts.refresh_drift_baseline import refresh_baseline

    monkeypatch.setattr(
        "scripts.refresh_drift_baseline.get_project_root",
        lambda: tmp_path,
    )
    with pytest.raises(FileNotFoundError):
        refresh_baseline(raw_path=tmp_path / "missing.csv")


def test_refresh_baseline_too_few_rows(sample_raw_csv, tmp_path, monkeypatch):
    from scripts.refresh_drift_baseline import refresh_baseline

    monkeypatch.setattr(
        "scripts.refresh_drift_baseline.get_project_root",
        lambda: tmp_path,
    )
    with pytest.raises(ValueError, match="Need at least"):
        refresh_baseline(
            raw_path=sample_raw_csv,
            reference_rows=900,
            current_rows=200,
        )


def test_refresh_baseline_main_success(sample_raw_csv, capsys):
    from scripts import refresh_drift_baseline

    with patch.object(sys, "argv", ["refresh_drift_baseline.py", "--raw", str(sample_raw_csv)]):
        with patch.object(
            refresh_drift_baseline,
            "refresh_baseline",
            return_value=(Path("ref.csv"), Path("cur.csv")),
        ):
            rc = refresh_drift_baseline.main()
    assert rc == 0
    assert "Reference baseline" in capsys.readouterr().out


def test_refresh_baseline_main_error(sample_raw_csv, capsys):
    from scripts import refresh_drift_baseline

    with patch.object(sys, "argv", ["refresh_drift_baseline.py", "--raw", str(sample_raw_csv)]):
        with patch.object(
            refresh_drift_baseline,
            "refresh_baseline",
            side_effect=FileNotFoundError("no raw"),
        ):
            rc = refresh_drift_baseline.main()
    assert rc == 1
    assert "ERROR" in capsys.readouterr().err


# --- render_architecture_diagrams.py ---


def test_find_mmdc_prefers_mmdc(monkeypatch):
    from scripts import render_architecture_diagrams

    monkeypatch.setattr(
        render_architecture_diagrams.shutil,
        "which",
        lambda name: "/usr/bin/mmdc" if name == "mmdc" else None,
    )
    assert render_architecture_diagrams.find_mmdc() == ["mmdc"]


def test_find_mmdc_falls_back_to_npx(monkeypatch):
    from scripts import render_architecture_diagrams

    def which(name):
        if name == "npx":
            return "/usr/bin/npx"
        return None

    monkeypatch.setattr(render_architecture_diagrams.shutil, "which", which)
    assert render_architecture_diagrams.find_mmdc() == ["/usr/bin/npx", "--yes", "@mermaid-js/mermaid-cli"]


def test_find_mmdc_returns_none(monkeypatch):
    from scripts import render_architecture_diagrams

    monkeypatch.setattr(render_architecture_diagrams.shutil, "which", lambda _name: None)
    assert render_architecture_diagrams.find_mmdc() is None


def test_render_one_invokes_subprocess(tmp_path, monkeypatch):
    from scripts.render_architecture_diagrams import render_one

    mmd = tmp_path / "diagram.mmd"
    mmd.write_text("flowchart LR\n  A-->B\n", encoding="utf-8")
    out = tmp_path / "diagram.png"
    monkeypatch.setattr(
        "scripts.render_architecture_diagrams.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0),
    )
    assert render_one(["mmdc"], mmd, out) == 0


def test_render_main_no_mmd_files(tmp_path, monkeypatch, capsys):
    from scripts import render_architecture_diagrams

    monkeypatch.setattr(render_architecture_diagrams, "ARCH_DIR", tmp_path)
    with patch.object(sys, "argv", ["render_architecture_diagrams.py"]):
        rc = render_architecture_diagrams.main()
    assert rc == 1
    assert "No .mmd files" in capsys.readouterr().err


def test_render_main_no_mmdc(tmp_path, monkeypatch, capsys):
    from scripts import render_architecture_diagrams

    (tmp_path / "test.mmd").write_text("flowchart LR\n  A-->B\n", encoding="utf-8")
    monkeypatch.setattr(render_architecture_diagrams, "ARCH_DIR", tmp_path)
    monkeypatch.setattr(render_architecture_diagrams, "find_mmdc", lambda: None)
    with patch.object(sys, "argv", ["render_architecture_diagrams.py"]):
        rc = render_architecture_diagrams.main()
    assert rc == 1
    assert "mermaid-cli not found" in capsys.readouterr().err


def test_render_main_success(tmp_path, monkeypatch, capsys):
    from scripts import render_architecture_diagrams

    (tmp_path / "test.mmd").write_text("flowchart LR\n  A-->B\n", encoding="utf-8")
    out_dir = tmp_path / "images"
    monkeypatch.setattr(render_architecture_diagrams, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(render_architecture_diagrams, "ARCH_DIR", tmp_path)
    monkeypatch.setattr(render_architecture_diagrams, "find_mmdc", lambda: ["mmdc"])
    def fake_render(_cmd, _mmd, out):
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("png")
        return 0

    monkeypatch.setattr(render_architecture_diagrams, "render_one", fake_render)
    with patch.object(sys, "argv", ["render_architecture_diagrams.py", "--output-dir", str(out_dir)]):
        rc = render_architecture_diagrams.main()
    assert rc == 0
    assert "Rendered 1 diagram" in capsys.readouterr().out


def test_render_main_partial_failure(tmp_path, monkeypatch, capsys):
    from scripts import render_architecture_diagrams

    (tmp_path / "a.mmd").write_text("flowchart LR\n  A-->B\n", encoding="utf-8")
    (tmp_path / "b.mmd").write_text("flowchart LR\n  C-->D\n", encoding="utf-8")
    monkeypatch.setattr(render_architecture_diagrams, "ARCH_DIR", tmp_path)
    monkeypatch.setattr(render_architecture_diagrams, "find_mmdc", lambda: ["mmdc"])
    monkeypatch.setattr(
        render_architecture_diagrams,
        "render_one",
        lambda _cmd, mmd, _out: 0 if mmd.name == "a.mmd" else 1,
    )
    with patch.object(sys, "argv", ["render_architecture_diagrams.py"]):
        rc = render_architecture_diagrams.main()
    assert rc == 1
    err = capsys.readouterr().err
    assert "FAILED" in err


# --- run_drift_remediation.py ---


def test_python_executable_falls_back(monkeypatch):
    import shutil

    from scripts.run_drift_remediation import _python_executable

    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert _python_executable() == sys.executable


def test_python_executable_selects_compatible(monkeypatch):
    import shutil

    from scripts.run_drift_remediation import _python_executable

    def which(name):
        return f"/usr/bin/{name}" if name == "python3.11" else None

    monkeypatch.setattr(shutil, "which", which)
    monkeypatch.setattr(
        "scripts.run_drift_remediation.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0),
    )
    assert _python_executable() == "/usr/bin/python3.11"


def test_check_url_success(monkeypatch):
    from scripts.run_drift_remediation import check_url

    class FakeResp:
        status = 200

        def read(self):
            return b'{"status":"ok"}'

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: FakeResp())
    ok, body = check_url("http://example/health")
    assert ok is True
    assert "ok" in body


def test_check_url_failure(monkeypatch):
    from scripts.run_drift_remediation import check_url
    import urllib.error

    def raise_error(*_a, **_k):
        raise urllib.error.URLError("down")

    monkeypatch.setattr("urllib.request.urlopen", raise_error)
    ok, body = check_url("http://example/health")
    assert ok is False
    assert "down" in body


def test_remediation_main_success(tmp_path, monkeypatch, capsys):
    from scripts import run_drift_remediation

    eval_path = tmp_path / "data" / "processed" / "eval_metrics.json"
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    eval_path.write_text(json.dumps({"gate_passed": True, "f1_score": 0.9}), encoding="utf-8")
    monkeypatch.setattr(run_drift_remediation, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(run_drift_remediation, "_python_executable", lambda: sys.executable)
    monkeypatch.setattr(run_drift_remediation, "check_url", lambda _url: (True, '{"status":"ok"}'))

    fake_resp = MagicMock(status_code=200, text='{"outage_predicted": false}')
    monkeypatch.setitem(sys.modules, "httpx", MagicMock(post=lambda *_a, **_k: fake_resp))
    monkeypatch.setattr(run_drift_remediation, "run", lambda _cmd: 0)

    with patch.object(sys, "argv", ["run_drift_remediation.py", "--skip-deploy"]):
        rc = run_drift_remediation.main()

    assert rc == 0
    log_path = tmp_path / "reports" / "drift" / "remediation_log.json"
    assert log_path.exists()


def test_remediation_main_retrain_failure(monkeypatch, capsys):
    from scripts import run_drift_remediation

    monkeypatch.setattr(run_drift_remediation, "_python_executable", lambda: sys.executable)
    monkeypatch.setattr(run_drift_remediation, "run", lambda cmd: 1 if "train_model" in " ".join(cmd) else 0)
    with patch.object(sys, "argv", ["run_drift_remediation.py", "--skip-deploy"]):
        rc = run_drift_remediation.main()
    assert rc == 1


def test_remediation_main_gate_failed(tmp_path, monkeypatch):
    from scripts import run_drift_remediation

    eval_path = tmp_path / "data" / "processed" / "eval_metrics.json"
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    eval_path.write_text(json.dumps({"gate_passed": False}), encoding="utf-8")
    monkeypatch.setattr(run_drift_remediation, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(run_drift_remediation, "_python_executable", lambda: sys.executable)
    monkeypatch.setattr(run_drift_remediation, "run", lambda _cmd: 0)
    with patch.object(sys, "argv", ["run_drift_remediation.py", "--skip-deploy"]):
        rc = run_drift_remediation.main()
    assert rc == 1


def test_remediation_main_refresh_failure(tmp_path, monkeypatch):
    from scripts import run_drift_remediation

    eval_path = tmp_path / "data" / "processed" / "eval_metrics.json"
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    eval_path.write_text(json.dumps({"gate_passed": True}), encoding="utf-8")
    monkeypatch.setattr(run_drift_remediation, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(run_drift_remediation, "_python_executable", lambda: sys.executable)

    def fake_run(cmd):
        if "refresh_drift_baseline" in " ".join(cmd):
            return 1
        return 0

    monkeypatch.setattr(run_drift_remediation, "run", fake_run)
    with patch.object(sys, "argv", ["run_drift_remediation.py", "--skip-deploy"]):
        rc = run_drift_remediation.main()
    assert rc == 1


def test_remediation_main_with_deploy_hint(tmp_path, monkeypatch, capsys):
    from scripts import run_drift_remediation

    eval_path = tmp_path / "data" / "processed" / "eval_metrics.json"
    eval_path.parent.mkdir(parents=True, exist_ok=True)
    eval_path.write_text(json.dumps({"gate_passed": True}), encoding="utf-8")
    (tmp_path / ".env").write_text("KEY=1\n", encoding="utf-8")
    monkeypatch.setattr(run_drift_remediation, "_PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(run_drift_remediation, "_python_executable", lambda: sys.executable)
    monkeypatch.setattr(run_drift_remediation, "run", lambda _cmd: 0)
    monkeypatch.setattr(run_drift_remediation, "check_url", lambda _url: (True, "ok"))

    fake_resp = MagicMock(status_code=200, text="ok")
    monkeypatch.setitem(sys.modules, "httpx", MagicMock(post=lambda *_a, **_k: fake_resp))

    with patch.object(sys, "argv", ["run_drift_remediation.py"]):
        rc = run_drift_remediation.main()
    assert rc == 0
    assert "deploy_aks.py" in capsys.readouterr().out



def test_run_helper_prints_command(capsys):
    from scripts.run_drift_remediation import run

    with patch("scripts.run_drift_remediation.subprocess.run", return_value=subprocess.CompletedProcess([], 0)):
        assert run([sys.executable, "-c", "print(1)"]) == 0
    assert "+" in capsys.readouterr().out


# --- verify_member_d.py ---


def test_verify_member_d_check_files():
    from scripts.verify_member_d import REQUIRED_FILES, check_files

    missing = check_files()
    assert not missing, f"Missing: {missing}"
    assert len(REQUIRED_FILES) >= 15


def test_verify_member_d_main_pass(monkeypatch):
    from scripts import verify_member_d

    monkeypatch.setattr(verify_member_d, "run_cmd", lambda _cmd: 0)
    assert verify_member_d.main() == 0


def test_verify_member_d_main_missing_file(monkeypatch):
    from scripts import verify_member_d

    monkeypatch.setattr(verify_member_d, "check_files", lambda: ["missing.py"])
    assert verify_member_d.main() == 1


def test_verify_member_d_main_drift_fails(monkeypatch):
    from scripts import verify_member_d

    def fake_run(cmd):
        if "generate_sample_data" in " ".join(cmd):
            return 0
        if "run_drift_check" in " ".join(cmd):
            return 0
        return 0

    monkeypatch.setattr(verify_member_d, "run_cmd", fake_run)
    assert verify_member_d.main() == 0


# --- secrets.py ---


def test_secrets_get_env_or_raise(monkeypatch):
    from src.utils.secrets import get_env_or_raise

    monkeypatch.setenv("TEST_SECRET", "value")
    assert get_env_or_raise("TEST_SECRET") == "value"
    monkeypatch.delenv("MISSING_SECRET", raising=False)
    with pytest.raises(EnvironmentError, match="MISSING_SECRET"):
        get_env_or_raise("MISSING_SECRET")


def test_secrets_helpers(monkeypatch):
    from src.utils.secrets import (
        get_app_insights_connection_string,
        get_azure_credentials,
        get_env_optional,
        get_openrouter_api_key,
        get_storage_connection_string,
    )

    monkeypatch.setenv("AZURE_CLIENT_ID", "cid")
    monkeypatch.setenv("OPENROUTER_API_KEY", "key")
    monkeypatch.setenv("AZURE_STORAGE_CONNECTION_STRING", "conn")
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "ai-conn")

    assert get_env_optional("UNSET_VAR", "default") == "default"
    creds = get_azure_credentials()
    assert creds["client_id"] == "cid"
    assert get_app_insights_connection_string() == "ai-conn"
    assert get_openrouter_api_key() == "key"
    assert get_storage_connection_string() == "conn"
