---- MODULE Catalog ----
EXTENDS Naturals, FiniteSets

(* Static practice catalog — immutable challenge metadata. *)

CONSTANTS Challenges

VARIABLES catalog

TypeOK == catalog = Challenges

Init == catalog = Challenges

Next == UNCHANGED catalog

Spec == Init /\ [][Next]_catalog

CatalogImmutable == catalog = Challenges

====
