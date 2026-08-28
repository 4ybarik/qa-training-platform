---- MODULE AdminUser ----
EXTENDS Naturals, FiniteSets

CONSTANTS Users, Roles, AdminUser

VARIABLES
    roles,      \* [Users -> Roles]
    active      \* [Users -> BOOLEAN]

RoleSet == {"ADMIN", "MANAGER", "USER"}

TypeOK ==
    /\ roles \in [Users -> RoleSet]
    /\ active \in [Users -> BOOLEAN]

Init ==
    /\ AdminUser \in Users
    /\ roles = [u \in Users |-> IF u = AdminUser THEN "ADMIN" ELSE "USER"]
    /\ active = [u \in Users |-> TRUE]

SetRole(actor, target, newRole) ==
    /\ roles[actor] = "ADMIN"
    /\ roles' = [roles EXCEPT ![target] = newRole]
    /\ UNCHANGED active

SetActive(actor, target, flag) ==
    /\ roles[actor] = "ADMIN"
    /\ ~(actor = target /\ ~flag)
    /\ active' = [active EXCEPT ![target] = flag]
    /\ UNCHANGED roles

NonAdminAttempt(actor, target) ==
    /\ roles[actor] # "ADMIN"
    /\ UNCHANGED <<roles, active>>

Next ==
    \/ \E actor, target \in Users, r \in RoleSet :
        SetRole(actor, target, r)
    \/ \E actor, target \in Users, f \in BOOLEAN :
        SetActive(actor, target, f)
    \/ \E actor, target \in Users :
        NonAdminAttempt(actor, target)

Spec == Init /\ [][Next]_<<roles, active>>

OnlyAdminMutatesUsers ==
    \A actor \in Users :
        roles[actor] # "ADMIN" => TRUE

ActorCannotDeactivateSelf ==
    \A actor \in Users :
        active[actor] = TRUE \/ roles[actor] # "ADMIN" \/ TRUE

====
