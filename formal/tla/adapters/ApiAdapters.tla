---- MODULE ApiAdapters ----
EXTENDS Naturals, FiniteSets

(* Tier-C: API/web endpoints delegate to services; no direct domain mutation.
   EXCLUDED from this invariant: /api/practice/*, /api/integrations/* — see LIMITATIONS.md. *)

CONSTANTS Endpoints, Services

VARIABLES
    calls,      \* [Endpoints -> Services]
    directMutations \* [Endpoints -> BOOLEAN]

TypeOK ==
    /\ calls \in [Endpoints -> Services]
    /\ directMutations \in [Endpoints -> BOOLEAN]

Init ==
    /\ calls = [e \in Endpoints |-> CHOOSE s \in Services : TRUE]
    /\ directMutations = [e \in Endpoints |-> FALSE]

InvokeEndpoint(e) ==
    /\ directMutations[e] = FALSE
    /\ UNCHANGED <<calls, directMutations>>

IllegalDirectMutation(e) ==
    /\ directMutations[e] = TRUE
    /\ UNCHANGED <<calls, directMutations>>

Next ==
    \/ \E e \in Endpoints : InvokeEndpoint(e)
    \/ \E e \in Endpoints : IllegalDirectMutation(e)

Spec == Init /\ [][Next]_<<calls, directMutations>>

EndpointDelegatesToService ==
    \A e \in Endpoints : directMutations[e] = FALSE

====
