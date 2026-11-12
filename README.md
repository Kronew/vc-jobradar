# VC-Jobradar

Dieses Projekt sammelt jeden Morgen automatisch neue Praktika und Werkstudentenstellen aus den Portfolio-Startups von 25 Venture-Capital-Firmen und verschickt sie als übersichtliche E-Mail. Es richtet sich an Studierende, die bei jungen, finanzierten Startups arbeiten möchten, deren Stellen aber oft nicht auf den großen Jobportalen erscheinen. Viele VCs wie HV Capital, HTGF, Earlybird, Cherry Ventures oder Speedinvest betreiben eine eigene Jobbörse, auf der alle offenen Stellen ihrer Portfolio-Firmen gesammelt werden. Der VC-Jobradar fragt diese Jobbörsen täglich ab, filtert die Stellen nach Stellenart, Stadt und Bereich, entfernt Duplikate und schickt nur die Stellen, die seit dem letzten Lauf neu dazugekommen sind. Optional bewertet ein Sprachmodell (Claude) jede Stelle anhand eines kurzen Profils.

Das Projekt läuft vollständig in GitHub Actions. Es wird also kein eigener Server und kein Rechner benötigt, der morgens eingeschaltet ist. Eingerichtet wird es über ein Formular: Nach dem ersten Start kommt eine Willkommens-Mail mit einem Link, und jede weitere Mail enthält einen Link, über den sich die Einstellungen jederzeit ändern lassen.


## Inhaltsverzeichnis

- Voraussetzungen
- Installation
  - Eigenes Repository aus der Vorlage erstellen
  - Gmail-App-Passwort erstellen
  - Secrets hinterlegen
  - Workflow-Berechtigungen setzen
- Verwendung
  - Erster Start
  - Einrichtung über das Formular
  - Tägliche Mail
  - Einstellungen ändern
- Funktionen
  - Datenquelle
  - Stellenart
  - Städte und Remote
  - Bereiche
  - Auswahl der VCs
  - Duplikaterkennung und bereits gemailte Stellen
  - KI-Bewertung
  - Zeitplan
- Lokale Nutzung und erweiterte Konfiguration
- Kosten und Datenschutz
- Fehlerbehebung
- Ordner und Dateien und ihr Zweck
  - jobtracker-Ordner
  - sources-Ordner
  - templates-Ordner
  - .github-Ordner
  - tests-Ordner
  - Dateien im Hauptverzeichnis
- Lizenz


## Voraussetzungen

- Ein GitHub-Konto (kostenlos)
- Ein Gmail-Konto, über das die Mails verschickt werden
- Optional ein API-Key von Anthropic für die KI-Bewertung
- Für die lokale Nutzung: Python 3.11 oder höher


## Installation

### Eigenes Repository aus der Vorlage erstellen

Dieses Repository ist als Vorlage (Template) angelegt. Jede Person erstellt daraus eine eigene Kopie, in der ihr persönlicher Jobradar läuft.

1. Bei GitHub einloggen und oben auf dieser Seite auf "Use this template" und dann auf "Create a new repository" klicken.
2. Einen Namen vergeben, zum Beispiel `mein-jobradar`.
3. "Private" auswählen. Das ist wichtig, weil der Jobradar die persönlichen Einstellungen (`settings.yaml`) und die Liste der bereits gemailten Stellen (`data/seen_jobs.json`) im Repository speichert. In einem öffentlichen Repository wären diese Daten für alle sichtbar.
4. Auf "Create repository" klicken.

### Gmail-App-Passwort erstellen

Die Mails werden über ein Gmail-Konto verschickt. Dafür wird nicht das normale Gmail-Passwort verwendet, sondern ein sogenanntes App-Passwort, das nur für diesen Zweck gilt und jederzeit widerrufen werden kann.

1. Im Google-Konto die Bestätigung in zwei Schritten aktivieren, falls sie noch nicht aktiv ist: https://myaccount.google.com/signinoptions/two-step-verification
2. Auf https://myaccount.google.com/apppasswords ein neues App-Passwort anlegen, zum Beispiel mit dem Namen "VC-Jobradar".
3. Das angezeigte 16-stellige Passwort kopieren. Die Leerzeichen können weggelassen werden.

### Secrets hinterlegen

