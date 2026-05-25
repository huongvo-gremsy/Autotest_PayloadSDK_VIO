"""
test_payload_runner.py
──────────────────────
Focused runner for PayloadSDK payload example binaries.
Produces the same HTML + JSON reports as the other automation runners.

Default flow:
1. payload_do_object_detection
2. payload_do_object_tracking
3. payload_download_media_files
4. payload_extract_tiff_file
5. payload_get_component_info
6. payload_get_fov_status
7. payload_get_status
8. payload_get_video_streaming
9. payload_set_camera_zoom_targetpos
10. payload_set_gps
11. payload_set_stream_bitrate
12. payload_set_stream_profile
13. payload_set_stream_resolution
14. payload_set_system_time
"""

from __future__ import annotations

import argparse
import logging
import random
import sys
from pathlib import Path

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


def validate_stream_resolution(device: int, resolution: int, parser: argparse.ArgumentParser) -> None:
    valid_ranges = {
        1: range(0, 3),  # EO: 1920x1080, 1280x720, 960x540
        2: range(0, 5),  # IR: 1280x1024, 640x512, 480x384, 320x256, 160x128
    }
    if resolution not in valid_ranges[device]:
        labels = {
            1: "EO resolutions: 0=1920x1080, 1=1280x720, 2=960x540",
            2: "IR resolutions: 0=1280x1024, 1=640x512, 2=480x384, 3=320x256, 4=160x128",
        }
        parser.error(f"--stream-resolution {resolution} is invalid for --stream-device {device}. {labels[device]}")


def pick_random_stream_resolution_pair() -> tuple[int, int]:
    device = random.choice([1, 2])
    resolution_choices = {
        1: [0, 1, 2],
        2: [0, 1, 2, 3, 4],
    }
    return device, random.choice(resolution_choices[device])


