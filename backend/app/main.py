from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .schemas import GenerateRequest, GenerateResponse, Plan
from .llm_client import client
from .dxf_generator import plan_to_dxf
from .utils import output_path
import time


app = FastAPI(title="Architect AI – MVP (dummy)")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/generate-or-modify-dxf", response_model=GenerateResponse)
async def generate_or_modify(req: GenerateRequest):
    if req.existing_plan is None:
        plan: Plan = client.generate(req.prompt)
    else:
        plan: Plan = client.modify(req.existing_plan, req.prompt)


    ts = int(time.time())
    dxf_file = output_path(f"plan_{ts}.dxf")
    plan_to_dxf(plan, dxf_file)


    return GenerateResponse(plan=plan, dxf_path=dxf_file)


# MVP-ben az OCR pipeline még nem kész, csak váz
@app.post("/image-to-dxf")
async def image_to_dxf():
    return {"status": "not_implemented_yet"}