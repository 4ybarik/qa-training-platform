---- MODULE Config ----
EXTENDS Naturals

(* Settings / get_settings — immutable config snapshot per process. *)

VARIABLES loaded

TypeOK == loaded \in BOOLEAN

Init == loaded = FALSE

Load == loaded' = TRUE

Next == Load

Spec == Init /\ [][Next]_loaded

====