Zugangsdaten werden nicht im Code gespeichert, sondern als verschlüsselte GitHub-Secrets. Sie können nach dem Speichern von niemandem mehr ausgelesen werden und werden nur dem Workflow beim Ausführen übergeben.

Im eigenen Repository unter Settings, dann Secrets and variables, dann Actions, mit "New repository secret" die folgenden Secrets anlegen:

```
SMTP_USER=            die Gmail-Adresse, über die verschickt wird
SMTP_APP_PASSWORD=    das App-Passwort aus dem vorherigen Schritt
EMAIL_TO=             die Adresse, an die die Mails gehen (mehrere mit Komma trennen)
ANTHROPIC_API_KEY=    optional, für die KI-Bewertung (https://platform.claude.com, API Keys)
```

### Workflow-Berechtigungen setzen

Unter Settings, dann Actions, dann General, im Bereich "Workflow permissions" die Option "Read and write permissions" auswählen und speichern. Der Jobradar braucht diese Berechtigung, um seine Einstellungen und die Liste der gemailten Stellen zurück ins Repository zu schreiben und um auf das Einstellungsformular zu antworten.


## Verwendung

### Erster Start

1. Im eigenen Repository auf den Reiter "Actions" klicken. Falls GitHub danach fragt, die Workflows aktivieren.
2. Links den Workflow "Täglicher Job-Check (VC-Jobradar)" auswählen und rechts über "Run workflow" starten.
3. Nach ein bis zwei Minuten kommt die Willkommens-Mail. Falls nicht, auch im Spam-Ordner nachsehen.

### Einrichtung über das Formular

In der Willkommens-Mail auf "Jetzt einrichten" klicken. Es öffnet sich ein Formular im eigenen Repository (technisch ein GitHub-Issue, man muss bei GitHub eingeloggt sein). Dort wird angegeben:

- ob Werkstudentenstellen, Praktika oder beides gesucht werden (Pflichtangabe)
- ein paar Sätze über sich, zum Beispiel Studium, Erfahrung, Startzeitpunkt und gewünschte Stunden (optional, nur für die KI-Bewertung)
- in welchen Städten gesucht wird: Berlin, München, Hamburg, Köln und Frankfurt am Main stehen zur Auswahl, zusätzlich kann eine andere Stadt eingetragen werden
- der Pendelradius um die gewählten Städte
- ob Remote-Stellen und Stellen aus dem restlichen Deutschland angezeigt werden sollen
- welche Bereiche interessant sind, zum Beispiel Sales, Marketing, Finance oder Software
- ob alle VCs berücksichtigt werden oder nur bestimmte
- eigene Stichwörter und Wörter, die nicht im Stellentitel vorkommen sollen

Nach dem Absenden übernimmt ein Workflow die Angaben innerhalb von etwa einer Minute, antwortet im Issue, schließt es und schickt eine Bestätigung per Mail. Direkt danach kommt die erste Jobmail mit den passenden Stellen der letzten 14 Tage.

### Tägliche Mail

Ab der Einrichtung kommt jeden Morgen eine Mail mit den Stellen, die seit dem letzten Lauf neu sind. Die Stellen sind nach Bereich gruppiert. Jede Stelle zeigt:

- den Stellentitel als Link zur Bewerbung
- die Firma und den Ort
- ob es sich um ein Praktikum oder eine Werkstudentenstelle handelt
- in welchem VC-Portfolio die Firma ist, zum Beispiel "Portfolio von Cherry Ventures · Atomico", wenn das Startup von mehreren VCs finanziert wird
- das Datum der Veröffentlichung
- mit KI-Bewertung zusätzlich eine Punktzahl von 1 bis 10 und einen Satz, warum die Stelle passt oder nicht

Stellen außerhalb der gewählten Städte erscheinen, falls gewünscht, in einem eigenen Abschnitt "Andere Städte" am Ende der Mail. Ganz unten steht eine Übersicht der aktuellen Einstellungen.

### Einstellungen ändern

