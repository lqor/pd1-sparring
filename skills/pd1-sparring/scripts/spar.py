#!/usr/bin/env python3
"""spar.py - state engine for the PD1 Sparring Partner skill.

Python 3.8+, standard library only. The coach (your AI agent) calls this; you
never have to. Every command prints JSON so the agent can read it reliably.

  spar.py init [--exam-date YYYY-MM-DD] [--hours N] [--background TEXT]
  spar.py status
  spar.py next --mode diagnose|drill|review [--n N] [--section DF|PAL|UI|TDD] [--topic T]
  spar.py show ID [ID ...]
  spar.py record ID right|wrong [--conf sure|unsure|guess] [--pick LETTERS] [--mode M]
  spar.py record-gen SECTION right|wrong [--topic T]
  spar.py mock-start            (60 questions, weighted like the real exam)
  spar.py mock-finish
  spar.py analyze-report --df N --pal N --ui N --tdd N
  spar.py plan
  spar.py katas | kata ID --solution FILE [--org ALIAS] | kata-show ID
  spar.py apex FILE [--org ALIAS]     (runs anonymous Apex, never in production)
  spar.py export | import CODE | reset --yes
"""
import argparse
import base64
import json
import os
import random
import re
import shutil
import subprocess
import sys
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
BANK_PATH = HERE.parent / "bank" / "questions.json"
KATA_PATH = HERE.parent / "bank" / "katas.json"

SECTIONS = {
    "DF": {"name": "Developer Fundamentals", "weight": 27},
    "PAL": {"name": "Process Automation and Logic", "weight": 28},
    "UI": {"name": "User Interface", "weight": 25},
    "TDD": {"name": "Testing, Debugging, and Deployment", "weight": 20},
}
PASS_MARK = 68
EXAM_QUESTIONS = 60
EXAM_MINUTES = 105
MOCK_SPLIT = {"DF": 16, "PAL": 17, "UI": 15, "TDD": 12}      # 60, by official weights
DIAG_SPLIT = {"DF": 5, "PAL": 6, "UI": 5, "TDD": 4}          # 20
INTERVALS = [0, 1, 3, 7, 14]                                   # days until box n is due


# ---------------------------------------------------------------- storage
def state_path():
    custom = os.environ.get("SPARRING_STATE")
    if custom:
        return Path(custom)
    return Path.home() / ".sparring" / "pd1" / "progress.json"


def today():
    return date.today().isoformat()


def new_state():
    return {
        "version": 1,
        "created": today(),
        "profile": {"exam_date": None, "hours_per_week": None, "background": None,
                    "prior_scores": None},
        "cards": {},
        "log": [],
        "generated": [],
        "mocks": [],
        "current_mock": None,
        "katas": {},
    }


def load_state():
    p = state_path()
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            backup = p.with_suffix(".corrupt.json")
            shutil.copy(p, backup)
            fail("Progress file was unreadable. A copy was kept at %s. Run "
                 "'reset --yes' to start fresh or 'import CODE' to restore." % backup)
    return new_state()


def save_state(state):
    p = state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
    tmp.replace(p)


def load_bank():
    if not BANK_PATH.exists():
        fail("Question bank not found at %s" % BANK_PATH)
    data = json.loads(BANK_PATH.read_text(encoding="utf-8"))
    return {q["id"]: q for q in data["questions"]}, data.get("meta", {})


def load_katas():
    if not KATA_PATH.exists():
        return {}
    data = json.loads(KATA_PATH.read_text(encoding="utf-8"))
    return {k["id"]: k for k in data["katas"]}


def out(obj):
    print(json.dumps(obj, indent=1, ensure_ascii=False))


def fail(msg, code=1):
    print(json.dumps({"error": msg}, indent=1))
    sys.exit(code)


# ---------------------------------------------------------------- stats
def section_stats(state, bank):
    stats = {}
    for code, info in SECTIONS.items():
        ids = [i for i, q in bank.items() if q["section"] == code]
        seen = [i for i in ids if i in state["cards"]]
        latest_right = sum(1 for i in seen if state["cards"][i]["last"] == "right")
        first_right = sum(1 for i in seen if state["cards"][i]["first"] == "right")
        gen = [g for g in state["generated"] if g["section"] == code]
        gen_right = sum(1 for g in gen if g["ok"])
        answered = len(seen) + len(gen)
        right = latest_right + gen_right
        stats[code] = {
            "name": info["name"],
            "weight": info["weight"],
            "bank_total": len(ids),
            "bank_seen": len(seen),
            "answered": answered,
            "accuracy_pct": round(100.0 * right / answered) if answered else None,
            "first_try_pct": round(100.0 * first_right / len(seen)) if seen else None,
        }
    return stats


