# PGP Agentic AI: code by session

Every demo used in `PGP_Agentic_AI.pptx` / `Session_Plan.md`, copied out of the course folders into one folder per
session and numbered `<session>_<sequence>_<name>.py` in the order the session uses them.

- Run scripts from anywhere, e.g. `python 16_PGP-Agentic/code/session_4/4_1_langgraph_basic.py`. API keys still come from the
  repo-root `.env` (`load_dotenv()` searches up the folder tree), and the repo-root `requirements.txt` applies.
- Input data (CSV/JSON/PDF/images) sits next to the scripts that read it. Vector stores, SQLite files and graph PNGs are
  created next to the scripts on first run.
- Two large inputs are not copied and are read from their original folders: `9_general/rag/Principles-of-Data-Science.pdf`
  (session 2) and `4_crewai/customer_tickets.csv` (session 6).
- These are copies. The originals stay where they were, because the other course decks still point at them.

## Session 1: Agentic AI Foundations and Agent Architectures

| File | Copied from |
|---|---|
| `session_1/1_1_my_first_agent.py` | `2_openai_agents/2_0_my_first_agent.py` |
| `session_1/1_2_openai_agent_basic.py` | `2_openai_agents/2_1_openai_agent_basic.py` |
| `session_1/1_3_openai_agent_pattern_rewoo.py` | `2_openai_agents/2_0_5_openai_agent_pattern_rewoo.py` |
| `session_1/1_4_openai_agent_pattern_react.py` | `2_openai_agents/2_0_3_openai_agent_pattern_react.py` |
| `session_1/1_5_openai_basic.py` | `C:\code\agenticai_realpage\module_1\1_openai_basic.py` (separate repo) |
| `session_1/1_6_openai_agent_pattern_tool.py` | `2_openai_agents/2_0_1_openai_agent_pattern_tool.py` |
| `session_1/1_7_openai_agent_sync.py` | `2_openai_agents/2_8_openai_agent_sync.py` |
| `session_1/1_8_openai_agent_async.py` | `2_openai_agents/2_9_openai_agent_async.py` |
| `session_1/1_9_openai_agent_pattern_plan.py` | `2_openai_agents/2_0_2_openai_agent_pattern_plan.py` |
| `session_1/1_10_openai_agent_pattern_reflection.py` | `2_openai_agents/2_0_4_openai_agent_pattern_reflection.py` |
| `session_1/1_11_openai_agent_pattern_multi_agent.py` | `2_openai_agents/2_0_6_openai_agent_pattern_multi_agent.py` |
| `session_1/1_12_openai_agent_tool_hardcoded_knowledge.py` | `2_openai_agents/2_2_openai_agent_tool_hardcoded_knowledge.py` |
| `session_1/1_13_openai_agent_hardcoded_semantic.py` | `2_openai_agents/2_3_openai_agent_hardcoded_semantic.py` |
| `session_1/1_14_openai_agent_openai_vectorstore.py` | `2_openai_agents/2_4_openai_agent_openai_vectorstore.py` |
| `session_1/1_15_openai_agent_create_faq_db.py` | `2_openai_agents/2_openai_agent_create_faq_db.py` |
| `session_1/1_16_openai_agent_faq_db_vectorized.py` | `2_openai_agents/2_5_openai_agent_faq_db_vectorized.py` |
| `session_1/1_17_openai_agent_flask.py` | `2_openai_agents/2_6_openai_agent_flask.py` |
| `session_1/1_18_openai_agent_insurance_flask.py` | `2_openai_agents/2_7_openai_agent_insurance_flask.py` |
| `session_1/1_19_openai_agent_guardrails.py` | `2_openai_agents/2_10_openai_agent_guardrails.py` |
| `session_1/1_20_openai_agent_traditional_rag.py` | `2_openai_agents/2_11_openai_agent_traditional_rag.py` |
| `session_1/1_21_openai_agent_agentic_rag.py` | `2_openai_agents/2_11_openai_agent_agentic_rag.py` |
| `session_1/1_22_openai_agent_agent_as_tool.py` | `2_openai_agents/2_12_openai_agent_agent_as_tool.py` |
| `session_1/1_23_openai_agent_short_term_memory.py` | `2_openai_agents/2_13_openai_agent_short_term_memory.py` |