Unten in jeder Jobmail gibt es den Link "Einstellungen ändern". Er öffnet dasselbe Formular, in dem die Textfelder bereits mit den aktuellen Werten ausgefüllt sind. Es muss nur geändert werden, was sich ändern soll: Leere Felder, die Auswahl "unverändert" und nicht angekreuzte Bereiche behalten die bisherige Einstellung. Ein einzelnes "-" in einem Textfeld löscht den bisherigen Inhalt. Das Formular wird nur übernommen, wenn es vom Besitzer oder der Besitzerin des Repositorys abgeschickt wird.


## Funktionen

### Datenquelle

Die Jobbörsen der VCs laufen fast alle über die Plattform Getro. Der Jobradar nutzt dieselbe öffentliche Suche, die diese Jobbörsen im Browser verwenden. Für jede Stellenart werden passende Suchbegriffe abgefragt (zum Beispiel "werkstudent" und "working student" oder "praktikum" und "internship"), pro VC höchstens einige Seiten mit kurzen Pausen zwischen den Anfragen. Getro liefert zu jeder Stelle Titel, Firma, Ort mit Koordinaten, Arbeitsmodell (vor Ort, hybrid, remote), Datum und Bewerbungslink. Da es sich nicht um eine offiziell dokumentierte Schnittstelle handelt, kann sie sich jederzeit ändern. Der Jobradar steht in keiner Verbindung zu den VCs oder zu Getro.

Aktuell sind folgende VCs enthalten: HV Capital, HTGF, Vsquared Ventures, b2venture, Senovo, 2150, Earlybird, Cherry Ventures, Point Nine, UVC Partners, Speedinvest, Headline, Creandum, Planet A, BlueYard, Peak, Antler, Firstminute, Seedcamp, Dawn Capital, Atomico, Accel, Insight Partners, General Catalyst und Index Ventures.

### Stellenart

Es kann nach Werkstudentenstellen, nach Praktika oder nach beidem gesucht werden. Eine Stelle wird nur behalten, wenn ihr Titel zur gewählten Stellenart passt, zum Beispiel "Werkstudent", "Working Student", "Praktikum", "Praktikant" oder "Intern". Abschlussarbeiten, Ausbildungsplätze, duale Studiengänge und Minijobs werden immer aussortiert. Wer nur Werkstudentenstellen sucht, bekommt zusätzlich keine Vollzeitstellen und Pflichtpraktika. Wer auch Praktika sucht, bekommt Stellen wie "Praktikum (Vollzeit, 6 Monate)" dagegen angezeigt.

### Städte und Remote

Zur Auswahl stehen die fünf deutschen Städte mit den meisten Startups: Berlin, München, Hamburg, Köln und Frankfurt am Main. Sie können beliebig kombiniert werden, und zusätzlich kann eine weitere Stadt eingetragen werden, deren Koordinaten dann einmalig bei OpenStreetMap nachgeschlagen werden. Eine Stelle gilt als passend, wenn sie innerhalb des Pendelradius um eine der gewählten Städte liegt. Für die wenigen Stellen ohne Koordinaten wird stattdessen der Ortsname verglichen, auch in englischer Schreibweise wie "Munich" oder "Cologne". Remote-Stellen in Deutschland werden auf Wunsch immer angezeigt, Remote-Stellen mit Einschränkung auf andere Länder werden aussortiert. Wird keine Stadt gewählt, gelten alle Stellen in Deutschland.

### Bereiche

Es gibt 14 Bereiche: Sales und Business Development, VC, Startup und Strategy, Marketing, Growth und Content, Kommunikation und PR, Marktforschung, Finance und Controlling, HR und Recruiting, Consulting und Projektmanagement, Data und Analytics, Produktmanagement, Software und IT, Operations und Supply Chain, Recht und Compliance sowie Design und UX. Jede Stelle wird anhand von Stichwörtern im Titel, ersatzweise in der Beschreibung, einem Bereich zugeordnet. Werden keine Bereiche gewählt, kommen alle Stellen, und nicht zuordenbare Stellen erscheinen unter "Sonstige". Eigene Stichwörter bilden einen zusätzlichen Bereich.

### Auswahl der VCs

Standardmäßig werden alle 25 VCs abgefragt. Im Formular können auch nur bestimmte VCs ausgewählt werden, zum Beispiel nur deutsche Investoren.

### Duplikaterkennung und bereits gemailte Stellen

