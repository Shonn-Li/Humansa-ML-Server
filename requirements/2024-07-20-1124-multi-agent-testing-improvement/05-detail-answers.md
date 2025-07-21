# Expert Phase Answers

## Q1: Should the testing system create isolated instances of the IterativeOrchestrator for each test to prevent state pollution between concurrent requests (addressing the shared iteration_count issue found in multi_agent_endpoint_v2.py)?
**Answer: YES**

## Q2: Should the testing system validate that every streaming event with a "start" type (like response.output_item.added) has a corresponding "completion" event (like response.output_item.done) to ensure proper event lifecycle?
**Answer: YES - It needs to follow the OpenAI RESPONSE API standard. If you don't remember, go look at the doc later.**

## Q3: Should the testing system implement deterministic mock responses for LLM calls during automated testing to ensure consistent test results (while still having separate tests with real LLM calls)?
**Answer: NO - Deterministic should be a fallback. Always use the LLM first to see if the accuracy works or not. Do maybe test approach in like a 3 attempt where if it doesn't trigger from 3 attempts there might be some issue with the code. and use gpt 4.o-mini**

## Q4: Should the testing system include specific timeout handling tests for each agent (testing behavior when RAG/Web/Attachment agents timeout) with configurable timeout values?
**Answer: YES**

## Q5: Should the testing system automatically generate edge case scenarios based on the code analysis (like empty results, malformed inputs, partial failures) rather than requiring manual test case creation?
**Answer: YES**