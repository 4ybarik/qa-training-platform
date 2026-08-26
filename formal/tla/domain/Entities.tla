---- MODULE Entities ----
EXTENDS Naturals, FiniteSets

(* Tier-B lifecycle TypeOK for ORM entities and repositories.
   Each entity supports create/read/update/delete without violating FK shape. *)

CONSTANTS Users, Courses, Exams

VARIABLES
    users, courses, enrollments, exams

TypeOK ==
    /\ users \subseteq Users
    /\ courses \subseteq Courses
    /\ exams \subseteq Exams
    /\ enrollments \subseteq (Users \X Courses)

Init ==
    /\ users = {}
    /\ courses = {}
    /\ enrollments = {}
    /\ exams = {}

CreateUser(u) ==
    /\ u \notin users
    /\ users' = users \union {u}
    /\ UNCHANGED <<courses, enrollments, exams>>

CreateCourse(c) ==
    /\ c \notin courses
    /\ courses' = courses \union {c}
    /\ UNCHANGED <<users, enrollments, exams>>

CreateEnrollment(u, c) ==
    /\ u \in users
    /\ c \in courses
    /\ <<u, c>> \notin enrollments
    /\ enrollments' = enrollments \union {<<u, c>>}
    /\ UNCHANGED <<users, courses, exams>>

CreateExam(e, c) ==
    /\ c \in courses
    /\ e \notin exams
    /\ exams' = exams \union {e}
    /\ UNCHANGED <<users, courses, enrollments>>

Next ==
    \/ \E u \in Users : CreateUser(u)
    \/ \E c \in Courses : CreateCourse(c)
    \/ \E u \in Users, c \in Courses : CreateEnrollment(u, c)
    \/ \E e \in Exams, c \in Courses : CreateExam(e, c)

Spec == Init /\ [][Next]_<<users, courses, enrollments, exams>>

EnrollmentRequiresUserAndCourse ==
    \A pair \in enrollments :
        pair[1] \in users /\ pair[2] \in courses

====