def smoothed_accuracy(st):
    """Laplace-smoothed accuracy so an unseen section counts as 50%, not 0 or 100."""
    if not st["answered"]:
        return 0.5
    right = (st["accuracy_pct"] or 0) / 100.0 * st["answered"]
    return (right + 1.0) / (st["answered"] + 2.0)


def projection(stats):
    total_answered = sum(s["answered"] for s in stats.values())
    if total_answered < 20 or any(s["answered"] < 3 for s in stats.values()):
        return None
    return round(sum(s["weight"] * (s["accuracy_pct"] or 0) / 100.0 for s in stats.values()))


def weak_topics(state, bank, limit=6):
    agg = {}
    for cid, card in state["cards"].items():
        q = bank.get(cid)
        if not q:
            continue
        key = (q["section"], q["topic"])
        a = agg.setdefault(key, [0, 0])
        a[0] += 1
        a[1] += 1 if card["last"] == "right" else 0
    for g in state["generated"]:
        if g.get("topic"):
            a = agg.setdefault((g["section"], g["topic"]), [0, 0])
            a[0] += 1
            a[1] += 1 if g["ok"] else 0
    rows = []
    for (sec, topic), (seen, right) in agg.items():
        missed = seen - right
        if missed:
            rows.append({"section": sec, "topic": topic, "seen": seen, "missed": missed,
                         "weight": SECTIONS[sec]["weight"]})
    rows.sort(key=lambda r: (-r["missed"] * r["weight"], r["topic"]))
    return rows[:limit]


def due_cards(state, bank):
    t = today()
    due = [cid for cid, c in state["cards"].items()
           if cid in bank and c["box"] < len(INTERVALS) and c["due"] <= t]
    due.sort(key=lambda cid: (state["cards"][cid]["box"], state["cards"][cid]["due"]))
    return due


def calibration(state):
    """How often 'sure' answers are wrong: the dangerous kind of mistake."""
    sure = [e for e in state["log"] if e.get("conf") == "sure"]
    guess = [e for e in state["log"] if e.get("conf") == "guess"]
    res = {}
    if len(sure) >= 5:
        res["sure_but_wrong_pct"] = round(100.0 * sum(1 for e in sure if not e["ok"]) / len(sure))
    if len(guess) >= 5:
        res["guess_right_pct"] = round(100.0 * sum(1 for e in guess if e["ok"]) / len(guess))
    return res


def days_to_exam(state):
    d = state["profile"].get("exam_date")
    if not d:
        return None
    try:
        return (date.fromisoformat(d) - date.today()).days
    except ValueError:
        return None


def recommend(state, bank, stats):
    total = sum(s["answered"] for s in stats.values())
    if total == 0:
        return "Run the 20-question diagnostic first: next --mode diagnose"
    if total < 20:
        return "Finish the diagnostic (%d of 20 answered): next --mode diagnose --n %d" % (
            total, 20 - total)
    due = len(due_cards(state, bank))
    proj = projection(stats)
    weakest = min(stats.items(), key=lambda kv: smoothed_accuracy(kv[1]) / 1.0)[0]
    parts = []
    if due:
        parts.append("%d review cards are due: next --mode review" % due)
    parts.append("Weakest section is %s: next --mode drill --section %s" % (
        SECTIONS[weakest]["name"], weakest))
    if proj is not None and proj >= 78 and not state["mocks"]:
        parts.append("Projection is %d%%. Time for a full mock: mock-start" % proj)
    dte = days_to_exam(state)
    if dte is not None and 0 <= dte <= 3:
        parts.append("Exam in %d day(s): reviews and one light drill only, no new mocks" % dte)
    return " | ".join(parts)