def build_steps(args: argparse.Namespace) -> list[Step]:
    def cmd(name: str, *extra: str) -> list[str]:
        return example_command(name, build_dir=args.build_dir) + list(extra)

    tiff_enabled = bool(args.tiff_file)
    tiff_path = str(Path(args.tiff_file).expanduser()) if args.tiff_file else ""
    random_stream_resolution_2 = pick_random_stream_resolution_pair()
    random_stream_resolution_3 = pick_random_stream_resolution_pair()

    return [
        Step(
            name="payload_do_object_detection",
            command=cmd("payload_do_object_detection"),
            timeout=args.object_detection_timeout,
            expect_output=[
                "Starting Set gimbal mode example...",
                "Waiting for payload signal!",
                "Set view source to EO!",
                "Enable object detection, delay in 10 secs",
                "Disable object detection. Exit!",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "tracking", "detection"],
        ),
        Step(
            name="payload_do_object_tracking",
            command=cmd("payload_do_object_tracking"),
            max_duration=args.object_tracking_duration,
            expect_output=[
                "Starting Do Object Tracking example...",
                "Waiting for payload signal!",
                "Thread created",
                "Active the tracker",
                "Start tracking new object",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED", "Error: Can not create thread!"],
            delay_after=1.0,
            tags=["payload", "tracking"],
        ),
        Step(
            name="payload_download_media_files",
            command=cmd("payload_download_media_files", *([args.download_dir] if args.download_dir else [])),
            max_duration=args.download_media_duration,
            expect_output=[
                "IP Address:",
                "Select an option:",
                "1. List media files",
                "2. Download a Image or a Video",
                "3. Download all Images",
                "4. Download all Videos",
                "Enter 'q' to quit",
            ],
            expect_absent=["Segmentation fault"],
            delay_after=1.0,
            tags=["payload", "media", "download"],
        ),
        Step(
            name="payload_extract_tiff_file",
            command=cmd("payload_extract_tiff_file", tiff_path) if tiff_enabled else cmd("payload_extract_tiff_file"),
            timeout=args.extract_tiff_timeout,
            expect_output=["Temp Data:"] if tiff_enabled else ["Usage: ./payload_extract_tiff_file <path_to_image>"],
            expect_absent=["Get Raw Temp Data error", "Could not open or find the image", "Image is not 16-bit grayscale."],
            enabled=tiff_enabled,
            delay_after=1.0,
            tags=["payload", "thermal", "tiff"],
        ),
        Step(
            name="payload_get_component_info",
            command=cmd("payload_get_component_info"),
            max_duration=args.component_info_duration,
            expect_output=[
                "Starting Triiger WB sample example...",
                "Waiting for payload signal!",
                " --> Got Component Info,",
                " -->  Model name:",
                " -->  Software version:",
                " -->  Serial number:",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "info"],
        ),
        Step(
            name="payload_get_fov_status",
            command=cmd("payload_get_fov_status"),
            max_duration=args.fov_status_duration,
            expect_output=[
                "Starting SendSystemTime example...",
                "Waiting for payload signal!",
                "Camera ID:",
                "HFOV:",
                "VFOV:",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "camera", "fov"],
        ),
        Step(
            name="payload_get_status",
            command=cmd("payload_get_status"),
            max_duration=args.status_duration,
            expect_output=[
                "Starting Set gimbal mode example...",
                "Waiting for payload signal!",
                "Payload EO_ZOOM_LEVEL:",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "status"],
        ),
        Step(
            name="payload_get_video_streaming",
            command=cmd("payload_get_video_streaming"),
            max_duration=args.video_streaming_duration,
            expect_output=[
                "Starting GetStreaming example...",
                "Waiting for payload signal!",
                "Send request to read camera's information",
                "Send request to read camera's information",
                "---> Got payload has streaming video, Check streaming URI",
                "---> Got streaming information: ",
                "Gstreamer thread created"
            ],
            expect_absent=["Segmentation fault", "could not construct pipeline"],
            delay_after=1.0,
            tags=["payload", "streaming", "video"],
        ),
        Step(
            name="payload_set_camera_zoom_targetpos",
            command=cmd("payload_set_camera_zoom_targetpos"),
            max_duration=args.zoom_target_duration,
            expect_output=[
                "Starting Zoom camera to specific level example...",
                "Waiting for payload signal!",
                "[EO] Switching to Combine zoom mode for extended range...",
                "[EO] zoom EO camera to 1x",
                "[EO] zoom EO camera to 13.5x",
                "[EO] Switching to Combine zoom mode for extended range..."
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "camera", "zoom"],
        ),
        Step(
            name="payload_set_gps",
            command=cmd("payload_set_gps"),
            max_duration=args.gps_duration,
            expect_output=[
                "Starting SendGPS example with moving coordinates...",
                "Route: New York City -> Philadelphia",
                "Waiting for payload signal!",
                "GPS Fix Type:",
                "Send GPS_RAW_INT to payload:",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "gps"],
        ),
        Step(
            name="payload_set_stream_bitrate",
            command=cmd(
                "payload_set_stream_bitrate",
                "-d",
                str(args.stream_device),
                "-b",
                str(args.stream_bitrate),
            ),
            timeout=args.stream_command_timeout,
            expect_output=[
                "Starting SetStreamBitrate example...",
                "Waiting for payload signal...",
                "[INFO] Target camera:",
                f"[INFO] Requested bitrate: {args.stream_bitrate} bps",
                "[SUCCESS] Stream bitrate for",
            ],
            expect_absent=["[ERROR]", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "stream", "bitrate"],
        ),
        Step(
            name="payload_set_stream_profile",
            command=cmd(
                "payload_set_stream_profile",
                "-d",
                str(args.stream_device),
                "-p",
                str(args.stream_profile),
            ),
            timeout=args.stream_command_timeout,
            expect_output=[
                "Starting SetStreamEncProfile example...",
                "Waiting for payload signal...",
                "[INFO] Target camera:",
                f"[INFO] Requested encoder profile: {args.stream_profile}",
                "[SUCCESS] Stream encoder profile for",
            ],
            expect_absent=["[ERROR]", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "stream", "profile"],
        ),
        Step(
            name="payload_set_stream_resolution",
            command=cmd(
                "payload_set_stream_resolution",
                "-d",
                str(args.stream_device),
                "-r",
                str(args.stream_resolution),
            ),
            timeout=args.stream_command_timeout,
            expect_output=[
                "Starting SetStreamResolution example...",
                "Waiting for payload signal...",
                "[INFO] Target camera:",
                f"[INFO] Requested resolution level: {args.stream_resolution}",
                "[SUCCESS] Stream resolution for",
            ],
            expect_absent=["[ERROR]", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "stream", "resolution"],
        ),
        Step(
            name="payload_set_stream_resolution_2_random",
            command=cmd(
                "payload_set_stream_resolution",
                "-d",
                str(random_stream_resolution_2[0]),
                "-r",
                str(random_stream_resolution_2[1]),
            ),
            timeout=args.stream_command_timeout,
            expect_output=[
                "Starting SetStreamResolution example...",
                "Waiting for payload signal...",
                "[INFO] Target camera:",
                f"[INFO] Requested resolution level: {random_stream_resolution_2[1]}",
                "[SUCCESS] Stream resolution for",
            ],
            expect_absent=["[ERROR]", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "stream", "resolution"],
        ),
        Step(
            name="payload_set_stream_resolution_3_random",
            command=cmd(
                "payload_set_stream_resolution",
                "-d",
                str(random_stream_resolution_3[0]),
                "-r",
                str(random_stream_resolution_3[1]),
            ),
            timeout=args.stream_command_timeout,
            expect_output=[
                "Starting SetStreamResolution example...",
                "Waiting for payload signal...",
                "[INFO] Target camera:",
                f"[INFO] Requested resolution level: {random_stream_resolution_3[1]}",
                "[SUCCESS] Stream resolution for",
            ],
            expect_absent=["[ERROR]", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "stream", "resolution"],
        ),
        Step(
            name="payload_set_system_time",
            command=cmd("payload_set_system_time"),
            max_duration=args.system_time_duration,
            expect_output=[
                "Starting SendSystemTime example...",
                "Waiting for payload signal!",
            ],
            expect_absent=["ERROR", "Segmentation fault", "FAILED"],
            delay_after=1.0,
            tags=["payload", "time"],
        ),
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PayloadSDK payload-only test runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--build-dir", default="build/examples", help="Path to compiled example binaries")
    parser.add_argument("--report-dir", default=None, help="Directory for run reports and summaries")
    parser.add_argument("--log-file", default=None, help="Optional log file path")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--object-detection-timeout", type=float, default=20.0, help="Timeout for payload_do_object_detection")
    parser.add_argument("--object-tracking-duration", type=float, default=15.0, help="How long to observe payload_do_object_tracking before stopping it")
    parser.add_argument("--download-media-duration", type=float, default=8.0, help="How long to observe the payload_download_media_files menu before stopping it")
    parser.add_argument("--extract-tiff-timeout", type=float, default=15.0, help="Timeout for payload_extract_tiff_file")
    parser.add_argument("--component-info-duration", type=float, default=8.0, help="How long to observe payload_get_component_info before stopping it")
    parser.add_argument("--fov-status-duration", type=float, default=8.0, help="How long to observe payload_get_fov_status before stopping it")
    parser.add_argument("--status-duration", type=float, default=8.0, help="How long to observe payload_get_status before stopping it")
    parser.add_argument("--video-streaming-duration", type=float, default=15.0, help="How long to observe payload_get_video_streaming before stopping it")
    parser.add_argument("--zoom-target-duration", type=float, default=25.0, help="How long to observe payload_set_camera_zoom_targetpos before stopping it")
    parser.add_argument("--gps-duration", type=float, default=8.0, help="How long to observe payload_set_gps before stopping it")
    parser.add_argument("--system-time-duration", type=float, default=8.0, help="How long to observe payload_set_system_time before stopping it")
    parser.add_argument("--stream-command-timeout", type=float, default=15.0, help="Timeout for stream configuration commands")
    parser.add_argument("--stream-device", type=int, default=1, choices=[1, 2], help="Camera device used by stream configuration steps: 1=EO, 2=IR")
    parser.add_argument("--stream-bitrate", type=int, default=2000000, choices=[512000, 1000000, 2000000, 4000000], help="Bitrate passed to payload_set_stream_bitrate")
    parser.add_argument("--stream-profile", type=int, default=1, choices=[0, 1, 2], help="Encoder profile passed to payload_set_stream_profile")
    parser.add_argument(
        "--stream-resolution",
        type=int,
        default=1,
        help=(
            "Resolution level passed to payload_set_stream_resolution. "
            "EO (-d 1): 0=1920x1080, 1=1280x720, 2=960x540. "
            "IR (-d 2): 0=1280x1024, 1=640x512, 2=480x384, 3=320x256, 4=160x128."
        ),
    )
    parser.add_argument("--download-dir", default=None, help="Optional download directory passed to payload_download_media_files")
    parser.add_argument("--tiff-file", default=None, help="Path to a TIFF image for payload_extract_tiff_file; step is skipped if omitted")
    parser.add_argument("--stop-on-failure", action="store_true", help="Abort suite after first failure")
    parser.add_argument("--only", nargs="*", default=None, help="Run only steps with these names")
    parser.add_argument("--skip", nargs="*", default=None, help="Skip steps with these names")
    parser.add_argument("--dry-run", action="store_true", help="Print steps without running them")
    args = parser.parse_args()
    validate_stream_resolution(args.stream_device, args.stream_resolution, parser)
    return args


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
    args.report_dir = str(create_run_report_dir(args.report_dir or default_report_dir(), prefix="payload_runner"))
    args.log_file = args.log_file or default_log_file(args.report_dir, prefix="payload_runner")
    configure_logging(level=args.log_level, log_file=args.log_file)

    steps = filter_steps(build_steps(args), args)
    active = [step for step in steps if step.enabled]
    inactive = [step for step in steps if not step.enabled]

    logger.info("PayloadSDK Payload Test Runner")
    logger.info("Build dir : %s", args.build_dir)
    logger.info("Steps     : %d active, %d skipped", len(active), len(inactive))
    if any(step.name == "payload_extract_tiff_file" for step in inactive) and not args.tiff_file:
        logger.info("TIFF step : skipped because --tiff-file was not provided")

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
        logger.info("%s  %-32s %s  %.1fs", icon, result.step.name, result.status, result.duration)

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

    write_report(suite, output_dir=args.report_dir, report_prefix="payload_runner")
    logger.info("LOG file    -> %s", args.log_file)

    sys.exit(0 if suite.failed == 0 else 1)


if __name__ == "__main__":
    main()
