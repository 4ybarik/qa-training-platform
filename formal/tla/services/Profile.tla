---- MODULE Profile ----
EXTENDS Naturals, FiniteSets

(* ProfileService: get/create-on-miss, update fields, avatar URL. *)

CONSTANTS Users

VARIABLES profiles

TypeOK == profiles \subseteq Users

Init == profiles = {}

Ensure(u) ==
    /\ u \in Users
    /\ profiles' = profiles \union {u}

Update(u) ==
    /\ u \in profiles
    /\ UNCHANGED profiles

Next ==
    \/ \E u \in Users : Ensure(u)
    \/ \E u \in Users : Update(u)

Spec == Init /\ [][Next]_profiles

====
