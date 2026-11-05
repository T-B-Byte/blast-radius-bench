"""pytest plugin: record per-test outcomes (nodeid -> passed/failed/skipped) and optionally
restrict the run to a selected set of nodeids (env BRB_SELECT = path to a json list)."""
import json, os

_results, _collect_errors = {}, []

def pytest_collection_modifyitems(session, config, items):
    sel = os.environ.get("BRB_SELECT")
    if not sel:
        return
    keep = set(json.load(open(sel)))
    selected = [i for i in items if i.nodeid in keep]
    deselected = [i for i in items if i.nodeid not in keep]
    if deselected:
        config.hook.pytest_deselected(items=deselected)
    items[:] = selected

def pytest_collectreport(report):
    if report.failed:
        _collect_errors.append(report.nodeid)

def pytest_runtest_logreport(report):
    prev = _results.get(report.nodeid)
    if report.failed:
        _results[report.nodeid] = "failed"
    elif report.skipped and prev is None:
        _results[report.nodeid] = "skipped"
    elif report.when == "call" and report.passed and prev in (None, "skipped"):
        _results[report.nodeid] = "passed"

def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("BRB_OUT")
    if out:
        json.dump({"results": _results, "collect_errors": _collect_errors}, open(out, "w"))
