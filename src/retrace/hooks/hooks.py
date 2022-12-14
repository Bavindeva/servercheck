import itertools
import multiprocessing as mp
import os
import shlex
from typing import Iterable, Optional

from pathlib import Path
from subprocess import PIPE, CalledProcessError, run, TimeoutExpired

from retrace.retrace import log_info, log_error, log_debug, RetraceTask
from .config import HOOK_PATH, HOOK_TIMEOUT, hooks_config

#   Hooks description:
#   pre_start -- When self.start() is called
#   start -- When task type is determined and the main task starts
#   pre_prepare_debuginfo -- Before the preparation of debuginfo packages
#   post_prepare_debuginfo -- After the preparation of debuginfo packages
#   pre_prepare_environment -- Before the preparation of retrace environment
#   post_prepare_environment -- After the preparation of retrace environment
#   pre_retrace -- Before starting of the retracing itself
#   post_retrace -- After retracing is done
#   success -- After retracing success
#   fail -- After retracing fails
#   pre_remove_task -- Before removing task
#   post_remove_task -- After removing task
#   pre_clean_task -- Before cleaning task
#   post_clean_task -- After cleaning task


def get_executables(directory: Path) -> Iterable[Path]:
    """
    Scan `directory` and return list of found executable scripts.
    """
    if not directory.is_dir():
        return []

    return (
        entry for entry in sorted(directory.iterdir())
        if entry.is_file() and os.access(entry, os.X_OK)
    )


class RetraceHook:
    taskid: int
    task_results_dir: Path

    def __init__(self, task: RetraceTask) -> None:
        self.taskid = task.get_taskid()
        self.task_results_dir = task.get_results_dir()

    def _get_cmdline(self, hook: str, exc: Optional[str] = None) -> Optional[str]:
        if exc:
            cmdline = hooks_config.get(f"{hook}.{exc}.cmdline", None)

        if not cmdline:
            cmdline = hooks_config.get(f"{hook}.cmdline", None)

        if cmdline:
            cmdline = cmdline.format(hook_name=hook,
                                     taskid=self.taskid,
                                     task_results_dir=self.task_results_dir)

        return cmdline

    @staticmethod
    def _get_hookdir() -> Path:
        hooks_path = hooks_config.get("main.hookdir", HOOK_PATH)

        return Path(hooks_path)

    @staticmethod
    def _get_timeout(hook: str, exc: Optional[str] = None) -> int:
        timeout = hooks_config.get("main.timeout", HOOK_TIMEOUT)

        if f"{hook}.timeout" in hooks_config:
            timeout = hooks_config.get(f"{hook}.timeout", timeout)

        if exc and f"{hook}.{exc}.timeout" in hooks_config:
            timeout = hooks_config.get(f"{hook}.{exc}.timeout", timeout)

        return int(timeout)

    def _process_script(self, hook: str, hook_path: Path, exc_path: str) -> None:
        exc = Path(exc_path).name
        script = exc_path

        log_debug(f"Running '{hook}' hook - script '{exc}'")
        hook_cmdline = self._get_cmdline(hook, exc)
        hook_timeout = self._get_timeout(hook, exc)

        if hook_cmdline:
            script = shlex.quote(f"{script} {hook_cmdline}")

        cmd = shlex.split(script)

        try:
            child = run(cmd, shell=True, timeout=hook_timeout, cwd=hook_path,
                        stdout=PIPE, stderr=PIPE, encoding="utf-8", check=True)
        except TimeoutExpired as ex:
            if ex.stdout:
                log_info(ex.stdout)
            if ex.stderr:
                log_error(ex.stderr)
            log_error(f"Hook script '{exc}' timed out in {ex.timeout} seconds.")
        except CalledProcessError as ex:
            if ex.stdout:
                log_info(ex.stdout)
            if ex.stderr:
                log_error(ex.stderr)
            log_error(f"Hook script '{exc}' failed with exit status {ex.returncode}.")
        else:
            if child.stdout:
                log_info(child.stdout)
            if child.stderr:
                log_error(child.stderr)

    def run(self, hook: str) -> None:
        """Called by the default hook implementations"""
        hook_path = Path(self._get_hookdir(), hook)
        executables = get_executables(hook_path)

        params = itertools.product([hook], [hook_path], executables)

        with mp.Pool() as hook_pool:
            hook_pool.starmap(self._process_script, params)
