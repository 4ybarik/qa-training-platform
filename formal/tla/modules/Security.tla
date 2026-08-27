---- MODULE Security ----
EXTENDS Naturals

(* Pure crypto helpers: hash_password, verify_password, JWT create/decode.
   Pre: password/token well-formed. Post: verify matches hash; decode checks type/exp. *)

VARIABLES lastOp

Ops == {"hash", "verify", "access", "refresh", "decode"}

TypeOK == lastOp \in Ops \union {"none"}

Init == lastOp = "none"

Hash == lastOp' = "hash"
Verify == lastOp' = "verify"
CreateAccess == lastOp' = "access"
CreateRefresh == lastOp' = "refresh"
Decode == lastOp' = "decode"

Next == Hash \/ Verify \/ CreateAccess \/ CreateRefresh \/ Decode

Spec == Init /\ [][Next]_lastOp

====
