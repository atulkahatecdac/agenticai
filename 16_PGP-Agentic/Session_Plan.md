# PGP – Agentic AI: Session Plan

Each session lists its topics. For each topic, the table points to the slides in the
original decks and the code to demo. Paths are relative to the repo root (`c:\code\agenticai`).

**Slide decks referenced**

| Short name | Deck |
|---|---|
| MAIN | `0_slides/Agentic AI.pptx` |
| ADV | `14_advanced/Agentic AI - Advanced Engineering.pptx` |
| REAL | `15_real/Agentic AI - Real.pptx` |

Slide numbers are the deck's own slide numbers. Where a slide says "(images)", those slides are diagram-only and have no text title.
Section-marker slides (e.g. "3) LangGraph", "Module 06: …") are deliberately not referenced.

---

## Session 1 – Agentic AI Foundations and Agent Architectures

All hands-on in this session uses the **OpenAI Agents SDK** (`pip install openai-agents`), from `2_openai_agents/`.

**Topics**
1. What an AI agent is and why we need one
2. Chatbots vs workflows vs agents
3. Agent components and architecture
4. Setup and API key
5. OpenAI Agents SDK basics
6. Giving an agent tools (`@function_tool`)
7. Building a multi-tool agent step by step
8. Sync vs async agents
9. Agent design patterns: Tool use, Planning, ReAct, Reflection, ReWOO, Multi-agent
10. Agentic AI framework landscape

### 1. What an AI agent is and why we need one
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 3 | AI Agent (definition, capabilities) | `2_openai_agents/2_0_my_first_agent.py` (teaser) |
| REAL | 4 | Real World Need of AI Agents | — |
| MAIN | 10 | What is an LLM? | — |
| MAIN | 16 | Why LLMs Alone Are Not Agents | `2_openai_agents/2_1_openai_agent_basic.py` (no tools) vs `2_0_my_first_agent.py` (tools) |
| REAL | 5 | Traditional vs Generative vs Agentic AI | — |
| MAIN | 17 | The Four Pillars of Agency | — |

### 2. Chatbots vs workflows vs agents
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 12–13 | Agents, Workflows, and Chatbots; Three Core Distinctions | — |
| MAIN | 15 | Workflow vs. Agentic System | `2_openai_agents/2_0_5_openai_agent_pattern_rewoo.py` (fixed plan) vs `2_0_3_openai_agent_pattern_react.py` (adaptive) |

### 3. Agent components and architecture
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 11 | Agentic AI (foundational components) | — |
| ADV | 148 | AI Agent Elements (perceive, reason, act, observe) | `2_openai_agents/2_0_3_openai_agent_pattern_react.py` |
| ADV | 6 | Typical Agent Architecture | `2_openai_agents/2_0_my_first_agent.py` |

### 4. Setup and API key
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 8–9 | Hands-on setup (Python, VS Code, venv, `pip install openai openai-agents`); OpenAI API key in `.env` | `2_openai_agents/2_1_openai_agent_basic.py` |

### 5. OpenAI Agents SDK basics
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 33 | Basic Terms (SDK vs API) | — |
| MAIN | 56–58 | Agents API; Agents API Basics; OpenAI Agents SDK primitives | `2_openai_agents/2_1_openai_agent_basic.py` |
| MAIN | 61 | First Agent SDK Example (Sync Approach) | `2_openai_agents/2_1_openai_agent_basic.py` |

### 6. Giving an agent tools
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 18 | AI Tool System at a Glance | `2_openai_agents/2_0_1_openai_agent_pattern_tool.py` |
| MAIN | 69–71 | Function (Tool) Calling Workflow; Tool Workflow; `@function_tool` code | `2_openai_agents/2_0_1_openai_agent_pattern_tool.py` |

### 7. Building a multi-tool agent step by step
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 22 | Building an AI Agent (7-step checklist) | `2_openai_agents/2_0_my_first_agent.py` |
| MAIN | 24–31 | Building a Multi-Assistant Agent Step-by-Step (steps 1–7) | `2_openai_agents/2_0_my_first_agent.py` |

### 8. Sync vs async agents
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 59–60 | Agents API: Sync or Async?; Sample Code | `2_openai_agents/2_8_openai_agent_sync.py`, `2_9_openai_agent_async.py` |
| MAIN | 64 | Sync Versus Async Processing in Agents | `2_openai_agents/2_8_openai_agent_sync.py`, `2_9_openai_agent_async.py` |

