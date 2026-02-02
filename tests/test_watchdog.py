import sys

from runtime.watchdog import run_watchdog


def test_watchdog_allows_output():
    rc = run_watchdog([sys.executable, "-c", "print('ok')"], cwd=None, timeout_no_output=1)
    assert rc == 0


def test_watchdog_times_out_on_silence():
    rc = run_watchdog([sys.executable, "-c", "import time; time.sleep(0.2)"], cwd=None, timeout_no_output=0.05)
    assert rc in {124, 125}
