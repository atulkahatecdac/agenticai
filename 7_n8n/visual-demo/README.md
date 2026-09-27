# Visual Similarity Search Demo (n8n + FaceNet + Qdrant + MySQL)

Upload a face photo in an n8n form and get back the **5 most visually similar
people** from a database of 50 synthetic portraits, shown as photo cards with
similarity scores and person details.

```
 n8n Form            FastAPI (this folder)         Qdrant              MySQL
┌────────────┐      ┌──────────────────────┐     ┌──────────────┐    ┌──────────────┐
│Upload Image│─────►│ POST /embedding      │     │ people_faces │    │ visual_demo  │
└────────────┘ file │  MTCNN  (find face)  │     │ 50 vectors   │    │ .people      │
                    │  FaceNet (512 nums)  │     └──────▲───────┘    └──────▲───────┘
                    └──────────┬───────────┘            │ top 5             │ details
                               │ 512-number embedding   │                   │
                               └────────────────────────┘───────────────────┘
                                                              │
                    ┌──────────────────────┐                  ▼
 Browser  ◄─────────│ GET /images/P0xx.jpg │◄──── Form Ending page (HTML cards)
                    └──────────────────────┘
```

**Key idea:** the image is never compared by an LLM. A vision model turns each
face into 512 numbers (an *embedding*); a vector database finds the nearest
embeddings; a normal SQL database supplies the details.

> The 50 people in `../synthetic_people_demo` are **fictional**. Present the
> score as *visual similarity*, not as proof of identity.

---

## What's in this folder