# ---------------------------------------------------------------- selection
def pick_unseen(state, bank, section, n, topic=None, rng=random):
    pool = [i for i, q in bank.items()
            if q["section"] == section and i not in state["cards"]
            and (topic is None or q["topic"] == topic)]
    rng.shuffle(pool)
    return pool[:n]


def pick_any(state, bank, section, n, exclude, rng=random):
    """Least-recently-seen questions, used when the unseen pool runs dry."""
    pool = [i for i, q in bank.items() if q["section"] == section and i not in exclude]
    rng.shuffle(pool)
    pool.sort(key=lambda i: state["cards"].get(i, {}).get("seen_on", ""))
    return pool[:n]


def stratified(state, bank, split, rng=random):
    ids = []
    for sec, n in split.items():
        got = pick_unseen(state, bank, sec, n, rng=rng)
        if len(got) < n:
            got += pick_any(state, bank, sec, n - len(got), set(got), rng=rng)
        ids += got
    rng.shuffle(ids)
    return ids


def pick_drill(state, bank, stats, n, section=None, topic=None, rng=random):
    ids = []
    due = [d for d in due_cards(state, bank)
           if (section is None or bank[d]["section"] == section)
           and (topic is None or bank[d]["topic"] == topic)]
    ids += due[: max(1, int(n * 0.4))] if due else []
    remaining = n - len(ids)
    if section:
        weights = {section: 1.0}
    else:
        weights = {s: SECTIONS[s]["weight"] * (1.0 - smoothed_accuracy(stats[s])) for s in SECTIONS}
    order = sorted(weights, key=lambda s: -weights[s])
    total_w = sum(weights.values()) or 1.0
    for sec in order:
        if remaining <= 0:
            break
        share = max(1, int(round(n * weights[sec] / total_w)))
        got = pick_unseen(state, bank, sec, min(share, remaining), topic=topic, rng=rng)
        ids += got
        remaining -= len(got)
    if remaining > 0:   # unseen pool exhausted: recycle misses first, then anything
        for sec in order:
            extra = [i for i in pick_any(state, bank, sec, remaining, set(ids), rng=rng)
                     if topic is None or bank[i]["topic"] == topic]
            ids += extra
            remaining -= len(extra)
            if remaining <= 0:
                break
    return ids[:n]


def coach_view(q):
    """Everything the coach needs. The coach must not reveal answer/why before the learner commits."""
    keys = ["id", "section", "topic", "difficulty", "multi", "stem", "code", "options",
            "answer", "why", "tell", "verify", "expect"]
    return {k: q[k] for k in keys if k in q and q[k] not in (None, "")}


# ---------------------------------------------------------------- commands
def cmd_init(args):
    state = load_state()
    prof = state["profile"]
    if args.exam_date:
        try:
            date.fromisoformat(args.exam_date)
        except ValueError:
            fail("exam date must be YYYY-MM-DD")
        prof["exam_date"] = args.exam_date
    if args.hours is not None:
        prof["hours_per_week"] = args.hours
    if args.background:
        prof["background"] = args.background
    save_state(state)
    out({"ok": True, "profile": prof, "state_file": str(state_path())})


def cmd_status(args):
    state = load_state()
    bank, meta = load_bank()
    stats = section_stats(state, bank)
    proj = projection(stats)
    out({
        "profile": state["profile"],
        "days_to_exam": days_to_exam(state),
        "bank": {"questions": len(bank), "version": meta.get("version"),
                 "aligned_to": meta.get("aligned_to")},
        "sections": stats,
        "projected_score_pct": proj,
        "pass_mark_pct": PASS_MARK,
        "projection_note": ("Weighted by official section weights from your latest answer on "
                            "each practice question. Practice is not the exam: aim for 80+ "
                            "on a fresh mock before you sit.") if proj is not None else
                           "Answer at least 20 questions (3+ per section) to get a projection.",
        "reviews_due": len(due_cards(state, bank)),
        "weak_topics": weak_topics(state, bank),
        "calibration": calibration(state),
        "mocks": state["mocks"][-3:],
        "katas_done": sorted(k for k, v in state["katas"].items() if v.get("passed")),
        "next_step": recommend(state, bank, stats),
        "state_file": str(state_path()),
    })


