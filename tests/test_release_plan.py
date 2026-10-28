import json
from pathlib import Path
import subprocess
import sys
import unittest


class ReleasePlanTest(unittest.TestCase):
    def givenEjecucionMain_whenResolverVersionYReintentar_thenVersionEstableYMonotona(self):
        repository = Path(__file__).resolve().parents[1]
        run_numbers = (42, 42, 43)
        executions = [
            subprocess.run(
                [
                    sys.executable, str(repository / "scripts/release_plan.py"),
                    "--event", "push", "--ref", "refs/heads/main",
                    "--run-number", str(run_number),
                ],
                capture_output=True, text=True, timeout=5,
            )
            for run_number in run_numbers
        ]

        for run_number, execution in zip(run_numbers, executions):
            with self.subTest(run_number=run_number):
                self.assertEqual(
                    execution.returncode, 0,
                    f"El planificador debe resolver la versión: {execution.stderr}",
                )
                plan = json.loads(execution.stdout)
                version = f"0.1.{run_number}"
                self.assertEqual(plan["version"], version)
                self.assertEqual(plan["tag"], f"v{version}")
                self.assertIs(plan["publish"], True)
                self.assertEqual(plan["apk"], f"domino-{version}.apk")
                self.assertEqual(plan["deb"], f"domino_{version}_amd64.deb")

    def givenPullRequest_whenResolverEntrega_thenNoPublica(self):
        repository = Path(__file__).resolve().parents[1]
        execution = subprocess.run(
            [
                sys.executable, str(repository / "scripts/release_plan.py"),
                "--event", "pull_request", "--ref", "refs/pull/7/merge",
                "--run-number", "42",
            ],
            capture_output=True, text=True, timeout=5,
        )

        self.assertEqual(
            execution.returncode, 0,
            f"El planificador debe resolver la entrega: {execution.stderr}",
        )
        plan = json.loads(execution.stdout)
        self.assertIs(plan["publish"], False)


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([
        ReleasePlanTest("givenEjecucionMain_whenResolverVersionYReintentar_thenVersionEstableYMonotona"),
        ReleasePlanTest("givenPullRequest_whenResolverEntrega_thenNoPublica"),
    ])


if __name__ == "__main__":
    unittest.main()
