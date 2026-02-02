"""Heuristic Lean4 tactic suggestion helper."""
import argparse


def suggest(goal: str) -> str:
    g = goal.lower()
    if "forall" in g or "∀" in g:
        return "Try `intro` to introduce variables."
    if "exists" in g or "∃" in g:
        return "Provide a witness with `refine ⟨_, ?_⟩` or `exists`."
    if " and " in g or "∧" in g:
        return "Use `constructor` or `cases` to split the conjunction."
    if " or " in g or "∨" in g:
        return "Use `cases` to split the disjunction."
    if "=" in g:
        return "Try `rfl`, `simp`, or `rw` with a known lemma."
    if "nat" in g or "induction" in g:
        return "Consider `induction` on the natural number."
    return "Consider breaking the goal into smaller lemmas."


def main() -> None:
    parser = argparse.ArgumentParser(description="Lean4 tactic suggestion")
    parser.add_argument("goal", help="goal description")
    args = parser.parse_args()
    print(suggest(args.goal))


if __name__ == "__main__":
    main()
