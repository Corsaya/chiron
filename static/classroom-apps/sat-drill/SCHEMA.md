# SAT Adaptive Drill — data contract

Each domain ships one JS file that assigns a global. The drill engine
(`sat-drill.js`) reads these and runs an adaptive ladder per skill.

## File shape

```js
// static/classroom-apps/sat-drill/data/<slug>.js
window.SAT_DRILL_<UPPER_SNAKE_SLUG> = {
  id: "advanced-math",              // slug, matches filename
  title: "Math — Advanced Math",
  domain: "math",                   // "math" | "rw"
  skills: [ /* Skill objects, in the same order as the crash-course file */ ]
};
```

## Skill object

```js
{
  id: "M1",                                    // official subcategory code
  name: "Factor a quadratic (simple trinomial)",
  rungs: [ /* Rung objects — see below */ ]
}
```

## Rung object

A **rung** is one question at one difficulty level. The engine enters at
`level: 0` and moves down on wrong answers, up on right ones.

```js
{
  level: 0,          // REQUIRED. 0 = real SAT difficulty (entry point).
                     //  +1 = harder/stretch
                     //  -1 = one step more basic (breaks the skill into a simpler case)
                     //  -2 = foundational (the prerequisite concept underneath it)
  prompt: "If $x^2 + 7x + 12 = 0$, what is the sum of the solutions?",
  choices: ["-7", "-12", "7", "12"],   // 4 choices, NO "A)" prefixes — engine adds letters.
                                        // Use `null` for a grid-in (student-produced response).
  answer: 0,         // index into choices (0-3). For grid-in: a string like "18" or "3/4".
  explain: "…",      // Full worked explanation, shown after they answer either way.
                     // Teach the METHOD, not just the answer.
  hint: "…",         // Shown on the FIRST wrong attempt at this rung, before dropping a level.
                     // A nudge toward the method — never gives the answer away.
  desmos: "…"        // OPTIONAL, math only. How to get this answer faster in Desmos.
                     // Only include when Desmos is genuinely faster than by hand.
                     // Omit the field entirely otherwise — do not write "N/A".
}
```

## Rung level requirements

- **Advanced Math (M*) and Standard English Conventions (C*)** — confirmed weak
  spots, need the deepest ladders: rungs at levels **-2, -1, 0, +1** (4 per skill).
- **All other domains** — rungs at levels **-1, 0, +1** (3 per skill).

Exactly one rung per level. The engine assumes levels are unique within a skill.

## Content rules

- **LaTeX**: inline `$…$` and display `$$…$$`. Supported commands are limited to
  what `renderMath()` handles: `\frac`, `\dfrac`, `\sqrt`, `\pi`, `\theta`,
  `\times`, `\div`, `\pm`, `\leq`, `\geq`, `\neq`, `\approx`, `\to`, `\sim`,
  `\triangle`, `\sin`, `\cos`, `\tan`, `\begin{aligned}…\end{aligned}`, and
  superscripts/subscripts via `^{}` / `_{}`. **Do not use anything else** —
  no `\text{}`, no `\left(`/`\right)`, no `\quad`, no `\cdot` (write `\times`
  or just `*`), no matrices, no `\overline`.
- **R&W rungs** that need a passage: put the passage in the `prompt`, separated
  from the question by a blank line. Keep passages under ~90 words — this is a
  drill, not a full test.
- **Answer position must vary.** Do not let the correct answer sit at index 1 or 2
  most of the time. Spread it across 0/1/2/3 roughly evenly across the file.
- **Distractors must be real.** Each wrong choice should correspond to a specific
  plausible mistake (sign error, off-by-one, right method wrong step), not filler.
- **`explain` is the teaching moment.** This is what the student reads when they
  get it wrong at their weakest point. Write it like you're explaining to someone
  who just failed the question — state the method, run it, and name the trap.
- No trailing commas in the emitted JS. The file must parse as valid JavaScript.