### 9. Agent design patterns
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 65 | Tool Use Pattern | `2_openai_agents/2_0_1_openai_agent_pattern_tool.py` |
| MAIN | 66 | Four Agentic AI Patterns at a Glance (Planning, ReAct, Reflection, ReWOO) | `2_openai_agents/2_0_2_openai_agent_pattern_plan.py`, `2_0_3_openai_agent_pattern_react.py`, `2_0_4_openai_agent_pattern_reflection.py`, `2_0_5_openai_agent_pattern_rewoo.py` |
| ADV | 149 | ReAct Pattern | `2_openai_agents/2_0_3_openai_agent_pattern_react.py` |
| ADV | 150 | Plan-and-Execute Pattern | `2_openai_agents/2_0_2_openai_agent_pattern_plan.py` |
| MAIN | 67 | Multi-agent Pattern | `2_openai_agents/2_0_6_openai_agent_pattern_multi_agent.py` |
| MAIN | 68 | Task / Design Pattern / Code table (more Agents SDK demos) | `2_openai_agents/2_2_*` … `2_13_*` |

### 10. Agentic AI framework landscape
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 21 | Agentic AI Frameworks/Technologies | — |

---

## Session 2 – LangChain Core: Chains, Memory and RAG

**Topics**
1. LangChain overview and architecture
2. LCEL and Runnables
3. Prompt templates and output parsers
4. Conversation memory (session and persistent)
5. Embeddings and vector databases (Chroma, FAISS)
6. Document loaders, text splitters and chunking
7. Building a RAG pipeline with retrievers
8. Hands-on: Q&A bot over PDFs

### 1. LangChain overview and architecture
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 145–151 | LangChain Architecture; LangChain concept infographics (prompt templates, output parsers, LCEL …) | `3_langgraph/3_0_langchain_lcel.py` |
| ADV | 131 | LangChain | `3_langgraph/3_0_langchain_lcel.py` |

### 2. LCEL and Runnables
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 132–133 | LCEL, Runnable; Example: Prompt \| LLM | `3_langgraph/3_0_langchain_lcel.py`, `3_langgraph/3_0_langchain_lcel_ollama.py` |

### 3. Prompt templates and output parsers
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 134 | Output Parsers | `14_advanced/05_langchain/output_parsers.py`, `output_parsers_openai.py` |
| ADV | 135 | Prompt Templates | `14_advanced/05_langchain/prompt_templates.py`, `prompt_templates_openai.py` |

### 4. Conversation memory
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 136 | Session Memory Types | `14_advanced/05_langchain/memory_types.py` |
| ADV | 137 | Persistent Memory | `14_advanced/05_langchain/persistent_chatbot.py` |

### 5. Embeddings and vector databases
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 99–108 | (images) Why RAG; What happens in RAG; Retriever; Embeddings; Vector similarity; ChromaDB Q&A; Embedding models; Vector DB comparison | `9_general/rag/rag_1_chroma_db_basic.py`, `2_openai_agents/vector_embedding_cosine_similarity.py` |
| ADV | 109–111 | CRUD operations and metadata filtering in ChromaDB; Filtering | `14_advanced/04_rag/chromadb_crud.py`, `chromadb_search.py`, `9_general/rag/rag_4_chroma_db_adding_metadata.py` |
| ADV | 112 | FAISS | `14_advanced/04_rag/faiss_search.py`, `faiss_search_ollama.py` |
| ADV | 117 | Similarity metrics (cosine, L2, dot product) | `9_general/rag/rag_cosine_euclidean_1.py` |

### 6. Document loaders, text splitters and chunking
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 138 | Document Loaders | `14_advanced/05_langchain/document_loaders.py` |
| ADV | 139 | Text Splitters | `14_advanced/05_langchain/text_splitters.py` |
| ADV | 120–121 | RAG – Chunking; Chunking Strategies | `14_advanced/05_langchain/text_splitters.py` |

### 7. Building a RAG pipeline with retrievers
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 140 | Building a RAG pipeline | `14_advanced/05_langchain/rag_pipeline.py`, `rag_pipeline_ollama.py`, `3_langgraph/3_1_langchain_rag.py` |
| ADV | 141–142 | Retrievers; Retriever Types | `14_advanced/05_langchain/retrievers.py` |

