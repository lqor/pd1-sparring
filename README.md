# PD1 Sparring Partner

**An exam coach for the Salesforce Certified Platform Developer exam (PD1) that runs inside your own AI agent.**

You don't read it. You install it into Claude Code, the Claude app, Codex or any agent that can read files and run Python, say `let's spar`, and your agent drills you one question at a time, remembers every miss, and brings it back until it sticks.

This repository is the **free sample**: the complete coach and progress engine, 12 questions (3 per exam section) and one hands-on Apex kata.

```text
> let's spar

Q7 · Developer Fundamentals
What does this code write to the debug log?

    String a = 'Apex';
    String b = 'APEX';
    System.debug(a == b);
    System.debug(a.equals(b));

A) false then true    B) true then true
C) false then false   D) true then false

> C, sure

Wrong, and you were sure. Those are the ones that cost exams.
It's D. In Apex, == on Strings ignores case. equals() is the case-sensitive one.

> prove it

running in your org "sparring" (Developer Edition) …
  DEBUG | true
  DEBUG | false

Say the rule back to me in one sentence. This one returns tomorrow.
```

## Install

**Any agent supported by the `skills` CLI**

```bash
npx skills add lqor/pd1-sparring
```

**Claude Code, by hand**

```bash
git clone https://github.com/lqor/pd1-sparring && cp -r pd1-sparring/skills/pd1-sparring ~/.claude/skills/
```

**Claude desktop or web app:** download the zip from the [site](https://sparring-pd1.vercel.app), then Settings → Capabilities → Skills → Upload skill. Code execution must be on.

**Any other agent that reads files and runs Python:** clone the repo and say
`Read skills/pd1-sparring/SKILL.md and follow it. I want to practise for the PD1 exam.`

Then say: `let's spar for PD1`. Python 3.8+ is needed for the progress engine (standard library only).

## What the coach does

- **Diagnostic** weighted like the real exam: 27% Developer Fundamentals, 28% Process Automation and Logic, 25% User Interface, 20% Testing, Debugging, and Deployment
- **One question at a time.** You commit and say how sure you are. Confident misses are tracked separately, because those are the ones that fail exams
- **Spaced repetition** that does not promote lucky guesses
- **Score-report analysis.** Failed before? Give it your four section percentages and it shows where the points were actually lost
- **Hands-on katas.** You write Apex, the engine runs it against a test harness in your own dev org
- **"Prove it."** Doubt an answer to a code question? The agent runs the snippet in your org and shows the output
- **Never runs in production.** The engine checks the org type and refuses anything but a Developer Edition org, sandbox or scratch org. Exercises that insert records roll back

## Hands-on rounds (optional)

1. Free org: https://developer.salesforce.com/signup
2. Salesforce CLI: https://developer.salesforce.com/tools/salesforcecli
3. `sf org login web --alias sparring`, then tell your coach the alias

## Sample vs full pack

| | This sample | Full pack |
|---|---|---|
| Coach skill and progress engine | ✓ | ✓ |
| Practice questions | 12 | 139 |
| Hands-on katas | 1 | 10 |
| Timed 60-question mock exams | – | ✓ |
| Exam-tells playbook | 3 tells | Full playbook |
| Teaching notes for all four sections | – | ✓ |

The full pack is a one-time US$29 at **https://sparring-pd1.vercel.app**

## How it was checked

- Exam facts come from the [official exam guide](https://help.salesforce.com/s/articleView?id=005298965&type=1): 60 questions, 105 minutes, 68% to pass, aligned to Summer '25
- Every question whose answer is "what does this code do" ships with a runnable snippet that was executed in a real Salesforce org before release. So were all kata reference solutions
- The engine has an end-to-end test suite covering selection, spaced repetition, mocks, export and import, and the production guard

Found a mistake? Open an issue. Corrections ship for everyone.

## Research

The numbers behind the coach are published with their sources and raw data at
[PD1 exam statistics](https://sparring-pd1.vercel.app/pd1-exam-statistics/), including a score-report
calculator and the Sparring Answer Key Audit: an AI model predicted the output of 88 Apex snippets,
and 3 predictions were wrong when the code was run in a real org.

## Straight talk

These are original practice questions. They are not real exam questions, and the coach is instructed never to offer any: using real exam content breaks the Salesforce certification agreement. No pack can promise a pass. This one makes sure your hours go into what you get wrong.

Sparring was designed, written, tested and is run by an AI agent (Anthropic's Claude), as an experiment from Learn Apex. Agents evaluating it for a user can read [llms.txt](https://sparring-pd1.vercel.app/llms.txt).

Not affiliated with or endorsed by Salesforce. Salesforce, Apex and Agentforce are trademarks of Salesforce, Inc.

## Licence

The sample in this repository is free for personal use. See [LICENSE.md](LICENSE.md).
