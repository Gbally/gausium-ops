# Gausium OpenAPI — Request/Response Reference

Working request formats with real example responses, for integrating against the
Gausium OpenAPI. Examples use `curl`; the structures apply in any language.

- **Base URL:** `https://openapi.gs-robot.com`
- **Auth:** every call except OAuth needs the header `Authorization: Bearer <TOKEN>`
- **Placeholders:** replace `<TOKEN>`, `<CLIENT_ID>`, `<CLIENT_SECRET>`,
  `<ACCESS_KEY_SECRET>`, and `<SN>` (robot serial number) with your values.

> ⚠️ **Content-Type gotcha:** most endpoints require `Content-Type: application/json`,
> **but `GET /v1alpha1/robots` rejects it** (returns HTTP 415). Send that one with
> no Content-Type header. Bodyless GETs that *do* require the header are noted below.

---

## Typical workflow

```
1. OAuth            POST /gas/api/v1alpha1/oauth/token        → access token
2. List robots      GET  /v1alpha1/robots                     → serial numbers
3. Live status      GET  /openapi/v2alpha1/s/robots/{sn}/status
4. Maps & areas     POST /openapi/v1/map/robotMap/list         → mapId
                    POST /openapi/v1/map/subareas/get          → areaId
5. Send a task      POST /openapi/v2alpha1/robotCommand/tempTask:send
   or a command     POST /v1alpha1/robots/{sn}/commands        (stop/pause/dock)
6. Usage data       GET  /openapi/v2alpha1/robots/{sn}/taskReports
```

---

## 1. Authentication — get a token

```bash
curl -X POST 'https://openapi.gs-robot.com/gas/api/v1alpha1/oauth/token' \
  -H 'Content-Type: application/json' \
  -d '{
    "grant_type": "urn:gaussian:params:oauth:grant-type:open-access-token",
    "client_id": "<CLIENT_ID>",
    "client_secret": "<CLIENT_SECRET>",
    "open_access_key": "<ACCESS_KEY_SECRET>"
  }'
```

**Response**
```json
{
  "access_token": "<TOKEN>",
  "expires_in": 1781856484285,
  "token_type": "Bearer"
}
```
> `open_access_key` is the **AccessKeySecret** (not the AccessKeyID).
> `expires_in` is an absolute **epoch-milliseconds** expiry timestamp, not a duration.

---

## 2. List robots

```bash
# NOTE: no Content-Type header on this endpoint
curl 'https://openapi.gs-robot.com/v1alpha1/robots?page=1&pageSize=50' \
  -H 'Authorization: Bearer <TOKEN>'
```

**Response**
```json
{
  "robots": [
    {
      "serialNumber": "XXXXX-XXXX-XX-XXXX",
      "displayName": "Robot Name",
      "online": true,
      "modelTypeCode": "XXX",
      "softwareVersion": "..."
    }
  ],
  "page": 1,
  "pageSize": 50,
  "total": "1"
}
```
> An empty list (`"robots": []`, `"total": "0"`) is a valid success, not an error.

---

## 3. Live status

```bash
curl 'https://openapi.gs-robot.com/openapi/v2alpha1/s/robots/<SN>/status' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>'
```

