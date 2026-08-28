---- MODULE PracticeTargets ----
EXTENDS Naturals, FiniteSets

(* Practice and integration API targets — excluded from ApiAdapters domain-delegation invariant.
   They intentionally mutate in-memory or adapter-local state for student test automation. *)

CONSTANTS PracticeEndpoints

VARIABLES directState

TypeOK ==
    directState \in SUBSET PracticeEndpoints

Init ==
    directState = PracticeEndpoints

Next ==
    UNCHANGED directState

Spec == Init /\ [][Next]_directState

PracticeTargetsOwnState ==
    directState = PracticeEndpoints

====
