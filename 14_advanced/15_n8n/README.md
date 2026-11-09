# Module 15 — Low-Code AI Automation with n8n (3-hour lab)

Seven importable n8n workflows that grow from a no-code form app into an AI support desk.
Do the **Before class** steps at home: Google OAuth and the OpenAI key take longer than any workflow.

| File | What it does | Block |
|---|---|---|
| `15_1_service_request_intake.json` | Web form → ticket ID → new row in the **Tickets** sheet → confirmation page | Hour 1 |
| `15_2_lead_capture.json` | Lead form → clean data + segment (hot/warm/cold) → MySQL `leads` → Switch → 3 different welcome emails | Hour 1 |
| `15_3_service_request_api.json` | Your own REST API: `POST /webhook/service-request` → validate → MySQL `tickets` → `201` JSON (or `400`) | Hour 2 |
| `15_4_email_triage.json` | New unread email → AI **Text Classifier** (Sales / Support / Billing / Spam / Other) → Gmail label → log row → mark as read | Hour 2 |
| `15_5_customer_lookup_api.json` | Helper API: `GET /webhook/customer?email=…` → `{ "tier": "Gold", "customer_id": "C-001" }` (unknown → `Standard`) | Hour 3 |
| `15_6_ai_support_desk.json` | Contact form → tier (15_5) → **LLM Chain + Structured Output Parser** → SLA → MySQL → High: draft + alert, else reply sent → log | Hour 3 |
| `15_7_error_handler.json` | Error Trigger → Error Log sheet → admin email with a link to the failed execution | Hour 3 |
| `15_schema.sql` | Creates `leads`, `customers` (4 sample customers, 2 Gold) and `tickets` | — |
| `tickets_header.csv` | Header row for the **Tickets** sheet tab (15_1) | — |
| `test_emails.txt` | Four test emails for 15_4, with the expected label | — |

All AI nodes use **OpenAI `gpt-4o-mini`, temperature 0** through an *OpenAI Chat Model* sub-node.
The workflows contain no credentials: after import, open every node that shows a warning and pick your own.

## Before class

**1. n8n and MySQL in Docker** (PowerShell)

```powershell
docker volume create n8n_data
docker run -d --name n8n -p 5678:5678 `
  -e GENERIC_TIMEZONE=Asia/Kolkata -e TZ=Asia/Kolkata `
  -v n8n_data:/home/node/.n8n `
  docker.n8n.io/n8nio/n8n

docker volume create mysql_data
docker run -d --name mysql -p 3306:3306 `
  -e MYSQL_ROOT_PASSWORD=root123 -e MYSQL_DATABASE=bizdb `
  -e MYSQL_USER=n8n -e MYSQL_PASSWORD=n8npass `
  -v mysql_data:/var/lib/mysql mysql:8.4
```

Wait about 20 seconds on the first start, then load the tables (from this folder):

```powershell
Get-Content 15_schema.sql | docker exec -i mysql mysql -un8n -pn8npass bizdb
```

Open http://localhost:5678 and create the owner account. Later sessions: `docker start n8n mysql`.
If you already have containers called `n8n` or `mysql`, reuse them or pick other names and ports.

**2. Google credentials** (Sheets, Gmail)

