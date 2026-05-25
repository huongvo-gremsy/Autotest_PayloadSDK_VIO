"""
utils/runner.py
───────────────
Core primitives for running C++ example binaries that may:
  • exit on their own   (well-behaved examples)
  • loop forever        (camera/gimbal stream examples that need Ctrl+C)

Key design
──────────
  Step.max_duration      : hard wall-clock limit before the process is killed
  Step.terminate_on_expect: kill early once all expect_output strings are seen
  Step.expect_output     : strings that MUST appear in stdout/stderr
  Step.expect_absent     : strings that must NOT appear (error detection)

Termination sequence for loop processes
────────────────────────────────────────
  1. SIGINT  (equivalent to Ctrl+C) — gives the process a chance to clean up
  2. wait 2 s
  3. SIGTERM — standard termination
  4. wait 2 s
  5. SIGKILL — force kill
"""

from __future__ import annotations

import logging
import os
import re
import shlex
import signal
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Sequence

logger = logging.getLogger(__name__)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Data classes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@dataclass
class Step:
    """
    One test step = one C++ binary invocation.

    Parameters
    ──────────
    name              : human-readable label shown in report
    command           : list or shell string — the binary + its arguments
    timeout           : seconds to wait for the process to EXIT ON ITS OWN
                        (use for examples that self-terminate)
    max_duration      : hard wall-clock cap; process is SIGINT'd after this
                        (use for infinite-loop examples)
                        Set to None to disable (rely on timeout alone).
    expect_output     : strings that must appear in combined stdout+stderr
    expect_absent     : strings that must NOT appear (e.g. "ERROR", "Segfault")
    terminate_on_expect: send SIGINT as soon as all expect_output strings seen
    delay_after       : seconds to sleep after the step finishes
    env               : extra environment variables (merged with os.environ)
    cwd               : working directory for the subprocess
    retries           : how many times to retry on failure
    retry_delay       : seconds between retries
    enabled           : set False to skip this step
    tags              : arbitrary labels for filtering (e.g. ["smoke", "eo"])
    """
    name: str
    command: str | list
    timeout: float = 30.0
    max_duration: Optional[float] = None      # None = no hard cap
    expect_output: List[str] = field(default_factory=list)
    expect_absent: List[str] = field(default_factory=list)
    terminate_on_expect: bool = False
    delay_after: float = 0.0
    env: dict = field(default_factory=dict)
    cwd: Optional[str] = None
    retries: int = 0
    retry_delay: float = 2.0
    enabled: bool = True
    tags: List[str] = field(default_factory=list)


@dataclass
class StepResult:
    """Result of a single Step execution."""
    step: Step
    passed: bool
    output: str                        # combined stdout + stderr
    return_code: Optional[int]
    duration: float                    # seconds
    started_at: datetime
    finished_at: datetime
    failure_reason: str = ""
    attempt: int = 1

    @property
    def status(self) -> str:
        if not self.step.enabled:
            return "SKIP"
        return "PASS" if self.passed else "FAIL"


@dataclass
class SuiteResult:
    """Aggregated result of the full regression run."""
    results: List[StepResult] = field(default_factory=list)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None

    @property
    def total(self):    return len(self.results)
    @property
    def passed(self):   return sum(1 for r in self.results if r.status == "PASS")
    @property
    def failed(self):   return sum(1 for r in self.results if r.status == "FAIL")
    @property
    def skipped(self):  return sum(1 for r in self.results if r.status == "SKIP")
    @property
    def duration(self):
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return 0.0


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Process runner
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _kill_process(proc: subprocess.Popen, step_name: str):
    """
    Graceful termination sequence:
      SIGINT → 2 s → SIGTERM → 2 s → SIGKILL
    """
    if proc.poll() is not None:
        return   # already dead

    logger.info("[%s] Sending SIGINT (Ctrl+C equivalent)…", step_name)
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
    except (ProcessLookupError, PermissionError):
        proc.send_signal(signal.SIGINT)

    for _ in range(20):          # wait up to 2 s
        if proc.poll() is not None:
            return
        time.sleep(0.1)

    if proc.poll() is None:
        logger.warning("[%s] Still alive after SIGINT, sending SIGTERM…", step_name)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            proc.terminate()

    for _ in range(20):
        if proc.poll() is not None:
            return
        time.sleep(0.1)

    if proc.poll() is None:
        logger.error("[%s] Still alive after SIGTERM, sending SIGKILL.", step_name)
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()


