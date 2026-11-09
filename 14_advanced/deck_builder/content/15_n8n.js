const M = "15_n8n/";

module.exports = {
  section: "Module 15 – Low-Code AI Automation with n8n",
  slides: [
    {
      kind: "opener",
      eyebrow: "Module 15",
      title: "Low-Code AI Automation with n8n",
      subtitle: "Three hours, seven workflows: from a web form to an AI support desk that handles its own failures",
      goals: [
        { icon: "FaWpforms", title: "Build a no-code app", text: "forms, a sheet as the database, business rules" },
        { icon: "FaPlug", title: "Call and publish APIs", text: "webhooks, HTTP requests, JSON responses" },
        { icon: "FaRobot", title: "Put an LLM inside a workflow", text: "classify, extract and write – with structured output" },
        { icon: "FaShieldHalved", title: "Run it reliably", text: "test vs production, error workflows, backups" },
      ],
      agenda: [
        "n8n in five words; setup",
        "15_1 Service request form (Sheets)",
        "15_2 Lead capture with business rules (MySQL)",
        "15_3 Your own REST API",
        "15_4 AI email triage",
        "15_5 + 15_6 Capstone: AI support desk",
        "15_7 Error workflow; running in production",
      ],
    },
    {
      title: "The Three-Hour Plan",
      subtitle: "Every hour ends with a working workflow; each one reuses what the last one taught",
      demo: M + "README.md",
      blocks: [
        { type: "table", size: 10.5, widths: [1.1, 2.4, 2.6, 2.4], head: ["Time", "Block", "Workflows", "New ideas"], rows: [
          ["0:00", "Concepts and setup check", "–", "Trigger, node, item, execution"],
          ["0:20", "No-code app", "15_1 Service request intake", "Forms, Sheets, test vs production"],
          ["0:45", "Business rules", "15_2 Lead capture", "Expressions, Switch, MySQL"],
          ["1:15", "APIs", "15_3 Service request API", "Webhook, validation, status codes"],
          ["1:45", "Generative AI", "15_4 Email triage", "Text Classifier, chat model sub-node"],
          ["2:15", "Capstone", "15_5 + 15_6 AI support desk", "LLM chain + structured output, SLA"],
          ["2:45", "Reliability", "15_7 Error handler", "Error workflow, backups"],
        ] },
        { type: "callout", eyebrow: "Before class", text: "Docker, Google OAuth and the OpenAI key take longer than any workflow – do the README's setup at home." },
      ],
    },
    {
      title: "n8n in Five Words",
      subtitle: "Workflow · Trigger · Node · Item · Execution",
      demo: "Concept",
      blocks: [
        { type: "flow", items: [
          { icon: "FaBolt", label: "Form Trigger", caption: "Starts a run" },
          { icon: "FaPen", label: "Edit Fields", caption: "Adds a ticket ID" },
          { icon: "FaTable", label: "Google Sheets", caption: "Appends a row" },
          { icon: "FaReply", label: "Form ending", caption: "Shows the ID" },
        ] },
        { type: "tiles", cols: 5, size: 10, items: [
          { icon: "FaDiagramProject", title: "Workflow", text: "The whole canvas – one automated process" },
          { icon: "FaBolt", title: "Trigger", text: "The first node: form, schedule, webhook, email" },
          { icon: "FaCubes", title: "Node", text: "One step that does one job" },
          { icon: "FaListCheck", title: "Item", text: "One JSON record; 20 rows = 20 items" },
          { icon: "FaClockRotateLeft", title: "Execution", text: "One run, saved with every node's data" },
        ] },
      ],
    },
    {
      title: "Setup: n8n and MySQL in Docker",
      subtitle: "Two containers; n8n reaches MySQL through host.docker.internal",
      demo: M + "15_schema.sql  ·  Get-Content 15_schema.sql | docker exec -i mysql mysql …",
      split: [1.3, 1],
      left: [
        { type: "code", caption: "PowerShell (first time only)", code:
`docker run -d --name n8n -p 5678:5678 \`
  -e GENERIC_TIMEZONE=Asia/Kolkata -e TZ=Asia/Kolkata \`
  -v n8n_data:/home/node/.n8n docker.n8n.io/n8nio/n8n

docker run -d --name mysql -p 3306:3306 \`
  -e MYSQL_ROOT_PASSWORD=root123 -e MYSQL_DATABASE=bizdb \`
  -e MYSQL_USER=n8n -e MYSQL_PASSWORD=n8npass \`
  -v mysql_data:/var/lib/mysql mysql:8.4

Get-Content 15_schema.sql |
  docker exec -i mysql mysql -un8n -pn8npass bizdb` },
      ],
      right: [
        { type: "steps", size: 10.5, items: [
          { title: "Open localhost:5678", text: "Create the owner account" },
          { title: "MySQL credential", text: "Host `host.docker.internal` – `localhost` is the n8n container itself" },
          { title: "Google credentials", text: "One OAuth client for Sheets and Gmail; add yourself as a test user" },
          { title: "OpenAI credential", text: "API key with a monthly limit" },
        ] },
      ],
    },
    {
      title: "Test vs Production",
      subtitle: "Every trigger has two URLs – know which one you are using",
      demo: M + "15_1_service_request_intake.json  (form: /form/raise-request)",
      blocks: [
        { type: "tiles", cols: 2, size: 10.5, items: [
          { icon: "FaWrench", title: "Test URL", text: "Listens after **Execute workflow**, for one run; data shows live on the canvas. Contains `/form-test/` or `/webhook-test/`." },
          { icon: "FaRocket", title: "Production URL", text: "Works any time once the workflow is active – the link you share. Contains `/form/` or `/webhook/`." },
          { icon: "FaPlay", title: "Activate (Publish)", text: "Switches the workflow on; triggers then run without the editor open." },
          { icon: "FaClockRotateLeft", title: "Executions", text: "Every production run is logged – open one to see what each node got and returned." },
        ] },
        { type: "callout", eyebrow: "Most common beginner mistake", text: "Sharing the test URL. It stops working after one submission." },
      ],
    },
    {
      title: "15_1 Service Request Intake",
      subtitle: "A no-code app: the form is the UI, a Google Sheet is the database",
      demo: M + "15_1_service_request_intake.json  ·  tickets_header.csv",
      blocks: [
        { type: "flow", items: [
          { icon: "FaWpforms", label: "Form Trigger", caption: "Name, email, category, priority, description" },
          { icon: "FaPen", label: "Edit Fields", caption: "ticket_id, created_at, status = Open" },
          { icon: "FaTable", label: "Save to Tickets Sheet", caption: "Append one row" },
          { icon: "FaReply", label: "Confirmation Page", caption: "\"Your ticket SR-261109-41\"" },
        ] },
        { type: "code", caption: "Edit Fields – a unique, readable ticket ID", code:
`ticket_id  = SR-{{ $now.toFormat('yyMMdd') }}-{{ $execution.id }}
created_at = {{ $now.toFormat('yyyy-MM-dd HH:mm') }}
status     = Open` },
      ],
    },
    {
      title: "Expressions: Reading Data Anywhere",
      subtitle: "Everything inside {{ }} is a small piece of JavaScript",
      demo: M + "15_2_lead_capture.json",
      split: [1, 1.15],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaBolt", title: "Current item", text: "`{{ $json.email }}` – a field from the node just before" },
          { icon: "FaDiagramProject", title: "Any earlier node", text: "`{{ $('Edit Fields').item.json.email }}`" },
          { icon: "FaClock", title: "Dates and times", text: "`{{ $now }}`, `{{ $today.minus({days: 1}) }}` (Luxon)" },
          { icon: "FaCode", title: "JavaScript methods", text: "`{{ $json.Email.trim().toLowerCase() }}`" },
        ] },
      ],
      right: [
        { type: "code", caption: "15_2 Edit Fields – clean and segment a lead", code:
`name    = {{ $json.Name.trim() }}
email   = {{ $json.Email.trim().toLowerCase() }}
segment = {{ $json.Budget == 'Above 5 lakh' ? 'hot'
           : $json.Budget == '1-5 lakh' ? 'warm'
           : 'cold' }}` },
        { type: "callout", eyebrow: "Why $('Edit Fields')?", text: "After the MySQL node, `$json` is only `{\"success\": true}` – so the emails read the lead from an earlier node." },
      ],
    },
    {
      title: "15_2 Lead Capture and Business Rules",
      subtitle: "Clean the input, store it, then route each lead by a rule",
      demo: M + "15_2_lead_capture.json  (form: /form/lead)",
      blocks: [
        { type: "flow", items: [
          { icon: "FaWpforms", label: "Form Trigger", caption: "Name, email, company, budget, source" },
          { icon: "FaPen", label: "Edit Fields", caption: "Clean + segment" },
          { icon: "FaDatabase", label: "MySQL", caption: "INSERT into leads" },
          { icon: "FaShuffle", label: "Switch", caption: "hot / warm / cold" },
          { icon: "FaEnvelope", label: "Welcome email", caption: "One of three Gmail nodes" },
        ] },
        { type: "tiles", cols: 4, size: 10, items: [
          { icon: "FaCodeBranch", title: "IF", text: "Two paths: true / false" },
          { icon: "FaShuffle", title: "Switch", text: "One path per rule or value" },
          { icon: "FaFilter", title: "Filter", text: "Drop items that fail a check" },
          { icon: "FaCodeMerge", title: "Merge", text: "Join two branches back into one" },
        ] },
      ],
    },
    {
      title: "15_3 Publish Your Own REST API",
      subtitle: "A Webhook trigger turns a workflow into an endpoint other systems can call",
      demo: M + "15_3_service_request_api.json  (POST /webhook/service-request)",
      split: [1, 1.1],
      left: [
        { type: "tree", boxW: 1.6, size: 10, rows: [["POST /webhook/service-request"], [{ label: "Valid Request?", fill: "coral" }], [{ label: "Edit Fields → MySQL", fill: "teal" }, "Respond 400"], [{ label: "Respond 201", fill: "teal" }]] },
      ],
      right: [
        { type: "code", caption: "PowerShell", code:
`$body = @{ name = 'Asha Patil'
           email = 'asha@example.com'
           issue = 'Printer not working' } | ConvertTo-Json
Invoke-RestMethod -Method Post \`
  -Uri http://localhost:5678/webhook-test/service-request \`
  -ContentType 'application/json' -Body $body
# status  ticket_id
# created SR-261109-26` },
        { type: "text", size: 11, color: "slate", text: "Drop `email` from the body → `400` with `{\"error\": \"name, email and issue are required\"}`. Webhook data sits under `$json.body`." },
      ],
    },
    {
      title: "Generative AI in a Workflow",
      subtitle: "Each AI step is one node inside an otherwise ordinary workflow",
      demo: M + "15_4_email_triage.json, 15_6_ai_support_desk.json",
      blocks: [
        { type: "tiles", cols: 4, size: 10, items: [
          { icon: "FaTags", title: "Classify", text: "Email → Billing (15_4)" },
          { icon: "FaWandMagicSparkles", title: "Extract", text: "Text → typed fields" },
          { icon: "FaCompress", title: "Summarise", text: "Ticket → 12-word summary (15_6)" },
          { icon: "FaPen", title: "Generate", text: "Ticket → draft reply (15_6)" },
        ] },
        { type: "table", size: 10, widths: [2.2, 3.6, 1.6], head: ["n8n node", "Use it for", "Here"], rows: [
          ["Text Classifier", "One output per category", "15_4"],
          ["Basic LLM Chain + Structured Output Parser", "Prompt in, validated JSON out", "15_6"],
          ["OpenAI Chat Model (sub-node)", "The model behind both: gpt-4o-mini, temperature 0", "both"],
          ["AI Agent", "A model that picks tools itself", "Module 06 onward"],
        ] },
      ],
    },
    {
      title: "15_4 AI Email Triage",
      subtitle: "Every unread email gets a label, a log row – and is never processed twice",
      demo: M + "15_4_email_triage.json  ·  test_emails.txt",
      blocks: [
        { type: "flow", items: [
          { icon: "FaInbox", label: "Gmail Trigger", caption: "Unread mail, every minute" },
          { icon: "FaTags", label: "Text Classifier", caption: "Sales · Support · Billing · Spam · Other" },
          { icon: "FaEnvelope", label: "Label …", caption: "AI/Billing etc." },
          { icon: "FaTable", label: "Log to Sheet", caption: "time, from, subject, category" },
          { icon: "FaCheck", label: "Mark as Read", caption: "So it is not seen again" },
        ] },
        { type: "callout", eyebrow: "Prompts for automation", text: "Exact categories with descriptions, an \"Other\" path for anything unclear, temperature 0 – same input, same answer." },
      ],
    },
    {
      title: "Capstone: 15_6 AI Support Desk",
      subtitle: "A form, an API call, an LLM with a schema, a rule, a database and two kinds of reply",
      demo: M + "15_5_customer_lookup_api.json → 15_6_ai_support_desk.json  (form: /form/support)",
      blocks: [
        { type: "flow", items: [
          { icon: "FaWpforms", label: "Form Trigger", caption: "Name, email, order no., message" },
          { icon: "FaIdCard", label: "HTTP Request", caption: "15_5: tier = Gold / Standard" },
          { icon: "FaBrain", label: "Classify & Draft Reply", caption: "LLM chain + output parser", color: "coral" },
          { icon: "FaDatabase", label: "Edit Fields → MySQL", caption: "ticket_id, SLA 4 h / 24 h" },
          { icon: "FaCodeBranch", label: "High Priority?", caption: "Draft + alert lead, or send" },
        ] },
        { type: "compare", size: 10.5, cols: [
          { title: "High priority", color: "coral", items: ["Reply saved as a Gmail **draft** – a human checks it", "Support lead alerted", "Ticket Log: reply_sent = draft"] },
          { title: "Otherwise", color: "teal", items: ["Reply sent automatically", "Ticket Log: reply_sent = yes", "SLA from the customer's tier"] },
        ] },
      ],
    },
    {
      title: "Structured Output: Text Becomes Data",
      subtitle: "The output parser forces the LLM's answer into fields later nodes can use",
      demo: M + "15_6_ai_support_desk.json",
      split: [1.1, 1],
      left: [
        { type: "code", caption: "System message (condensed)", code:
`You are the support triage assistant for an online
electronics store. Return:
  category  Billing | Technical | Delivery | General
  priority  Low | Medium | High
            (High = money lost, service down, very upset)
  summary   max 12 words
  reply     polite, max 80 words, greet by first name,
            do not promise refunds, amounts or dates` },
      ],
      right: [
        { type: "code", caption: "Structured Output Parser – JSON example", code:
`{
  "category": "Billing",
  "priority": "High",
  "summary": "Charged twice for September plan",
  "reply": "Dear Asha, ..."
}` },
        { type: "text", size: 11, color: "slate", text: "Later nodes read `{{ $json.output.priority }}` – no string parsing, and a malformed answer fails loudly." },
      ],
    },
    {
      title: "15_7 When Things Fail",
      subtitle: "Plan for failure from the first workflow",
      demo: M + "15_7_error_handler.json  (test: docker stop mysql, submit the 15_6 form)",
      split: [1, 1.1],
      left: [
        { type: "icons", d: 0.38, size: 11, items: [
          { icon: "FaArrowsRotate", title: "Retry On Fail", text: "Node settings: retry with a wait – for brief network or API hiccups" },
          { icon: "FaCodeBranch", title: "Continue (error output)", text: "Failed items take a separate path instead of stopping the run" },
          { icon: "FaTriangleExclamation", title: "Error workflow", text: "Workflow settings → Error workflow → 15_7" },
          { icon: "FaMagnifyingGlass", title: "Read the failed execution", text: "The red node shows the error and the input that caused it" },
        ] },
      ],
      right: [
        { type: "flow", items: [
          { icon: "FaTriangleExclamation", label: "Error Trigger", caption: "Any failed production run", color: "coral" },
          { icon: "FaPen", label: "Edit Fields", caption: "workflow, node, message, URL" },
          { icon: "FaTable", label: "Log Error", caption: "Error Log sheet" },
          { icon: "FaBell", label: "Alert Admin", caption: "Email with a link to the run" },
        ] },
      ],
    },
    {
      title: "Running It for Real",
      subtitle: "Four questions to answer before an AI workflow goes live",
      demo: "Concept  ·  backups: README.md → Backups",
      blocks: [
        { type: "tiles", cols: 4, size: 10, items: [
          { icon: "FaCoins", title: "Cost", text: "gpt-4o-mini costs a fraction of a rupee per email – set a monthly limit anyway" },
          { icon: "FaTriangleExclamation", title: "Wrong answers", text: "Validate outputs, keep an \"Other\" path, log what the AI decided" },
          { icon: "FaUserShield", title: "Privacy", text: "Text sent to the model leaves your network – no passwords or card numbers" },
          { icon: "FaShieldHalved", title: "Prompt injection", text: "An email can contain instructions: treat input as data, keep a human on risky actions" },
        ] },
        { type: "tiles", cols: 4, size: 10, items: [
          { icon: "FaRocket", title: "Activate", text: "Production URLs work only while a workflow is active" },
          { icon: "FaClock", title: "Time zone", text: "`GENERIC_TIMEZONE` drives every Schedule Trigger" },
          { icon: "FaLink", title: "Public URL", text: "On a server set `WEBHOOK_URL` so forms and links point to it" },
          { icon: "FaServer", title: "Back up", text: "Export workflows as JSON (into Git); dump MySQL" },
        ] },
      ],
    },
    {
      kind: "summary",
      title: "Module 15 Summary",
      subtitle: "What you built",
      built: [
        { tag: "15_1", title: "A no-code form app", text: "Form → sheet → confirmation" },
        { tag: "15_2", title: "Business rules", text: "Clean, store in MySQL, route by segment" },
        { tag: "15_3", title: "Your own API", text: "Webhook with validation and status codes" },
        { tag: "15_4", title: "AI email triage", text: "Classifier → label → log" },
        { tag: "15_6", title: "AI support desk", text: "LLM + schema + SLA + human review + error workflow" },
      ],
      takeaways: [
        "Share production URLs, never test URLs",
        "Expressions read any earlier node: $('Node').item.json",
        "Put the LLM in one node and give it a schema",
        "Keep a human on high-stakes replies",
        "Add an error workflow before you go live",
      ],
      next: "Module 16: Guardrails – NeMo, Guardrails AI and Safety",
    },
  ],
};
