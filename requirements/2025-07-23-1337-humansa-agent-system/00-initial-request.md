# Initial Request - Humansa Agent System

## Date: 2025-07-23

## Original Request:
Please investigate the agent, we need to really, right now it's more about how we should build our agent to support the API that I've requested and the features to store users' memory.

Please set up a Humana environment, test environment on port 5003 with a new database, with new mock medical record base, and new table, mock table for user, not mock table, more like come up with your own design of a user ID table that the server would have access to, and the endpoints to access them for mocking purpose.

So we can start iterating our multi-agent process to support booking appointments and things like that. So we can determine how we should do the appointment flow, how we should do the rag flow, and the other one by improving the technology behind response API.

So we can start iterating our new response API of agent v2, so we can test out the second version of our Humana endpoint. Plan ahead. I'm thinking of building a new rag processor for different files and contents with router, using llama index's most advanced techniques, from one of their article you can search it up online, and build a multi-agent workflow with an orchestrator pattern, with an orchestrator agent and sub-agent to determine specific tasks, such as how to promote their product, how to find the right doctor, how to do this and that, and the parent agent, and also how to determine the context window of a conversation, where it should be stored for the user, its relationship in between them.

Those are the kind of things we need to plan out the Humana agent.

## Key Requirements Identified:
1. Multi-agent system for medical platform
2. Test environment on port 5003
3. Medical records database design
4. User memory storage system
5. Appointment booking workflow
6. Advanced RAG processor with router
7. Orchestrator pattern for agents
8. Context window management
9. API v2 design
10. Integration with existing Humansa requirements