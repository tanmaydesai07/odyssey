import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent / "tools"))

# Load .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

os.environ["TOKENIZERS_PARALLELISM"] = "0"

from zen_model import ZenModel
from case_classifier import CaseClassifierTool
# from jurisdiction_resolver import JurisdictionResolverTool
from intake_analyzer import IntakeAnalyzerTool, WorkflowPlannerTool
from legal_retriever import LegalRetrieverTool

print("Testing Legal Tools Directly...")
print("=" * 60)

# Initialize model
model = ZenModel(model_id=os.getenv("ZEN_MODEL", "minimax-m2.5-free"))

# Initialize tools
case_classifier = CaseClassifierTool()
# jurisdiction_resolver = JurisdictionResolverTool()
intake_analyzer = IntakeAnalyzerTool()
workflow_planner = WorkflowPlannerTool()
legal_retriever = LegalRetrieverTool()

# Test query
user_query = "I bought a laptop that stopped working after 1 month. How can I file a consumer complaint?"

print(f"\n1. Classifying case type...")
result1 = case_classifier.forward(user_query)
print(f"Result: {result1[:500]}...")

print(f"\n2. Analyzing intake...")
result2 = intake_analyzer.forward(user_query, "consumer")
print(f"Result: {result2}")

print(f"\n3. Workflow planning...")
result3 = workflow_planner.forward("consumer", "Delhi", "{}")
print(f"Result: {result3}")

print(f"\n4. Retrieving legal info...")
result4 = legal_retriever.forward("consumer complaint filing process India", top_k=3)
print(f"Result: {result4[:800]}...")

print("\n" + "=" * 60)
print("All tools working!")
print("=" * 60)