Viele Startups sind im Portfolio mehrerer VCs und erscheinen deshalb auf mehreren Jobbörsen. Der Jobradar erkennt solche Duplikate über die Bewerbungs-URL sowie über Firma und Titel und zeigt die Stelle nur einmal an, zusammen mit allen VCs, bei denen sie auftaucht. Außerdem merkt er sich alle verschickten Stellen 60 Tage lang in `data/seen_jobs.json`, damit keine Stelle zweimal gemailt wird.

### KI-Bewertung

Ist ein `ANTHROPIC_API_KEY` hinterlegt und ein Profil ausgefüllt, bewertet Claude jede neue Stelle von 1 bis 10. Berücksichtigt werden die Passung zum Profil und zu den gewählten Bereichen, die Stellenart, der Ort, der Startzeitpunkt und die Sprachanforderungen. Standardmäßig kommen nur Stellen ab 6 Punkten in die Mail. Die Stellen werden in Gruppen bewertet, damit nur wenige Anfragen nötig sind. Ohne API-Key oder ohne Profil wird die Bewertung übersprungen und alle passenden Stellen werden verschickt.

### Zeitplan

Der tägliche Lauf ist für 07:30 Uhr deutscher Zeit eingeplant. Da GitHub mit UTC-Zeit arbeitet und keine Sommerzeit kennt, gibt es zwei Zeitpunkte, von denen nur der erste ab 07:00 Uhr tatsächlich etwas tut. GitHub garantiert bei geplanten Workflows keine Uhrzeit und startet sie in der Praxis oft mehrere Stunden später. Die Mail kommt deshalb meist im Laufe des Vormittags oder Mittags. Wer eine feste Uhrzeit braucht, kann den Workflow von außen anstoßen, zum Beispiel über cron-job.org und die workflow_dispatch-Schnittstelle von GitHub.


## Lokale Nutzung und erweiterte Konfiguration

Der Jobradar kann auch lokal ausgeführt werden, zum Beispiel zum Testen:

```
git clone https://github.com/DEIN_GITHUB_NAME/DEIN_REPO.git
cd DEIN_REPO
python -m venv .venv
source .venv/bin/activate          # unter Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
cp .env.example .env               # Zugangsdaten eintragen
```

Danach stehen folgende Befehle zur Verfügung:

```
python -m jobtracker --dry-run                               alle Stellen abfragen und nur ausgeben, nichts senden
python -m jobtracker --dry-run -v                            zusätzlich alle verworfenen Stellen mit Grund anzeigen
python -m jobtracker --dry-run --preview data/preview.html   die Mail als HTML-Datei speichern
python -m jobtracker --days 14                               Zeitfenster einmalig auf 14 Tage setzen
python -m jobtracker.settings url                            Link zum Einstellungsformular ausgeben
pytest                                                       Tests ausführen (ohne Internetverbindung)
```

Alle Standardwerte stehen in `jobtracker/defaults.yaml`. Wer darüber hinaus etwas anpassen möchte, legt eine `config.yaml` im Hauptverzeichnis an. Sie wird über die Standardwerte und die Formular-Einstellungen gelegt: Abschnitte werden zusammengeführt, Listen werden ersetzt. Ein Beispiel:

```
sources:
  vc_boards:
    max_days_old: 30      # Zeitfenster in Tagen
scoring:
  min_score: 7            # nur Stellen ab 7 von 10 Punkten
mail:
  max_jobs: 30            # höchstens 30 Stellen pro Mail
```

In GitHub Actions kann diese Datei alternativ als Secret `CONFIG_YAML` hinterlegt werden.

Für Stichwörter gilt: Sie müssen am Wortanfang stehen, Groß- und Kleinschreibung sowie Umlaute spielen keine Rolle. "vertrieb" trifft also auch "Vertriebsassistenz". Ein `$` am Ende verlangt das ganze Wort, "intern$" trifft also "Intern", aber nicht "International".

Weitere VCs können ergänzt werden, wenn ihre Jobbörse über Getro läuft. Im Seitenquelltext der Jobbörse steht dann eine Angabe wie `"network":{"id":"617"}`. Der VC wird in `jobtracker/defaults.yaml` unter `sources.vc_boards.boards` mit Name und ID eingetragen und zusätzlich in `.github/ISSUE_TEMPLATE/einstellungen.yml` als Auswahlmöglichkeit ergänzt. Ein Test prüft, dass beide Listen übereinstimmen.