| File | Purpose |
|---|---|
| `main.py` | FastAPI service: `POST /embedding` (image → 512-dim face vector, also keeps a copy of the upload), `GET /images/{file}` (database photos) and `GET /uploads/{file}` (the user's uploaded photo) |
| `uploads/` | Created automatically; copies of photos uploaded through n8n (git-ignored, safe to delete) |
| `build_vector_db.py` | One-time loader: embeds all 50 photos and stores them in Qdrant with their metadata |
| `requirements.txt` | Pinned dependencies for this folder's own venv |

Data used (in `../synthetic_people_demo`): `P001.jpg`–`P050.jpg`,
`people.csv`, `people.sql`.

---

## Prerequisites

- **Windows + Python 3.12** and [uv](https://docs.astral.sh/uv/)
- **Docker Desktop** running three containers:
  - **n8n** on port `5678`
  - **MySQL 8** (same Docker network as n8n)
  - **Qdrant** on port `6333`

The FastAPI service runs as **plain Python on the host**, not in Docker.
n8n reaches it (and Qdrant) through `host.docker.internal`.

---

## 1. Python environment (own venv, do not use the repo's shared `.venv`)

`facenet-pytorch 2.6.0` hard-pins `torch 2.2.x`, `torchvision 0.17.x`,
`Pillow 10.2.x` and `numpy < 2`. These clash with the repo's root
`requirements.txt`, so this folder gets its **own** venv with every version
pinned. `torch` is the CPU-only build (no multi-GB CUDA download).

```powershell
cd 7_n8n\visual-demo
uv venv --python 3.12 venv
uv pip install --python venv -r requirements.txt --index-strategy unsafe-best-match
uv pip check --python venv          # should say: All installed packages are compatible
```

Without uv: `python -m venv venv` then `venv\Scripts\pip install -r requirements.txt`.

---

## 2. Start the embedding API

```powershell
venv\Scripts\python main.py
```

- Listens on `http://localhost:8001` (bound to `0.0.0.0` so Docker can reach it).
- The **first** start downloads the FaceNet `vggface2` weights (~107 MB) and
  caches them; later starts are fast.
- Leave this window running for the rest of the demo.

**Checkpoint:** open `http://localhost:8001/docs`, try `POST /embedding` with
`../synthetic_people_demo/P017.jpg`. You should get:

```json
{ "filename": "P017.jpg", "upload_file": "53b8...f641.jpg", "dimensions": 512, "embedding": [-0.036, 0.061, ...] }
```

`upload_file` is a copy of the uploaded photo saved in `uploads/`, so the
result page can show the user's own image next to the matches. Send the form
field `save=false` to skip saving (`build_vector_db.py` does this).

Also check `http://localhost:8001/images/P017.jpg` shows the photo.

---

## 3. Qdrant (vector database)

Start Qdrant if it isn't already running:

```powershell
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant
# or, for an existing stopped container:  docker start <container-name>
```

Then load the 50 face embeddings (the API from step 2 must be running):

```powershell
venv\Scripts\python build_vector_db.py
```

This (re)creates the collection `people_faces` (512 dims, cosine distance) and
stores each vector with a payload of `person_id, name, age, department,
location, image_file`. Point ids are numeric: `P017` → `17`. It is safe to
re-run; it drops and rebuilds the collection each time.

It ends with a self-test that searches with `P017.jpg`:

```
Test search with P017.jpg - top 5:
  Match 1 -> P017 Rahul      -> 1.00
  Match 2 -> P045 Mohit      -> 0.87
  Match 3 -> P011 Aditya     -> 0.86
  Match 4 -> P015 Arjun      -> 0.86
  Match 5 -> P035 Amit       -> 0.85
```

Browse the collection at `http://localhost:6333/dashboard`.

> If the Qdrant container has no volume mounted, its data survives
> stop/start but is lost if the container is removed. Just re-run
> `build_vector_db.py`.

---

## 4. MySQL (person details)

`../synthetic_people_demo/people.sql` creates database `visual_demo`, table
`people`, and inserts all 50 rows.

If you don't have a MySQL container yet, put it on the same Docker network as
n8n so n8n can reach it by name:

```powershell
docker network create n8n-net
docker run -d --name mysql --network n8n-net -e MYSQL_ROOT_PASSWORD=<password> mysql:8.0
docker network connect n8n-net n8n      # if n8n isn't on that network yet
```

Load the data (PowerShell has no `<` redirect, so pipe it in):

```powershell
Get-Content ..\synthetic_people_demo\people.sql | docker exec -i mysql mysql -uroot -p<password>
```

Verify:

```powershell
docker exec mysql mysql -uroot -p<password> -e "SELECT COUNT(*) FROM visual_demo.people;"
# -> 50
```

---

## 5. n8n workflow

Open n8n at `http://localhost:5678` and build this chain:

```
Upload Image → Get Embedding for Input Image → HTTP Request (Qdrant)
     → Code in JavaScript (Top 5) → Select rows from a table (MySQL)
     → Code in JavaScript1 (Build page) → Form (Form Ending)
```

### Two URL rules to remember

| Who is calling | Use | Why |
|---|---|---|
| n8n (inside Docker) → FastAPI / Qdrant | `http://host.docker.internal:<port>` | inside a container, `localhost` means the container itself |
| n8n → MySQL | host `mysql`, port `3306` | same Docker network, reach it by container name |
| Browser → FastAPI images | `http://localhost:8001` | the browser runs on the host |

### 5.1 Upload Image: *n8n Form Trigger*

- Form field: **Label** `Image`, **Type** File (accept `.jpg,.png`).
- The uploaded file becomes a binary property named **`Image`** (capital I,
  it takes the field label).

### 5.2 Get Embedding for Input Image: *HTTP Request*

| Setting | Value |
|---|---|
| Method | `POST` |
| URL | `http://host.docker.internal:8001/embedding` |
| Send Body | on |
| Body Content Type | `Form-Data` |
| Parameter Type | `n8n Binary File` |
| Name | `image` (lowercase; must match `image: UploadFile` in `main.py`) |
| Input Data Field Name | `Image` (the binary property from the form) |

Connect it **directly** to Upload Image. A *Set / Edit Fields* node in
between drops the binary file unless its *Include Binary File* option is on.

Output: `filename`, `upload_file`, `dimensions: 512`, `embedding: [...]`.

### 5.3 HTTP Request: *Qdrant similarity search*

| Setting | Value |
|---|---|
| Method | `POST` |
| URL | `http://host.docker.internal:6333/collections/people_faces/points/query` |
| Send Body | on, Body Content Type `JSON`, Specify Body `Using JSON` |

JSON body (expression):

```
{
  "query": {{ JSON.stringify($json.embedding) }},
  "limit": 5,
  "with_payload": true
}
```

Output: `result.points`, 5 entries each with `score` and `payload`.

### 5.4 Code in JavaScript: *Top 5* (Run Once for All Items)

```js
const points = $input.first().json.result.points;

return points.map((p, i) => ({
  json: {
    rank: i + 1,
    person_id: p.payload.person_id,
    name: p.payload.name,
    similarity: Number(p.score.toFixed(2)),
    department: p.payload.department,
    location: p.payload.location,
    image_file: p.payload.image_file,
  },
}));
```

Output: **5 items**, which look good in the Table view for class.

### 5.5 Select rows from a table: *MySQL*

- Credential: host `mysql`, port `3306`, database `visual_demo`, your user/password.
- Operation **Select**, table `people`.
- Condition: column `person_id` **Equal** `{{ $json.person_id }}`.

Runs once per item → 5 rows with full person details.

### 5.6 Code in JavaScript1: *Build result page* (Run Once for All Items)

Shows the user's uploaded photo first, then pairs each MySQL row with its
rank/score from the *Top 5* node and builds the 5 match cards. The `<img>` URLs
point at the FastAPI `/uploads` and `/images` endpoints, so the **browser**
loads the photos (n8n itself never reads the image files).

```js
const matches = $('Code in JavaScript').all().map(i => i.json);  // rank + similarity
const people  = $input.all().map(i => i.json);                    // MySQL rows
const upload  = $('Get Embedding for Input Image').first().json;  // user's photo

const uploaded = `
  <div style="display:inline-block;padding:8px;border:2px solid #f60;
              border-radius:8px;text-align:center;font-family:sans-serif;font-size:13px">
    <b>Your photo</b><br>
    <img src="http://localhost:8001/uploads/${upload.upload_file}"
         width="160" height="160" style="object-fit:cover;border-radius:6px;margin:6px 0"><br>
    ${upload.filename}
  </div>`;

const cards = people.map((p, i) => `
  <div style="display:inline-block;width:150px;margin:8px;padding:8px;
              border:1px solid #ddd;border-radius:8px;text-align:center;
              vertical-align:top;font-family:sans-serif;font-size:13px">
    <b>#${matches[i].rank}</b> &nbsp; ${(matches[i].similarity * 100).toFixed(0)}%<br>
    <img src="http://localhost:8001/images/${p.image_file}"
         width="130" height="130" style="border-radius:6px;margin:6px 0"><br>
    <b>${p.name}</b> (${p.person_id})<br>
    ${p.age} · ${p.department}<br>${p.location}
  </div>`).join('');

const html = `
  <h2 style="font-family:sans-serif">Uploaded image</h2>
  <div>${uploaded}</div>
  <h2 style="font-family:sans-serif">Top 5 visually similar people</h2>
  <div>${cards}</div>
  <p style="font-family:sans-serif;font-size:12px;color:#666">
    Similarity measures visual resemblance between face embeddings,
    not proof of identity.
  </p>`;

return [{ json: { html } }];
```

If you rename the *Top 5* or *Get Embedding* nodes, update the `$('...')`
references to match.

### 5.7 Form: *n8n Form* (action node, not a trigger)

| Setting | Value |
|---|---|
| Page Type | `Form Ending` |
| On n8n Form Submission | `Show Text` |
| Text | `{{ $json.html }}`: switch the field to **Expression** mode (it turns green) |

---

## 6. Run the demo

1. Make sure these are running: `main.py` (step 2), Qdrant, MySQL, n8n.
2. In n8n click **Execute workflow**. The upload form opens in a new tab.
3. Choose a photo (e.g. `../synthetic_people_demo/P017.jpg`) and submit.
4. The same tab shows your uploaded photo, then the 5 match cards with rank,
   similarity %, and details.

Uploading one of the database photos returns itself as match #1 at 100%;
the rest typically score ~0.85 because the synthetic portraits share a
similar style. Try a different photo of a real (consenting) face to see
lower scores.

**Good classroom moments:**
- Open the *Get Embedding* node output: *"these 512 numbers are the image."*
- Open the Qdrant dashboard and show the 50 stored vectors and payloads.
- Show the *Top 5* table, then the MySQL lookup, then the final page:
  each specialised component does one job.

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `expects ... binary file 'Image', but none was found` | A node before the HTTP Request dropped the binary (e.g. *Edit Fields*). Connect Upload Image directly, or enable *Include Binary File*. Also happens when you press **Execute step** on a later node: re-run earlier nodes from saved data that has no file. Always test via **Execute workflow** + the form. Unpin any pinned data on Upload Image. |
| `400 No face detected` | MTCNN found no face. Use a clearer front-facing photo, or set the HTTP node's *Settings → On Error* to continue. |
| n8n can't reach `localhost:8001` / `localhost:6333` | Use `host.docker.internal` from inside n8n. |
| Connection refused on 8001 | `main.py` isn't running. |
| Qdrant `Not found: Collection people_faces` | Run `build_vector_db.py`. |
| Final page shows the literal text `{{ $json.html }}` | The Form node's Text field is in *Fixed* mode; switch it to *Expression*. |
| Cards appear but photos are broken | `main.py` not running, or the browser can't reach `localhost:8001`. If n8n strips `<img>` tags in your version, use Upload Image → *Respond When: Using 'Respond to Webhook' Node* and a **Respond to Webhook** node (Respond With: Text, body `{{ $json.html }}`, header `Content-Type: text/html`). |
| Package conflicts when installing | You installed into the repo's shared `.venv`. Use this folder's own `venv` (step 1). |