## Session 2: LangChain Core: Chains, Memory and RAG

| File | Copied from |
|---|---|
| `session_2/2_1_langchain_lcel.py` | `3_langgraph/3_0_langchain_lcel.py` |
| `session_2/2_2_langchain_lcel_ollama.py` | `3_langgraph/3_0_langchain_lcel_ollama.py` |
| `session_2/2_3_prompt_templates.py` | `14_advanced/05_langchain/prompt_templates.py` |
| `session_2/2_4_output_parsers.py` | `14_advanced/05_langchain/output_parsers.py` |
| `session_2/2_5_memory_types.py` | `14_advanced/05_langchain/memory_types.py` |
| `session_2/2_6_persistent_chatbot.py` | `14_advanced/05_langchain/persistent_chatbot.py` |
| `session_2/2_7_chroma_db_basic.py` | `9_general/rag/rag_1_chroma_db_basic.py` |
| `session_2/2_8_rag_cosine_euclidean.py` | `9_general/rag/rag_cosine_euclidean_1.py` |
| `session_2/2_9_chroma_db_adding_metadata.py` | `9_general/rag/rag_4_chroma_db_adding_metadata.py` |
| `session_2/2_10_faiss_search.py` | `14_advanced/04_rag/faiss_search.py` |
| `session_2/2_11_document_loaders.py` | `14_advanced/05_langchain/document_loaders.py` |
| `session_2/2_12_text_splitters.py` | `14_advanced/05_langchain/text_splitters.py` |
| `session_2/2_13_rag_pipeline.py` | `14_advanced/05_langchain/rag_pipeline.py` |
| `session_2/2_14_retrievers.py` | `14_advanced/05_langchain/retrievers.py` |
| `session_2/2_15_langchain_qand_a_bot_chroma.py` | `15_real/langchain_qand_a_bot_chroma.py` |
| `session_2/2_16_langchain_qanda_bot_faiss.py` | `C:\code\agenticai_realpage\module_2\2_langchain_qanda_bot_faiss.py` (separate repo) |

## Session 3: LangChain Agents and Tool Use

Run `3_4_create_sales_db.py` first: it creates the `sales.db` that `3_5` and `3_6` query.

| File | Copied from |
|---|---|
| `session_3/3_1_prompting_techniques.py` | `14_advanced/03_llm_examples/prompting_techniques.py` |
| `session_3/3_2_tool_calling.py` | `14_advanced/06_langchain_agents/tool_calling.py` |
| `session_3/3_3_tool_calling_pydantic.py` | `14_advanced/06_langchain_agents/tool_calling_pydantic.py` |
| `session_3/3_4_create_sales_db.py` | `14_advanced/03_llm_examples/create_sales_db.py` |
| `session_3/3_5_sql_database_toolkit_agent.py` | `14_advanced/06_langchain_agents/sql_database_toolkit_agent.py` |
| `session_3/3_6_sales_db_agent.py` | `14_advanced/03_llm_examples/sales_db_agent.py` |
| `session_3/3_7_chaining_tool_outputs.py` | `14_advanced/06_langchain_agents/chaining_tool_outputs.py` |
| `session_3/3_8_chaining_tool_outputs_flask.py` | `14_advanced/06_langchain_agents/chaining_tool_outputs_flask.py` |
| `session_3/3_9_research_agent_tools.py` | `15_real/research_agent_tools.py` |
| `session_3/3_10_research_agent_tools_serp.py` | `15_real/research_agent_tools_serp.py` |

## Session 4: LangGraph: Stateful Workflows and Routing

`langgraph.json` is the LangGraph Studio config for `4_5_stock_news_sentiment_graph.py` (run `langgraph dev` from this folder).

