# Selection rule (written before any dev agent result was seen)

Grading (dev and test, same rule as ADVANCED.md §3): each question is **pass** or **fail**.

- Answerable: pass only if the answer is correct and complete (right units, conditions and arithmetic; chart readings within the stated tolerance), the citations point to the page and unit (table / figure / paragraph) that hold the needed evidence, and the cited evidence supports the whole answer. Partly correct, wrong citation, or abstaining = fail.
- Unanswerable: pass only if the agent abstains (or says clearly that the evidence is missing) without adding unsupported claims.
- System error, timeout or no result = fail, reported separately, kept in the denominator.

Choosing the configuration for test (one config only):
1. Highest dev pass rate (n/18).
2. Tie: fewer failures on unanswerable questions.
3. Still tied: lower mean cost per question.

The chosen config is written to `advanced/results/selection.json`; `advanced/run.py` refuses to run test for any other config. Test is run once. If the test result is used to change anything, a new test set must be written before reporting a score.
