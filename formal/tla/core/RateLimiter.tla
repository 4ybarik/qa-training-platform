---- MODULE RateLimiter ----
EXTENDS Naturals, FiniteSets

CONSTANTS Keys, MaxAttempts

VARIABLES hits \* [Keys -> 0..MaxAttempts]

TypeOK ==
    hits \in [Keys -> 0..MaxAttempts]

Init ==
    hits = [k \in Keys |-> 0]

Hit(k) ==
    /\ hits[k] < MaxAttempts
    /\ hits' = [hits EXCEPT ![k] = hits[k] + 1]

Reject(k) ==
    /\ hits[k] >= MaxAttempts
    /\ UNCHANGED hits

Reset(k) ==
    /\ hits' = [hits EXCEPT ![k] = 0]

Next ==
    \/ \E k \in Keys : Hit(k)
    \/ \E k \in Keys : Reject(k)
    \/ \E k \in Keys : Reset(k)

Spec == Init /\ [][Next]_hits

HitsNeverExceedMaxInsideWindow ==
    \A k \in Keys : hits[k] <= MaxAttempts

====
