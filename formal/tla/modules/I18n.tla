---- MODULE I18n ----
EXTENDS FiniteSets

Languages == {"ru", "en"}

VARIABLES lang

TypeOK == lang \in Languages

Init == lang = "ru"

SetLang(l) ==
    /\ l \in Languages
    /\ lang' = l

Next == \E l \in Languages : SetLang(l)

Spec == Init /\ [][Next]_lang

====