## Kosten und Datenschutz

GitHub Actions ist für private Repositorys bis 2.000 Minuten im Monat kostenlos. Ein Lauf dauert etwa zwei bis drei Minuten, im Monat also rund 90 Minuten. Gmail ist kostenlos. Die optionale KI-Bewertung kostet bei etwa 50 Stellen am Tag weniger als einen Cent pro Tag.

Die persönlichen Einstellungen und die Liste der gemailten Stellen liegen im eigenen privaten Repository. Das Gmail-App-Passwort und der API-Key liegen verschlüsselt als GitHub-Secrets. Nur bei aktivierter KI-Bewertung werden der Profiltext und die Stellenanzeigen an die Claude-API geschickt. Wird eine andere Stadt eingetragen, wird nur deren Name einmalig an OpenStreetMap (Nominatim) übermittelt.


## Fehlerbehebung

Die Willkommens-Mail kommt nicht: Zuerst den Spam-Ordner prüfen. Danach im Repository unter "Actions" den letzten Lauf öffnen. Steht dort "Secrets fehlen noch", sind `SMTP_USER`, `SMTP_APP_PASSWORD` oder `EMAIL_TO` nicht oder falsch angelegt. Die Meldung "Username and Password not accepted" bedeutet, dass das App-Passwort falsch ist.

Das Formular wurde abgeschickt, aber nichts passiert: Unter "Actions" den Workflow "Einstellungen übernehmen" öffnen. Der Workflow antwortet außerdem direkt im Issue. Die häufigste Ursache ist die fehlende Einstellung "Read and write permissions".

Die erste Mail ist sehr lang: Die erste Mail enthält alle passenden Stellen der letzten 14 Tage, höchstens 60. Danach kommen nur noch die Stellen, die seit dem letzten Lauf neu sind.

Fast alle Stellen sind in Berlin und München: Dort sitzen die meisten VC-finanzierten Startups. Mit mehreren Städten oder der Option "Stellen aus ganz Deutschland" werden auch die übrigen Stellen angezeigt.

Verbesserungen aus der Vorlage übernehmen: Ein Repository aus einer Vorlage ist eine unabhängige Kopie. Neue Versionen können übernommen werden, indem die Dateien aus diesem Repository in das eigene kopiert werden. Die eigene `settings.yaml` und der Ordner `data` dürfen dabei nicht überschrieben werden.


## Ordner und Dateien und ihr Zweck

### jobtracker-Ordner

Der Ordner `jobtracker` enthält das eigentliche Programm. Er wird mit `python -m jobtracker` gestartet.

main.py: Dies ist die Hauptdatei, in der der gesamte Ablauf zusammenläuft. Sie liest die Befehlszeilen-Optionen (`--dry-run`, `--preview`, `--days`, `--scheduled` und weitere), lädt die Konfiguration und fragt die Quellen ab. Anschließend übergibt sie die Stellen an den Filter, entfernt Duplikate und bereits gemailte Stellen, startet bei Bedarf die KI-Bewertung, erstellt die Mail, verschickt sie und speichert die gemailten Stellen. Ist noch nichts eingerichtet, verschickt sie stattdessen die Willkommens-Mail. Mit `--scheduled` sorgt sie dafür, dass der Jobradar höchstens einmal am Tag und erst ab 07:00 Uhr läuft.

settings.py: Diese Datei verwaltet die persönlichen Einstellungen. Sie liest das ausgefüllte Formular aus dem GitHub-Issue (die Antworten stehen dort als Text unter Überschriften und als angekreuzte Kästchen), übernimmt nur die geänderten Felder und speichert das Ergebnis in `settings.yaml`. Für eine eingetragene andere Stadt ermittelt sie die Koordinaten über OpenStreetMap. Aus den Einstellungen leitet sie die Teile der Konfiguration ab, die das Programm braucht: Suchbegriffe und Pflichtwörter je nach Stellenart, Ausschlüsse, Städte mit Koordinaten, Bereiche und die Liste der VCs. Außerdem erzeugt sie den Link zum vorausgefüllten Formular und die Übersicht der Einstellungen für die Mail. Der Workflow `settings.yml` ruft diese Datei mit `python -m jobtracker.settings apply` auf.

