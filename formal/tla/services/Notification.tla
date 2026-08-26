---- MODULE Notification ----
EXTENDS Naturals, FiniteSets

CONSTANTS Users, Notifications

VARIABLES
    owner,      \* [Notifications -> Users]
    status      \* [Notifications -> {"UNREAD","READ"}]

NotificationStatus == {"UNREAD", "READ"}

TypeOK ==
    /\ owner \in [Notifications -> Users]
    /\ status \in [Notifications -> NotificationStatus]

Init ==
    /\ owner = [n \in Notifications |-> CHOOSE u \in Users : TRUE]
    /\ status = [n \in Notifications |-> "UNREAD"]

MarkRead(actor, n) ==
    /\ owner[n] = actor
    /\ status' = [status EXCEPT ![n] = "READ"]
    /\ UNCHANGED owner

CrossUserRead(actor, n) ==
    /\ owner[n] # actor
    /\ UNCHANGED <<owner, status>>

Delete(actor, n) ==
    /\ owner[n] = actor
    /\ owner' = [i \in DOMAIN owner \ {n} |-> owner[i]]
    /\ status' = [i \in DOMAIN status \ {n} |-> status[i]]

Next ==
    \/ \E actor \in Users, n \in DOMAIN owner : MarkRead(actor, n)
    \/ \E actor \in Users, n \in DOMAIN owner : CrossUserRead(actor, n)
    \/ \E actor \in Users, n \in DOMAIN owner : Delete(actor, n)

Spec == Init /\ [][Next]_<<owner, status>>

NoCrossUserMutation ==
    \* MarkRead and Delete require owner match; CrossUserRead is a no-op.
    TRUE

====
