---- MODULE PracticeModule ----
EXTENDS Naturals, FiniteSets

(* practice.catalog / practice package helpers (non-API). *)

CONSTANTS Challenges

VARIABLES loaded

TypeOK == loaded \in BOOLEAN

Init == loaded = FALSE

Load == loaded' = TRUE

Next == Load

Spec == Init /\ [][Next]_loaded

====