def cmd_next(args):
    state = load_state()
    bank, _ = load_bank()
    stats = section_stats(state, bank)
    rng = random.Random(args.seed) if args.seed is not None else random
    if args.section and args.section not in SECTIONS:
        fail("section must be one of %s" % ", ".join(SECTIONS))
    if args.mode == "diagnose":
        ids = stratified(state, bank, DIAG_SPLIT, rng=rng)
        if args.n:
            ids = ids[: args.n]
    elif args.mode == "review":
        ids = due_cards(state, bank)[: args.n or 10]
    else:
        ids = pick_drill(state, bank, stats, args.n or 8, args.section, args.topic, rng=rng)
    out({"mode": args.mode, "count": len(ids),
         "rule": "Ask ONE at a time. Never show answer, why or tell before the learner commits.",
         "questions": [coach_view(bank[i]) for i in ids]})


def cmd_show(args):
    bank, _ = load_bank()
    missing = [i for i in args.ids if i not in bank]
    if missing:
        fail("Unknown question id(s): %s" % ", ".join(missing))
    out({"questions": [coach_view(bank[i]) for i in args.ids]})


def cmd_record(args):
    state = load_state()
    bank, _ = load_bank()
    if args.id not in bank:
        fail("Unknown question id %s" % args.id)
    ok = args.result == "right"
    card = state["cards"].get(args.id)
    if card is None:
        card = {"box": 0, "seen": 0, "right": 0, "first": args.result}
        state["cards"][args.id] = card
    card["seen"] += 1
    card["right"] += 1 if ok else 0
    card["last"] = args.result
    card["seen_on"] = today()
    if ok:
        # a lucky guess does not earn a promotion
        card["box"] = card["box"] if args.conf == "guess" else min(card["box"] + 1, len(INTERVALS))
    else:
        card["box"] = 0
    interval = INTERVALS[card["box"]] if card["box"] < len(INTERVALS) else 3650
    if not ok or args.conf == "guess":
        # misses and lucky guesses both come back, but never earlier than tomorrow
        interval = 1 if not ok else max(1, interval)
    card["due"] = (date.today() + timedelta(days=interval)).isoformat()
    mode = args.mode or ("mock" if state.get("current_mock") else "drill")
    state["log"].append({"d": today(), "id": args.id, "ok": ok, "conf": args.conf,
                         "pick": args.pick, "mode": mode})
    save_state(state)
    out({"ok": True, "id": args.id, "result": args.result, "box": card["box"],
         "next_review": card["due"]})


def cmd_record_gen(args):
    if args.section not in SECTIONS:
        fail("section must be one of %s" % ", ".join(SECTIONS))
    state = load_state()
    state["generated"].append({"d": today(), "section": args.section, "topic": args.topic,
                               "ok": args.result == "right"})
    save_state(state)
    out({"ok": True, "generated_logged": len(state["generated"])})


def cmd_mock_start(args):
    state = load_state()
    bank, _ = load_bank()
    rng = random.Random(args.seed) if args.seed is not None else random
    ids = stratified(state, bank, MOCK_SPLIT, rng=rng)
    fresh = sum(1 for i in ids if i not in state["cards"])
    state["current_mock"] = {"started": datetime.now().isoformat(timespec="seconds"), "ids": ids,
                             "log_start": len(state["log"])}
    save_state(state)
    out({"ok": True, "questions": len(ids), "minutes": EXAM_MINUTES, "pass_mark_pct": PASS_MARK,
         "fresh_questions": fresh, "ids": ids,
         "rule": ("Exam conditions: one question at a time via 'show ID', no feedback and no "
                  "hints until mock-finish. Record every answer with 'record ID right|wrong'. "
                  "If fresh_questions is under 45, tell the learner this mock repeats questions "
                  "and replace repeats with verified generated variants where you can.")})


