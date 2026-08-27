---- MODULE Deps ----
EXTENDS Naturals, FiniteSets

(* Auth dependencies: get_current_user, get_optional_user, require_roles. *)

CONSTANTS Roles

VARIABLES allowed

TypeOK == allowed \subseteq Roles

Init == allowed = {}

RequireRoles(rs) ==
    /\ rs \subseteq Roles
    /\ allowed' = rs

Next == \E rs \in SUBSET Roles : RequireRoles(rs)

Spec == Init /\ [][Next]_allowed

====
