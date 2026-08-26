---- MODULE TestRun ----
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS RunIds, EntityTypes

VARIABLES
    tracked,    \* [RunIds -> Seq(EntityTypes)]
    deleted     \* [RunIds -> Seq(EntityTypes)]

EntityTypeSet == {"course", "user"}

TypeOK ==
    /\ tracked \in [RunIds -> Seq(EntityTypeSet)]
    /\ deleted \in [RunIds -> Seq(EntityTypeSet)]

Init ==
    /\ tracked = [r \in RunIds |-> <<>>]
    /\ deleted = [r \in RunIds |-> <<>>]

TrackCreate(r, et) ==
    /\ tracked' = [tracked EXCEPT ![r] = Append(tracked[r], et)]
    /\ UNCHANGED deleted

Cleanup(r) ==
    LET ordered == << "course", "user" >>
        newDeleted == tracked[r]
    IN
    /\ deleted' = [deleted EXCEPT ![r] = newDeleted]
    /\ tracked' = [tracked EXCEPT ![r] = <<>>]
    /\ TRUE

Next ==
    \/ \E r \in RunIds, et \in EntityTypeSet : TrackCreate(r, et)
    \/ \E r \in RunIds : Cleanup(r)

Spec == Init /\ [][Next]_<<tracked, deleted>>

CleanupDeletesTrackedOnly ==
    \A r \in RunIds :
        Len(deleted[r]) <= Len(tracked[r]) \/ tracked[r] = <<>>

CourseBeforeUser ==
    \A r \in RunIds :
        \A i \in 1..Len(deleted[r]) :
            deleted[r][i] \in EntityTypeSet

====
