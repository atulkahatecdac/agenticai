module.exports = {
  section: "Agentic RAG and Memory",
  slides: [
    {
      title: "04a – Agentic RAG",
      subtitle: "Search becomes a tool: the model decides whether to search, what for, and whether to search again",
      demo: "04a_agentic_rag.py",
      split: [1.2, 1],
      left: [
        { type: "code", caption: "04a_agentic_rag.py – the agent loop", size: 9, code:
"def run_agent(messages):\n    for _ in range(5):   # at most 5 rounds of tool calls\n        response = client.chat.completions.create(\n            model=MODEL, messages=messages, tools=TOOLS)\n        message = response.choices[0].message\n        if not message.tool_calls:   # this is the answer\n            return message.content\n        messages.append(message)\n        for call in message.tool_calls:\n            args = json.loads(call.function.arguments)\n            if call.function.name == \"search_documents\":\n                result = search_documents(**args)\n            else:\n                result = list_documents()\n            messages.append({\"role\": \"tool\",\n                \"tool_call_id\": call.id, \"content\": result})" },
      ],
      right: [
        { type: "compare", size: 10.5, cols: [
          { title: "Plain RAG (03a)", color: "slate", items: ["Code always searches", "Once, with the user's exact words"] },
          { title: "Agentic RAG (04a)", color: "coral", items: ["Model decides", "Writes its own query, can search again"] },
        ] },
        { type: "tiles", cols: 1, size: 10.5, items: [
          { icon: "FaMagnifyingGlass", title: "search_documents(query)", text: "The 3 nearest chunks" },
          { icon: "FaListUl", title: "list_documents()", text: "What is in the knowledge base" },
        ] },
      ],
    },
    {
      title: "04a – What the Agent Decided",
      subtitle: "The same four questions; the tool calls are printed as they happen",
      demo: "04a_agentic_rag.py",
      blocks: [
        { type: "table", size: 10.5, widths: [3.3, 2.9, 1.8], head: ["Question", "Agent calls", "Why"], rows: [
          ["Hi, good morning!", "nothing", "small talk"],
          ["What is the hotel limit in Pune?", "search(\"hotel limit Pune\")", "one fact"],
          ["I travel for work on a public holiday. What do I get, and by when must I use it?", "search(\"travel for work public holiday compensation\")  then  search(\"public holiday travel policy\")", "answer spans both PDFs"],
          ["Which documents can you answer from?", "list_documents()", "a different tool"],
        ] },
        { type: "callout", eyebrow: "This is what \"agentic\" means", text: "The program gives the model tools and a goal; the model plans the steps. Our code only runs the tools it asks for." },
      ],
    },
    {
      title: "05a – Short-Term Memory in Postgres",
      subtitle: "Save every message; send the last 10 of the same session with each new question",
      demo: "05a_memory.py first  ·  05a_memory.py second",
      split: [1.2, 1],
      left: [
        { type: "code", caption: "05a_memory.py", size: 9, code:
"CREATE TABLE messages (id SERIAL PRIMARY KEY,\n    session_id TEXT, role TEXT, content TEXT,\n    created_at TIMESTAMPTZ DEFAULT now())\n\ndef load_history(session_id):\n    rows = conn.execute(\n        \"SELECT role, content FROM messages \"\n        \"WHERE session_id = %s \"\n        \"ORDER BY id DESC LIMIT %s\",\n        (session_id, MEMORY_SIZE)).fetchall()\n    # newest first from SQL -> oldest first\n    return [{\"role\": role, \"content\": content}\n            for role, content in reversed(rows)]" },
      ],
      right: [
        { type: "code", caption: "two separate runs", code:
"$ python 05a_memory.py first\n(remembered 0 earlier messages)\nQ: How much annual leave does a\n   full-time employee get?\nA: 18 days per calendar year ...\n\n$ python 05a_memory.py second\n(remembered 2 earlier messages)\nQ: And what about interns?\nA: 1 day of leave for each month ..." },
        { type: "bullets", size: 10.5, items: [
          "**Short-term:** last 10 messages, so the prompt stays small",
          "**In the database, not in Python:** survives a restart",
        ] },
      ],
    },
  ],
};
