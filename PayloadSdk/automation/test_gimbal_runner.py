"""
test_gimbal_runner.py
─────────────────────
Focused runner for PayloadSDK gimbal example binaries.
Produces the same HTML + JSON reports as the main regression runner.

Default flow:
1. check_connect
2. gimbal_load_settings
3. gimbal_change_settings
4. gimbal_load_settings
5. gimbal_move_angle
6. gimbal_move_speed
7. gimbal_set_mode
8. gimbal_control_example
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from utils.publish_cli import add_publish_args, maybe_publish_report
from utils.runner import (
    Step,
    configure_logging,
    create_run_report_dir,
    default_log_file,
    default_report_dir,
    example_command,
    run_suite,
    write_report,
)

logger = logging.getLogger(__name__)


def format_mount_orient_expectation(pitch: float, yaw: float) -> str:
    return f"Mount Orient : Pich: {pitch:.2f} - Roll: -0.00 - Yaw: {yaw:.2f}"


def build_steps(args: argparse.Namespace) -> list[Step]:
    def cmd(name: str, *extra: str) -> list[str]:
        return example_command(name, build_dir=args.build_dir) + list(extra)

    return [
        Step(
            name="check_connect",
            command=cmd("check_connect"),
            max_duration=args.connect_duration,
            retries=args.connect_retries,
            retry_delay=args.retry_delay,
            expect_output=["Starting ConnectPayload example", "Waiting for payload signal!"],
            expect_absent=["ERROR", "Segmentation fault"],
            delay_after=2.0,
            tags=["gimbal", "connect"],
        ),
        Step(
            name="gimbal_load_settings_before",
            command=cmd("gimbal_load_settings"),
            max_duration=15.0,
            terminate_on_expect=True,
            expect_output=[
                # SDK transport layer is up
                "START WRITE THREAD",
                # Gimbal handshake complete
                "Payload connected!",
                # All 30 params received — RC_LPF_PAN is the last one (index 29)
                "Gimbal_param: id: RC_LPF_PAN",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["gimbal", "settings"],
        ),
        Step(
            name="gimbal_change_settings",
            command=cmd("gimbal_change_settings"),
            timeout=15.0,
            expect_output=[
                # SDK transport layer is up
                "START WRITE THREAD",
                # Gimbal handshake complete
                "Payload connected!",
                # STIFF_TILT should be reported during the change/verify cycle
                "Gimbal_param: index: 2, id: STIFF_TILT, value:",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["gimbal", "settings"],
        ),
        Step(
            name="gimbal_load_settings_after",
            command=cmd("gimbal_load_settings"),
            max_duration=15.0,
            terminate_on_expect=True,
            expect_output=[
                # SDK transport layer is up
                "START WRITE THREAD",
                # Gimbal handshake complete
                "Payload connected!",
                # All 30 params received — RC_LPF_PAN is the last one (index 29)
                "Gimbal_param: id: GYRO_LPF",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["gimbal", "settings"],
        ),
        Step(
            name="gimbal_move_angle",
            command=cmd(
                "gimbal_move_angle",
                "-p",
                str(args.pitch),
                "-y",
                str(args.yaw),
            ),
            timeout=args.motion_timeout,
            expect_output=[
                "Starting Set gimbal mode example",
                f"Move gimbal pitch to {args.pitch:.2f} deg, yaw to {args.yaw:.2f} deg",
                format_mount_orient_expectation(args.pitch, args.yaw),
            ],
            expect_absent=["Invalid pitch value", "Invalid yaw value", "ERROR", "Segmentation fault"],
            delay_after=1.0,
            tags=["gimbal", "motion"],
        ),
        Step(
            name="gimbal_move_speed",
            command=cmd("gimbal_move_speed"),
            timeout=args.motion_timeout,
            expect_output=[
                "Starting Set gimbal mode example",
                "Payload connected!",
                "Set gimbal RC mode",
                "Move gimbal yaw to the right 20 deg/s, delay in 5secs",
                "Move gimbal yaw to the left 20 deg/s, delay in 5secs",
                "Keep gimbal stop, delay in 5secs",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["gimbal", "motion"],
        ),
        Step(
            name="gimbal_set_mode",
            command=cmd("gimbal_set_mode"),
            timeout=args.set_mode_timeout,
            expect_output=[
                "Starting Set gimbal mode example",
                "Payload connected!",
                "Gimbal set mode LOCK, delay in 5 secs",
                "Gimbal set mode FOLLOW, delay in 5 secs",
                "Gimbal set mode MAPPING, delay in 5 secs",
                "Gimbal set mode OFF, delay in 5 secs",
                "Gimbal set mode RESET, delay in 5 secs",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["gimbal", "mode"],
        ),
        Step(
            name="gimbal_control_example",
            command=cmd("gimbal_control_example"),
            timeout=args.control_timeout,
            expect_output=[
                "Starting Set gimbal mode example",
                "Payload connected!",
                "Gimbal set mode FOLLOW, delay in 3 secs",
                "Move gimbal angular velocity: pitch = -20 deg/s, yaw = 50 deg/s, delay in 3 secs",
                "Gimbal set re-center YAW ------",
                "Gimbal set re-center PITCH ------",
                "Move gimbal angular position: pitch = -40 deg, yaw = 90 deg, delay in 3 secs",
                "Delay in 3 secs before changing to LOCK MODE",
                "Gimbal set mode LOCK, delay in 3 secs",
                "Move gimbal angular velocity: pitch = 20 deg/s, yaw = -50 deg/s, delay in 3 secs",
                "Move gimbal angular position: pitch = 40 deg, yaw = -90 deg, delay in 3 secs",
                "Delay in 3 secs before changing to FOLLOW MODE",
                "Delay in 3 secs before changing to MAPPING MODE",
                "Gimbal set mode MAPPING, delay in 5 secs",
                "Gimbal set mode RESET, delay in 5 secs",
                "Gimbal set mode OFF, delay in 5 secs",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["gimbal", "mode", "control"],
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PayloadSDK gimbal-only test runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--build-dir",       default="build/examples", help="Path to compiled example binaries")
    parser.add_argument("--report-dir",      default=None,             help="Directory for run reports and summaries")
    parser.add_argument("--log-file",        default=None,             help="Optional log file path")
    parser.add_argument("--log-level",       default="INFO",           choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--connect-duration", type=float, default=8.0,  help="How long to observe check_connect before stopping it")
    parser.add_argument("--load-duration",    type=float, default=8.0,  help="How long to observe gimbal_load_settings before stopping it")
    parser.add_argument("--command-timeout",  type=float, default=20.0, help="Timeout for self-exiting settings commands")
    parser.add_argument("--motion-timeout",   type=float, default=20.0, help="Timeout for gimbal motion examples")
    parser.add_argument("--set-mode-timeout", type=float, default=30.0, help="Timeout for gimbal_set_mode")
    parser.add_argument("--control-timeout",  type=float, default=130.0, help="Timeout for gimbal_control_example")
    parser.add_argument("--connect-retries",  type=int,   default=2,    help="Retries for connection step")
    parser.add_argument("--retry-delay",      type=float, default=3.0,  help="Seconds between retries")
    parser.add_argument("--pitch",            type=float, default=-10.0, help="Pitch angle passed to gimbal_move_angle")
    parser.add_argument("--yaw",              type=float, default=15.0,  help="Yaw angle passed to gimbal_move_angle")
    parser.add_argument("--stop-on-failure",  action="store_true",       help="Abort suite after first failure")
    parser.add_argument("--only",             nargs="*", default=None,   help="Run only steps with these names")
    parser.add_argument("--skip",             nargs="*", default=None,   help="Skip steps with these names")
    parser.add_argument("--dry-run",          action="store_true",       help="Print steps without running them")
    add_publish_args(parser)
    return parser.parse_args()


def filter_steps(steps: list[Step], args: argparse.Namespace) -> list[Step]:
    if args.only:
        steps = [s for s in steps if s.name in args.only]
    if args.skip:
        for step in steps:
            if step.name in args.skip:
                step.enabled = False
    return steps


def main():
    args = parse_args()
    args.report_dir = str(create_run_report_dir(args.report_dir or default_report_dir(), prefix="gimbal"))
    args.log_file = args.log_file or default_log_file(args.report_dir, prefix="gimbal")
    configure_logging(level=args.log_level, log_file=args.log_file)

    steps = filter_steps(build_steps(args), args)
    active = [step for step in steps if step.enabled]
    inactive = [step for step in steps if not step.enabled]

    logger.info("PayloadSDK Gimbal Test Runner")
    logger.info("Build dir : %s", args.build_dir)
    logger.info("Steps     : %d active, %d skipped", len(active), len(inactive))

    if args.dry_run:
        print("\nDRY RUN — steps that would execute:\n")
        for index, step in enumerate(active, 1):
            limit = step.max_duration if step.max_duration is not None else step.timeout
            mode = "max_duration" if step.max_duration is not None else "timeout"
            print(f"  {index:2d}. {step.name}  [{mode}={limit}s]")
            print(f"      cmd    : {step.command}")
            print(f"      expect : {step.expect_output}")
            print(f"      tags   : {step.tags}")
        print(f"\nSkipped: {[step.name for step in inactive]}\n")
        return

    def _on_done(result):
        icon = "PASS" if result.status == "PASS" else ("SKIP" if result.status == "SKIP" else "FAIL")
        logger.info("%s  %-30s %s  %.1fs", icon, result.step.name, result.status, result.duration)

    suite = run_suite(steps, stop_on_failure=args.stop_on_failure, on_step_done=_on_done)

    logger.info("")
    logger.info("=" * 55)
    logger.info(
        "  RESULTS:  %d passed  %d failed  %d skipped  (%.1fs total)",
        suite.passed,
        suite.failed,
        suite.skipped,
        suite.duration,
    )
    logger.info("=" * 55)

    paths = write_report(suite, output_dir=args.report_dir, report_prefix="gimbal")
    maybe_publish_report(args, paths["html"])
    logger.info("LOG file    -> %s", args.log_file)

    sys.exit(0 if suite.failed == 0 else 1)


if __name__ == "__main__":
    main()
