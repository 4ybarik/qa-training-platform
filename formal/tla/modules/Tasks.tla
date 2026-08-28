---- MODULE Tasks ----
EXTENDS Naturals

(* Integration task worker: process_payload with optional delay/fail. *)

VARIABLES status

Statuses == {"idle", "ok", "failed"}

TypeOK == status \in Statuses

Init == status = "idle"

Succeed == status' = "ok"
Fail == status' = "failed"

Next == Succeed \/ Fail

Spec == Init /\ [][Next]_status

====