1. [Google Cloud Console](https://console.cloud.google.com/) → new project.
2. **APIs & Services → Library**: enable **Google Sheets API**, **Google Drive API** and **Gmail API**.
3. **OAuth consent screen**: External; add your own Gmail address under **Test users**.
4. **Credentials → Create credentials → OAuth client ID** → *Web application*,
   redirect URI `http://localhost:5678/rest/oauth2-credential/callback`.
5. In n8n (**Credentials → Add credential**) create *Google Sheets OAuth2 API* and *Gmail OAuth2*
   with that client ID and secret, then click **Sign in with Google**.

**3. OpenAI**: create an API key at platform.openai.com, add a little billing credit and set a monthly
limit. In n8n: **Credentials → Add credential → OpenAI**.

**4. MySQL credential in n8n**: host `host.docker.internal` (not `localhost`, which is the n8n
container itself), database `bizdb`, user `n8n`, password `n8npass`, port `3306`.

**5. One Google Sheet** with these tabs and header rows:

| Tab | Headers (row 1) | Used by |
|---|---|---|
| Tickets | `ticket_id,created_at,name,email,category,priority,description,status,comment` | 15_1 |
| Email Log | `time, from, subject, category` | 15_4 |
| Ticket Log | `time, ticket_id, category, priority, reply_sent` | 15_6 |
| Error Log | `time, workflow, node, message, execution_url` | 15_7 |

Import a workflow with **Workflows → Create → ⋯ → Import from File**. Each one has a yellow note with its own setup steps.

## Hour 1 — no-code app and business rules

**15_1 Service Request Intake**: pick your Sheets credential and spreadsheet, click **Execute workflow**,
open the **Test URL** and submit a **High** request. A row like `SR-261109-41` appears in Tickets and the
confirmation page shows the same ID. Activate (Publish) it: the production form is
http://localhost:5678/form/raise-request.

**15_2 Lead Capture**: pick MySQL and Gmail credentials, activate, submit three leads at
http://localhost:5678/form/lead, one per budget band, then:

```powershell
docker exec -it mysql mysql -un8n -pn8npass bizdb -e "SELECT name, budget, segment FROM leads"
```

Each lead has the right segment and got a different welcome email. After the **MySQL** node `$json` is only
`{"success": true}`, which is why the emails read the lead from `$('Edit Fields')`.

## Hour 2 — APIs and AI

**15_3 Service Request API**: click **Execute workflow** (it listens on the *test* URL), then:

```powershell
$body = @{ name = 'Asha Patil'; email = 'asha@example.com'; issue = 'Printer not working' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://localhost:5678/webhook-test/service-request' `
  -ContentType 'application/json' -Body $body
```

You get `created` and a ticket ID. Remove `email` and send again → HTTP `400`. Once the workflow is active,
use `/webhook/` instead of `/webhook-test/`.

**15_4 Email Triage**: in Gmail create labels `AI/Sales`, `AI/Support`, `AI/Billing`, `AI/Spam`, and in each
**Label …** node pick the matching one. Send the four emails in `test_emails.txt` to yourself, then Execute.
Each email leaves the classifier on a different output, gets its label and an Email Log row, and is marked
as read so it is not processed twice.

## Hour 3 — capstone: AI support desk

1. Import **15_5**, pick MySQL, **activate** it, and test:
   `Invoke-RestMethod 'http://localhost:5678/webhook/customer?email=asha@example.com'` → `Gold  C-001`.
2. Import **15_6** and **15_7**; pick credentials; change the example addresses
   (`support-team@example.com`, `admin@example.com`).
3. In 15_6: **⋯ → Settings → Error workflow → 15_7 Error Handler**. Activate 15_6 and 15_7.
4. At http://localhost:5678/form/support:
   - as `asha@example.com` (Gold): "I was charged twice for my September plan!" → Billing / High, SLA 4 h,
     reply saved as a Gmail **draft**, support lead alerted, Ticket Log `reply_sent = draft`;
   - as an unknown customer: "What are your store timings?" → General / Low, SLA 24 h, reply sent.
5. `docker exec -it mysql mysql -un8n -pn8npass bizdb -e "SELECT ticket_id, category, priority, sla_hours, summary FROM tickets"`
6. Error handling: `docker stop mysql`, submit the 15_6 form, `docker start mysql`. Within seconds the
   Error Log gets a row and the admin an email. The Error Trigger fires only for production runs.

## Troubleshooting

| Problem | Fix |
|---|---|
| Test URL shows 404 | Click **Execute workflow** first; the test URL listens for one submission only. |
| `redirect_uri_mismatch` | The redirect URI in Google Cloud must match n8n's OAuth redirect URL exactly. |
| "Access blocked: app not verified" | Add your Gmail address as a **Test user** on the consent screen. |
| `ECONNREFUSED 127.0.0.1:3306` | MySQL host must be `host.docker.internal`. |
| `port is already allocated` | Another MySQL uses 3306: run with `-p 3307:3306` and use port 3307 in the credential. |
| `404` from your webhook | `/webhook-test/` only while listening in the editor; `/webhook/` once active; method must match. |
| Expression shows `undefined` | Field names are case-sensitive (`Email` ≠ `email`); webhook data sits under `$json.body`. |
| `401` / `429` from OpenAI | Re-copy the key; add billing credit. |
| Same email processed twice | Keep the trigger on **Unread** and the **Mark as Read** node. |
| Times are 5½ hours off | Start the container with `GENERIC_TIMEZONE` and `TZ` set. |

## Backups

```powershell
docker exec n8n n8n export:workflow --all --output=/home/node/.n8n/workflows.json
docker cp n8n:/home/node/.n8n/workflows.json .
docker exec mysql mysqldump -uroot -proot123 --result-file=/tmp/bizdb.sql bizdb
docker cp mysql:/tmp/bizdb.sql .
```