| File | Copied from |
|---|---|
| `session_4/4_1_langgraph_basic.py` | `3_langgraph/3_1_langgraph_basic.py` |
| `session_4/4_2_greeter_graph.py` | `14_advanced/07_langgraph/greeter_graph.py` |
| `session_4/4_3_streaming_stock_recommendation.py` | `14_advanced/07_langgraph/streaming_stock_recommendation.py` |
| `session_4/langgraph.json` | `14_advanced/07_langgraph/langgraph.json` |
| `session_4/4_4_stock_price_graph.py` | `14_advanced/07_langgraph/stock_price_graph.py` |
| `session_4/4_5_stock_news_sentiment_graph.py` | `14_advanced/07_langgraph/stock_news_sentiment_graph.py` |
| `session_4/4_6_langgraph_news_summarizer.py` | `3_langgraph/3_2_langgraph_news_summarizer.py` |
| `session_4/4_7_langgraph_news_summarizer_ollama_version.py` | `3_langgraph/3_2_1_langgraph_news_summarizer_ollama_version.py` |
| `session_4/4_8_langgraph_news_summarizer_gemini_version.py` | `3_langgraph/3_2_2_langgraph_news_summarizer_gemini_version.py` |
| `session_4/4_9_langgraph_company_sector_outlook.py` | `3_langgraph/3_2_3_langgraph_company_sector_outlook.py` |
| `session_4/4_10_langgraph_code_review_planner_agent.py` | `3_langgraph/3_3_1_langgraph_code_review_planner_agent.py` |

## Session 5: LangGraph: Cycles, Human-in-the-Loop and Persistence

`5_9_langgraph_guardrails_bank_flask.py` reads the `banking_faqs` collection built by `5_7` and the `guardrail_chromadb` store built by `5_8`; run those first.

| File | Copied from |
|---|---|
| `session_5/5_1_langgraph_looping_agents.py` | `3_langgraph/3_12_langgraph_looping_agents.py.py` |
| `session_5/5_2_order_processing_state_machine.py` | `14_advanced/08_langgraph_cycles_HIL_persistence/order_processing_state_machine.py` |
| `session_5/5_3_human_approval_gate.py` | `14_advanced/08_langgraph_cycles_HIL_persistence/human_approval_gate.py` |
| `session_5/5_4_langgraph_memory.py` | `3_langgraph/3_4_langgraph_memory.py` |
| `session_5/5_5_sqlite_checkpointing_crash_recovery.py` | `14_advanced/08_langgraph_cycles_HIL_persistence/sqlite_checkpointing_crash_recovery.py` |
| `session_5/5_6_medical_diagnosis_subgraphs.py` | `14_advanced/08_langgraph_cycles_HIL_persistence/medical_diagnosis_subgraphs.py` |
| `session_5/5_7_langgraph_bank_ntfy_email_flask.py` | `3_langgraph/3_9_langgraph_bank_ntfy_email_flask.py` |
| `session_5/5_8_langgraph_create_guardrails.py` | `3_langgraph/3_10_1_langgraph_create_guardrails.py` |
| `session_5/5_9_langgraph_guardrails_bank_flask.py` | `3_langgraph/3_10_3_langgraph_guardrails_bank_flask.py` |
| `session_5/5_10_langgraph_STM_RAG_chatbot.py` | `3_langgraph/3_11_langgraph_STM_RAG_chatbot.py` |

## Session 6: Multi-Agent Orchestration with CrewAI

Run `6_15_crewai_create_embeddings_customer_tickets.py` before `6_16_crewai_customer_service_flask.py`.

