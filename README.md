# 🎯 VC-Jobradar

**Jeden Morgen eine Mail mit neuen Praktika und Werkstudentenstellen bei Startups, die von
Venture-Capital-Firmen finanziert werden.** Kostenlos, ohne Anmeldung bei einem Jobportal,
ohne eigenen Server – und eingerichtet wird alles über ein kurzes Formular.

- 🏢 **25 VCs, Hunderte Startups:** HV Capital, HTGF, Earlybird, Cherry Ventures, Speedinvest,
  Point Nine, Vsquared, UVC, Accel, Index Ventures und mehr
- 🎓 **Praktikum, Werkstudentenstelle oder beides** – jede Stelle ist in der Mail gekennzeichnet
- 📍 **Berlin, München, Hamburg, Köln, Frankfurt** oder eine eigene Stadt, plus Remote
- 🗂️ **14 Bereiche** zur Auswahl: Sales, Marketing, VC/Strategy, Finance, HR, Data, Software …
- ⚙️ **Einstellungen jederzeit per Klick aus der Mail ändern**
- 🤖 optional: **KI-Bewertung** jeder Stelle anhand deines Profils (Claude)

---

## Inhalt

- [Was macht der VC-Jobradar?](#was-macht-der-vc-jobradar)
- [So sieht die tägliche Mail aus](#so-sieht-die-tägliche-mail-aus)
- [Einrichten in 4 Schritten](#einrichten-in-4-schritten-ca-10-minuten)
- [Einstellungen ändern](#einstellungen-ändern)
- [Wie funktioniert das im Hintergrund?](#wie-funktioniert-das-im-hintergrund)
- [Kosten & Datenschutz](#kosten--datenschutz)
- [Häufige Fragen & Fehlerbehebung](#häufige-fragen--fehlerbehebung)
- [Für Fortgeschrittene](#für-fortgeschrittene)

---

## Was macht der VC-Jobradar?

Startups mit Risikokapital wachsen schnell und suchen laufend Praktikant:innen und Werkstudierende.
Ihre Stellen stehen aber oft nicht bei Indeed oder StepStone, sondern nur auf ihrer eigenen
Karriereseite. Die gute Nachricht: Viele VCs betreiben eine **Jobbörse mit allen offenen Stellen
ihrer Portfolio-Startups** (z. B. [jobs.earlybird.com](https://jobs.earlybird.com/jobs)).

Der VC-Jobradar fragt diese Jobbörsen **jeden Morgen automatisch** ab und schickt dir eine Mail mit
den Stellen, die zu dir passen:

1. **Sammeln:** Er durchsucht die Jobbörsen von 25 VCs nach Praktika und/oder Werkstudentenstellen.
2. **Filtern:** Er behält nur Stellen in deinen Städten (oder remote) und in deinen Bereichen.
3. **Aufräumen:** Steht eine Stelle bei mehreren VCs, kommt sie nur einmal – mit allen VCs dazu.
   Stellen, die du schon bekommen hast, kommen nicht nochmal.
4. **Bewerten (optional):** Claude gibt jeder Stelle 1–10 Punkte und einen Satz, warum sie passt.
5. **Mailen:** Du bekommst eine übersichtliche Mail, sortiert nach Bereich, mit Bewerbungslink.

Das Ganze läuft in **GitHub Actions** – das ist ein kostenloser Dienst von GitHub, der Programme
nach Zeitplan ausführt. Du brauchst also keinen Computer, der morgens an ist.

## So sieht die tägliche Mail aus

```
🎯 VC-Jobradar – 12.11.2026 – 14 neue Stellen
──────────────────────────────────────────────────────────────

SALES / BUSINESS DEVELOPMENT (3)

  ┌────────────────────────────────────────────────────────┐
  │ 8/10  Praktikum                                        │
  │ Business Development Intern (m/f/d)                    │
  │ Acme Robotics · Munich, Germany                        │
  │ 💼 Portfolio von HV Capital · Earlybird                │
  │ VC-Portfolio · 10.11.2026                              │
  │ „Passt gut: B2B-Vertrieb in einem Deep-Tech-Startup,   │
  │   6 Monate ab März.“                                   │
  │ [ Jetzt bewerben → ]                                   │
  └────────────────────────────────────────────────────────┘
  …

MARKETING / GROWTH / CONTENT (2)
  …

ANDERE STÄDTE (4)          ← Stellen außerhalb deiner Städte
  …

  ┌────────────────────────────────────────────────────────┐
  │ ⚙️ Deine Einstellungen                                  │
  │ Suche: Werkstudentenstellen, Praktika                  │
  │ Städte: Berlin, München · 30 km                        │
  │ Bereiche: Sales / Business Development, Marketing …    │
  │ VCs: alle (25)                                         │
  │ [ Einstellungen ändern → ]                             │
  └────────────────────────────────────────────────────────┘
```

Die Punkte und der Satz in Anführungszeichen erscheinen nur, wenn du die KI-Bewertung einschaltest.

## Einrichten in 4 Schritten (ca. 10 Minuten)

Du brauchst: ein kostenloses **GitHub-Konto** und ein **Gmail-Konto** (zum Verschicken der Mails).

### Schritt 1: Eigene Kopie anlegen – als privates Repo

1. Bei GitHub einloggen.
2. Oben auf dieser Seite auf **„Use this template“ → „Create a new repository“** klicken.
3. Einen Namen vergeben (z. B. `mein-jobradar`) und **„Private“** auswählen. ⚠️ Wichtig: Der Jobradar
   speichert deine Einstellungen und die schon gemailten Stellen in deinem Repo. In einem
   öffentlichen Repo könnte das jeder lesen.
4. **„Create repository“** klicken.

### Schritt 2: Gmail-App-Passwort erstellen

Damit der Jobradar Mails über dein Gmail-Konto verschicken darf, braucht er ein eigenes Passwort
(nicht dein normales Gmail-Passwort):

1. In deinem Google-Konto die [Bestätigung in zwei Schritten](https://myaccount.google.com/signinoptions/two-step-verification)
   einschalten (falls noch nicht aktiv – ohne sie gibt es keine App-Passwörter).
2. [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) öffnen, einen Namen
   eingeben (z. B. „VC-Jobradar“) und auf **„Erstellen“** klicken.
3. Das angezeigte **16-stellige Passwort** kopieren (die Leerzeichen kannst du weglassen).

### Schritt 3: Zugangsdaten im Repo hinterlegen

In deinem neuen Repo auf **Settings → Secrets and variables → Actions → New repository secret**
klicken und nacheinander anlegen:

| Name | Wert |
|---|---|
| `SMTP_USER` | deine Gmail-Adresse, z. B. `anna.muster@gmail.com` |
| `SMTP_APP_PASSWORD` | das App-Passwort aus Schritt 2 |
| `EMAIL_TO` | wohin die Mails gehen sollen – meist dieselbe Adresse (mehrere mit Komma trennen) |
| `ANTHROPIC_API_KEY` | *optional*, für die KI-Bewertung – siehe [Kosten](#kosten--datenschutz) |

„Secrets“ sind verschlüsselt gespeichert: Niemand kann sie wieder auslesen, auch du nicht – nur
der Jobradar bekommt sie beim Ausführen.

Danach noch unter **Settings → Actions → General → Workflow permissions** die Option
**„Read and write permissions“** auswählen und speichern.

### Schritt 4: Starten und einrichten

1. Im Repo auf **Actions** klicken. Falls GitHub fragt, die Workflows aktivieren
   („I understand my workflows, go ahead and enable them“).
2. Links **„Täglicher Job-Check (VC-Jobradar)“** auswählen → rechts **„Run workflow“** → grüner
   Button **„Run workflow“**.
3. Nach ein, zwei Minuten kommt die **Willkommens-Mail** (auch im Spam-Ordner nachsehen).
4. In der Mail auf **„Jetzt einrichten“** klicken. Es öffnet sich ein Formular in deinem Repo:
   ankreuzen, was du suchst, Städte und Bereiche wählen, optional ein paar Sätze über dich – und
   unten auf **„Create“** bzw. **„Submit new issue“** klicken.
5. Etwa eine Minute später kommt eine **Bestätigung** und direkt danach deine **erste Jobmail** mit
   den passenden Stellen der letzten 14 Tage.

**Fertig!** Ab jetzt kommt jeden Morgen eine Mail mit den Stellen, die seit gestern neu sind.

## Einstellungen ändern

Ganz unten in jeder Jobmail steht, was gerade eingestellt ist, und ein Button
**„Einstellungen ändern“**. Er öffnet das Formular mit deinen aktuellen Werten. Ändere nur, was du
ändern willst – **leere Felder, „unverändert“ und nichts Angekreuztes behalten die alte Einstellung.**
Nach dem Absenden bekommst du eine Bestätigung; die nächste tägliche Mail nutzt die neuen Werte.

| Feld | Was es bewirkt |
|---|---|
| **Was suchst du?** | Werkstudentenstellen, Praktika oder beides. Jede Stelle bekommt in der Mail ein Etikett. |
| **Über dich** | Ein paar Sätze für die KI-Bewertung: Studium, Erfahrung, ab wann, wie viele Stunden … |
| **Städte** | Berlin, München, Hamburg, Köln, Frankfurt – beliebig kombinierbar. Stellen dort kommen zuerst. Nichts gewählt = ganz Deutschland. |
| **Andere Stadt** | optional eine weitere Stadt, z. B. Karlsruhe oder Leipzig |
| **Pendelradius** | 10–100 km um jede gewählte Stadt (Standard 30 km) |
| **Remote-Stellen** | 100 %-Remote-Stellen in Deutschland mitnehmen? |
| **Stellen aus ganz Deutschland** | alle übrigen Stellen zusätzlich im Abschnitt „Andere Städte“ am Ende der Mail? |
| **Bereiche** | 14 Bereiche zum Ankreuzen oder „Alle Bereiche“ |
| **VCs** | alle 25 VCs oder nur bestimmte |
| **Eigene Stichwörter** | zusätzliche Themen, z. B. „Nachhaltigkeit“ oder „Einkauf“ |
| **Ausschließen** | Wörter, die nicht im Stellentitel vorkommen sollen, z. B. „Senior“ |

> Das Formular ist ein GitHub-„Issue“ in deinem Repo. Du musst bei GitHub eingeloggt sein. Übernommen
> wird es nur, wenn es von dir als Besitzer:in des Repos kommt.

## Wie funktioniert das im Hintergrund?

```
                        ┌─────────────── jeden Morgen (GitHub Actions) ───────────────┐
                        │                                                              │
 25 VC-Jobbörsen ──► Stellenart ──► Stadt / ──► Bereich ──► Duplikate ──► schon ──► KI- ──► Mail
   (Getro-Suche)     (Praktikum,    Remote                   über alle     gemailt?   Bewertung
                      Werkstudent)                           VCs           (60 Tage)  (optional)
                        │                                                              │
                        └──────────────────────────────────────────────────────────────┘

 Mail ──► „Einstellungen ändern“ ──► Formular (GitHub-Issue) ──► Workflow speichert settings.yaml
```

- **Datenquelle:** Die Jobbörsen der VCs laufen fast alle über [Getro](https://www.getro.com). Der
  Jobradar nutzt dieselbe Suche, die diese Seiten im Browser verwenden – mit kurzen Pausen zwischen
  den Anfragen.
- **Täglicher Lauf** (`.github/workflows/daily.yml`): sammelt, filtert, verschickt die Mail und merkt
  sich die verschickten Stellen in `data/seen_jobs.json`.
- **Einstellungen** (`.github/workflows/settings.yml`): startet, sobald du das Formular abschickst,
  liest es aus und speichert deine Auswahl in `settings.yaml`.
- **Zeitplan:** eingeplant für 07:30 Uhr. GitHub startet geplante Abläufe allerdings ohne Garantie,
  oft mit **mehreren Stunden Verspätung** – die Mail kommt also eher im Laufe des Vormittags oder
  Mittags.

## Kosten & Datenschutz

**Kosten:** GitHub Actions ist für private Repos bis 2.000 Minuten im Monat kostenlos; ein Lauf
dauert 2–3 Minuten, also rund 90 Minuten im Monat. Gmail ist kostenlos. Die optionale KI-Bewertung
mit Claude kostet bei ~50 Stellen am Tag deutlich unter einem Cent pro Tag
(API-Key auf [platform.claude.com](https://platform.claude.com) → *API Keys*, Guthaben nötig).

**Datenschutz:**
- Deine Einstellungen und die Liste der verschickten Stellen liegen **in deinem privaten Repo**.
- Gmail-Passwort und API-Key liegen verschlüsselt als GitHub-Secrets.
- Nur wenn du die KI-Bewertung nutzt, gehen dein Profiltext und die Stellenanzeigen an die Claude-API.
- Gibst du eine „andere Stadt“ ein, wird sie einmalig bei [OpenStreetMap](https://www.openstreetmap.org)
  (Nominatim) nachgeschlagen, um ihre Koordinaten zu ermitteln.

## Häufige Fragen & Fehlerbehebung

**Die Willkommens-Mail kommt nicht.**
Spam-Ordner prüfen. Dann im Repo unter *Actions* den letzten Lauf öffnen: Steht dort
„Secrets fehlen noch“, sind `SMTP_USER`, `SMTP_APP_PASSWORD` oder `EMAIL_TO` nicht (richtig) angelegt.
Ein Fehler wie `Username and Password not accepted` heißt: App-Passwort falsch oder Leerzeichen mit kopiert.

**Ich habe das Formular abgeschickt, aber nichts passiert.**
Unter *Actions → Einstellungen übernehmen* nachsehen. Der Workflow antwortet außerdem direkt im Issue.
Häufigste Ursache: „Read and write permissions“ aus Schritt 3 fehlt. Das Formular wird außerdem nur
übernommen, wenn du es selbst (als Besitzer:in des Repos) abschickst.

**Die erste Mail ist riesig.**
Die erste Mail enthält alle passenden Stellen der letzten 14 Tage (höchstens 60). Danach kommen nur
noch die Stellen, die seit dem letzten Lauf neu sind – meist eine Handvoll pro Tag.

**Warum so viele Stellen in München und Berlin?**
Dort sitzen die meisten VC-finanzierten Startups. Wähle ruhig mehrere Städte oder lass „Stellen aus
ganz Deutschland“ an, dann siehst du den Rest unter „Andere Städte“.

**Kann ich die Mail-Uhrzeit festlegen?**
GitHub garantiert keine Uhrzeit. Wer eine feste Zeit braucht, kann den Workflow extern anstoßen,
z. B. mit [cron-job.org](https://cron-job.org) über die GitHub-API (`workflow_dispatch`).

**Wie bekomme ich Verbesserungen aus dieser Vorlage?**
Repos aus einer Vorlage sind unabhängige Kopien. Neue Versionen kannst du übernehmen, indem du die
Dateien aus diesem Repo in deins kopierst (deine `settings.yaml` und `data/` dabei nicht überschreiben).

**Ein VC fehlt.**
Gerne per Pull Request ergänzen – siehe [Weitere VCs hinzufügen](#weitere-vcs-hinzufügen).

## Die VCs

HV Capital · HTGF · Vsquared Ventures · b2venture · Senovo · 2150 · Earlybird · Cherry Ventures ·
Point Nine · UVC Partners · Speedinvest · Headline · Creandum · Planet A · BlueYard · Peak · Antler ·
Firstminute · Seedcamp · Dawn Capital · Atomico · Accel · Insight Partners · General Catalyst · Index Ventures

Der VC-Jobradar steht in keiner Verbindung zu diesen VCs oder zu Getro.

## Für Fortgeschrittene

### Lokal ausprobieren

```bash
git clone https://github.com/<du>/<dein-repo>.git && cd <dein-repo>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env                                     # Zugangsdaten eintragen
python -m jobtracker --dry-run                           # alles abfragen, nur ausgeben, nichts senden
python -m jobtracker --dry-run -v                        # zusätzlich: verworfene Stellen mit Grund
python -m jobtracker --dry-run --preview data/preview.html   # Mail als HTML-Datei ansehen
python -m jobtracker.settings url                        # Link zum Einstellungsformular
pytest                                                   # Tests (ohne Internet)
```

### Mehr anpassen mit `config.yaml`

Alle Standardwerte stehen in [`jobtracker/defaults.yaml`](jobtracker/defaults.yaml): Stellenarten
mit ihren Suchbegriffen, Ausschlüsse, Bereiche mit ihren Stichwörtern, Städte, die VC-Liste.
Eine `config.yaml` im Repo wird **über** die Standardwerte und die Formular-Einstellungen gelegt
(Abschnitte werden zusammengeführt, Listen ersetzt):

```yaml
sources:
  vc_boards:
    max_days_old: 30        # Zeitfenster in Tagen (nicht größer als storage.retention_days)
scoring:
  min_score: 7              # nur Stellen ab 7/10 (mit KI-Bewertung)
mail:
  max_jobs: 30              # höchstens 30 Stellen pro Mail
```

In GitHub Actions kann die Datei alternativ aus dem Secret `CONFIG_YAML` kommen
(`gh secret set CONFIG_YAML < config.yaml`).

**Stichwort-Regel:** Begriffe müssen am **Wortanfang** stehen, Groß-/Kleinschreibung und Umlaute sind
egal – `vertrieb` trifft auch „Vertriebsassistenz“. Ein `$` am Ende verlangt das ganze Wort:
`intern$` trifft „Intern“, aber nicht „International“.

### Weitere VCs hinzufügen

1. Die Jobbörse des VCs öffnen (z. B. `jobs.earlybird.com/jobs`) und den Seitenquelltext anzeigen.
   Steht dort `"network":{"id":"617"…`, läuft sie über Getro. Viele VCs haben auch eine Adresse der
   Form `<name>.getro.com`.
2. In `jobtracker/defaults.yaml` unter `sources.vc_boards.boards` eintragen:
   `- {name: Earlybird, network_id: 617}`
3. Den Namen auch im Formular `.github/ISSUE_TEMPLATE/einstellungen.yml` unter `VCs` ergänzen
   (ein Test prüft, dass beide Listen übereinstimmen).

### Projektstruktur

```
jobtracker/
  main.py           Ablauf: sammeln → filtern → Mail (--dry-run, --preview, --scheduled, --days)
  settings.py       Einstellungsformular auslesen, settings.yaml schreiben, Link erzeugen
  defaults.yaml     Standardwerte: Stellenarten, Städte, Bereiche, VC-Liste
  config.py         legt defaults.yaml ← settings.yaml ← config.yaml übereinander
  filters.py        Stellenart, Ausschlüsse, Stadt/Remote, Bereich
  geo.py            Entfernungen & Ortsabgleich
  scoring.py        KI-Bewertung mit Claude
  storage.py        Duplikaterkennung & seen_jobs.json
  mailer.py         Mails (Jobs, Willkommen, Bestätigung) & Versand
  templates/        Aussehen der Mails
  sources/          vc_boards.py: Abfrage der Getro-Jobbörsen
.github/
  ISSUE_TEMPLATE/einstellungen.yml   das Einstellungsformular
  workflows/daily.yml                täglicher Lauf
  workflows/settings.yml             übernimmt das Formular
  workflows/tests.yml                Tests bei jedem Push
tests/              pytest, ohne Internet
```

## Lizenz

[MIT](LICENSE) – du darfst den Code frei nutzen, verändern und weitergeben.
