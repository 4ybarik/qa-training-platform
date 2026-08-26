---- MODULE CourseLifecycle ----
EXTENDS Naturals, FiniteSets

CONSTANTS Users, Courses, MaxProgress

VARIABLES
    courseStatus,   \* [Courses -> {"DRAFT","PUBLISHED","ARCHIVED"}]
    enrollments,    \* subset of Users x Courses
    progress        \* [Users x Courses -> 0..MaxProgress]

CourseStatusSet == {"DRAFT", "PUBLISHED", "ARCHIVED"}

TypeOK ==
    /\ courseStatus \in [Courses -> CourseStatusSet]
    /\ enrollments \subseteq (Users \X Courses)
    /\ progress \in [enrollments -> 0..MaxProgress]

Init ==
    /\ courseStatus = [c \in Courses |-> "PUBLISHED"]
    /\ enrollments = {}
    /\ progress = <<>>

Enroll(u, c) ==
    /\ <<u, c>> \notin enrollments
    /\ courseStatus[c] # "ARCHIVED"
    /\ enrollments' = enrollments \union {<<u, c>>}
    /\ progress' = progress @@ (<<u, c>> :> 0)
    /\ courseStatus' = courseStatus

DuplicateEnroll(u, c) ==
    /\ <<u, c>> \in enrollments
    /\ UNCHANGED <<courseStatus, enrollments, progress>>

UpdateProgress(u, c, p) ==
    /\ <<u, c>> \in enrollments
    /\ p \in 0..MaxProgress
    /\ progress' = [progress EXCEPT ![<<u, c>>] = IF progress[<<u, c>>] >= p
                                                   THEN progress[<<u, c>>]
                                                   ELSE p]
    /\ UNCHANGED <<courseStatus, enrollments>>

ArchiveCourse(c) ==
    /\ courseStatus' = [courseStatus EXCEPT ![c] = "ARCHIVED"]
    /\ UNCHANGED <<enrollments, progress>>

Next ==
    \/ \E u \in Users, c \in Courses : Enroll(u, c)
    \/ \E u \in Users, c \in Courses : DuplicateEnroll(u, c)
    \/ \E u \in Users, c \in Courses, p \in 0..MaxProgress : UpdateProgress(u, c, p)
    \/ \E c \in Courses : ArchiveCourse(c)

Spec == Init /\ [][Next]_<<courseStatus, enrollments, progress>>

AtMostOneEnrollmentPerUserCourse ==
    \A u \in Users, c \in Courses :
        Cardinality({e \in enrollments : e = <<u, c>>}) <= 1

ProgressIn0to100 ==
    \A e \in enrollments : progress[e] \in 0..MaxProgress

====