### 8. Hands-on: Q&A bot over PDFs
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 67 | Build a Q&A Bot from PDFs | `15_real/langchain_qand_a_bot_chroma.py`, `langchain_qand_a_bot_chroma_ollama.py`, `9_general/rag/rag_10_chroma_db_data_science_pdf_chatbot.py` |

---

## Session 3 – LangChain Agents and Tool Use

**Topics**
1. Agent fundamentals (recap)
2. Prompting techniques that drive agents
3. Creating custom tools and binding them to an LLM
4. Tools with Pydantic schemas
5. AgentExecutor
6. ReAct agent
7. Plan-and-Execute agent
8. SQL database agents
9. Multi-step reasoning and tool chaining
10. Tool-augmented research agent

### 1. Agent fundamentals (recap)
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 147 | Agent Fundamentals | — |

### 2. Prompting techniques that drive agents
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 82–83 | Structuring System Prompts for Domain-Expert Personas; Template and Example | `14_advanced/03_llm_examples/prompting_techniques.py` |
| ADV | 84–86 | Zero/one/few-shot prompting; Chain-of-Thought (+ example) | `14_advanced/03_llm_examples/prompting_techniques.py` |
| ADV | 89–90 | ReAct Prompting; ReAct Example | `14_advanced/03_llm_examples/prompting_techniques.py` |

### 3. Creating custom tools and binding them to an LLM
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 151–152 | Creating Custom Tools; Tool in LangChain (`@tool`, `bind_tools`) | `14_advanced/06_langchain_agents/tool_calling.py` |

### 4. Tools with Pydantic schemas
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 153 | Tools and Pydantic | `14_advanced/06_langchain_agents/tool_calling_pydantic.py` |

### 5. AgentExecutor
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 154 | AgentExecutor (with sample run walk-through) | `14_advanced/06_langchain_agents/agent_executor_serp_gutenberg.py` |

### 6. ReAct agent
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 149 | ReAct Pattern | `14_advanced/06_langchain_agents/react_agent_web_search_python_repl.py` |

### 7. Plan-and-Execute agent
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 150 | Plan-and-Execute Pattern | `14_advanced/06_langchain_agents/plan_and_execute_agent.py` |

### 8. SQL database agents
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 155 | SQLDatabaseToolkit | `14_advanced/06_langchain_agents/sql_database_toolkit_agent.py`, `14_advanced/03_llm_examples/sales_db_agent.py` (`create_sales_db.py` first) |

### 9. Multi-step reasoning and tool chaining
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 156 | Multi-Step Reasoning | `14_advanced/06_langchain_agents/chaining_tool_outputs.py`, `chaining_tool_outputs_flask.py` |

### 10. Tool-augmented research agent
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 82 | Tool-Augmented Research Agent | `15_real/research_agent_tools.py`, `research_agent_tools_serp.py` |

---

## Session 4 – LangGraph: Stateful Workflows and Routing

**Topics**
1. Why LangGraph (LangChain vs LangGraph)
2. Core components: State, nodes, edges
3. Building the first graph
4. Reducers
5. Conditional routing
6. Message graphs
7. Streaming
8. Multi-node pipelines and LangGraph Studio

### 1. Why LangGraph
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 167–168 | Evolution of Approaches to Work with LLMs; Comparison of the Approaches | `3_langgraph/3_1_not_langgraph_langchain_instead.py` |
| REAL | 69 | LangChain versus LangGraph | `3_langgraph/3_1_not_langgraph_langchain_instead.py` |

### 2. Core components: State, nodes, edges
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 170 | LangGraph: Key Components | `14_advanced/07_langgraph/greeter_graph.py` |
| ADV | 160 | State using TypedDict | `14_advanced/07_langgraph/greeter_graph.py` |
| MAIN | 171 | TypedDict vs Pydantic BaseModel | — |

### 3. Building the first graph
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 71–74 | First LangGraph Application (walk-through) | `3_langgraph/3_1_langgraph_basic.py` |
| ADV | 161 | Building a Graph | `3_langgraph/3_1_langgraph_basic.py` |

### 4. Reducers
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 75–76 | LangGraph Reducer; Using Reducer with LLM | `15_real/langgraph_reducer_return_policy.py` |

### 5. Conditional routing
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 162 | Conditional Nodes | `14_advanced/07_langgraph/conditional_routing_specialists.py` |

