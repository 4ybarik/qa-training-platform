---- MODULE Quality ----
EXTENDS Naturals, Sequences

(* Quality history read model — append-only snapshot list. *)

VARIABLES history

TypeOK == history \in Seq(Nat)

Init == history = <<>>

AppendSnapshot(n) ==
    /\ n \in Nat
    /\ history' = Append(history, n)

Next == \E n \in 0..10 : AppendSnapshot(n)

Spec == Init /\ [][Next]_history

====
