---- MODULE AuthAccount ----
EXTENDS Naturals, Sequences, FiniteSets

CONSTANTS Users, MaxLoginAttempts, WindowSize

VARIABLES
    accounts,       \* [email -> {status, active}]
    loginHits,      \* [email -> Nat]
    tokensIssued    \* Nat

AccountStatus == {"Absent", "Active", "Inactive"}

TypeOK ==
    /\ accounts \in [Users -> AccountStatus]
    /\ loginHits \in [Users -> 0..MaxLoginAttempts]
    /\ tokensIssued \in Nat

Init ==
    /\ accounts = [u \in Users |-> "Absent"]
    /\ loginHits = [u \in Users |-> 0]
    /\ tokensIssued = 0

Register(u) ==
    /\ accounts[u] = "Absent"
    /\ accounts' = [accounts EXCEPT ![u] = "Active"]
    /\ loginHits' = loginHits
    /\ tokensIssued' = tokensIssued

LoginSuccess(u) ==
    /\ accounts[u] = "Active"
    /\ loginHits[u] < MaxLoginAttempts
    /\ loginHits' = [loginHits EXCEPT ![u] = loginHits[u] + 1]
    /\ accounts' = accounts
    /\ tokensIssued' = tokensIssued + 1

LoginFailInactive(u) ==
    /\ accounts[u] = "Inactive"
    /\ UNCHANGED <<accounts, loginHits, tokensIssued>>

Deactivate(u) ==
    /\ accounts[u] = "Active"
    /\ accounts' = [accounts EXCEPT ![u] = "Inactive"]
    /\ loginHits' = loginHits
    /\ tokensIssued' = tokensIssued

Next ==
    \/ \E u \in Users : Register(u)
    \/ \E u \in Users : LoginSuccess(u)
    \/ \E u \in Users : LoginFailInactive(u)
    \/ \E u \in Users : Deactivate(u)

Spec == Init /\ [][Next]_<<accounts, loginHits, tokensIssued>>

EmailUnique ==
    \A u1, u2 \in Users :
        accounts[u1] # "Absent" /\ accounts[u2] # "Absent" => u1 = u2

InactiveCannotIssueTokens ==
    \A u \in Users : accounts[u] = "Inactive" => loginHits[u] <= MaxLoginAttempts

LoginHitsWithinWindow ==
    \A u \in Users : loginHits[u] <= MaxLoginAttempts

====
