---- MODULE Learning ----
EXTENDS Naturals

CONSTANTS Users, Challenges, MaxAttempts

VARIABLES
    attempts,       \* [Users \X Challenges -> 0..MaxAttempts]
    bestScore,      \* [Users \X Challenges -> 0..100]
    completed       \* [Users \X Challenges -> BOOLEAN]

Pairs == Users \X Challenges

TypeOK ==
    /\ attempts \in [Pairs -> 0..MaxAttempts]
    /\ bestScore \in [Pairs -> 0..100]
    /\ completed \in [Pairs -> BOOLEAN]

Init ==
    /\ attempts = [key \in Pairs |-> 0]
    /\ bestScore = [key \in Pairs |-> 0]
    /\ completed = [key \in Pairs |-> FALSE]

RecordGrade(user, challenge, score, passed) ==
    LET key == <<user, challenge>>
    IN
    /\ attempts[key] < MaxAttempts
    /\ attempts' = [attempts EXCEPT ![key] = @ + 1]
    /\ bestScore' = [bestScore EXCEPT
        ![key] = IF score > bestScore[key] THEN score ELSE bestScore[key]]
    /\ completed' = [completed EXCEPT ![key] = @ \/ passed]

Next ==
    \E user \in Users, challenge \in Challenges,
       score \in 0..100 :
        RecordGrade(user, challenge, score, score = 100)

Spec == Init /\ [][Next]_<<attempts, bestScore, completed>>

CompletedHasAttempt ==
    \A key \in Pairs : completed[key] => attempts[key] > 0

PerfectScoreCompletes ==
    \A key \in Pairs : bestScore[key] = 100 => completed[key]

====
