# AI-Powered Legal Assistance Platform

An AI agent that helps citizens navigate legal workflows in India - filing FIRs, consumer complaints, RTI applications, and labour complaints.

## Features

- **Case Classification** - Automatically identifies the type of legal matter
- **Jurisdiction Resolution** - Determines the correct court/authority based on location
- **Multi-step Workflows** - Step-by-step guidance through legal processes
- **Document Generation** - Drafts FIRs, complaints, RTI applications
- **Authority Finding** - Locates relevant offices, portals, and helplines
- **Regional Language Support** - Translation to Hindi, Tamil, Telugu, and other Indian languages
- **Safety Guardrails** - Crisis detection and appropriate escalation

## Supported Case Types

- 🏪 Consumer Complaints (Consumer Protection Act, 2019)
- 🚔 Police FIRs (Indian Penal Code)
- 📄 RTI Applications (Right to Information Act)
- 👷 Labour Complaints (Industrial Disputes Act, Payment of Wages Act)

## Usage

1. Describe your legal situation (e.g., "I bought a defective phone and want to file a consumer complaint")
2. The agent will guide you through the appropriate workflow
3. Generate draft documents ready for submission

## Technical Details

- **Framework**: smolagents (CodeAgent)
- **LLM**: OpenCode Zen (minimax-m2.5-free)
- **RAG**: ChromaDB with legal knowledge corpus
- **UI**: Gradio

## Environment Variables

Set in HuggingFace Spaces secrets:
- `ZEN_API_KEY` - Your OpenCode Zen API key
- `ZEN_MODEL` - Model ID (default: minimax-m2.5-free)

## License

MIT License