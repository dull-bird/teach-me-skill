# Teach Me Value Rubric

Use this rubric when deciding whether a development phase should become a
learning capture.

## Score Dimensions

Score each dimension from 0-2, then add them:

- Novelty: 0 familiar, 1 partly new, 2 likely new.
- Transferability: 0 local detail, 1 useful pattern, 2 broadly reusable.
- Project relevance: 0 incidental, 1 explains a file/module, 2 explains how the
  project works.
- Hidden complexity: 0 obvious, 1 some mechanism, 2 easy to miss but important.
- Future bug risk: 0 harmless, 1 can cause confusion, 2 likely source of bugs.
- Algorithmic value: 0 no reusable thought, 1 light pattern, 2 strong reasoning
  model or tradeoff.
- User signal: 0 no signal, 1 uncertain language, 2 explicit "why/teach/review".
- Concept importance: 0 minor/peripheral, 1 domain-relevant idea, 2 foundational
  or field-defining. Score this on the idea itself, independent of how much
  tool activity produced it — a chapter of a book or a research paper can score
  2 here with zero file edits, tests, or builds behind it.

## Interpretation

- 9 or more: capture as a full note.
- 6-8: capture only if it is one of the top 1-3 concepts this phase.
- 5 or less: do not create a note unless the user manually asked.

Tool-call volume (file edits, test runs, builds) is not part of this rubric
and should never gate it. It only feeds the earlier, mechanical "is this worth
a review at all" trigger — a phase with heavy tool activity but low scores
here still shouldn't be captured, and a phase with almost no tool activity
(reading a book, importing a PDF, discussing an article) can still score high
here on Concept importance and Novelty alone.

## High-Value Examples

- Why Vite uses esbuild for dependency pre-bundling.
- How a dependency graph lets a bundler rebuild only affected modules.
- Why Vue component state should be lifted instead of duplicated.
- How optimistic UI trades correctness complexity for perceived speed.
- Why idempotency matters for retryable APIs.
- Why normalization prevents duplicated client-side state bugs.
- Why spaced repetition times review at the point recall becomes effortful,
  not on a fixed calendar interval (from a book on learning science).
- How a historical event's causes are usually overdetermined rather than
  single-cause, and why that changes how you should explain it (from reading
  a history chapter, no code involved).

## Low-Value Examples

- A one-off CSS color value.
- A package version unless the version changes behavior.
- A command flag that the user can trivially rediscover.
- A file rename with no architecture consequence.

## Interesting Versus Useful

Interesting facts are allowed only when they support future engineering
judgment. Prefer "this helps you decide what to do next time" over "this is a
fun detail."
