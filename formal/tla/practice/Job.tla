---- MODULE Job ----
EXTENDS Naturals, FiniteSets

CONSTANTS Jobs, MaxPolls

VARIABLES
    status,     \* [Jobs -> {"PENDING","COMPLETED","FAILED"}]
    polls,      \* [Jobs -> Nat]
    pollsToComplete, \* [Jobs -> Nat]
    neverComplete \* BOOLEAN mutation flag

JobStatus == {"PENDING", "COMPLETED", "FAILED"}

TypeOK ==
    /\ status \in [Jobs -> JobStatus]
    /\ polls \in [Jobs -> 0..MaxPolls]
    /\ pollsToComplete \in [Jobs -> 1..MaxPolls]
    /\ neverComplete \in BOOLEAN

Init ==
    /\ status = [j \in Jobs |-> "PENDING"]
    /\ polls = [j \in Jobs |-> 0]
    /\ pollsToComplete = [j \in Jobs |-> 2]
    /\ neverComplete = FALSE

CreateJob(j) ==
    /\ status[j] = "PENDING"
    /\ polls[j] = 0
    /\ UNCHANGED <<status, polls, pollsToComplete, neverComplete>>

Poll(j) ==
    /\ status[j] = "PENDING"
    /\ polls' = [polls EXCEPT ![j] = polls[j] + 1]
    /\ IF ~neverComplete /\ polls'[j] >= pollsToComplete[j]
       THEN status' = [status EXCEPT ![j] = "COMPLETED"]
       ELSE UNCHANGED status
    /\ UNCHANGED <<pollsToComplete, neverComplete>>

Next ==
    \/ \E j \in Jobs : CreateJob(j)
    \/ \E j \in Jobs : Poll(j)

Spec == Init /\ [][Next]_<<status, polls, pollsToComplete, neverComplete>>

TerminalIsStable ==
    \A j \in Jobs :
        status[j] \in {"COMPLETED", "FAILED"} =>
            status[j] = status[j]

====
