---- MODULE Types ----
EXTENDS Naturals, FiniteSets

(* Tier-B/C: Pydantic schemas, enums, domain errors — structural TypeOK only. *)

RoleSet == {"ADMIN", "MANAGER", "USER"}
CourseStatusSet == {"DRAFT", "PUBLISHED", "ARCHIVED"}
QuestionTypeSet == {"SINGLE", "MULTI", "TEXT", "DND"}
NotificationStatusSet == {"UNREAD", "READ"}
ErrorKindSet == {"NotFound", "Conflict", "Auth", "Permission", "RateLimit"}

VARIABLES schemaRegistry

TypeOK ==
    schemaRegistry \subseteq
        (RoleSet \union CourseStatusSet \union QuestionTypeSet \union
         NotificationStatusSet \union ErrorKindSet)

Init ==
    schemaRegistry = RoleSet \union CourseStatusSet \union QuestionTypeSet \union
                     NotificationStatusSet \union ErrorKindSet

Next ==
    UNCHANGED schemaRegistry

Spec == Init /\ [][Next]_schemaRegistry

SchemaRegistryComplete ==
    Cardinality(schemaRegistry) >= 5

====