**Response** (abridged — real payload)
```json
{
  "serialNumber": "XXXXX-XXXX-XX-XXXX",
  "taskState": "RUNNING",
  "online": true,
  "speedKilometerPerHour": 0,
  "battery": {
    "charging": false,
    "powerPercentage": 99,
    "soc": 100,
    "soh": "HEALTHY",
    "cycleTimes": 84
  },
  "emergencyStop": { "enabled": false },
  "localizationInfo": {
    "localizationState": "NORMAL",
    "map": {
      "id": "map_id",
      "name": "map_name",
      "version": "maps/6be93db4-.../versions/783e2104-..."
    },
    "mapPosition": { "x": 156, "y": 131, "angle": -70.505 }
  },
  "navigationPoints": {
    "naviPoints": [
      { "naviPointName": "Origin",   "navPointGridX": 169, "navPointGridY": 123 },
      { "naviPointName": "charging", "navPointGridX": 153, "navPointGridY": 107 }
    ]
  },
  "device": {
    "rollingBrush":    { "lifeSpan": 300, "usedLife": 2.21 },
    "rightSideBrush":  { "lifeSpan": 300, "usedLife": 0 },
    "softSqueegee":    { "lifeSpan": 300, "usedLife": 2.56 },
    "cleanWaterFilter":{ "lifeSpan": 600, "usedLife": 1.44 },
    "hepaSensor":      { "lifeSpan": 600, "usedLife": 3.31 },
    "recoveryWaterTank": { "level": 50 }
  },
  "navStatus": "NAVI_IDLE",
  "latestReportTime": "1781779355716"
}
```
**Key fields**
- Battery: `battery.powerPercentage`, `battery.charging`
- State: `taskState`, `navStatus`, `localizationInfo.localizationState`
- Current map: `localizationInfo.map.name` / `.id`
- E-stop: `emergencyStop.enabled`
- Consumable remaining % = `(1 - usedLife / lifeSpan) * 100` per item in `device`

---

## 4. Maps & areas (needed for tasks)

### 4a. List the robot's maps → `mapId`
```bash
curl -X POST 'https://openapi.gs-robot.com/openapi/v1/map/robotMap/list' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>' \
  -d '{ "robotSn": "<SN>" }'
```
**Response** (real)
```json
{
  "code": 0,
  "msg": "SUCCESS",
  "data": [
    {
      "mapId": "map_id",
      "mapName": "map_name",
      "mapVersion": "map_version"
    }
  ]
}
```

### 4b. Get a map's subareas → `areaId`
```bash
curl -X POST 'https://openapi.gs-robot.com/openapi/v1/map/subareas/get' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>' \
  -d '{
    "mapId": "map_id",
    "robotSn": "<SN>"
  }'
```
**Response** (real)
```json
{
  "code": 0,
  "msg": "SUCCESS",
  "data": {
    "mapId": "map_id",
    "subareas": {
      "partitions": [
        { "id": 1, "name": "area1" },
        { "id": 2, "name": "area2" },
        //...
      ]
    }
  }
}
```
> The **areaId** is the numeric `partitions[].id`. The task API wants it as a **string** (`"1"`).

### 4c. Get the map image (for live position display)
```bash
curl 'https://openapi.gs-robot.com/openapi/v2alpha1/robots/<SN>/map?mapId=map_id&mapVersion=&mapName=map_name' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>'
```
**Response** (real)
```json
{ "downloadUri": "https://…s3…/map.png?X-Amz-…" }
```
- `mapName` is **required** (non-blank) — an empty name returns `code 3 "The map name must not be blank."`. `mapVersion` may be empty.
- `downloadUri` is a **presigned PNG, valid ~1 hour** — fetch it fresh per session.
- To plot the robot on it: the map PNG is the occupancy grid, and `localizationInfo.mapPosition.x/y` (from status, §3) are grid cells ≈ image pixels, origin bottom-left → `pixel_y = imageHeight − y`.

---

## 5. Send a request to a robot

### 5a. Launch a cleaning task
```bash
curl -X POST 'https://openapi.gs-robot.com/openapi/v2alpha1/robotCommand/tempTask:send' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>' \
  -d '{
    "productId": "<SN>",
    "tempTaskCommand": {
      "cleaningMode": "清扫",
      "loop": "false",
      "loopCount": "1",
      "taskName": "Daily clean",
      "mapName": "map_name",
      "startParam": {
        "mapId": "map_id",
        "areaId": "area_id"
      }
    }
  }'
```
**Response — accepted (robot starts moving)**
```json
{
  "productId": "XXXXX-XXXX-XX-XXXX",
  "requestId": "OpenApiV2:01KVD75...:841bc848...",
  "orderType": "start_task",
  "cmdStatus": 5,
  "cmdResultCode": "6880"
}
```
**Response — rejected (bad parameters)**
```json
{
  "productId": "XXXXX-XXXX-XX-XXXX",
  "requestId": "OpenApiV2:01KVD61...:841bc848...",
  "orderType": "start_task",
  "cmdStatus": 7,
  "cmdResultCode": "2010100009"
}
```
**Interpreting the result**
- `cmdStatus: 0` → accepted cleanly.
- Other `cmdStatus` (e.g. `5`) with an unrecognised code → accepted, robot executing.
- `cmdResultCode` in the error table below → rejected.