### 6. Message graphs
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 163 | Message Graph | `14_advanced/07_langgraph/message_graph_bank_faq.py` |

### 7. Streaming
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 164 | Streaming | `14_advanced/07_langgraph/streaming_stock_recommendation.py` |

### 8. Multi-node pipelines and LangGraph Studio
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 165 | Visualizing and Debugging Graphs in LangGraph Studio | `14_advanced/07_langgraph/langgraph.json`, `stock_price_graph.py`, `stock_news_sentiment_graph.py` |
| MAIN | 174–178 | LangGraph Examples; (images) | `3_langgraph/3_2_langgraph_news_summarizer.py` (+ `_ollama`/`_gemini` versions), `3_2_3_langgraph_company_sector_outlook.py`, `3_3_1_langgraph_code_review_planner_agent.py` |

---

## Session 5 – LangGraph: Cycles, Human-in-the-Loop and Persistence

**Topics**
1. Cycles and loops
2. Human-in-the-loop (HITL)
3. Checkpointers and persistence
4. State schema design
5. Subgraphs
6. Guardrails in LangGraph
7. End-to-end: stateful banking chatbot

### 1. Cycles and loops
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 179 | Looping in LangGraph | `3_langgraph/3_12_langgraph_looping_agents.py.py` |
| ADV | 168 | Creating Loops in LangGraph | `3_langgraph/3_3_0_langgraph_code_review.py`, `14_advanced/08_langgraph_cycles_HIL_persistence/order_processing_state_machine.py` |

### 2. Human-in-the-loop (HITL)
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 169–170 | Human In the Loop (HIL) | `14_advanced/08_langgraph_cycles_HIL_persistence/human_approval_gate.py` |
| REAL | 102–103 | Human In The Loop (HITL) UX; Code Example | `15_real/support_ticketing_agent_hitl.py` |

### 3. Checkpointers and persistence
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 79 | Checkpointers | `3_langgraph/3_4_langgraph_memory.py`, `14_advanced/08_langgraph_cycles_HIL_persistence/sqlite_checkpointing_crash_recovery.py` |

### 4. State schema design
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 98–99 | State Schema Design; Example of State Schema | `15_real/langgraph_reducer_return_policy.py` |

### 5. Subgraphs
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 172 | Subgraphs | `14_advanced/08_langgraph_cycles_HIL_persistence/simple_subgraph_example.py` |

### 6. Guardrails in LangGraph
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 80 | Guardrails | `3_langgraph/3_10_1_langgraph_create_guardrails.py`, `3_10_2_langgraph_test_guardrails_flask.py`, `3_10_3_langgraph_guardrails_bank_flask.py` |

### 7. End-to-end: stateful banking chatbot
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| — | — | `12_project/12_2_banking_chatbot/Banking-Agentic-AI.pptx` (project deck) | `3_langgraph/3_5_langgraph_bank_chromadb_flask_chatbot.py`, `3_9_langgraph_bank_ntfy_email_flask.py`, `3_11_langgraph_STM_RAG_chatbot.py` |

---

## Session 6 – Multi-Agent Orchestration with CrewAI

**Topics**
1. CrewAI concepts: agents, tasks, crews, process
2. Building crews for real tasks
3. Crew vs Flow, and conditional routing
4. Hierarchical crews and manager agents
5. Human-in-the-loop and controlled autonomy
6. Memory and knowledge
7. Structured outputs and agent-to-agent communication
8. Guardrails, error handling and reliability
9. Observability for crews
10. End-to-end crew application

### 1. CrewAI concepts
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 181–182 | What is CrewAI?; Sample CrewAI Usage | `14_advanced/13_crew_ai/13_1_crewai_basics.py` |
| ADV | 219 | CrewAI | `14_advanced/13_crew_ai/13_1_crewai_basics.py` |

### 2. Building crews for real tasks
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 183–184 | CrewAI Examples; (image) | `4_crewai/4_1_crewai_document_generator.py`, `4_2_crewai_log_analyzer.py`, `4_4_crewai_cloud_bill.py`, `4_6_crewai_stock_analysis_flask.py` |

### 3. Crew vs Flow, and conditional routing
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 220–224 | Crew and Flow; Crew vs Flow; Flow Building Blocks; Conditional Routing; How to Develop a Flow | `14_advanced/13_crew_ai/13_2_crew_vs_flow.py` |

