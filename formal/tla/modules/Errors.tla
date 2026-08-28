---- MODULE Errors ----
EXTENDS FiniteSets

(* Domain error hierarchy and HTTP mapping. *)

ErrorKinds == {"NotFound", "Conflict", "Auth", "Permission", "RateLimit"}

VARIABLES registered

TypeOK == registered \subseteq ErrorKinds

Init == registered = ErrorKinds

Next == UNCHANGED registered

Spec == Init /\ [][Next]_registered

AllKindsRegistered == registered = ErrorKinds

====
