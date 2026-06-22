# Gausium Ops — User Guide & API Reference

A desktop dashboard (PyQt6) for operating Gausium cleaning robots through the
Gausium OpenAPI: view the fleet, monitor live status, launch cleaning tasks,
send the robot to its dock, pull task reports, and test raw API requests.

> ⚠️ **Exploration tool — not for production.** This app exists to experiment with
> robot control and to understand the Gausium OpenAPI. It is **not production-ready**
> and should **not be used in production**. It's an unofficial, community client, not
> affiliated with Gausium. Review what each command does before sending it to a real robot.

---

## 1. Getting started

### Install & run
```bash
bash launch.sh
```
First run creates a local `.venv` and installs PyQt6 (~60 MB). Every later run
uses the same command.

### Get your API credentials
From the [Gausium Developer Portal](https://developer.gs-robot.com) you receive
**four** values across two files:

| File | Values |
|------|--------|
| Client file | `ClientID`, `ClientSecret` |
| Access key file | `AccessKeyID`, `AccessKeySecret` |

You only need **three** of them to connect, mapped as follows:

| App field | Paste this value |
|-----------|------------------|
| Client ID | `ClientID` |
| Client secret | `ClientSecret` |
| Open access key | **`AccessKeySecret`** |

> `AccessKeyID` is **not** used by the OAuth call.

### Connect
1. Fill the three fields in the top bar.
2. Click **⚡ Connect**. On success the token indicator turns green and shows
   the remaining validity; the fleet and the robot dropdown load automatically.
3. Credentials are saved locally (see [§8](#8-where-your-data-is-stored)) so you
   don't retype them. The access token is **not** stored — it's fetched fresh
   and auto-renewed before expiry.

---

## 2. The tabs

| Tab | What it does |
|-----|--------------|
| **Fleet** | Cards for every robot on the account (online state, model, version). Click **Select** to target one. |
| **Live status** | Battery, mode, current map, consumables, a colour-coded **health banner**, and Stop / Pause / Resume + **Return to charging**. Auto-refreshes on the chosen interval. |
| **Launch task** | Loads the robot's maps & areas, then dispatches a temporary cleaning task. See [§4](#4-launching-a-task). |
| **Live map** | Shows the robot's live position on the real map, with its travelled path. See [§5](#5-live-map--monitoring). |
| **Reports** | Date-range task history → KPI cards + area/battery charts + per-task list. |
| **API console** | Send any request with the live token and inspect the raw response. See [§6](#6-api-console). |
| **Activity log** | Timestamped record of every call. Copy / Clear buttons. |

The robot is chosen with the **S/N dropdown** in the top bar; it's filled from
the fleet after connecting. Selecting a robot card jumps to Live status.

---

## 3. Key concepts

### Site vs. siteless
A "site" is a cloud-managed deployment that binds a robot to managed maps. Many
robots are **siteless** — they keep their own maps without a site. This tool uses
the siteless map endpoints, so it works either way. (The older `getSiteInfo`
call returns *"The robot is not on a site"* for siteless robots and is not used.)

### Where map and area IDs come from
These come from **two different calls** — a common source of confusion:

1. **mapId** ← *List robot maps* (`robotMap/list`) → each map has `mapId` + `mapName`.
2. **areaId** ← *Get subareas* (`subareas/get`, needs the `mapId`) →
   `subareas.partitions[]`, each with a numeric `id` and a `name`.

> The area ID is the **numeric `id`** under `partitions` — and the task API wants
> it as a **string** (e.g. `"1"`).

### Cleaning modes
Modes are reported by the robot (often in Chinese). The dropdown shows an English
hint (`清扫 — Sweep`) but sends the original value. Unmapped modes show as-is; add
translations in `MODE_TRANSLATIONS` in `gausium_ops.py`.

---

## 4. Launching a task

1. Open **Launch task** → click **Load maps from robot**.
2. Pick a **Map** (Map ID + name auto-fill; its areas load automatically).
3. Pick an **Area**, a **Cleaning mode**, type a **Task name**, set **Loop count**.
4. Check the **payload preview**, then **Start task**.

### Reading the result
| Response | Meaning |
|----------|---------|
| `cmdStatus: 0` | Accepted cleanly. |
| `cmdStatus` other (e.g. 5) with an unknown code | Accepted — robot executing. |
| `cmdResultCode` in the error table (e.g. `2010100009`) | **Rejected** — the log shows the decoded reason. |

Common rejection: **`2010100009` "Operation data failure"** → usually a wrong
`areaId` or a `cleaningMode` the robot doesn't support.

### Return to charging
On **Live status**, **⌂ Return to charging** reads the current map and finds the
dock navigation point (any point whose name contains "charg"), shows the exact
payload for confirmation, then sends a `CROSS_NAVIGATE` command. If the robot's
dock point is named differently, it reports that no charging point was found.

### Health banner (Live status)
The top of **Live status** shows a colour-coded banner derived from each status
poll (no extra request — it reads the same payload):

- 🟢 **Normal**
- 🟡 **warn** — battery ≤30% (not charging), or "possibly stalled" (running but
  not moving for several consecutive polls)
- 🔴 **danger** — robot offline, emergency stop active, localization lost, or
  battery ≤15%

This is a polling approximation. Richer, real-time alerts (e.g. precise stuck/fault
events) come from Gausium's **Incident Push** webhook — see `API_REQUESTS.md` §7.

---

## 5. Live map & monitoring

The **Live map** tab plots the robot on its actual floor-plan map. It works for any
connected robot, independent of whether you launched a task here.

1. Connect and select a robot, open **Live map**, click **▶ Start monitoring**.
2. The map image loads and the robot appears as a **red dot + heading arrow**, with
   reference markers for the nav points (the **charging dock** highlighted in teal).
3. The robot's **travelled path** is drawn as a purple trail so you can see where
   it has cleaned.

Controls:
- **Every** — poll interval (2 / 5 / 10 s).
- **Flip Y** — vertical-axis correction if the position is mirrored (on by default).
- **Trail** — show/hide the travelled path; **Clear trail** wipes it. The trail also
  resets each time you press Start.
- **▶ Start / ⏹ Stop monitoring** — monitoring continues regardless of which tab you
  view, until you stop it.

> The position comes from `localizationInfo.mapPosition` in the status payload, and
> the map image from `GET /openapi/v2alpha1/robots/{sn}/map` (a presigned, 1-hour
> image URL fetched fresh each session). Grid coordinates map onto the image pixels
> directly (1 cell ≈ 1 px, origin bottom-left).

---

## 6. API console

A debugging surface for raw requests:
- **Preset** dropdown fills method + path + body for common calls.
- Edit method / path / JSON body freely. `{sn}` is replaced with the selected robot.
- **Content-Type** toggle — leave on for most calls; **off** for `/v1alpha1/robots`
  (it rejects a Content-Type header).
- Response shows the HTTP status and pretty-printed JSON, with a Copy button.

Use it to discover IDs (run *List robot maps* → *Get subareas*) or to test a
request before trusting a button.

---

## 7. API reference

Base URL: `https://openapi.gs-robot.com`. All requests except OAuth need
`Authorization: Bearer <token>`.

| Purpose | Method & path | Body / params | Content-Type |
|---------|---------------|---------------|--------------|
| OAuth token | `POST /gas/api/v1alpha1/oauth/token` | `client_id`, `client_secret`, `open_access_key`, `grant_type` | json |
| List robots | `GET /v1alpha1/robots?page=1&pageSize=50` | — | **none** |
| Robot status | `GET /openapi/v2alpha1/s/robots/{sn}/status` | — | json |
| Stop/Pause/Resume | `POST /v1alpha1/robots/{sn}/commands` | `serialNumber`, `remoteTaskCommandType` (`STOP_TASK`/`PAUSE_TASK`/`RESUME_TASK`) | json |
| Return to dock | `POST /v1alpha1/robots/{sn}/commands` | `remoteNavigationCommandType: "CROSS_NAVIGATE"`, `commandParameter.startNavigationParameter.{map, position}` | json |
| List robot maps | `POST /openapi/v1/map/robotMap/list` | `{ "robotSn": "{sn}" }` → `data[].{mapId, mapName}` | json |
| Get subareas | `POST /openapi/v1/map/subareas/get` | `{ "mapId", "robotSn" }` → `data.subareas.partitions[].{id, name}` | json |
| Get map image | `GET /openapi/v2alpha1/robots/{sn}/map?mapId=…&mapVersion=&mapName=…` | `mapName` required (non-blank) → `{ downloadUri }` (presigned PNG, 1 h) | json |
| Launch task | `POST /openapi/v2alpha1/robotCommand/tempTask:send` | `productId`, `tempTaskCommand.{cleaningMode, loop, loopCount, taskName, mapName, startParam.{mapId, areaId(string)}}` | json |
| Task reports | `GET /openapi/v2alpha1/robots/{sn}/taskReports?page=1&pageSize=50&startTimeUtcFloor=…&startTimeUtcUpper=…` | — | json |

### Path families (why prefixes differ)
- **`/gas/api/…`** — OAuth only.
- **`/v1alpha1/…`** — fleet list and the command endpoint.
- **`/openapi/v1/…`** and **`/openapi/v2alpha1/…`** — maps, subareas, status, tasks, reports.

### Robot command enums
- `remoteTaskCommandType`: `START_TASK`, `PAUSE_TASK`, `RESUME_TASK`, `STOP_TASK`
- `remoteNavigationCommandType`: `CROSS_NAVIGATE`, `PAUSE_NAVIGATE`, `RESUME_NAVIGATE`, `STOP_NAVIGATE`
- `remoteControlCommandType`: `REMOTE_CONTROL_START`, `REMOTE_CONTROL_MOVE`, `REMOTE_CONTROL_STOP`

### Task-startup result codes (`cmdResultCode`)
| Code | Meaning |
|------|---------|
| 2010100006 | Invalid tag |
| 2010100007 | Task area unreachable |
| 2010100008 | Task area operation type mismatch |
| 2010100009 | Operation data failure (task parameters rejected) |
| 2010100010 | No color camera installed |
| 2010100011 | No inspection equipment neural stick installed |
| 2010100012 | There are temporary tasks |
| 2010100013 | The robot cannot switch sites in the current state |

---

## 8. Where your data is stored

Credentials and the last-used SN are saved to:
```
~/.gausium_ops/credentials.json
```
This is **outside the project folder**, so sharing the code does not share your
credentials. The bearer token is never written to disk. To wipe saved data,
delete that file.

---

## 9. Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `SSL: CERTIFICATE_VERIFY_FAILED … Basic Constraints … not marked critical` | Python 3.13 strict TLS flag. Handled in code (flag cleared, `certifi` bundle if installed). |
| OAuth `400 Invalid open access key` | Put **AccessKeySecret** in "Open access key", not AccessKeyID. |
| `415 Content-Type 'application/json' is not supported` | A GET that rejects Content-Type — the app omits it for `/v1alpha1/robots`. In the console, untick the Content-Type toggle. |
| `415 Content-Type is missing` | The opposite — that endpoint requires `application/json`. Leave the toggle on. |
| Fleet returns 0 robots | Account has no robots, or a `relation` filter excluded them (the app sends none). |
| `"The robot is not on a site"` | Siteless robot — use *List robot maps* / *Get subareas*, not site info. |
| Task rejected `2010100009` | Wrong `areaId` or unsupported `cleaningMode`; pick from the dropdowns after loading maps/areas. |
| `area_id: invalid value … for type TYPE_STRING` | `areaId` must be a string — the app handles this. |
| Live map: `"The map name must not be blank"` | The map-image endpoint requires `mapName`; the app sends it from status automatically (in the console, fill `mapName`). |
| Live map dot mirrored / offset | Toggle **Flip Y**; if still off, the grid↔pixel mapping needs adjusting. |

---

*This tool is a community client and is not affiliated with Gausium. Endpoint
behaviour is based on the [Gausium Developer Documentation](https://developer.gs-robot.com)
and live testing; some fields (e.g. `cmdStatus` values) are inferred from observed behaviour.*
