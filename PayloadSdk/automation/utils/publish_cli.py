"""
Shared CLI options for report publishing.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from utils.publish_report import publish_to_github_pages

logger = logging.getLogger(__name__)


def add_publish_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--publish-report",
        action="store_true",
        help="Publish the generated HTML report to the GitHub Pages branch after the run",
    )
    parser.add_argument(
        "--publish-branch",
        default="gh-pages",
        help="Git branch used for GitHub Pages publishing",
    )
    parser.add_argument(
        "--publish-remote",
        default="origin",
        help="Git remote used for GitHub Pages publishing",
    )


def maybe_publish_report(args: argparse.Namespace, html_report_path: str | Path) -> None:
    if not getattr(args, "publish_report", False):
        return

    target = publish_to_github_pages(
        html_report_path,
        branch=args.publish_branch,
        remote=args.publish_remote,
    )
    logger.info("GitHub Pages publish complete -> %s", target)