defaults.yaml: In dieser Datei stehen alle Standardwerte: die Stellenarten mit ihren Suchbegriffen und Pflichtwörtern, die immer geltenden Ausschlüsse, die fünf Städte mit Koordinaten und Ortsnamen, die 14 Bereiche mit ihren Stichwörtern, die Liste der VCs mit ihren Getro-IDs sowie Einstellungen für die Mail, die KI-Bewertung und die Speicherdauer. Wer etwas grundlegend ändern möchte, etwa einen VC oder einen Bereich ergänzen, findet hier die richtige Stelle.

config.py: Diese Datei setzt die Konfiguration aus drei Ebenen zusammen: zuerst die Standardwerte aus `defaults.yaml`, darüber die Formular-Einstellungen aus `settings.yaml` und ganz oben eine optionale `config.yaml`. Existiert weder `settings.yaml` noch `config.yaml`, gilt der Jobradar als nicht eingerichtet. Außerdem liest sie Zugangsdaten aus den Umgebungsvariablen.

filters.py: Hier wird entschieden, welche Stellen behalten werden. Der Filter prüft, ob der Titel zur gewählten Stellenart passt, ob ein Ausschlusswort vorkommt, ob die Stelle im Pendelradius einer gewählten Stadt liegt oder remote ist und welchem Bereich sie angehört. Er vermerkt außerdem an jeder Stelle, ob es ein Praktikum oder eine Werkstudentenstelle ist, und markiert Stellen außerhalb der gewählten Städte für den Abschnitt "Andere Städte". Für jede verworfene Stelle wird ein Grund festgehalten, der mit `-v` angezeigt werden kann.

geo.py: Diese Datei berechnet Entfernungen zwischen Koordinaten (Haversine-Formel) und prüft, ob eine Stelle innerhalb des Radius um eine der gewählten Städte liegt. Für Stellen ohne Koordinaten vergleicht sie den Ortsnamen mit einer Liste bekannter Orte.

text.py: Hilfsfunktionen für Texte. Sie vereinheitlicht Groß- und Kleinschreibung sowie Umlaute, entfernt HTML aus Beschreibungen und prüft, ob ein Stichwort am Wortanfang vorkommt. Diese Prüfung wird überall verwendet, wo Stichwörter verglichen werden.

storage.py: Diese Datei erkennt Duplikate innerhalb eines Laufs, zum Beispiel wenn dieselbe Stelle bei mehreren VCs steht, und führt dabei die Namen aller VCs zusammen. Außerdem verwaltet sie `data/seen_jobs.json`, in der alle gemailten Stellen mit Datum stehen. Einträge, die älter als 60 Tage sind, werden automatisch entfernt. Der Tag des letzten Laufs wird ebenfalls dort gespeichert, damit pro Tag nur eine Mail verschickt wird.

scoring.py: Hier ist die KI-Bewertung umgesetzt. Die Datei schickt die neuen Stellen in Gruppen von 15 zusammen mit dem Profil an Claude und erhält für jede Stelle eine strukturierte Antwort mit Punktzahl, Begründung und Angaben dazu, ob Ort und Stundenumfang passen. Die Anweisungen an das Modell passen sich der gewählten Stellenart an. Schlägt eine Gruppe fehl, werden die Stellen trotzdem verschickt, damit nichts verloren geht.

mailer.py: Diese Datei erstellt alle Mails und verschickt sie über Gmail. Die tägliche Jobmail gruppiert die Stellen nach Bereich, sortiert sie nach Punktzahl und Datum, begrenzt sie auf höchstens 60 Stellen und hängt die Übersicht der Einstellungen mit dem Link zum Formular an. Außerdem erstellt sie die Willkommens-Mail und die Bestätigungen nach dem Absenden des Formulars. Jede Mail wird als HTML und zusätzlich als reiner Text verschickt.

models.py: Hier ist festgelegt, welche Angaben zu einer Stelle gespeichert werden, zum Beispiel Titel, Firma, Ort, Koordinaten, Link, Datum, Stellenart, Bereich, die zugehörigen VCs und die Punktzahl.

### sources-Ordner

