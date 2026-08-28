---- MODULE Playground ----
EXTENDS Naturals, FiniteSets

CONSTANTS Paths, ControlPaths

VARIABLES
    mode,       \* {"off","probabilistic","scenario"}
    chaosApplied \* [Paths -> BOOLEAN]

ModeSet == {"off", "probabilistic", "scenario"}
ScenarioSet == {"slow", "fail", "fail-first", "malformed-json"}

TypeOK ==
    /\ mode \in ModeSet
    /\ chaosApplied \in [Paths -> BOOLEAN]

Init ==
    /\ mode = "off"
    /\ chaosApplied = [p \in Paths |-> FALSE]

EnableProbabilistic ==
    /\ mode' = "probabilistic"
    /\ UNCHANGED chaosApplied

ApplyChaos(p) ==
    /\ mode # "off"
    /\ p \notin ControlPaths
    /\ chaosApplied' = [chaosApplied EXCEPT ![p] = TRUE]
    /\ UNCHANGED mode

SkipControlPath(p) ==
    /\ p \in ControlPaths
    /\ UNCHANGED <<mode, chaosApplied>>

Next ==
    \/ EnableProbabilistic
    \/ \E p \in Paths : ApplyChaos(p)
    \/ \E p \in ControlPaths : SkipControlPath(p)

Spec == Init /\ [][Next]_<<mode, chaosApplied>>

ControlPathsNeverChaosed ==
    \A p \in ControlPaths : ~chaosApplied[p]

====
