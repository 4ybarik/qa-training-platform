---- MODULE ExamAttempt ----
EXTENDS Naturals, FiniteSets

CONSTANTS Users, Exams, PassThreshold, MaxProgress

VARIABLES
    scores,         \* [Users x Exams -> 0..100]
    passed,         \* [Users x Exams -> BOOLEAN]
    progress,       \* [Users x Exams -> 0..MaxProgress]
    hasEnrollment   \* [Users x Exams -> BOOLEAN]

TypeOK ==
    /\ scores \in [Users \X Exams -> 0..100]
    /\ passed \in [Users \X Exams -> BOOLEAN]
    /\ progress \in [Users \X Exams -> 0..MaxProgress]
    /\ hasEnrollment \in [Users \X Exams -> BOOLEAN]

Init ==
    /\ scores = [p \in Users \X Exams |-> 0]
    /\ passed = [p \in Users \X Exams |-> FALSE]
    /\ progress = [p \in Users \X Exams |-> 0]
    /\ hasEnrollment = [p \in Users \X Exams |-> FALSE]

SetEnrollment(u, e) ==
    /\ hasEnrollment' = [hasEnrollment EXCEPT ![<<u, e>>] = TRUE]
    /\ UNCHANGED <<scores, passed, progress>>

Submit(u, e, score) ==
    /\ score \in 0..100
    /\ scores' = [scores EXCEPT ![<<u, e>>] = score]
    /\ passed' = [passed EXCEPT ![<<u, e>>] = (score >= PassThreshold)]
    /\ progress' = [progress EXCEPT ![<<u, e>>] =
        IF hasEnrollment[<<u, e>>]
        THEN IF score >= PassThreshold
             THEN MaxProgress
             ELSE IF progress[<<u, e>>] >= score THEN progress[<<u, e>>] ELSE score
        ELSE progress[<<u, e>>]]
    /\ UNCHANGED hasEnrollment

Next ==
    \/ \E u \in Users, e \in Exams : SetEnrollment(u, e)
    \/ \E u \in Users, e \in Exams, s \in 0..100 : Submit(u, e, s)

Spec == Init /\ [][Next]_<<scores, passed, progress, hasEnrollment>>

PassedIffScoreGe60 ==
    \A u \in Users, e \in Exams :
        passed[<<u, e>>] <=> scores[<<u, e>>] >= PassThreshold

CertificateOnlyIfPassed ==
    \A u \in Users, e \in Exams :
        passed[<<u, e>>] => scores[<<u, e>>] >= PassThreshold

ProgressMonotonic ==
    \A u \in Users, e \in Exams :
        ~hasEnrollment[<<u, e>>] \/ progress[<<u, e>>] \in 0..MaxProgress

====
