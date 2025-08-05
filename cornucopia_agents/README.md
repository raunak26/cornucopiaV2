# cornucopia_agents/

This folder contains all modular agent definitions for the CornucopiaV2 lab automation pipeline, built on the OpenAI Agents SDK.

## Agents
- **PromptCreatorAgent**: Clarifies user intent and produces structured prompts.
- **ProtocolGeneratorAgent**: Generates Opentrons protocol code from structured prompts.
- **QCAgent**: Simulates protocols and extracts errors using `opentrons_simulate`.
- **runner.py**: Orchestrates agent execution and pipeline flow.

## Usage in Pipeline
1. User input is clarified by PromptCreatorAgent.
2. ProtocolGeneratorAgent generates Python code for Opentrons Flex.
3. QCAgent simulates the code and provides QC feedback.

All agents are designed to be composable and can be called via the OpenAI Agents SDK `Runner` interface.
