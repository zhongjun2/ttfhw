import os
import time
import datetime
import requests
import git
from stages.base import BaseStage
from metrics.collector import MetricsCollector

GITCODE_API = "https://gitcode.com/api/v4"


class ContributeStage(BaseStage):
    def __init__(self, config: dict):
        self._config = config
        self._token = config.get("gitcode_token", "")
        self._fork = config.get("fork_repo", "")
        self._upstream = config.get("upstream_repo", "")
        self._timeouts = config.get("timeout", {})
        self._issue_mc = MetricsCollector()
        self._pr_mc = MetricsCollector()
        self._pr_ci_fields: dict = {}

    def _headers(self) -> dict:
        return {"PRIVATE-TOKEN": self._token}

    def _get_project_id(self, namespace_path: str) -> int | None:
        """Resolve 'owner/repo' path to numeric GitLab project ID."""
        r = requests.get(
            f"{GITCODE_API}/projects/{namespace_path.replace('/', '%2F')}",
            headers=self._headers(),
        )
        if r.status_code == 200:
            return r.json().get("id")
        return None

    def setup(self) -> None:
        pass

    def run(self) -> None:
        self.run_issue()
        self.run_pr()

    def run_issue(self) -> None:
        if not self._token:
            self._issue_mc.add_error("gitcode_token_not_configured")
            self._issue_mc.set_fail()
            return
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
        payload = {
            "title": f"[TTFHW-TEST] Automated test issue {ts}",
            "description": "This is an automated TTFHW test issue. Please ignore.",
        }
        self._issue_mc.start("submit")
        resp = requests.post(
            f"{GITCODE_API}/projects/{self._upstream.replace('/', '%2F')}/issues",
            json=payload,
            headers=self._headers(),
        )
        self._issue_mc.stop("submit")

        if resp.status_code != 201:
            self._issue_mc.add_error(f"issue_create_failed: HTTP {resp.status_code}")
            self._issue_mc.set_fail()
            return

        issue_iid = resp.json().get("iid")
        self._poll_issue_response(issue_iid)

    def _poll_issue_response(self, issue_iid: int) -> None:
        timeout = self._timeouts.get("issue_response_s", 3600)
        deadline = time.monotonic() + timeout
        response_start = time.monotonic()
        first_response_s = None
        project = self._upstream.replace("/", "%2F")

        while time.monotonic() < deadline:
            r = requests.get(
                f"{GITCODE_API}/projects/{project}/issues/{issue_iid}/notes",
                headers=self._headers(),
            )
            comments = r.json()
            if comments:
                first_response_s = round(time.monotonic() - response_start, 3)
                break
            time.sleep(30)

        # null on timeout (spec requirement), warn status
        self._issue_mc._extras = getattr(self._issue_mc, "_extras", {})
        self._issue_mc._extras["first_response_s"] = first_response_s
        if first_response_s is None:
            self._issue_mc.set_warn()

    def run_pr(self) -> None:
        if not self._token:
            self._pr_mc.add_error("gitcode_token_not_configured")
            self._pr_mc.set_fail()
            return

        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S")
        branch = f"ttfhw-test-{ts}"

        # Resolve fork's numeric project ID (required by GitLab MR API)
        fork_project_id = self._get_project_id(self._fork)
        if fork_project_id is None:
            self._pr_mc.add_error(f"fork_project_not_found: {self._fork}")
            self._pr_mc.set_fail()
            return

        # Push fixture to fork
        try:
            repo = git.Repo.clone_from(
                f"https://oauth2:{self._token}@gitcode.com/{self._fork}.git",
                f"/tmp/ttfhw-fork-{ts}",
            )
            repo.git.checkout("-b", branch)
            # Create a test file to trigger CI
            test_file = os.path.join(str(repo.working_dir), f"ttfhw_test_{ts}.txt")
            with open(test_file, "w") as fh:
                fh.write("TTFHW test")
            repo.git.add(A=True)
            repo.index.commit(f"[TTFHW-TEST] Test operator contribution {ts}")
            repo.remote("origin").push(branch)
        except Exception as e:
            self._pr_mc.add_error(f"fork_push_failed: {e}")
            self._pr_mc.set_fail()
            return

        payload = {
            "source_branch": branch,
            "target_branch": "master",
            "title": f"[TTFHW-TEST] Automated test PR {ts}",
            "description": "Automated TTFHW test PR. Please ignore.",
            "source_project_id": fork_project_id,
        }
        self._pr_mc.start("submit")
        resp = requests.post(
            f"{GITCODE_API}/projects/{self._upstream.replace('/', '%2F')}/merge_requests",
            json=payload,
            headers=self._headers(),
        )
        self._pr_mc.stop("submit")

        if resp.status_code != 201:
            self._pr_mc.add_error(f"pr_create_failed: HTTP {resp.status_code}")
            self._pr_mc.set_fail()
            return

        mr_iid = resp.json().get("iid")
        self._poll_ci(mr_iid)

    def _poll_ci(self, mr_iid: int) -> None:
        timeout = self._timeouts.get("ci_total_s", 7200)
        deadline = time.monotonic() + timeout
        self._pr_mc.start("ci_total")
        ci_queue_start = time.monotonic()
        ci_prepare_start = ci_run_start = None
        ci_result = "timeout"
        project = self._upstream.replace("/", "%2F")

        while time.monotonic() < deadline:
            r = requests.get(
                f"{GITCODE_API}/projects/{project}/merge_requests/{mr_iid}/pipelines",
                headers=self._headers(),
            )
            pipelines = r.json()
            if not pipelines:
                time.sleep(60)
                continue

            pipeline = pipelines[0]
            status = pipeline.get("status", "")

            if ci_prepare_start is None and status == "running":
                ci_prepare_start = time.monotonic()
                self._pr_ci_fields["ci_queue_s"] = round(ci_prepare_start - ci_queue_start, 3)

            if ci_run_start is None and ci_prepare_start and status == "running":
                # NOTE: ci_prepare_s requires job-level log parsing to measure accurately.
                # In this version, ci_prepare_s is recorded as 0.0 (a known limitation).
                ci_run_start = ci_prepare_start
                self._pr_ci_fields["ci_prepare_s"] = 0.0

            if status in ("success", "failed", "canceled"):
                ci_end = time.monotonic()
                if ci_run_start:
                    self._pr_ci_fields["ci_run_s"] = round(ci_end - ci_run_start, 3)
                ci_result = status
                break

            time.sleep(60)

        # Ensure all CI timing fields are present (None if not reached)
        self._pr_ci_fields.setdefault("ci_queue_s", None)
        self._pr_ci_fields.setdefault("ci_prepare_s", None)
        self._pr_ci_fields.setdefault("ci_run_s", None)

        self._pr_mc.stop("ci_total")
        self._pr_ci_fields["ci_total_s"] = self._pr_mc.elapsed("ci_total")
        self._pr_ci_fields["ci_result"] = ci_result
        if ci_result == "timeout":
            self._pr_mc.set_warn()

    def verify(self) -> bool:
        return self._issue_mc.status() != "fail" and self._pr_mc.status() != "fail"

    def teardown(self) -> None:
        pass

    def metrics(self) -> dict:
        issue_d = self._issue_mc.to_dict()
        issue_d["submit_s"] = self._issue_mc.elapsed("submit")
        # first_response_s is null on timeout (stored in _extras, not via elapsed)
        issue_d["first_response_s"] = getattr(self._issue_mc, "_extras", {}).get("first_response_s")

        pr_d = self._pr_mc.to_dict()
        pr_d["submit_s"] = self._pr_mc.elapsed("submit")
        pr_d.update(self._pr_ci_fields)

        return {"issue": issue_d, "pr_ci": pr_d}