base.py: Die Grundlage für alle Datenquellen. Sie stellt eine Verbindung mit automatischen Wiederholungen bei Fehlern bereit, hält Pausen zwischen den Anfragen ein und wandelt Datumsangaben in ein einheitliches Format um.

vc_boards.py: Diese Datei fragt die Getro-Jobbörsen der VCs ab. Für jeden VC und jeden Suchbegriff blättert sie durch die Ergebnisse, jeweils 20 Stellen pro Seite, und wandelt jede Stelle in das einheitliche Format um. Dabei übernimmt sie Koordinaten, Arbeitsmodell und den Namen des VCs. Stellen, die älter als das eingestellte Zeitfenster sind, werden übersprungen. Fällt die Jobbörse eines einzelnen VCs aus, laufen die anderen weiter und der Fehler erscheint als Hinweis unten in der Mail.

### templates-Ordner

email.html.j2: Die Vorlage für die tägliche Jobmail. Sie legt fest, wie Bereiche, Stellen, Etiketten, Punktzahlen und die Übersicht der Einstellungen dargestellt werden. Die Gestaltung ist so gewählt, dass die Mail in gängigen Mailprogrammen und auf dem Handy gut lesbar ist.

notice.html.j2: Die Vorlage für kurze Mails ohne Stellen, also die Willkommens-Mail und die Bestätigungen nach dem Absenden des Formulars.

### .github-Ordner

ISSUE_TEMPLATE/einstellungen.yml: Das Einstellungsformular. Es legt fest, welche Felder, Auswahllisten und Kästchen beim Klick auf "Jetzt einrichten" oder "Einstellungen ändern" erscheinen.

ISSUE_TEMPLATE/config.yml: Erlaubt neben dem Formular auch normale Issues, zum Beispiel für Fragen oder Fehlermeldungen.

workflows/daily.yml: Der tägliche Workflow. Er installiert die Abhängigkeiten, startet den Jobradar mit den hinterlegten Secrets und schreibt die aktualisierte Liste der gemailten Stellen zurück ins Repository. Er kann auch von Hand gestartet werden, auf Wunsch als Testlauf ohne Mailversand. Sind noch keine Secrets hinterlegt, beendet er sich mit einem Hinweis, statt mit einem Fehler abzubrechen.

workflows/settings.yml: Dieser Workflow startet, sobald das Einstellungsformular abgeschickt wird. Er prüft, ob es vom Besitzer oder der Besitzerin des Repositorys stammt, übernimmt die Angaben mit `settings.py`, speichert `settings.yaml`, antwortet im Issue, schließt es und verschickt die Bestätigung. Bei der ersten Einrichtung verschickt er direkt im Anschluss die erste Jobmail.

workflows/tests.yml: Führt bei jeder Änderung am Code automatisch alle Tests aus.

### tests-Ordner

Der Ordner enthält die automatischen Tests, die ohne Internetverbindung laufen. Sie prüfen unter anderem die Auswertung der Getro-Antworten, die Filterregeln für Stellenarten, Städte und Bereiche, die Duplikaterkennung, das Auslesen des Formulars, das Zusammensetzen der Konfiguration, den Aufbau der Mails und dass Formular und Standardwerte zueinander passen. `conftest.py` stellt dafür Beispieldaten bereit.

### Dateien im Hauptverzeichnis

requirements.txt: Die Python-Pakete, die der Jobradar benötigt.

requirements-dev.txt: Zusätzlich die Pakete für die Tests.

pyproject.toml: Grundlegende Angaben zum Projekt und zur Testumgebung.

.env.example: Eine Vorlage für die lokale Datei `.env`, in der die Zugangsdaten für die lokale Nutzung eingetragen werden. Die Datei `.env` selbst wird nie ins Repository übernommen.

.gitignore: Legt fest, welche Dateien nicht ins Repository gehören, zum Beispiel `.env`, eine lokale `config.yaml` und die virtuelle Umgebung.

settings.yaml: Diese Datei gibt es in der Vorlage nicht. Sie entsteht im eigenen Repository beim Absenden des Formulars und enthält die persönlichen Einstellungen.

data/seen_jobs.json: Auch diese Datei entsteht erst im eigenen Repository. Sie enthält die bereits gemailten Stellen.


## Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Der Code darf frei genutzt, verändert und weitergegeben werden. Details stehen in der Datei `LICENSE`.
