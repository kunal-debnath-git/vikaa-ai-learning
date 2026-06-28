from fastapi import APIRouter, HTTPException
import json
import pathlib

router = APIRouter()

_BASE = pathlib.Path(__file__).parent.parent.parent / "_Databricks_GenAI_MCQ"
MCQ_PATH      = _BASE / "mcqs.json"
SCENARIO_PATH = _BASE / "scenarios_updated.json"


@router.get("/databricks/mcqs")
async def get_databricks_mcqs():
    if not MCQ_PATH.exists():
        raise HTTPException(status_code=404, detail="MCQ dataset not found")
    with open(MCQ_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/databricks/scenarios")
async def get_databricks_scenarios():
    if not SCENARIO_PATH.exists():
        raise HTTPException(status_code=404, detail="Scenarios dataset not found")
    with open(SCENARIO_PATH, "r", encoding="utf-8") as f:
        return json.load(f)
