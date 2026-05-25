"""
test_camera_eo_runner.py
────────────────────────
Focused runner for PayloadSDK EO camera example binaries.
Produces the same HTML + JSON reports as the main regression runner.

Default flow:
1. check_connect
2. camera_change_settings
3. camera_do_setzoom_individual
4. camera_eo_capture_image
5. camera_eo_record_video
6. camera_eo_set_shutter_speed
7. camera_eo_set_zoom_focus
8. camera_eo_trigger_wb_onepush
9. camera_ir_capture_image
10. camera_ir_record_video
11. camera_ir_set_palette
12. camera_ir_set_zoom
13. camera_ir_do_ffc_control
14. camera_ir_isotherm_profile
"""

from __future__ import annotations

import argparse
import logging
import sys

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
            tags=["camera", "eo", "connect"],
        ),
        Step(
            name="camera_eo_capture_image",
            command=cmd("camera_eo_capture_image"),
            timeout=args.capture_timeout,
            expect_output=[
                "Starting CaptureImage example...",
                "Waiting for payload signal!",
                "Payload connected!",
                "Got payload storage info:",
                "   ---> Storage ready, check capture status",
                "Got payload capture status: image_status: 0.00, video_status: 0.00",
                "   ---> Payload is idle, Check camera mode",
                "   ---> Payload in Image mode, do capture image",
                "   ---> Payload is completed capture image, Do next sequence 0",
                "CLOSE PORT",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "eo", "capture"],
        ),
        Step(
            name="camera_eo_record_video",
            command=cmd("camera_eo_record_video"),
            timeout=args.record_timeout,
            expect_output=[
                "Starting RecordVideo example...",
                "Waiting for payload signal!",
                "Payload connected!",
                "[EO] Forcing view source to EO...",
                "Got payload storage info:",
                "   ---> Storage ready, check capture status",
                "Got payload capture status: image_status: 0.00, video_status: 0.00",
                "   ---> Payload is idle, Check camera mode",
                "Got camera mode: 1.00",
                "   ---> Payload in Image mode, do capture image",
                "Payload is recording video in 10s, wait...",
                "   ---> Payload is completed record video",
                "CLOSE PORT",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "eo", "record"],
        ),
        Step(
            name="camera_eo_set_shutter_speed",
            command=cmd("camera_eo_set_shutter_speed"),
            max_duration=args.shutter_timeout,
            expect_output=[
                "Starting SetShutterSpeed example...",
                "Waiting for payload signal!",
                "Payload connected!",
                "[EO] Forcing view source to EO...",
                "Shutter (C_V_SP): 1/10 (code 13)",
                "Shutter (C_V_SP): 1/1000 (code 27)",
                "TERMINATING AT USER REQUEST",
                "CLOSE PORT",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            terminate_on_expect=True,
            delay_after=1.0,
            tags=["camera", "eo", "shutter"],
        ),
        Step(
            name="camera_eo_set_zoom_focus",
            command=cmd("camera_eo_set_zoom_focus"),
            timeout=args.zoom_focus_timeout,
            expect_output=[
                "Starting CaptureImage example...",
                "Waiting for payload signal!",
                "Payload connected!",
                "Set view source to EO! ",
                " --> Got ack, from command: 511 - result: 0.00",
                "Set zoom level to 1x !",
                "Zoom In 4 times!",
                " --> Got ack, from command: 531 - result: 0.00",
                "Zoom Out 2 times!",
                "Start Zoom In!",
                "Stop Zoom!",
                "Start Zoom Out!",
                "Zoom Range 50%!",
                "Zoom Range 70%!",
                "Zoom Range 100%!",
                "Zoom Range 0%!",
                "Start Focus In!",
                " --> Got ack, from command: 532 - result: 0.00",
                "Stop Focus!",
                "Start Focus Out!",
                "Auto Focus!",
                "!--------------------! ",
                "CLOSE PORT",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "eo", "zoom", "focus"],
        ),

        Step(
            name="camera_eo_trigger_wb_onepush",
            command=cmd("camera_eo_trigger_wb_onepush"),
            max_duration=args.wb_duration,
            expect_output=[
                "Starting Triiger WB sample example...",
                "Payload connected!",
                "send trigger command_____test",

            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "eo", "white-balance"],
        ),

        Step(
            name="camera_ir_capture_image",
            command=cmd("camera_ir_capture_image"),
            timeout=args.capture_timeout,
            expect_output=[
                "Starting CaptureImage example...",
                "Waiting for payload signal!",
                "[IR] Forcing view source to IR...",
                "Got payload storage info:",
                "   ---> Storage ready, check capture status",
                "Got payload capture status: image_status: 0.00, video_status: 0.00",
                "   ---> Payload is idle, Check camera mode",
                "   ---> Payload in Image mode, do capture image",
                "   ---> Payload is completed capture image, Do next sequence 0",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "ir", "capture"],
        ),
        Step(
            name="camera_ir_record_video",
            command=cmd("camera_ir_record_video"),
            timeout=args.record_timeout,
            expect_output=[
                "Starting RecordVideo example...",
                "Waiting for payload signal!",
                "[IR] Forcing view source to IR...",
                "Got payload storage info:",
                "   ---> Storage ready, check capture status",
                "Got payload capture status: image_status: 0.00, video_status: 0.00",
                "   ---> Payload is idle, Check camera mode",
                "Got camera mode: 1.00",
                "Payload is recording video in 10s, wait...",
                "   ---> Payload is completed record video",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "ir", "record"],
        ),
        Step(
            name="camera_ir_set_palette",
            command=cmd("camera_ir_set_palette"),
            timeout=args.command_timeout,
            expect_output=[
                "Waiting for payload signal!",
                "[IR] Forcing view source to IR...",
                "Starting set palete example...",
                " --> SET:      F1: WhiteHot         |       G1: WhiteHot",
                " --> SET:      F1: Hottest          |       G1: BlackHot",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "ir", "palette"],
        ),
        Step(
            name="camera_ir_set_zoom",
            command=cmd("camera_ir_set_zoom"),
            timeout=args.zoom_focus_timeout,
            expect_output=[
                "Starting CaptureImage example...",
                "Waiting for payload signal!",
                "Set view source to IR!",
                "Set zoom level to 1x !",
                "Zoom In 4 times!",
                "Zoom Out 2 times!",
                "Start Zoom In!",
                "Stop Zoom!",
                "Start Zoom Out!",
                "Zoom Range 50%!",
                "Zoom Range 70%!",
                "Zoom Range 100%!",
                "Zoom Range 0%!",
                "!--------------------!",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "ir", "zoom"],
        ),
        Step(
            name="camera_ir_do_ffc_control",
            command=cmd("camera_ir_do_ffc_control"),
            timeout=args.do_ffc_control_timeout,
            expect_output=[
                "Starting IR FFC Control example...",
                "Waiting for payload signal!",
                "[IR] Forcing view source to IR...",
                "Change FFC to Auto, waiting for 5secs.",
                "Change FFC to Manual, waiting for 5secs.",
                "Trigger FFC, 1",
                "Trigger FFC, 5",
                "Done. Exit...",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "ir", "ffc"],
        ),
        Step(
            name="camera_ir_isotherm_profile",
            command=cmd("camera_ir_isotherm_profile"),
            max_duration=args.ir_isotherm_duration,
            expect_output=[
                "Starting IR Isotherm Profile example...",
                "Waiting for payload signal!",
                "Enable the isotherm",
                "Disable all isotherm region to clear the previous settings",
                "Set the IR gain to High",
                "Set the Unit to Celsius",
                "Apply the settings for region 1",
                "Now the region 1 was configured for detecting the human's body temperature",
                "Change profile to Human Detect",
                "Now the region 1 was configured for detecting the fires",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "ir", "isotherm"],
        ),
        Step(
            name="camera_time_lapse_photography",
            command=cmd("camera_time_lapse_photography"),
            timeout=args.command_timeout,
            expect_output=[
                "Starting CaptureImage example...",
                "Waiting for payload signal!",
                "Payload connected!",
                "Payload is capturing image elapsed time between 3.0s, within 12s, wait...",
                "---> Payload is completed capture image",
                "CLOSE PORT",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "eo", "settings"],
        ),

        Step(
            name="camera_change_settings",
            command=cmd("camera_change_settings"),
            timeout=args.command_timeout,
            expect_output=[
                "Starting SetPayloadSettings example...",
                "Waiting for payload signal!",
                "Payload connected!",
                "------------------------> Init values",
                " --> Param_id: CAM_MODE, value: 1.00",
                "Change some params",
                "------------------------> Changed values",
                " --> Param_id: TRACK_MODE, value: 0.00",
                "CLOSE PORT",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "eo", "settings"],
        ),
        Step(
            name="camera_load_settings",
            command=cmd("camera_load_settings"),
            timeout=args.command_timeout,
            expect_output=[
                "Starting LoadPayloadSettings example...",
                "Waiting for payload signal!",
                "Payload connected!",
                " --> Param_id: CAM_MODE, value: 1.00",
                "--> Param_id: TRACK_MODE, value:",
                "CLOSE PORT",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["camera", "eo", "settings"],
        ),
        Step(
            name="camera_do_setzoom_individual",
            command=cmd("camera_do_setzoom_individual"),
            timeout=args.zoom_individual_timeout,
            expect_output=[
                "[Init] Starting payload zoom control example...",
                "[Init] Waiting for payload handshake...",
                "Payload connected!",
                "[EO] Switching zoom mode to Super Resolution...",
                "[EO] Forcing view source to EO over IR composite...",
                "[EO] Setting Super Resolution zoom to 1x.",
                "[EO] Stepping Super Resolution zoom up to 4x.",
                "[EO] Driving Super Resolution zoom to 30x.",
                "[EO] Switching to Combine zoom mode for extended range...",
                "[EO] Combine zoom: resetting to 1x.",
                "[EO] Combine zoom: jumping to 40x.",
                "[EO] Combine zoom: pushing to 240x.",
                "[IR] Switching view source to IR over EO composite...",
                "[IR] Setting zoom to 1x.",
                "[IR] Stepping zoom to 4x.",
                "[IR] Increasing zoom to 8x for maximum magnification.",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            terminate_on_expect=True,
            delay_after=1.0,
            tags=["camera", "eo", "zoom"],
        ),

    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PayloadSDK EO camera-only test runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--build-dir", default="build/examples", help="Path to compiled example binaries")
    parser.add_argument("--report-dir", default=None, help="Directory for run reports and summaries")
    parser.add_argument("--log-file", default=None, help="Optional log file path")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--connect-duration", type=float, default=8.0, help="How long to observe check_connect before stopping it")
    parser.add_argument("--command-timeout", type=float, default=25.0, help="Default timeout for EO commands")
    parser.add_argument("--capture-timeout", type=float, default=30.0, help="Timeout for camera_eo_capture_image")
    parser.add_argument("--record-timeout", type=float, default=30.0, help="Timeout for camera_eo_record_video")
    parser.add_argument("--shutter-timeout", type=float, default=20.0, help="Timeout for camera_eo_set_shutter_speed")
    parser.add_argument("--zoom-focus-timeout", type=float, default=60.0, help="Timeout for camera_eo_set_zoom_focus")
    parser.add_argument("--ir-isotherm-duration", type=float, default=25.0, help="How long to observe camera_ir_isotherm_profile before stopping it")
    parser.add_argument("--zoom-individual-timeout", type=float, default=55.0, help="Timeout for camera_do_setzoom_individual")
    parser.add_argument("--wb-duration", type=float, default=5.0, help="How long to observe camera_eo_trigger_wb_onepush before stopping it")
    parser.add_argument("--connect-retries", type=int, default=2, help="Retries for connection step")
    parser.add_argument("--retry-delay", type=float, default=3.0, help="Seconds between retries")
    parser.add_argument("--stop-on-failure", action="store_true", help="Abort suite after first failure")
    parser.add_argument("--only", nargs="*", default=None, help="Run only steps with these names")
    parser.add_argument("--skip", nargs="*", default=None, help="Skip steps with these names")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without running them")
    parser.add_argument("--do-ffc-control-timeout", type=float, default=28.0, help="Timeout for camera ir do ffc control")
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
    args.report_dir = str(create_run_report_dir(args.report_dir or default_report_dir(), prefix="camera_runner"))
    args.log_file = args.log_file or default_log_file(args.report_dir, prefix="camera_runner")
    configure_logging(level=args.log_level, log_file=args.log_file)

    steps = filter_steps(build_steps(args), args)
    active = [step for step in steps if step.enabled]
    inactive = [step for step in steps if not step.enabled]

    logger.info("PayloadSDK Camera Test Runner")
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

    write_report(suite, output_dir=args.report_dir, report_prefix="camera_runner")
    logger.info("LOG file    -> %s", args.log_file)

    sys.exit(0 if suite.failed == 0 else 1)


if __name__ == "__main__":
    main()
