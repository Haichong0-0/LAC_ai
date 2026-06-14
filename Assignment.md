THE ASSIGNMENT

Build a small retrieval and reasoning system that:

1. Ingests a corpus of approximately 50 to 100 short documents. Use any public dataset of your choosing (Wikipedia abstracts, ArXiv abstracts, news articles, product reviews, your call).
2. Embeds the corpus with a vector model of your choice.
3. Implements a semantic search layer that returns the top K relevant documents for a query.
4. Wraps retrieval with an LLM call to answer a natural language question over the corpus (basic RAG).
5. Exposes either an HTTP API or a CLI to query the system.

Stack of your choice. We use Python, FastAPI, PostgreSQL with pgvector, and Claude internally. Build with what you know best. Given your EY ChromaDB and HackLondon LangChain background, this should be familiar ground.

DELIVERABLES

A public GitHub repository containing:

- Working code that runs locally with clear setup instructions
- A README explaining your design choices, what you would improve with more time, and the tradeoffs you made
- A short evaluation: pick 3 to 5 test queries, measure retrieval quality with a metric of your choice, write 2 to 3 sentences on what the evaluation tells you