### 4. Hierarchical crews and manager agents
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 225 | Hierarchical Crews and Manager Agents | `14_advanced/13_crew_ai/13_3_hierarchical_crew.py` |

### 5. Human-in-the-loop and controlled autonomy
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 226 | Human In The Loop (HITL) and Controlled Autonomy | `14_advanced/13_crew_ai/13_4_human_in_the_loop.py` |

### 6. Memory and knowledge
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 227 | Memory and Knowledge | `14_advanced/13_crew_ai/13_5_memory_and_knowledge.py`, `4_crewai/4_3_crewai_With_Memory.py` vs `4_3_crewai_Without_Memory.py` |

### 7. Structured outputs and agent-to-agent communication
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 228 | Structured Outputs and Pydantic + Reliable Agent Communication | `14_advanced/13_crew_ai/13_6_structured_outputs.py` |

### 8. Guardrails, error handling and reliability
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 229 | Guardrails, Error Handling and Reliability | `14_advanced/13_crew_ai/13_7_guardrails_and_reliability.py` |

### 9. Observability for crews
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 185 | Adding Observability Using LangSmith | `4_crewai/4_5_crewai_observability.py` |

### 10. End-to-end crew application
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| — | — | (no dedicated slide) Customer-service crew with embeddings + Flask UI | `4_crewai/4_before_7_crewai_create_embeddings_customer_tickets.py`, then `4_7_crewai_customer_service_flask.py` |

---

## Session 7 – Multi-Agent Systems with Microsoft AutoGen

**Topics**
1. AutoGen overview
2. AssistantAgent and tools
3. Synchronous vs asynchronous agents
4. Structured output
5. Multimodal messages
6. Teams / group chats: round-robin, selector, magentic
7. GraphFlow (including parallel join)
8. Memory

### 1. AutoGen overview
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 187–188 | AutoGen; Details / Code table | `5_autogen/5_1_autogen_basic.py` |

### 2. AssistantAgent and tools
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 189–190 | AssistantAgent; Step / Component / What Happens table | `5_autogen/5_2_autogen_forex_api.py`, `5_3_autogen_forex_api_text_message.py` |

### 3. Synchronous vs asynchronous agents
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 191 | Synchronous Versus Asynchronous Agents | `5_autogen/5_5_autogen_synchronous_agents.py`, `5_6_autogen_asynchronous_agents.py` |

### 4. Structured output
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 192 | Structured Output | `5_autogen/5_7_autogen_structured_output.py` |

### 5. Multimodal messages
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| — | — | (no dedicated slide) | `5_autogen/5_4_autogen_multimodal_message.py` |

### 6. Teams / group chats
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 193 | Teams | `5_autogen/5_8_autogen_round_robin_group_chat.py`, `5_9_autogen_selector_group_chat.py`, `5_10_autogen_magentic_group_chat.py`, `5_11_autogen_recession_claim.py` |

### 7. GraphFlow
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 194 | AutoGen GraphFlow (Similar to LangGraph) | `5_autogen/5_12_autogen_graphflow.py`, `5_13_autogen_graphflow_parallel_join.py` |

### 8. Memory
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| MAIN | 195 | Memory | `5_autogen/5_14_autogen_memory.py` |

---

## Session 8 – Agentic RAG and GraphRAG for Agents

**Topics**
1. RAG failure modes and advanced approaches
2. Traditional RAG vs agentic RAG
3. Retrieval + reasoning
4. Self-RAG
5. Corrective RAG (CRAG)
6. Re-ranking retrieved chunks
7. Hybrid search
8. GraphRAG
9. Multi-hop reasoning
10. Evaluating RAG with RAGAS

### 1. RAG failure modes and advanced approaches
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 231–233 | RAG Failure Modes; Various Approaches for Advanced RAG; (image) | `3_langgraph/3_1_rag_hallucination_eval.py` |

### 2. Traditional RAG vs agentic RAG
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 85–86 | Traditional vs Agentic RAG; (image) | `15_real/traditional_vs_agentic_rag.py`, `traditional_vs_agentic_rag_serp.py`, `2_openai_agents/2_11_openai_agent_traditional_rag.py` vs `2_11_openai_agent_agentic_rag.py` |
| REAL | 87 | Common Adaptive Strategies | `15_real/adaptive_retrieval_strategies.py`, `adaptive_retrieval_strategies_serp.py` |