def cmd_mock_finish(args):
    state = load_state()
    bank, _ = load_bank()
    mock = state.get("current_mock")
    if not mock:
        fail("No mock in progress. Start one with mock-start.")
    ids = set(mock["ids"])
    answers = {}
    for e in state["log"][mock.get("log_start", 0):]:
        if e["mode"] == "mock" and e["id"] in ids:
            answers[e["id"]] = e["ok"]
    by_sec = {}
    for sec in SECTIONS:
        sec_ids = [i for i in mock["ids"] if bank[i]["section"] == sec]
        right = sum(1 for i in sec_ids if answers.get(i))
        by_sec[sec] = {"name": SECTIONS[sec]["name"], "right": right, "of": len(sec_ids),
                       "pct": round(100.0 * right / len(sec_ids)) if sec_ids else None}
    total_right = sum(1 for i in mock["ids"] if answers.get(i))
    pct = round(100.0 * total_right / len(mock["ids"]))
    started = datetime.fromisoformat(mock["started"])
    minutes = round((datetime.now() - started).total_seconds() / 60.0)
    result = {"d": today(), "score_pct": pct, "right": total_right, "of": len(mock["ids"]),
              "unanswered": len(ids) - len(answers), "minutes": minutes, "by_section": by_sec,
              "passed": pct >= PASS_MARK}
    state["mocks"].append(result)
    state["current_mock"] = None
    save_state(state)
    missed = [i for i in mock["ids"] if not answers.get(i)]
    out({"result": result, "missed_ids": missed,
         "debrief_rule": "Debrief the misses grouped by topic, worst topic first, using 'show'."})


