---- MODULE Quality ----
EXTENDS Naturals, Sequences

(* Quality history read model — append-only snapshot list. *)

CONSTANT MaxHistory

VARIABLES history

TypeOK == /\ history \in Seq(0..10)
          /\ Len(history) <= MaxHistory

Init == history = <<>>

AppendSnapshot(n) ==
    /\ n \in Nat
    /\ Len(history) < MaxHistory
    /\ history' = Append(history, n)

Next == \E n \in 0..10 : AppendSnapshot(n)

Spec == Init /\ [][Next]_history

====
