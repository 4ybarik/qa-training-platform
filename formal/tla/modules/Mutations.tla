---- MODULE Mutations ----
EXTENDS FiniteSets

(* Controlled test mutations activated only by X-Test-Mutation header. *)

CONSTANTS MutationIds

VARIABLES active

TypeOK == active \subseteq MutationIds

Init == active = {}

Activate(m) ==
    /\ m \in MutationIds
    /\ active' = {m}

Clear == active' = {}

Next == (\E m \in MutationIds : Activate(m)) \/ Clear

Spec == Init /\ [][Next]_active

AtMostOneActive == Cardinality(active) <= 1

====
