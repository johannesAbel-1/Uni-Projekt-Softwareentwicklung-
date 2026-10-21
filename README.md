# Zuordnung zu TIMEWERK-Anforderungen

Basis: MS1_TIMEWERK_Version 2.pdf, insbesondere Seiten 9–17; ISEF01-Themenblatt, Thema A.

| ID | Umsetzung | Einschränkung / nächster Schritt |
|---|---|---|
| F01 Benutzerverwaltung | Registrierung, Anmeldung, Abmeldung; kontobezogene SQL-Daten | Lokal; Admin-Verwaltung und Passwortreset fehlen |
| F02 Lernziele und Workload | Ziele mit Modul, Termin, Workload anlegen und bearbeiten | Mehrere Ziele können denselben Modulnamen tragen; kein separater Modulkatalog |
| F03 Sechsmonatsplanung | Sechs monatliche Stundenbudgets, zwei Planungsquartale | Rollierend ab aktuellem Monat; Budgets nicht automatisch auf Module verteilt |
| F04 Monatsplanung | Lernblöcke, Aufgaben, Zwischenziele mit Terminen | Zwischenziele als Aufgaben; Meilensteine über Zieltermine |
| F05 Lernzeiterfassung | Start, Pause, Fortsetzen, Beenden, Zuordnung zu Ziel und optional Block | Vor dem Verlassen speichern; keine automatische Lernerkennung |
| F06 Zielerreichung | Aufgaben abhaken, Ziele separat als erreicht markieren, wieder öffnen | Aufgabenfortschritt und fachliche Zielerreichung getrennt |
| F07 Dashboard | Monatlicher Soll-Ist-Vergleich, 7-Tage-Grafik, Aufgabenprozente, Zielzähler | Monats-Soll = eingegebenes Budget, Tages-Soll = Lernblöcke |
| F08 Meilensteinkontrolle | Termin- und aufgabenbasierter Status pro Lernziel | Keine separate Meilensteintabelle; einfache dokumentierte Schwelle |
| F09 Plan B | Nutzerbestätigte Tagesverschiebung, Archiv des vorherigen Plans, Einzelbearbeitung | Kein automatischer Kapazitätsausgleich; Budgets separat anpassen |
| F10 Inaktivität | Erinnerung 15 Minuten nach Beginn ohne zugeordnete Lernsitzung | Nur In-App bei geöffneter Seite bzw. Wiederaufruf |
| R02 Browserbereitstellung | Lokal über Python, ohne Installation für lokale Browserclients | Öffentlicher Tutor-Link noch nicht eingerichtet |
| R03 Datenbank | SQLite mit Benutzerbezug und Fremdschlüsseln | Planarchive/Monatsbudgets als JSON |
| Q01/Q02 Bedienung | Fünf Bereiche, klare Beschriftungen, Textstatus, fokussierte Formulare | Nutzer-/Barrierefreiheitstest im Team fortsetzen |
| Q03 Berechnung | Sekundenbasierte aktive Lernzeit; unabhängiger Aufgabenfortschritt | Kein wissenschaftlicher Lernerfolgsnachweis |
| Q04 Datenhaltung | Transaktionale SQL-Speicherung, Fehlermeldung, Export | Keine Mehrtab-Konfliktbehandlung |
| Q05 Zugriffsschutz | Kontentrennung, Passwort-Hash, Cookie-Sitzung, CSRF | Öffentlichen Betrieb separat härten und prüfen |
| Q07 Responsive | Desktop-, Tablet- und Smartphone-Breakpoints | Noch kein vollständiger Endgerätetest |

## Verwendete Fachregeln

1. Aufgabenfortschritt = erledigte Aufgaben / alle Aufgaben des Ziels × 100. Ohne Aufgaben: „Keine Aufgaben geplant“.
2. Erreichtes Ziel: „Eingehalten“, wenn am oder vor Zieltermin bestätigt, ansonsten „Verspätet erreicht“.
3. Offenes Ziel nach Termin: „Verfehlt“.
4. Noch offenes Ziel: „Gefährdet“, wenn mindestens eine Aufgabe überfällig ist oder der Termin in weniger als sieben Tagen liegt und weniger als 75 % der Aufgaben erledigt sind. Sonst „Im Plan“.
5. Erinnerung: Beginn eines geplanten Lernblocks liegt mehr als 15 Minuten zurück und es gibt keine diesem Block zugeordnete Sitzung. Ein gerade aktiver, diesem Block zugeordneter Timer unterdrückt die Erinnerung.
6. Plan B: offene Aufgaben werden verschoben, auch überfällige. Nur zukünftige, noch nicht erfasste Lernblöcke werden gemeinsam verschoben. Zieltermine nur bei aktivierter Option. Bereits erfasste Lernzeiten bleiben unverändert.

Die Schwellenwerte 15 Minuten und 75 % sind Implementierungsentscheidungen dieses Prototyps und sollten in MS 3 abgestimmt werden. Das ist kein behaupteter Wortlaut eurer Unterlagen.

## Noch vor einer vollständigen MS-4-Abgabe

Hosting und Tutor-Testkonten, weitergehende Sicherheits- und Endgerätetests, Rollen-/Admin-Konzept, belastbarer Testabschlussbericht sowie fachliche/technische/betriebliche Dokumentation und Benutzerhandbuch in eurem Abgabeformat. README und diese Zuordnung sind ein technischer Einstieg und ersetzen diese Abnahmeunterlagen nicht.