def cmd_analyze_report(args):
    scores = {"DF": args.df, "PAL": args.pal, "UI": args.ui, "TDD": args.tdd}
    for k, v in scores.items():
        if v is None or not (0 <= v <= 100):
            fail("Give all four section percentages (0-100): --df --pal --ui --tdd")
    total = sum(SECTIONS[s]["weight"] * scores[s] / 100.0 for s in SECTIONS)
    rows = []
    for s in SECTIONS:
        w = SECTIONS[s]["weight"]
        lost = w * (100 - scores[s]) / 100.0
        rows.append({"section": s, "name": SECTIONS[s]["name"], "weight": w, "score_pct": scores[s],
                     "questions_in_exam": MOCK_SPLIT[s],
                     "points_lost": round(lost, 1),
                     "points_per_10pct_gain": round(w / 10.0, 1)})
    rows.sort(key=lambda r: -r["points_lost"])
    gap = PASS_MARK - total
    state = load_state()
    state["profile"]["prior_scores"] = scores
    save_state(state)
    out({"estimated_overall_pct": round(total, 1), "pass_mark_pct": PASS_MARK,
         "gap_to_pass_pts": round(gap, 1),
         "approx_questions_short": max(0, int(-(-gap * EXAM_QUESTIONS // 100))) if gap > 0 else 0,
         "sections_by_points_lost": rows,
         "how_to_read": ("points_lost is the share of the whole exam you dropped in that "
                         "section. Work the list top-down: the biggest number is where the "
                         "pass is hiding, even if another section has a lower percentage."),
         "note": "Estimate only. Salesforce reports section percentages, not the exact total."})


def cmd_plan(args):
    state = load_state()
    bank, _ = load_bank()
    stats = section_stats(state, bank)
    dte = days_to_exam(state)
    hours = state["profile"].get("hours_per_week") or 5
    weights = {s: SECTIONS[s]["weight"] * (1.0 - smoothed_accuracy(stats[s])) for s in SECTIONS}
    prior = state["profile"].get("prior_scores")
    if prior and sum(s["answered"] for s in stats.values()) < 20:
        weights = {s: SECTIONS[s]["weight"] * (100 - prior[s]) / 100.0 for s in SECTIONS}
    total_w = sum(weights.values()) or 1.0
    sessions_per_week = max(2, min(7, int(round(hours * 60 / 40.0))))
    share = {s: round(100.0 * weights[s] / total_w) for s in SECTIONS}
    order = sorted(SECTIONS, key=lambda s: -weights[s])
    weeks = None if dte is None else max(1, -(-dte // 7))
    out({
        "days_to_exam": dte,
        "weeks": weeks,
        "sessions_per_week": sessions_per_week,
        "session_minutes": 40,
        "focus_share_pct": share,
        "priority_order": [SECTIONS[s]["name"] for s in order],
        "session_recipe": ["5 min: due reviews (next --mode review)",
                           "25 min: 8-question drill in the top-priority section",
                           "10 min: one kata, or re-teach your worst miss out loud"],
        "milestones": ["Diagnostic done (20 questions)",
                       "Every section at 60%+ on latest answers",
                       "First full mock at 70%+",
                       "Second mock at 80%+ on mostly fresh questions: you are ready to sit"],
        "booking_rule": ("No exam date set. Pick one 2-4 weeks out and run 'init --exam-date'. "
                         "A date turns studying into training.") if dte is None else None,
    })


def cmd_katas(args):
    state = load_state()
    katas = load_katas()
    out({"katas": [{"id": k["id"], "title": k["title"], "section": k["section"],
                    "topic": k["topic"], "minutes": k.get("minutes", 10),
                    "passed": bool(state["katas"].get(k["id"], {}).get("passed"))}
                   for k in katas.values()]})


def cmd_kata_show(args):
    katas = load_katas()
    if args.id not in katas:
        fail("Unknown kata id %s" % args.id)
    k = dict(katas[args.id])
    k["coach_rule"] = ("Show the learner title, brief and starter only. Keep 'reference' to "
                       "yourself until they pass or ask to give up after two real attempts.")
    out(k)


def sf_bin():
    exe = shutil.which("sf")
    if not exe:
        fail("Salesforce CLI ('sf') is not installed or not on PATH. Hands-on mode needs it: "
             "https://developer.salesforce.com/tools/salesforcecli . Chat-only mode still works.", 3)
    return exe


def run_sf(argv, timeout=180):
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        fail("Salesforce CLI timed out after %ds" % timeout, 3)
    text = proc.stdout.strip() or proc.stderr.strip()
    try:
        return json.loads(text[text.index("{"):])
    except (ValueError, IndexError):
        fail("Unexpected Salesforce CLI output: %s" % text[:400], 3)


def assert_safe_org(org):
    """Refuse to run learner code anywhere that could be production."""
    sf = sf_bin()
    argv = [sf, "data", "query", "-q",
            "SELECT OrganizationType, IsSandbox FROM Organization", "--json"]
    if org:
        argv += ["-o", org]
    res = run_sf(argv)
    if res.get("status") != 0:
        fail("Could not reach the org (%s). Log in with: sf org login web --alias sparring"
             % res.get("message", "unknown error"), 3)
    rec = res["result"]["records"][0]
    if not (rec.get("IsSandbox") or rec.get("OrganizationType") == "Developer Edition"):
        fail("Refusing to run: this org is '%s' and not a sandbox, scratch org or Developer "
             "Edition. Sparring never runs code in production. Sign up for a free org at "
             "https://developer.salesforce.com/signup and pass --org." % rec.get("OrganizationType"), 2)
    return rec


def run_apex_source(source, org):
    assert_safe_org(org)
    tmp = Path(os.environ.get("TMPDIR", "/tmp")) / ("sparring_%d.apex" % os.getpid())
    tmp.write_text(source, encoding="utf-8")
    try:
        argv = [sf_bin(), "apex", "run", "--file", str(tmp), "--json"]
        if org:
            argv += ["-o", org]
        res = run_sf(argv)
    finally:
        try:
            tmp.unlink()
        except OSError:
            pass
    r = res.get("result") or res.get("data") or {}
    logs = r.get("logs") or ""
    debug = [html_unescape(m) for m in re.findall(r"\|USER_DEBUG\|\[\d+\]\|[A-Z]+\|(.*)", logs)]
    return {
        "compiled": bool(r.get("compiled")),
        "success": bool(r.get("success")),
        "debug": debug,
        "compile_problem": r.get("compileProblem") or None,
        "line": pos_int(r.get("line")),
        "exception": r.get("exceptionMessage") or None,
        "stack": (r.get("exceptionStackTrace") or None),
        "cli_message": None if r else res.get("message"),
    }


def pos_int(v):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def html_unescape(s):
    return (s.replace("&quot;", '"').replace("&#39;", "'").replace("&lt;", "<")
             .replace("&gt;", ">").replace("&amp;", "&"))


def cmd_apex(args):
    src = Path(args.file).read_text(encoding="utf-8")
    out(run_apex_source(src, args.org))


def cmd_kata(args):
    katas = load_katas()
    if args.id not in katas:
        fail("Unknown kata id %s" % args.id)
    k = katas[args.id]
    solution = Path(args.solution).read_text(encoding="utf-8")
    res = run_apex_source(solution.rstrip() + "\n\n// ---- sparring harness ----\n" + k["harness"],
                          args.org)
    passed = res["success"] and any("KATA_PASS" in d for d in res["debug"])
    state = load_state()
    rec = state["katas"].setdefault(args.id, {"attempts": 0, "passed": False})
    rec["attempts"] += 1
    if passed:
        rec["passed"] = True
        rec["passed_on"] = today()
    save_state(state)
    res["passed"] = passed
    res["attempts"] = rec["attempts"]
    if not passed and res["compiled"] and res["exception"]:
        res["hint_rule"] = "Read the assertion message with the learner; do not paste a fix."
    out(res)


def cmd_export(args):
    state = load_state()
    raw = json.dumps(state, separators=(",", ":")).encode("utf-8")
    code = "SPAR1:" + base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")
    out({"code": code, "how": "Paste this code to your coach in a new chat and say 'resume'."})


def cmd_import(args):
    code = args.code.strip()
    if not code.startswith("SPAR1:"):
        fail("That does not look like a Sparring progress code (it should start with SPAR1:).")
    try:
        state = json.loads(zlib.decompress(base64.urlsafe_b64decode(code[6:])).decode("utf-8"))
    except Exception:
        fail("Progress code is damaged or incomplete. Copy the whole code and try again.")
    if state.get("version") != 1 or "cards" not in state:
        fail("Progress code is from an incompatible version.")
    save_state(state)
    out({"ok": True, "cards": len(state["cards"]), "state_file": str(state_path())})


def cmd_reset(args):
    if not args.yes:
        fail("This deletes all progress. Re-run with --yes to confirm.")
    p = state_path()
    if p.exists():
        shutil.copy(p, p.with_suffix(".bak.json"))
    save_state(new_state())
    out({"ok": True, "note": "Progress reset. Previous file kept as progress.bak.json."})


def main():
    ap = argparse.ArgumentParser(prog="spar.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True

    p = sub.add_parser("init"); p.add_argument("--exam-date"); p.add_argument("--hours", type=float)
    p.add_argument("--background"); p.set_defaults(fn=cmd_init)
    p = sub.add_parser("status"); p.set_defaults(fn=cmd_status)
    p = sub.add_parser("next")
    p.add_argument("--mode", choices=["diagnose", "drill", "review"], default="drill")
    p.add_argument("--n", type=int); p.add_argument("--section"); p.add_argument("--topic")
    p.add_argument("--seed", type=int); p.set_defaults(fn=cmd_next)
    p = sub.add_parser("show"); p.add_argument("ids", nargs="+"); p.set_defaults(fn=cmd_show)
    p = sub.add_parser("record"); p.add_argument("id")
    p.add_argument("result", choices=["right", "wrong"])
    p.add_argument("--conf", choices=["sure", "unsure", "guess"]); p.add_argument("--pick")
    p.add_argument("--mode"); p.set_defaults(fn=cmd_record)
    p = sub.add_parser("record-gen"); p.add_argument("section")
    p.add_argument("result", choices=["right", "wrong"]); p.add_argument("--topic")
    p.set_defaults(fn=cmd_record_gen)
    p = sub.add_parser("mock-start"); p.add_argument("--seed", type=int)
    p.set_defaults(fn=cmd_mock_start)
    p = sub.add_parser("mock-finish"); p.set_defaults(fn=cmd_mock_finish)
    p = sub.add_parser("analyze-report")
    for s in ("df", "pal", "ui", "tdd"):
        p.add_argument("--" + s, type=float)
    p.set_defaults(fn=cmd_analyze_report)
    p = sub.add_parser("plan"); p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("katas"); p.set_defaults(fn=cmd_katas)
    p = sub.add_parser("kata-show"); p.add_argument("id"); p.set_defaults(fn=cmd_kata_show)
    p = sub.add_parser("kata"); p.add_argument("id"); p.add_argument("--solution", required=True)
    p.add_argument("--org"); p.set_defaults(fn=cmd_kata)
    p = sub.add_parser("apex"); p.add_argument("file"); p.add_argument("--org")
    p.set_defaults(fn=cmd_apex)
    p = sub.add_parser("export"); p.set_defaults(fn=cmd_export)
    p = sub.add_parser("import"); p.add_argument("code"); p.set_defaults(fn=cmd_import)
    p = sub.add_parser("reset"); p.add_argument("--yes", action="store_true")
    p.set_defaults(fn=cmd_reset)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
