---- MODULE Resource ----
EXTENDS Naturals, FiniteSets

CONSTANTS Namespaces, Resources, MaxVersion

VARIABLES
    store,      \* [Namespaces -> SUBSET Resources]
    versions    \* [Resources -> Nat]

TypeOK ==
    /\ store \in [Namespaces -> SUBSET Resources]
    /\ versions \in [Resources -> 0..MaxVersion]

Init ==
    /\ store = [ns \in Namespaces |-> {}]
    /\ versions = [r \in Resources |-> 0]

Create(ns, r) ==
    /\ r \notin store[ns]
    /\ \A other \in Namespaces : r \notin store[other]
    /\ store' = [store EXCEPT ![ns] = store[ns] \union {r}]
    /\ versions' = [versions EXCEPT ![r] = 1]
    /\ UNCHANGED <<>>

Update(ns, r, etag) ==
    /\ r \in store[ns]
    /\ etag = versions[r]
    /\ versions[r] < MaxVersion
    /\ versions' = [versions EXCEPT ![r] = versions[r] + 1]
    /\ UNCHANGED store

StaleUpdate(ns, r, etag) ==
    /\ r \in store[ns]
    /\ etag # versions[r]
    /\ UNCHANGED <<store, versions>>

Delete(ns, r) ==
    /\ r \in store[ns]
    /\ store' = [store EXCEPT ![ns] = store[ns] \ {r}]
    /\ UNCHANGED versions

Next ==
    \/ \E ns \in Namespaces, r \in Resources : Create(ns, r)
    \/ \E ns \in Namespaces, r \in Resources, e \in 0..MaxVersion : Update(ns, r, e)
    \/ \E ns \in Namespaces, r \in Resources, e \in 0..MaxVersion : StaleUpdate(ns, r, e)
    \/ \E ns \in Namespaces, r \in Resources : Delete(ns, r)

Spec == Init /\ [][Next]_<<store, versions>>

NamespaceIsolation ==
    \A ns1, ns2 \in Namespaces, r \in Resources :
        ns1 # ns2 => (r \in store[ns1] => r \notin store[ns2])

====