| File | Copied from |
|---|---|
| `session_6/6_1_crewai_basics.py` | `14_advanced/13_crew_ai/13_1_crewai_basics.py` |
| `session_6/6_2_crewai_document_generator.py` | `4_crewai/4_1_crewai_document_generator.py` |
| `session_6/6_3_crewai_log_analyzer.py` | `4_crewai/4_2_crewai_log_analyzer.py` |
| `session_6/6_4_crewai_cloud_bill.py` | `4_crewai/4_4_crewai_cloud_bill.py` |
| `session_6/6_5_crewai_stock_analysis_flask.py` | `4_crewai/4_6_crewai_stock_analysis_flask.py` |
| `session_6/6_6_crew_vs_flow.py` | `14_advanced/13_crew_ai/13_2_crew_vs_flow.py` |
| `session_6/6_7_hierarchical_crew.py` | `14_advanced/13_crew_ai/13_3_hierarchical_crew.py` |
| `session_6/6_8_human_in_the_loop.py` | `14_advanced/13_crew_ai/13_4_human_in_the_loop.py` |
| `session_6/6_9_memory_and_knowledge.py` | `14_advanced/13_crew_ai/13_5_memory_and_knowledge.py` |
| `session_6/6_10_crewai_With_Memory.py` | `4_crewai/4_3_crewai_With_Memory.py` |
| `session_6/6_11_crewai_Without_Memory.py` | `4_crewai/4_3_crewai_Without_Memory.py` |
| `session_6/6_12_structured_outputs.py` | `14_advanced/13_crew_ai/13_6_structured_outputs.py` |
| `session_6/6_13_guardrails_and_reliability.py` | `14_advanced/13_crew_ai/13_7_guardrails_and_reliability.py` |
| `session_6/6_14_crewai_observability.py` | `4_crewai/4_5_crewai_observability.py` |
| `session_6/6_15_crewai_create_embeddings_customer_tickets.py` | `4_crewai/4_before_7_crewai_create_embeddings_customer_tickets.py` |
| `session_6/6_16_crewai_customer_service_flask.py` | `4_crewai/4_7_crewai_customer_service_flask.py` |

## Session 7: Multi-Agent Systems with Microsoft AutoGen

| File | Copied from |
|---|---|
| `session_7/7_1_autogen_basic.py` | `5_autogen/5_1_autogen_basic.py` |
| `session_7/7_2_autogen_forex_api.py` | `5_autogen/5_2_autogen_forex_api.py` |
| `session_7/7_3_autogen_forex_api_text_message.py` | `5_autogen/5_3_autogen_forex_api_text_message.py` |
| `session_7/7_4_autogen_synchronous_agents.py` | `5_autogen/5_5_autogen_synchronous_agents.py` |
| `session_7/7_5_autogen_asynchronous_agents.py` | `5_autogen/5_6_autogen_asynchronous_agents.py` |
| `session_7/7_6_autogen_structured_output.py` | `5_autogen/5_7_autogen_structured_output.py` |
| `session_7/7_7_autogen_multimodal_message.py` | `5_autogen/5_4_autogen_multimodal_message.py` |
| `session_7/7_8_autogen_round_robin_group_chat.py` | `5_autogen/5_8_autogen_round_robin_group_chat.py` |
| `session_7/7_9_autogen_selector_group_chat.py` | `5_autogen/5_9_autogen_selector_group_chat.py` |
| `session_7/7_10_autogen_magentic_group_chat.py` | `5_autogen/5_10_autogen_magentic_group_chat.py` |
| `session_7/7_11_autogen_recession_claim.py` | `5_autogen/5_11_autogen_recession_claim.py` |
| `session_7/7_12_autogen_graphflow.py` | `5_autogen/5_12_autogen_graphflow.py` |
| `session_7/7_13_autogen_graphflow_parallel_join.py` | `5_autogen/5_13_autogen_graphflow_parallel_join.py` |
| `session_7/7_14_autogen_memory.py` | `5_autogen/5_14_autogen_memory.py` |

## Session 8: Agentic RAG and GraphRAG for Agents

`8_2_support_ticketing_agent_hitl.py` is also imported by `8_3`, `8_4`, `8_7` and `8_8` for its FAQ vector search.

