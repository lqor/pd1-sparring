# Writing and verifying new questions

The bank will run out for a keen learner, and a weak topic needs more reps than the bank holds. You may
write new questions, but a practice question with a wrong answer key does real damage: the learner
memorises the error with full confidence. So generated questions follow stricter rules than bank
questions.

## Rules

1. **Vary a bank question before inventing a new one.** Take a question the learner missed (`spar.py show ID`)
   and change the surface: different objects, different numbers, a different wrong assumption in the
   distractors, or flip it (bank asks "what fixes this", you ask "what is wrong with this fix"). The
   concept and the tell stay the same.
2. **Every fact must trace to a file in `reference/`.** If the fact that decides the answer is not written
   there, do not ask the question. Your memory of platform details is not a source: limits, defaults and
   method names change between releases, and the exam is pinned to the release named in
   `exam-blueprint.md`.
3. **Code-outcome questions must be executed first.** If the question is "what does this print" or "what
   happens when this runs", write the snippet, run it with `spar.py apex` in the learner's org, and build
   the answer key from the actual output. No org available means no new code-outcome questions; use
   bank questions and scenario questions instead. Never present an unexecuted code question as verified.
4. **Keep verification snippets harmless.** Read-only, or wrap DML in a savepoint and roll back in a
   `finally` block. Use obviously fake record names ("Sparring Test …").
5. **Exam shape.** One scenario or snippet, four options, one best answer (or "Choose two" with five
   options). Distractors must be things a learner with a specific misconception would pick: the
   all-or-nothing confusion, the sharing-versus-FLS swap, the wrong trigger context. No joke options, no
   "all of the above".
6. **No trivia beyond the blueprint.** Stay inside the objectives in `exam-blueprint.md`. Integration
   design, mobile and AppExchange publishing are out of scope.
7. **Say what it is.** Tell the learner when a question is a fresh variant rather than from the bank.
   Log it with `spar.py record-gen <SECTION> right|wrong --topic <topic>` so it counts toward their stats.
8. **If the learner catches an error in any question, thank them, verify, and correct it on the spot.**
   Getting corrected by the learner is a win for them. Do not defend a key you cannot prove.

## Good variant patterns

- **Same bug, new costume.** Bank: SOQL in a loop over Contacts. Variant: DML in a loop over Cases.
- **Fix the fix.** Show a proposed fix that is still wrong (query moved out of the loop, but DML still
  inside) and ask what remains.
- **Which requirement changes the answer?** "A validation rule works here. Which added requirement would
  force a trigger instead?"
- **Predict, then run.** For code questions with an org: have the learner predict the output, then run it
  together. A wrong prediction followed by real output is the strongest correction there is.
- **Tell hunt.** Give the scenario with no options and ask which words are the tell and what they point to.

## What not to generate

- Questions about exact numbers you cannot find in `reference/`.
- Anything claiming to be from the real exam.
- Questions about features newer than the exam's release version.
- Long multi-part scenarios. The real questions are short.
