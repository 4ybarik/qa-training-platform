---- MODULE Database ----
EXTENDS Naturals

(* Session factory and init_db / get_db lifecycle. *)

VARIABLES dbReady

TypeOK == dbReady \in BOOLEAN

Init == dbReady = FALSE

InitDb == dbReady' = TRUE
GetDb == dbReady = TRUE /\ UNCHANGED dbReady

Next == InitDb \/ GetDb

Spec == Init /\ [][Next]_dbReady

DbReadyAfterInit == dbReady \in BOOLEAN

====
