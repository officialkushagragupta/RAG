"""
Prompt templates and the structured-output schema for question generation.

Centralized here so RAGService/QuestionService can iterate on wording
without touching orchestration logic.
"""

# Used by RAGService to answer a question grounded in retrieved chunks.
# {context} is pre-formatted by RAGService as one block per retrieved chunk,
# each labeled with its document/section/page (see RAGService._format_context),
# so the model can ground its answer in the right document section and the
# citations returned alongside the answer make sense to the user.
RAG_ANSWER_PROMPT_TEMPLATE = """\
You are a helpful assistant answering questions about a single uploaded document. \
Answer using ONLY the information in the context below. If the answer is not \
contained in the context, say so plainly instead of guessing.

Context:
{context}

Conversation so far:
{chat_history}

Question: {question}

Write a clear, well-organized answer in Markdown (use lists, bold, or short \
paragraphs where it helps readability). Do not repeat the question back."""

# Used by QuestionService right after a document is indexed. {context} is a
# representative text sample from the document (not retrieved via similarity
# search -- there's no query yet at this point).
RECOMMENDED_QUESTIONS_PROMPT_TEMPLATE = """\
Read the following excerpt from a document and propose {recommended_questions_count} \
clear, standalone questions a reader would likely want to ask about it. Cover \
different topics/sections rather than variations on the same question. Write \
each question as it would be typed by a curious reader, not as a section title.

Document excerpt:
{context}"""

# Used by QuestionService after every answer. {context} is the same chunk text
# used to ground that answer (passed through by api.chat, not re-retrieved).
FOLLOWUP_QUESTIONS_PROMPT_TEMPLATE = """\
Given this question-and-answer exchange about a document, propose \
{followup_questions_count} natural follow-up questions the reader might ask \
next. They should build on what was just discussed, not repeat it.

Question: {question}
Answer: {answer}

Relevant document context:
{context}"""

# Gemini `response_schema` for both recommended- and follow-up-question
# generation: pass via GenerationConfig(response_mime_type="application/json",
# response_schema=SUGGESTED_QUESTIONS_RESPONSE_SCHEMA) so the SDK returns (and
# validates) a plain JSON array of strings -- no free-form-text parsing.
# `google-generativeai` accepts a plain Python type directly for this.
SUGGESTED_QUESTIONS_RESPONSE_SCHEMA = list[str]