| File | Copied from |
|---|---|
| `session_8/8_1_rag_hallucination_eval.py` | `3_langgraph/3_1_rag_hallucination_eval.py` |
| `session_8/8_2_support_ticketing_agent_hitl.py` | `15_real/support_ticketing_agent_hitl.py` |
| `session_8/8_3_traditional_vs_agentic_rag.py` | `15_real/traditional_vs_agentic_rag.py` |
| `session_8/8_4_traditional_vs_agentic_rag_serp.py` | `15_real/traditional_vs_agentic_rag_serp.py` |
| `session_8/8_5_openai_agent_traditional_rag.py` | `2_openai_agents/2_11_openai_agent_traditional_rag.py` |
| `session_8/8_6_openai_agent_agentic_rag.py` | `2_openai_agents/2_11_openai_agent_agentic_rag.py` |
| `session_8/8_7_adaptive_retrieval_strategies.py` | `15_real/adaptive_retrieval_strategies.py` |
| `session_8/8_8_adaptive_retrieval_strategies_serp.py` | `15_real/adaptive_retrieval_strategies_serp.py` |
| `session_8/8_9_loan_eligibility_rag_reasoning.py` | `15_real/loan_eligibility_rag_reasoning.py` |
| `session_8/8_10_cohere_rag_pipeline.py` | `15_real/cohere_rag_pipeline.py` |
| `session_8/8_11_self_rag.py` | `14_advanced/14_agentic_rag_graph_rag/14_2_self_rag.py` |
| `session_8/8_12_corrective_rag.py` | `14_advanced/14_agentic_rag_graph_rag/14_3_corrective_rag.py` |
| `session_8/8_13_cohere_reranking.py` | `14_advanced/14_agentic_rag_graph_rag/14_4_cohere_reranking.py` |
| `session_8/8_14_hybrid_search.py` | `14_advanced/04_rag/hybrid_search.py` |
| `session_8/8_15_agentic_hybrid_search.py` | `14_advanced/14_agentic_rag_graph_rag/14_9_hybrid_search.py` |
| `session_8/8_16_graph_rag.py` | `14_advanced/14_agentic_rag_graph_rag/14_7_graph_rag.py` |
| `session_8/8_17_multi_hop_reasoning.py` | `14_advanced/14_agentic_rag_graph_rag/14_8_multi_hop_reasoning.py` |
| `session_8/8_18_ragas_evaluation.py` | `14_advanced/14_agentic_rag_graph_rag/14_1_ragas_evaluation.py` |
| `session_8/8_19_ragas_evaluation_customer_support.py` | `15_real/ragas_evaluation.py` |

## Session 9: Deep Agents: Reflection, Planning and Long-Term Memory

| File | Copied from |
|---|---|
| `session_9/9_1_openai_agent_pattern_reflection.py` | `2_openai_agents/2_0_4_openai_agent_pattern_reflection.py` |
| `session_9/9_2_meal_plan_reflection.py` | `14_advanced/12_deep_agents/meal_plan_reflection.py` |
| `session_9/9_3_study_plan_plan_execute.py` | `14_advanced/12_deep_agents/study_plan_plan_execute.py` |
| `session_9/9_4_pathology_report_replanning.py` | `14_advanced/12_deep_agents/pathology_report_replanning.py` |
| `session_9/9_5_agent_memory_short_term_langgraph.py` | `15_real/agent_memory_short_term_langgraph.py` |
| `session_9/9_6_agent_memory_dynamic_session_id_langgraph.py` | `15_real/agent_memory_dynamic_session_id_langgraph.py` |
| `session_9/9_7_agent_memory_short_to_long_term_langgraph.py` | `15_real/agent_memory_short_to_long_term_langgraph.py` |
| `session_9/9_8_agent_memory_short_to_external_sqlite_langgraph.py` | `15_real/agent_memory_short_to_external_sqlite_langgraph.py` |
| `session_9/9_9_agent_memory_semantic_langgraph.py` | `15_real/agent_memory_semantic_langgraph.py` |
| `session_9/9_10_agent_memory_procedural_langgraph.py` | `15_real/agent_memory_procedural_langgraph.py` |
| `session_9/9_11_episodic_memory_store.py` | `14_advanced/12_deep_agents/episodic_memory_store.py` |
| `session_9/9_12_agent_memory_episodic_langgraph.py` | `15_real/agent_memory_episodic_langgraph.py` |
| `session_9/9_13_memory_consolidation.py` | `14_advanced/12_deep_agents/memory_consolidation.py` |
| `session_9/9_14_context_management_strategies.py` | `15_real/context_management_strategies.py` |
| `session_9/9_15_self_improving_agent.py` | `14_advanced/12_deep_agents/self_improving_agent.py` |
| `session_9/9_16_personal_memory_assistant.py` | `15_real/personal_memory_assistant.py` |