### 3. Retrieval + reasoning
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 89–90 | Retrieval + Reasoning; Example | `15_real/loan_eligibility_rag_reasoning.py` |

### 4. Self-RAG
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 242 | Self-RAG | `14_advanced/14_agentic_rag_graph_rag/14_2_self_rag.py` |

### 5. Corrective RAG (CRAG)
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 243 | Corrective RAG (CRAG) | `14_advanced/14_agentic_rag_graph_rag/14_3_corrective_rag.py` |

### 6. Re-ranking retrieved chunks
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 244 | Re-ranking with Cohere and Cross-encoder Models | `14_advanced/14_agentic_rag_graph_rag/14_4_cohere_reranking.py` |

### 7. Hybrid search
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 124 | Hybrid Search | `14_advanced/04_rag/hybrid_search.py` |
| ADV | 249 | Hybrid Search (agentic RAG) | `14_advanced/14_agentic_rag_graph_rag/14_9_hybrid_search.py` |

### 8. GraphRAG
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 247 | GraphRAG | `14_advanced/14_agentic_rag_graph_rag/14_7_graph_rag.py` |

### 9. Multi-hop reasoning
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 248 | Multi-Hop Reasoning | `14_advanced/14_agentic_rag_graph_rag/14_8_multi_hop_reasoning.py` |

### 10. Evaluating RAG with RAGAS
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 234–241 | RAGAS; Metrics; Faithfulness; Answer Relevance; Context Precision; Context Recall | `14_advanced/14_agentic_rag_graph_rag/14_1_ragas_evaluation.py`, `15_real/ragas_evaluation.py` |

---

## Session 9 – Deep Agents: Reflection, Planning and Long-Term Memory

**Topics**
1. What makes an agent "deep"
2. Self-reflection loops
3. Multi-turn reflection with a quality threshold
4. Plan-and-Execute
5. Replanning
6. ReAct vs Plan-and-Execute
7. Long-term memory types
8. Episodic memory
9. Memory consolidation
10. Context propagation and trimming
11. Self-improvement from failures
12. Unified architecture: reflection + planning + memory

### 1. What makes an agent "deep"
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 206 | What Makes an Agent 'Deep' | — |

### 2. Self-reflection loops
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 207 | Self-reflection Loops | `2_openai_agents/2_0_4_openai_agent_pattern_reflection.py` |

### 3. Multi-turn reflection with a quality threshold
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 208 | Multi-Turn Reflection | `14_advanced/12_deep_agents/meal_plan_reflection.py` |

### 4. Plan-and-Execute
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 209 | Plan-and-Execute | `14_advanced/12_deep_agents/study_plan_plan_execute.py` |

### 5. Replanning
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 210 | Replanning | `14_advanced/12_deep_agents/pathology_report_replanning.py` |

### 6. ReAct vs Plan-and-Execute
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 211 | ReAct Versus Plan-and-Execute | `2_openai_agents/2_0_3_openai_agent_pattern_react.py` vs `2_0_2_openai_agent_pattern_plan.py` |

### 7. Long-term memory types
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 96–97 | Memory Types; Memory Examples | `15_real/agent_memory_short_term_langgraph.py`, `agent_memory_short_to_long_term_langgraph.py`, `agent_memory_short_to_external_sqlite_langgraph.py` |
| ADV | 212 | Long Term Memory Types | `15_real/agent_memory_semantic_langgraph.py`, `agent_memory_procedural_langgraph.py` |

### 8. Episodic memory
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 213 | Episodic Memory | `14_advanced/12_deep_agents/episodic_memory_store.py`, `15_real/agent_memory_episodic_langgraph.py` |

### 9. Memory consolidation
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 214 | Memory Consolidation | `14_advanced/12_deep_agents/memory_consolidation.py` |

### 10. Context propagation and trimming
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| REAL | 100–101 | Context Propagation and Trim Strategies; Context Trimming Strategies | `15_real/context_management_strategies.py` |

### 11. Self-improvement from failures
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 216 | Agent Self-Improvement Using Semantic Self-Generation from Failures | `14_advanced/12_deep_agents/self_improving_agent.py` |

### 12. Unified architecture: reflection + planning + memory
| Deck | Slides | Slide content | Code example |
|---|---|---|---|
| ADV | 217 | Combining Reflection, Planning, and Memory into One Unified Agent Architecture | `15_real/personal_memory_assistant.py` |