def _run_once(step: Step) -> StepResult:
    """Execute one Step and return a StepResult."""
    started_at = datetime.now(timezone.utc)
    output_lines: List[str] = []
    output_lock = threading.Lock()
    found_expect: set = set()
    killed_reason = ""

    cmd = step.command if isinstance(step.command, list) else shlex.split(step.command)
    env = {**os.environ, **step.env}
    cwd = step.cwd or os.getcwd()

    logger.info("━━ [%s] Starting: %s", step.name, " ".join(cmd))

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            cwd=cwd,
            text=True,
            bufsize=1,
            start_new_session=True,   # allows killpg
        )
    except FileNotFoundError:
        finished_at = datetime.now(timezone.utc)
        return StepResult(
            step=step,
            passed=False,
            output="",
            return_code=None,
            duration=(finished_at - started_at).total_seconds(),
            started_at=started_at,
            finished_at=finished_at,
            failure_reason=f"Binary not found: {cmd[0]}",
        )

    stop_event = threading.Event()

    def _reader():
        """Read stdout/stderr line by line; check expect_output in real time."""
        for line in proc.stdout:
            line = line.rstrip("\n")
            with output_lock:
                output_lines.append(line)
            logger.debug("[%s] %s", step.name, line)

            # Track which expected strings have appeared
            for expected in step.expect_output:
                if expected in line:
                    found_expect.add(expected)

            # Terminate early once all expected strings seen
            if (
                step.terminate_on_expect
                and set(step.expect_output) == found_expect
                and not stop_event.is_set()
            ):
                logger.info(
                    "[%s] All expected outputs found — terminating early.", step.name
                )
                stop_event.set()
                _kill_process(proc, step.name)
                break

    reader_thread = threading.Thread(target=_reader, daemon=True)
    reader_thread.start()

    # ── Timeout / max_duration watchdog ────────────────────────────────────
    effective_limit = step.max_duration if step.max_duration is not None else step.timeout

    watchdog_fired = threading.Event()

    def _watchdog():
        if not stop_event.wait(timeout=effective_limit):
            # Limit reached before early-termination or natural exit
            nonlocal killed_reason
            if step.max_duration is not None and proc.poll() is None:
                killed_reason = f"max_duration={step.max_duration}s reached"
                logger.info("[%s] %s — sending SIGINT.", step.name, killed_reason)
            else:
                killed_reason = f"timeout={step.timeout}s reached"
                logger.warning("[%s] %s — killing process.", step.name, killed_reason)
            stop_event.set()
            _kill_process(proc, step.name)
        watchdog_fired.set()

    watchdog = threading.Thread(target=_watchdog, daemon=True)
    watchdog.start()

    # Wait for process to finish
    try:
        proc.wait(timeout=effective_limit + 10)
    except subprocess.TimeoutExpired:
        _kill_process(proc, step.name)
        proc.wait()

    stop_event.set()   # signal watchdog to exit if still waiting
    reader_thread.join(timeout=5)
    watchdog.join(timeout=5)

    finished_at = datetime.now(timezone.utc)
    duration = (finished_at - started_at).total_seconds()
    return_code = proc.returncode
    output = "\n".join(output_lines)

    # ── Evaluate pass/fail ──────────────────────────────────────────────────
    failures = []

    missing = [e for e in step.expect_output if e not in found_expect]
    if missing:
        failures.append(f"Missing expected output: {missing}")

    for absent in step.expect_absent:
        if absent in output:
            failures.append(f"Forbidden string found in output: {absent!r}")

    # A process killed by SIGINT/SIGTERM for max_duration is not a failure
    # (it was a controlled stop). Only flag non-zero exit as failure when
    # the process exited on its own (no max_duration kill).
    if not killed_reason and return_code not in (0, -signal.SIGINT, -signal.SIGTERM):
        failures.append(f"Non-zero exit code: {return_code}")

    passed = len(failures) == 0
    failure_reason = "; ".join(failures)

    status = "PASS" if passed else "FAIL"
    logger.info(
        "── [%s] %s  (%.1fs, rc=%s)%s",
        step.name, status, duration, return_code,
        f"  ✗ {failure_reason}" if not passed else "",
    )

    if step.delay_after:
        logger.info("[%s] Waiting %.1fs before next step…", step.name, step.delay_after)
        time.sleep(step.delay_after)

    return StepResult(
        step=step,
        passed=passed,
        output=output,
        return_code=return_code,
        duration=duration,
        started_at=started_at,
        finished_at=finished_at,
        failure_reason=failure_reason,
    )


