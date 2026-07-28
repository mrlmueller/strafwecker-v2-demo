# strafwecker

Ein Wecker, der Geld kostet, wenn man liegen bleibt.

Der Raspberry Pi klingelt und funkt gleichzeitig einen ESP32 im Badezimmer an.
Wird dessen Knopf nicht innerhalb von vier Minuten gedrückt, ruft der ESP32 eine
Cloud Function auf, die per Stripe 2 € abbucht. Aufstehen ist billiger.

## Warum die Architektur so aussieht

Die Idee steht und fällt damit, dass der Knopf nicht vom Bett aus erreichbar ist.
Der Auslöser muss also physisch woanders sitzen als der Wecker — und daraus folgt
der Rest:

- **Raspberry Pi**, FastAPI, dreischichtig aufgebaut: weckt, steuert über Tuya
  eine Smart-Steckdose, hält den Zustand in SQLite.
- **ESP32**, MicroPython, im Bad: hat genau einen Knopf und eine Frist. Läuft die
  ab, ruft *er* den Zahlungsendpunkt auf — nicht der Pi. Ein Wecker, der seine
  eigene Strafe abschalten kann, ist keine Strafe.
- **Cloud Function** auf GCP: nimmt den Aufruf entgegen und löst die Zahlung aus.
  Bewusst außerhalb der Wohnung, damit ein gezogener Stecker nichts rettet.
- **Next.js-Frontend** auf Vercel: Weckzeiten, Verlauf, Auswertung.

## Sicherheit

Der API-Schlüssel des Pi-Backends lag zunächst im Frontend und wanderte hinter
einen serverseitigen Proxy (`frontend/proxy.ts`), der zusätzlich gegen eine
IP-Allowlist prüft. Der ESP32 authentifiziert sich mit einem eigenen Schlüssel,
damit der Zahlungsaufruf nicht von jedem Gerät im Netz kommen kann.

Die Konfiguration wird über `pydantic-settings` erzwungen: fehlt ein Wert,
startet die Anwendung gar nicht. Eine halb konfigurierte Instanz, die klingelt,
aber nicht abbuchen kann, wäre schlechter als keine.

## Stack

Python mit FastAPI und Pydantic auf dem Pi · MicroPython auf dem ESP32, per USB
geflasht · Next.js 16 mit React und TypeScript auf Vercel · SQLite ·
Tuya-Local für die Steckdose · Google Cloud Function für die Zahlung · drei
GitHub-Actions-Workflows für Backend-Deployment, ESP32-Prüfung und Frontend-Build.

## Tests

```bash
export API_KEY=… TUYA_DEV_ID=… TUYA_LOCAL_KEY=… TUYA_IP=… ESP32_IP=…
python -m pytest backend/tests    # 126 Tests
python -m pytest esp32/tests      #   6 Tests
```

132 Tests, alle grün. Die Suiten werden getrennt aufgerufen, weil
`backend/test_logic.py` und `esp32/tests/test_logic.py` gleich heißen und pytest
sie ohne Paketkontext nicht auseinanderhält. `backend/.env.example` listet die
erwarteten Konfigurationsnamen.

## Frontend ohne Hardware ausprobieren

`frontend/utils/mockApi.ts` ersetzt die Netzwerkaufrufe durch einen
In-Memory-Store mit Beispiel-Weckzeiten, aktiviert über `NEXT_PUBLIC_USE_MOCK_API`.
So lässt sich die Oberfläche ohne Pi, ohne ESP32 und ohne Steckdose bedienen.

## Zur Arbeitsweise

`docs/superpowers/` enthält die Spezifikationen und Pläne dieses Projekts,
datiert und vor der jeweiligen Umsetzung entstanden — darunter der
Architekturentwurf, der dem heutigen Aufbau zugrunde liegt, und die Überlegungen
zum Deployment auf den Pi.

## Zu diesem Repository

Entwickelt im Mai 2026, veröffentlicht als Momentaufnahme im Juli 2026 aus einem
privaten Repository mit 102 Commits. Der Weckton ist nicht enthalten, siehe
`backend/ALARM-SOUND.md`. Die Geräteadressen im Code gehören zu einem lokalen
Netz und sind aus dem Internet nicht erreichbar.

## Lizenz

MIT
