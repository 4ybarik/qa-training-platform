---- MODULE Enums ----
EXTENDS FiniteSets

RoleSet == {"ADMIN", "MANAGER", "USER"}
CourseStatusSet == {"DRAFT", "PUBLISHED", "ARCHIVED"}
QuestionTypeSet == {"SINGLE", "MULTI", "TEXT", "DND"}
NotificationStatusSet == {"UNREAD", "READ"}

VARIABLES enums

TypeOK ==
    enums = RoleSet \union CourseStatusSet \union QuestionTypeSet \union NotificationStatusSet

Init ==
    enums = RoleSet \union CourseStatusSet \union QuestionTypeSet \union NotificationStatusSet

Next == UNCHANGED enums

Spec == Init /\ [][Next]_enums

====
