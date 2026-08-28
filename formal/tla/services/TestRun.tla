---- MODULE TestRun ----
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS RunIds, EntityTypes

VARIABLES
    tracked,       \* [RunIds -> SUBSET EntityTypeSet]
    everTracked,   \* [RunIds -> SUBSET EntityTypeSet]
    deleted        \* [RunIds -> Seq(EntityTypeSet)]

EntityTypeSet == {"course", "user"}

TypeOK ==
    /\ tracked \in [RunIds -> SUBSET EntityTypeSet]
    /\ everTracked \in [RunIds -> SUBSET EntityTypeSet]
    /\ deleted \in [RunIds -> Seq(EntityTypeSet)]

Init ==
    /\ tracked = [r \in RunIds |-> {}]
    /\ everTracked = [r \in RunIds |-> {}]
    /\ deleted = [r \in RunIds |-> <<>>]

TrackCreate(r, et) ==
    /\ tracked' = [tracked EXCEPT ![r] = @ \union {et}]
    /\ everTracked' = [everTracked EXCEPT ![r] = @ \union {et}]
    /\ UNCHANGED deleted

DeletionOrder(items) ==
    IF "course" \in items
    THEN IF "user" \in items THEN <<"course", "user">> ELSE <<"course">>
    ELSE IF "user" \in items THEN <<"user">> ELSE <<>>

Cleanup(r) ==
    /\ deleted' = [deleted EXCEPT ![r] = DeletionOrder(tracked[r])]
    /\ tracked' = [tracked EXCEPT ![r] = {}]
    /\ UNCHANGED everTracked

Next ==
    \/ \E r \in RunIds, et \in EntityTypeSet : TrackCreate(r, et)
    \/ \E r \in RunIds : Cleanup(r)

Spec == Init /\ [][Next]_<<tracked, everTracked, deleted>>

CleanupDeletesTrackedOnly ==
    \A r \in RunIds :
        \A i \in 1..Len(deleted[r]) : deleted[r][i] \in everTracked[r]

CourseBeforeUser ==
    \A r \in RunIds :
        \A i, j \in 1..Len(deleted[r]) :
            deleted[r][i] = "course" /\ deleted[r][j] = "user" => i < j

====