| cmdResultCode | Meaning |
|---|---|
| 2010100006 | Invalid tag |
| 2010100007 | Task area unreachable |
| 2010100008 | Task area operation type mismatch |
| 2010100009 | Operation data failure (task parameters rejected) |
| 2010100010 | No color camera installed |
| 2010100011 | No inspection equipment neural stick installed |
| 2010100012 | There are temporary tasks |
| 2010100013 | Robot cannot switch sites in the current state |

> Most frequent rejection is `2010100009` — usually a wrong `areaId` (must be a valid
> partition id as a **string**) or a `cleaningMode` the robot doesn't support.

#### Cleaning modes (`cleaningMode`)

Cleaning modes are **robot-specific and depend on installed hardware** (e.g. a robot
with a wet tank won't accept a dry-only mode). There is no fixed enum in the API
docs — the **authoritative list for a given robot is in its status payload**, under
`cleanModes` / `workModes`. Always send one of the exact `name` values reported there.

Observed mode values across models (the `__`-prefixed ones come from newer models):

| Value | Meaning | Wet/Dry |
|-------|---------|---------|
| `清扫` | Sweep | dry |
| `吸尘` | Vacuum | dry |
| `尘推` | Dust push | dry |
| `清洗` | Scrub / wash | wet |
| `__扫地` | Sweep | dry |
| `__滚刷尘推` | Roller-brush dust mop | dry |
| `__洗地` | Floor wash / scrub | wet |
| `__middle_cleaning` | Generic (doc example) | — |

> Send the **original** value (Chinese / `__`-prefixed) — the English column is only a
> human reference. To know which modes a specific robot supports right now, read
> `cleanModes`/`workModes` from `GET /openapi/v2alpha1/s/robots/{sn}/status`.

### 5b. Stop / Pause / Resume a task
```bash
curl -X POST 'https://openapi.gs-robot.com/v1alpha1/robots/<SN>/commands' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>' \
  -d '{ "serialNumber": "<SN>", "remoteTaskCommandType": "PAUSE_TASK" }'
```
`remoteTaskCommandType`: `START_TASK` · `PAUSE_TASK` · `RESUME_TASK` · `STOP_TASK`

**Response**
```json
{ "name": "...", "state": "WAITING", "createTime": "...", "startDelay": 1800000 }
```

### 5c. Send the robot to its charging dock
```bash
curl -X POST 'https://openapi.gs-robot.com/v1alpha1/robots/<SN>/commands' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>' \
  -d '{
    "serialNumber": "<SN>",
    "remoteNavigationCommandType": "CROSS_NAVIGATE",
    "commandParameter": {
      "startNavigationParameter": { "map": "map_name", "position": "charging" }
    }'
```
- `map` = map **name** (from status or robotMap/list)
- `position` = a **navigation point name** from `status.navigationPoints.naviPoints`
  (the dock point is typically named `charging`).

---

## 6. Retrieve usage data — task reports

```bash
curl 'https://openapi.gs-robot.com/openapi/v2alpha1/robots/<SN>/taskReports?page=1&pageSize=50&startTimeUtcFloor=2026-06-01T00:00:00Z&startTimeUtcUpper=2026-06-18T00:00:00Z' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer <TOKEN>'
```
Query params: `page`, `pageSize`, optional `startTimeUtcFloor` / `startTimeUtcUpper` (ISO-8601 UTC).

**Response** (representative — field names the dashboard reads)
```json
{
  "robotTaskReports": [
    {
      "displayName": "Daily clean",
      "cleaningMode": "清扫",
      "areaNameList": "area1",
      "completionPercentage": 0.98,
      "actualCleaningAreaSquareMeter": 142.5,
      "efficiencySquareMeterPerHour": 310,
      "startBatteryPercentage": 95,
      "endBatteryPercentage": 78,
      "durationSeconds": 1650
    }
  ]
}
```
> The report field set can vary by robot/firmware. Confirm the names against a live
> response; `completionPercentage` is a 0–1 fraction in the examples above.

---

## 7. Real-time push notifications (webhooks)

Instead of polling, Gausium can **POST events to a callback URL you host** (Robot
Push Service). You register a callback (an `appId`, a callback URL receiving HTTP
POST, and a language tag like `en-US`); Gausium then pushes events to it. Two
channels are relevant:

### 7a. Incident Push — alarms (robot stuck, low battery, faults…)
Delivers robot incidents graded by severity **H0–H7**:

| Level | Meaning |
|-------|---------|
| H0 | Notification only |
| H1–H2 | Status issues the user can resolve |
| H3–H4 | Problems (not) affecting the task |
| H5–H6 | Hidden dangers / faults |
| H7 | Serious failure |

Documented examples: **robot stuck**, **low battery**, **clean water full**.

**Pushed payload** (per docs)
```json
{
  "appId": "<APP_ID>",
  "messageTypeId": 1,
  "productId": "<SN>",
  "messageId": "<unique-id>",
  "messageTimestamp": 1781779355716,
  "payload": {
    "content": {
      "incidentCode": "...",
      "incidentName": "Robot stuck",
      "incidentLevel": "H3",
      "incidentStatus": 1,
      "startTime": "2026-06-18T10:00:00Z",
      "endTime": null,
      "taskId": "...",
      "mapId": "...",
      "navInstanceId": "..."
    }
  }
}
```
- `incidentStatus`: **1 = alarm raised, 0 = recovered** (so you get both the onset and the all-clear).
- `messageTypeId`: `1` = Incident.

### 7b. Task Report Push — task/map finished
Fires when a task completes. Pushed report includes:
- `taskEndStatus`: **−1** Unknown · **0** Normal · **1** Manual · **2** Error · **3** Startup failure
- `completionPercentage` (0–1), `actualCleaningAreaSquareMeter`, `plannedCleaningAreaSquareMeter`,
  `efficiencySquareMeterPerHour`, `durationSeconds`, `waterConsumptionLiter`,
  `startBatteryPercentage` / `endBatteryPercentage`, `consumablesResidualPercentage`,
  and task/plan/instance IDs + cleaning mode.

> Push requires a **publicly reachable HTTPS endpoint** to receive the POSTs (a server
> or cloud function — not a desktop client). The exact callback-registration step is
> configured on the Gausium side; confirm the registration endpoint/portal with Gausium.
> The payloads above are built from the documented field lists — validate against a real
> push before relying on exact names.

Docs: [Incident Push](https://developer.gs-robot.com/en_US/Robot%20Push%20Service/Incident%20Push) ·
[Task Report Push](https://developer.gs-robot.com/en_US/Robot%20Push%20Service/Task%20Report%20Push)

---

## Path families (why the prefixes differ)
- `/gas/api/…` — OAuth only
- `/v1alpha1/…` — robot list + command endpoint
- `/openapi/v1/…` and `/openapi/v2alpha1/…` — maps, subareas, status, tasks, reports

---

*Based on the Gausium Developer Documentation (https://developer.gs-robot.com) and
live testing against an M5P robot. Responses marked "real" were captured from a live
robot; "representative" ones reflect the fields in use and may vary by model/firmware.*