def run_step(step: Step) -> StepResult:
    """Run a Step with retries."""
    if not step.enabled:
        now = datetime.now(timezone.utc)
        logger.info("── [%s] SKIP (disabled)", step.name)
        return StepResult(
            step=step, passed=True, output="", return_code=None,
            duration=0.0, started_at=now, finished_at=now,
            failure_reason="skipped",
        )

    result = None
    for attempt in range(1, step.retries + 2):
        result = _run_once(step)
        result.attempt = attempt
        if result.passed:
            break
        if attempt <= step.retries:
            logger.warning(
                "[%s] Attempt %d/%d failed — retrying in %.1fs…",
                step.name, attempt, step.retries + 1, step.retry_delay,
            )
            time.sleep(step.retry_delay)
    return result


def run_suite(
    steps: List[Step],
    stop_on_failure: bool = False,
    on_step_done: Optional[Callable[[StepResult], None]] = None,
) -> SuiteResult:
    """Run a list of Steps in order and return a SuiteResult."""
    suite = SuiteResult(started_at=datetime.now(timezone.utc))
    for step in steps:
        result = run_step(step)
        suite.results.append(result)
        if on_step_done:
            on_step_done(result)
        if stop_on_failure and not result.passed and result.status != "SKIP":
            logger.error("Stop-on-failure triggered at step '%s'.", step.name)
            break
    suite.finished_at = datetime.now(timezone.utc)
    return suite


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Helpers used by regression_runner.py
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def example_command(name: str, build_dir: str = "build/examples") -> list:
    """Return the command list for a named example binary."""
    return [str(Path(build_dir) / name)]


def configure_logging(level: str = "INFO", log_file: Optional[str] = None):
    handlers = [logging.StreamHandler()]
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
        handlers=handlers,
        force=True,
    )


def default_report_dir() -> Path:
    """Return the default automation report directory."""
    return Path(__file__).resolve().parent.parent / "report"


def create_run_report_dir(base_dir: str | Path | None = None, prefix: str = "regression") -> Path:
    """Create and return a timestamped per-run report directory."""
    root_dir = Path(base_dir) if base_dir else default_report_dir()
    run_dir = root_dir / f"{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def default_log_file(output_dir: str | Path, prefix: str = "regression") -> str:
    """Return a timestamped log-file path inside the report directory."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return str(Path(output_dir) / f"{prefix}_{ts}.log")


def write_report(
    suite: SuiteResult,
    output_dir: str | Path | None = None,
    report_prefix: str = "regression",
) -> dict:
    """Write HTML, JSON, and text summary reports. Returns paths dict."""
    from utils.report import render_html, render_json, render_text_summary
    output_dir = Path(output_dir) if output_dir else default_report_dir()
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = str(Path(output_dir) / f"{report_prefix}_{ts}.json")
    html_path = str(Path(output_dir) / f"{report_prefix}_{ts}.html")
    txt_path = str(Path(output_dir) / f"{report_prefix}_{ts}.txt")
    render_json(suite, json_path)
    render_html(suite, html_path)
    render_text_summary(suite, txt_path)
    logger.info("Report written → %s", html_path)
    return {"json": json_path, "html": html_path, "txt": txt_path}
